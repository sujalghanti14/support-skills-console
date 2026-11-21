"""Unit tests for the skill scripts' pure functions (the logic the web app calls)."""
import unittest

from helpers import CHANGELOG, GOOD_TRIAGE, POLICY, ROUTING, RUBRIC, TONE, grade, webapp

reply, triage, qa, bugs = webapp.reply, webapp.triage, webapp.qa, webapp.bugs


class ReplyExtractTests(unittest.TestCase):
    def test_money_formats(self):
        vals = {v for k, vs, _ in reply.extract("$29, US$ 1,200.50, 40 dollars, USD 12") for v in vs if k == "money"}
        self.assertEqual(vals, {29.0, 1200.5, 40.0, 12.0})

    def test_percent_and_range(self):
        figs = reply.extract("save 20% or 10 percent, within 5-10 business days")
        self.assertIn(("percent", (20.0,), "20%"), figs)
        self.assertIn(("percent", (10.0,), "10 percent"), figs)
        self.assertIn(("duration:business day", (5.0, 10.0), "5-10 business days"), figs)

    def test_ignores_plain_numbers_and_dates(self):
        self.assertEqual(reply.extract("We have 40 people, see you Nov 3, day 94"), [])


class ReplyCheckTests(unittest.TestCase):
    def check(self, draft, allow=None, policy=POLICY):
        return reply.check(draft, policy, TONE, allow)

    def test_policy_figures_pass(self):
        r = self.check("Hi Jo, refunds land in 5-10 business days; annual saves 20% on $29.")
        self.assertTrue(r["passed"], r["problems"])

    def test_figure_not_in_policy_fails(self):
        r = self.check("Hi Jo, full refund within 30 days.")
        self.assertFalse(r["passed"])
        self.assertTrue(any("30 days" in p for p in r["problems"]))

    def test_range_with_one_bad_endpoint_fails(self):
        r = self.check("Refunds arrive in 3-5 business days.")
        self.assertFalse(r["passed"])
        self.assertEqual(len(r["problems"]), 1)
        self.assertIn("3", r["problems"][0])

    def test_allow_bare_number(self):
        self.assertFalse(self.check("Your $87.40 charge.")["passed"])
        self.assertTrue(self.check("Your $87.40 charge.", ["87.40"])["passed"])

    def test_allow_exact_phrase_is_kind_specific(self):
        self.assertTrue(self.check("Reply within 1 business day.", ["1 business day"])["passed"])
        self.assertFalse(self.check("A $1 fee.", ["1 business day"])["passed"])

    def test_blank_and_unparseable_allow(self):
        r = self.check("Hello", ["", "  ", "abc"])
        self.assertTrue(r["passed"])
        self.assertEqual(r["warnings"], ["could not parse allow value 'abc'"])

    def test_money_in_words(self):
        for draft in ("a fifty dollar credit", "twenty dollars back", "ten percent off"):
            with self.subTest(draft=draft):
                r = self.check(draft)
                self.assertTrue(any("IN WORDS" in p for p in r["problems"]), r)

    def test_banned_phrases_case_and_whitespace(self):
        r = self.check("Hi,\nWe   APOLOGIZE for any\ninconvenience.")
        self.assertIn("BANNED PHRASE: 'we apologize for any inconvenience'", r["problems"])

    def test_banned_phrase_needs_word_boundary(self):
        self.assertTrue(self.check("That was unkindly put, sorry.")["passed"])

    def test_live_policy_change(self):
        draft = "Monthly plans: full refund within 14 days."
        self.assertTrue(self.check(draft)["passed"])
        changed = POLICY.replace("within 14 days", "within 7 days")
        self.assertFalse(self.check(draft, policy=changed)["passed"])

    def test_banned_list_parsed_from_tone_guide(self):
        phrases = reply.banned_phrases(TONE)
        self.assertIn("rest assured", phrases)
        self.assertGreater(len(phrases), 10)


class TriageTests(unittest.TestCase):
    def v(self, **changes):
        return triage.validate({**GOOD_TRIAGE, **changes}, ROUTING)

    def test_good_record(self):
        self.assertEqual(self.v(), [])

    def test_non_escalated_routes_to_category_team(self):
        self.assertEqual(self.v(escalation=None, team="tier2-support", priority="high"), [])
        self.assertTrue(self.v(escalation=None, team="billing-ops", priority="high"))

    def test_unknown_category_and_priority(self):
        errs = self.v(category="refunds", priority="asap")
        self.assertTrue(any("unknown category" in e for e in errs))
        self.assertTrue(any("invalid priority" in e for e in errs))

    def test_escalation_must_be_urgent_and_right_team(self):
        errs = self.v(escalation="legal", team="incident-oncall", priority="high")
        self.assertTrue(any("must route to team 'legal'" in e for e in errs))
        self.assertTrue(any("urgent" in e for e in errs))

    def test_invalid_escalation(self):
        self.assertTrue(any("invalid escalation" in e for e in self.v(escalation="fire")))

    def test_confidence_bounds_and_bool(self):
        for c in (-0.1, 1.01, "0.5", True, None):
            with self.subTest(c=c):
                self.assertTrue(any("confidence" in e for e in self.v(confidence=c)))
        self.assertEqual(self.v(confidence=0), [])
        self.assertEqual(self.v(confidence=1), [])

    def test_summary_rules(self):
        self.assertTrue(any("max 200" in e for e in self.v(summary="x" * 201)))
        self.assertEqual(self.v(summary="x" * 200), [])
        self.assertTrue(any("summary" in e for e in self.v(summary="  ")))

    def test_missing_fields(self):
        rec = dict(GOOD_TRIAGE)
        del rec["team"], rec["reasoning"]
        self.assertEqual(sorted(triage.validate(rec, ROUTING)),
                         ["missing field: reasoning", "missing field: team"])


class QATests(unittest.TestCase):
    def test_parse_rubric(self):
        criteria, tags, autofail = qa.parse_rubric(RUBRIC)
        self.assertEqual(criteria, {"resolution": 3, "accuracy": 3, "tone": 2, "ownership": 1, "efficiency": 1})
        self.assertEqual(autofail, {"wrong_policy_figure", "missed_escalation", "security_data_exposed"})
        self.assertIn("no_next_step", tags)

    def test_bad_rubric_raises_not_exits(self):
        with self.assertRaises(ValueError):
            qa.parse_rubric("# empty")

    def test_pass_rule(self):
        r = qa.aggregate([
            grade("A"),                                                 # pass
            grade("B", accuracy=1, tags=["wrong_policy_figure"]),       # auto-fail
            grade("C", efficiency=1, tags=["sla_breach"]),              # criterion at 1 -> fail
            grade("D", resolution=3, accuracy=3, tone=3, ownership=3, efficiency=3),  # exactly 3.0 -> pass
            grade("E", resolution=2, accuracy=3, tone=3, ownership=3, efficiency=3),  # 2.7 -> fail
        ], RUBRIC)
        self.assertEqual(r["errors"], [])
        self.assertEqual((r["n"], r["passes"]), (5, 2))
        self.assertIn("| B | billing-ops | sam | 4 | 1 | 4 | 4 | 4 |", r["report_md"])
        self.assertIn("FAIL (auto)", r["report_md"])

    def test_patterns_threshold_and_order(self):
        gs = [grade(f"T{i}") for i in range(20)]
        gs[0] = grade("T0", tags=["no_next_step"]); gs[1] = grade("T1", tags=["no_next_step"])
        gs[2] = grade("T2", tags=["robotic_tone"])                  # 1/20 = 5%: not a pattern
        gs[3] = grade("T3", accuracy=1, tags=["wrong_policy_figure"]); gs[4] = grade("T4", accuracy=1, tags=["wrong_policy_figure"])
        r = qa.aggregate(gs, RUBRIC)
        self.assertEqual(r["patterns"], ["wrong_policy_figure", "no_next_step"])  # auto-fail first

    def test_validation_errors(self):
        cases = {
            "unknown tag": grade(tags=["rude"]),
            "no evidence": grade(tags=["no_next_step"], evidence={}),
            "integer 1-4": grade(tone=5),
            "integer 1-4 ": grade(tone=True),
            "requires tag": grade(accuracy=1),
            "missing 'agent'": {k: v for k, v in grade().items() if k != "agent"},
            "must be objects": {**grade(), "tags": "x"},
            "JSON object": "not a dict",
        }
        for needle, g in cases.items():
            with self.subTest(needle=needle):
                errs = qa.aggregate([g], RUBRIC)["errors"]
                self.assertTrue(any(needle.strip() in e for e in errs), errs)

    def test_empty(self):
        self.assertEqual(qa.aggregate([], RUBRIC)["errors"], ["no grades supplied"])

    def test_parse_grades_json_and_jsonl(self):
        self.assertEqual(len(qa.parse_grades('[{"a":1},{"a":2}]')), 2)
        self.assertEqual(len(qa.parse_grades('{"a":1}\n\n{"a":2}\n')), 2)
        with self.assertRaises(ValueError):
            qa.parse_grades("[{oops")


class ChangelogTests(unittest.TestCase):
    def test_known_issue_ranks_first(self):
        r = bugs.search(CHANGELOG, "CSV export keeps timing out with 80k rows")
        self.assertFalse(r["weak"])
        self.assertEqual((r["results"][0]["ki"], r["results"][0]["status"]), ("KI-412", "KNOWN_OPEN"))

    def test_fixed_entry(self):
        top = bugs.search(CHANGELOG, "2FA code rejected")["results"][0]
        self.assertEqual(top["status"], "FIXED")
        self.assertIn("Two-factor", top["text"])

    def test_synonyms(self):
        self.assertEqual(bugs.search(CHANGELOG, "android app closes on big picture")["results"][0]["ki"], "KI-409")

    def test_weak_and_no_terms(self):
        self.assertTrue(bugs.search(CHANGELOG, "Gantt drag and drop reorders wrong row")["weak"])
        r = bugs.search(CHANGELOG, "the and it is")
        self.assertEqual((r["terms"], r["results"]), ([], []))
        self.assertEqual(bugs.search(CHANGELOG, "zzzqqq")["results"], [])

    def test_top_limits_results(self):
        self.assertEqual(len(bugs.search(CHANGELOG, "login email export crash invoice", top=2)["results"]), 2)

    def test_entries_parsed(self):
        entries = bugs.parse(CHANGELOG)
        self.assertEqual(len(entries), 8)
        self.assertTrue(all(e["version"] and e["section"] for e in entries))


if __name__ == "__main__":
    unittest.main()
