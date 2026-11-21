#!/usr/bin/env python3
"""Validate a triage record against the routing table.

Usage: python validate_triage.py triage.json [--routing path/to/routing.json]
Exit 0 and print OK if valid; exit 1 and list problems otherwise.
"""
import argparse
import json
import sys
from pathlib import Path

DEFAULT_ROUTING = Path(__file__).resolve().parent.parent / "references" / "routing.json"
REQUIRED = ["ticket_id", "category", "team", "priority", "escalation",
            "confidence", "summary", "reasoning"]


def validate(rec: dict, routing: dict) -> list[str]:
    errs = []
    for k in REQUIRED:
        if k not in rec:
            errs.append(f"missing field: {k}")
    if errs:
        return errs

    cats = routing["categories"]
    escs = routing["escalation"]
    if rec["category"] not in cats:
        errs.append(f"unknown category '{rec['category']}'. Valid: {sorted(cats)}")
    if rec["priority"] not in routing["priorities"]:
        errs.append(f"invalid priority '{rec['priority']}'. Valid: {routing['priorities']}")

    esc = rec["escalation"]
    if esc is not None and esc not in escs:
        errs.append(f"invalid escalation '{esc}'. Valid: {sorted(escs)} or null")

    # Team must be consistent with category / escalation.
    if esc in escs:
        expected = escs[esc]["team"]
        if rec["team"] != expected:
            errs.append(f"escalation '{esc}' must route to team '{expected}', got '{rec['team']}'")
        if rec["priority"] != "urgent":
            errs.append("escalated tickets must have priority 'urgent'")
    elif rec["category"] in cats:
        expected = cats[rec["category"]]["team"]
        if rec["team"] != expected:
            errs.append(f"category '{rec['category']}' routes to '{expected}', got '{rec['team']}'")

    c = rec["confidence"]
    if isinstance(c, bool) or not isinstance(c, (int, float)) or not 0 <= c <= 1:
        errs.append("confidence must be a number between 0 and 1")
    if not isinstance(rec["summary"], str) or not rec["summary"].strip():
        errs.append("summary must be a non-empty string")
    elif len(rec["summary"]) > 200:
        errs.append(f"summary is {len(rec['summary'])} chars; max 200")
    if not isinstance(rec["reasoning"], str) or not rec["reasoning"].strip():
        errs.append("reasoning must be a non-empty string")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--routing", default=str(DEFAULT_ROUTING))
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    routing = json.loads(Path(a.routing).read_text(encoding="utf-8"))
    try:
        rec = json.loads(Path(a.record).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"INVALID JSON: {e}")
        return 1
    errs = validate(rec, routing)
    if errs:
        print("FAIL")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
