"""End-to-end browser tests: real server + headless Chromium via Playwright."""
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import WSGIRequestHandler, make_server

from helpers import POLICY, webapp


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


class E2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.policy = cls.tmp / "policy.md"
        cls.policy.write_text(POLICY, encoding="utf-8")
        cls.server = make_server("127.0.0.1", 0, webapp.create_app({"POLICY_PATH": cls.policy}),
                                 request_handler=QuietHandler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.policy.write_text(POLICY, encoding="utf-8")
        self.ctx = self.browser.new_context()
        self.page = self.ctx.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.on("console", lambda m: m.type == "error" and self.errors.append(m.text))
        self.page.goto(self.base)

    def tearDown(self):
        self.ctx.close()
        self.assertEqual(self.errors, [], "browser console/page errors")

    def tab(self, name):
        self.page.get_by_role("tab", name=name).click()

    # ---------- navigation ----------
    def test_tabs_switch_and_aria(self):
        p = self.page
        expect(p.locator("#panel-triage")).to_be_visible()
        expect(p.locator("#panel-reply")).to_be_hidden()
        self.tab("Reply check")
        expect(p.locator("#panel-reply")).to_be_visible()
        expect(p.locator("#panel-triage")).to_be_hidden()
        expect(p.get_by_role("tab", name="Reply check")).to_have_attribute("aria-selected", "true")

    def test_keyboard_arrow_navigation(self):
        p = self.page
        p.get_by_role("tab", name="Triage").focus()
        p.keyboard.press("ArrowRight")
        expect(p.locator("#panel-reply")).to_be_visible()
        p.keyboard.press("ArrowLeft"); p.keyboard.press("ArrowLeft")
        expect(p.locator("#panel-bugs")).to_be_visible()   # wraps around

    def test_selected_tab_survives_reload(self):
        self.tab("QA report")
        self.page.reload()
        expect(self.page.locator("#panel-qa")).to_be_visible()

    # ---------- triage ----------
    def test_triage_example_validates(self):
        p = self.page
        p.click("#triage-example")
        p.click("#triage-run")
        expect(p.locator("#triage-result .banner.ok")).to_contain_text("Valid")

    def test_triage_invalid_and_bad_json(self):
        p = self.page
        p.click("#triage-example")
        p.fill("#triage-input", p.input_value("#triage-input").replace('"bug"', '"refunds"'))
        p.click("#triage-run")
        expect(p.locator("#triage-result .banner.bad")).to_contain_text("Invalid")
        expect(p.locator("#triage-result li")).to_contain_text(["unknown category 'refunds'"])
        p.fill("#triage-input", "{oops")
        p.click("#triage-run")
        expect(p.locator("#triage-result li")).to_contain_text(["invalid JSON"])

    def test_triage_empty_and_server_400(self):
        p = self.page
        p.click("#triage-run")
        expect(p.locator("#triage-result .banner.warn")).to_contain_text("Paste a triage record")
        p.fill("#triage-input", "[1,2]")   # valid JSON, not an object -> API 400
        p.click("#triage-run")
        expect(p.locator("#triage-result .banner.bad")).to_contain_text("must be a JSON object")
        # The browser logs every non-2xx response as a console error; this 400 is expected.
        self.errors = [e for e in self.errors if "status of 400" not in e]

    # ---------- reply ----------
    def test_reply_example_fails_then_fixed_draft_passes(self):
        p = self.page
        self.tab("Reply check")
        p.click("#reply-example")
        p.click("#reply-run")
        expect(p.locator("#reply-result .banner.bad")).to_contain_text("FAIL")
        problems = p.locator("#reply-result li.bad")
        expect(problems.filter(has_text="30 days")).to_have_count(1)
        expect(problems.filter(has_text="fifty dollar")).to_have_count(1)
        expect(problems.filter(has_text="rest assured")).to_have_count(1)

        p.fill("#reply-input", "Hi Dana,\n\nI've refunded your $87.40 duplicate charge. It lands in 5-10 business days.\n\n- Sam")
        p.click("#reply-run")
        expect(p.locator("#reply-result li.bad")).to_contain_text(["$87.40"])
        p.fill("#reply-allow", "87.40")
        p.click("#reply-run")
        expect(p.locator("#reply-result .banner.ok")).to_contain_text("PASS")
        expect(p.locator("#reply-result li.ok")).to_have_count(2)

    def test_reply_uses_live_policy(self):
        p = self.page
        self.tab("Reply check")
        p.fill("#reply-input", "Monthly plans get a full refund within 14 days.")
        p.click("#reply-run")
        expect(p.locator("#reply-result .banner.ok")).to_be_visible()
        self.policy.write_text(POLICY.replace("within 14 days", "within 7 days"), encoding="utf-8")
        p.click("#reply-run")
        expect(p.locator("#reply-result .banner.bad")).to_be_visible()
        p.click("#policy-toggle")
        expect(p.locator("#policy-view")).to_contain_text("within 7 days")
        expect(p.locator("#policy-toggle")).to_have_attribute("aria-expanded", "true")
        p.click("#policy-toggle")
        expect(p.locator("#policy-view")).to_be_hidden()

    def test_user_input_is_never_rendered_as_html(self):
        p = self.page
        self.tab("Reply check")
        p.fill("#reply-input", 'refund of $999 <img src=x onerror="window.__xss=1"> dear customer')
        p.click("#reply-run")
        expect(p.locator("#reply-result .banner.bad")).to_be_visible()
        self.assertEqual(p.locator("#reply-result img").count(), 0)
        self.assertIsNone(p.evaluate("window.__xss"))

    # ---------- QA ----------
    def test_qa_example_builds_report_and_downloads(self):
        p = self.page
        self.tab("QA report")
        p.click("#qa-example")
        p.click("#qa-run")
        expect(p.locator("#qa-result .banner")).to_contain_text("no_next_step")
        expect(p.locator("#qa-result .stat").nth(1)).to_contain_text("1/4")
        expect(p.locator("#qa-result pre")).to_contain_text("# Weekly Support QA Report")
        with p.expect_download() as dl:
            p.click("#qa-download")
        self.assertEqual(dl.value.suggested_filename, "qa-report.md")
        self.assertIn("Pass rate", Path(dl.value.path()).read_text(encoding="utf-8"))

    def test_qa_validation_errors(self):
        p = self.page
        self.tab("QA report")
        p.fill("#qa-input", '[{"ticket_id":"T-9","team":"x","agent":"y","scores":{"resolution":5},"tags":["rude"],"evidence":{}}]')
        p.click("#qa-run")
        expect(p.locator("#qa-result .banner.bad")).to_contain_text("Validation failed")
        expect(p.locator("#qa-result li").filter(has_text="unknown tag 'rude'")).to_have_count(1)

    # ---------- bugs ----------
    def test_bug_search_known_issue(self):
        p = self.page
        self.tab("Known issues")
        p.fill("#bugs-input", "CSV export keeps timing out, 80k rows")
        p.press("#bugs-input", "Enter")
        first = p.locator("#bugs-result .result-card").first
        expect(first).to_contain_text("KI-412")
        expect(first.locator(".pill")).to_have_text("KNOWN_OPEN")

    def test_bug_search_weak_none_and_empty(self):
        p = self.page
        self.tab("Known issues")
        p.click("#bugs-run")
        expect(p.locator("#bugs-result .banner.warn")).to_contain_text("Describe the symptom")
        p.fill("#bugs-input", "the and it is")
        p.click("#bugs-run")
        expect(p.locator("#bugs-result .banner.warn")).to_contain_text("No searchable words")
        p.fill("#bugs-input", "zzzqqq")
        p.click("#bugs-run")
        expect(p.locator("#bugs-result .banner")).to_contain_text("likely a NEW bug")

    # ---------- robustness ----------
    def test_server_failure_is_shown_and_button_reenabled(self):
        p = self.page
        p.route("**/api/bugs/search", lambda r: r.fulfill(status=500, body="boom"))
        self.tab("Known issues")
        p.fill("#bugs-input", "csv export")
        p.click("#bugs-run")
        expect(p.locator("#bugs-result .banner.bad")).to_contain_text("Request failed (500)")
        expect(p.locator("#bugs-run")).to_be_enabled()
        # A failed resource load logs a console error by design; don't count it.
        self.errors = [e for e in self.errors if "500" not in e]

    def test_mobile_width_has_no_horizontal_scroll(self):
        p = self.page
        p.set_viewport_size({"width": 375, "height": 800})
        for name in ("Triage", "Reply check", "QA report", "Known issues"):
            self.tab(name)
            if name == "QA report":
                p.click("#qa-example"); p.click("#qa-run")
                expect(p.locator("#qa-result pre")).to_be_visible()
            overflow = p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            self.assertLessEqual(overflow, 0, f"horizontal overflow on {name}")


if __name__ == "__main__":
    unittest.main()
