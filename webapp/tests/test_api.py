"""API tests: every endpoint through Flask's test client, including bad input."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import GOOD_TRIAGE, POLICY, grade, webapp


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        # Copy the policy to a temp file so tests can edit it without touching the real one.
        self.tmp = Path(tempfile.mkdtemp())
        self.policy = self.tmp / "policy.md"
        self.policy.write_text(POLICY, encoding="utf-8")
        self.app = webapp.create_app({"POLICY_PATH": self.policy, "TESTING": True})
        self.c = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def post(self, url, payload):
        return self.c.post(url, json=payload)


class BasicsTests(ApiTestCase):
    def test_health(self):
        self.assertEqual(self.c.get("/api/health").get_json(), {"status": "ok"})

    def test_index_and_static(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Support Skills Console", r.data)
        r.close()
        for path in ("/static/app.js", "/static/style.css"):
            r = self.c.get(path)
            self.assertEqual(r.status_code, 200, path)
            r.close()

    def test_unknown_route_is_json_404(self):
        r = self.c.get("/api/nope")
        self.assertEqual((r.status_code, r.get_json()), (404, {"error": "not found"}))

    def test_wrong_method_is_json_405(self):
        r = self.c.get("/api/reply/check")
        self.assertEqual(r.status_code, 405)
        self.assertIn("error", r.get_json())

    def test_non_json_body_is_400(self):
        for url in ("/api/triage/validate", "/api/reply/check", "/api/qa/aggregate", "/api/bugs/search"):
            with self.subTest(url=url):
                r = self.c.post(url, data="hello", content_type="text/plain")
                self.assertEqual(r.status_code, 400)
                r = self.c.post(url, json=[1, 2])
                self.assertEqual(r.status_code, 400)

    def test_oversized_request_is_413(self):
        r = self.c.post("/api/reply/check", data=json.dumps({"draft": "x" * (2 * 1024 * 1024)}),
                        content_type="application/json")
        self.assertEqual(r.status_code, 413)

    def test_security_headers(self):
        for path in ("/", "/api/health", "/api/nope"):
            with self.subTest(path=path):
                r = self.c.get(path)
                self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
                self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(r.headers["X-Frame-Options"], "DENY")
                r.close()

    def test_routing_and_policy(self):
        self.assertIn("billing", self.c.get("/api/routing").get_json()["categories"])
        self.assertIn("Refund", self.c.get("/api/policy").get_json()["text"])


class TriageApiTests(ApiTestCase):
    url = "/api/triage/validate"

    def test_valid_object_and_string(self):
        for rec in (GOOD_TRIAGE, json.dumps(GOOD_TRIAGE)):
            r = self.post(self.url, {"record": rec})
            self.assertEqual(r.get_json(), {"valid": True, "errors": []})

    def test_invalid_record(self):
        body = self.post(self.url, {"record": {**GOOD_TRIAGE, "category": "x"}}).get_json()
        self.assertFalse(body["valid"])
        self.assertTrue(body["errors"])

    def test_bad_json_string_reports_error(self):
        body = self.post(self.url, {"record": "{not json"}).get_json()
        self.assertFalse(body["valid"])
        self.assertIn("invalid JSON", body["errors"][0])

    def test_record_wrong_type_is_400(self):
        for rec in (None, 5, [1], '"a string"'):
            with self.subTest(rec=rec):
                self.assertEqual(self.post(self.url, {"record": rec}).status_code, 400)


class ReplyApiTests(ApiTestCase):
    url = "/api/reply/check"

    def test_pass_and_fail(self):
        self.assertTrue(self.post(self.url, {"draft": "Refunds take 5-10 business days."}).get_json()["passed"])
        body = self.post(self.url, {"draft": "Dear customer, refund within 30 days."}).get_json()
        self.assertFalse(body["passed"])
        self.assertEqual(len(body["problems"]), 2)

    def test_allow_as_list_or_comma_string(self):
        for allow in (["87.40"], "87.40, 12.5"):
            with self.subTest(allow=allow):
                self.assertTrue(self.post(self.url, {"draft": "Your $87.40 charge.", "allow": allow}).get_json()["passed"])

    def test_bad_inputs_are_400(self):
        for payload in ({}, {"draft": "   "}, {"draft": 5}, {"draft": "hi", "allow": [1]},
                        {"draft": "hi", "allow": {"a": 1}}, {"draft": "x" * 200_001}):
            with self.subTest(payload=str(payload)[:40]):
                r = self.post(self.url, payload)
                self.assertEqual(r.status_code, 400)
                self.assertIn("error", r.get_json())

    def test_policy_is_read_live_on_each_request(self):
        draft = {"draft": "Monthly plans: full refund within 14 days."}
        self.assertTrue(self.post(self.url, draft).get_json()["passed"])
        self.policy.write_text(POLICY.replace("within 14 days", "within 7 days"), encoding="utf-8")
        self.assertFalse(self.post(self.url, draft).get_json()["passed"])
        self.assertIn("within 7 days", self.c.get("/api/policy").get_json()["text"])


class QaApiTests(ApiTestCase):
    url = "/api/qa/aggregate"

    def test_list_and_string_and_jsonl(self):
        gs = [grade("A"), grade("B", accuracy=1, tags=["wrong_policy_figure"])]
        for payload in (gs, json.dumps(gs), "\n".join(json.dumps(g) for g in gs)):
            with self.subTest(kind=type(payload).__name__):
                body = self.post(self.url, {"grades": payload}).get_json()
                self.assertEqual((body["errors"], body["n"], body["passes"]), ([], 2, 1))
                self.assertIn("# Weekly Support QA Report", body["report_md"])

    def test_validation_errors_returned_not_500(self):
        body = self.post(self.url, {"grades": [grade(tags=["rude"])]}).get_json()
        self.assertTrue(any("unknown tag" in e for e in body["errors"]))
        body = self.post(self.url, {"grades": "[{oops"}).get_json()
        self.assertIn("invalid JSON", body["errors"][0])
        body = self.post(self.url, {"grades": []}).get_json()
        self.assertEqual(body["errors"], ["no grades supplied"])

    def test_bad_inputs_are_400(self):
        for payload in ({}, {"grades": "  "}, {"grades": {"a": 1}}, {"grades": 3}, {"grades": '{"a":1}x'}):
            with self.subTest(payload=payload):
                r = self.post(self.url, payload)
                # '{"a":1}x' is a JSONL line that fails to parse -> reported as error, 200
                if payload.get("grades") == '{"a":1}x':
                    self.assertIn("invalid JSON", r.get_json()["errors"][0])
                else:
                    self.assertEqual(r.status_code, 400)

    def test_jsonl_scalar_line_reports_error(self):
        r = self.post(self.url, {"grades": "5"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["errors"], ["#0: each grade must be a JSON object"])


class BugsApiTests(ApiTestCase):
    url = "/api/bugs/search"

    def test_search(self):
        body = self.post(self.url, {"query": "csv export timeout 80k rows"}).get_json()
        self.assertEqual(body["results"][0]["ki"], "KI-412")
        self.assertLessEqual(len(body["results"]), 5)

    def test_top(self):
        body = self.post(self.url, {"query": "login email export crash invoice", "top": 1}).get_json()
        self.assertEqual(len(body["results"]), 1)

    def test_bad_inputs_are_400(self):
        for payload in ({}, {"query": ""}, {"query": 3}, {"query": "x", "top": 0},
                        {"query": "x", "top": 51}, {"query": "x", "top": "5"}, {"query": "x", "top": True}):
            with self.subTest(payload=payload):
                self.assertEqual(self.post(self.url, payload).status_code, 400)


if __name__ == "__main__":
    unittest.main()
