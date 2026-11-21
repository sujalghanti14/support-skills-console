import sys
from pathlib import Path

WEBAPP = Path(__file__).resolve().parent.parent
ROOT = WEBAPP.parent
if str(WEBAPP) not in sys.path:
    sys.path.insert(0, str(WEBAPP))

import app as webapp  # noqa: E402

POLICY = (ROOT / "company-docs" / "refund-pricing-policy.md").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "company-docs" / "CHANGELOG.md").read_text(encoding="utf-8")
TONE = webapp.DEFAULTS["TONE_PATH"].read_text(encoding="utf-8")
RUBRIC = webapp.DEFAULTS["RUBRIC_PATH"].read_text(encoding="utf-8")
ROUTING = __import__("json").loads(webapp.DEFAULTS["ROUTING_PATH"].read_text(encoding="utf-8"))

GOOD_TRIAGE = {
    "ticket_id": "T-1", "category": "bug", "team": "incident-oncall", "priority": "urgent",
    "escalation": "outage", "confidence": 0.9, "summary": "Workspace-wide 502s.",
    "reasoning": "'none of the 40 people' indicates an outage.",
}


def grade(tid="T-1", team="billing-ops", agent="sam", tags=None, evidence=None, **scores):
    s = {"resolution": 4, "accuracy": 4, "tone": 4, "ownership": 4, "efficiency": 4}
    s.update(scores)
    tags = tags or []
    return {"ticket_id": tid, "team": team, "agent": agent, "scores": s, "tags": tags,
            "evidence": evidence if evidence is not None else {t: "quote" for t in tags}}
