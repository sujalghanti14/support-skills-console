#!/usr/bin/env python3
"""Deterministic guard for outbound support replies.

Fails if the draft:
  * states a money amount, percentage, or time window that does not appear
    in the CURRENT policy document (read fresh on every run),
  * writes money/percentages in words (which would dodge the check),
  * uses a banned phrase from the tone-of-voice guide.

Usage:
  python check_reply.py draft.txt --policy company-docs/refund-pricing-policy.md
                        [--tone references/tone-of-voice.md] [--allow 87.40 --allow "1 business day"]

--allow  whitelists figures that come from the customer's own account/ticket data
         (e.g. the exact amount they were charged). A bare number allows that value
         in any form; a phrase like "1 business day" allows only that figure.
Exit code 0 = PASS, 1 = FAIL.
"""
import argparse
import re
import sys
from pathlib import Path

DEFAULT_TONE = Path(__file__).resolve().parent.parent / "references" / "tone-of-voice.md"

NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
MONEY_RE = re.compile(rf"(?:US\$|\$|USD\s?)\s?({NUM})|({NUM})\s?(?:dollars|USD)\b", re.I)
PCT_RE = re.compile(rf"({NUM})\s?(?:%|percent\b|per cent\b)", re.I)
UNIT = r"(business[\s-]days?|days?|weeks?|months?|years?|hours?|minutes?)"
DUR_RE = re.compile(
    rf"\b(\d+(?:\.\d+)?)(?:\s?(?:-|–|—|to)\s?(\d+(?:\.\d+)?))?[\s-]+{UNIT}\b", re.I)
WORD_NUM = (r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|"
            r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand")
WORD_MONEY_RE = re.compile(rf"\b(?:{WORD_NUM})\b[\w\s-]{{0,20}}?\b(dollars?|bucks|percent)\b", re.I)


def norm_unit(u: str) -> str:
    u = u.lower().replace("-", " ")
    u = re.sub(r"\s+", " ", u)
    return u[:-1] if u.endswith("s") else u


def to_float(s: str) -> float:
    return float(s.replace(",", ""))


def extract(text: str) -> list[tuple[str, tuple, str]]:
    """Return (kind, values, matched_text). A range like '5-10 days' is ONE figure with two
    values; it is only valid if every value is valid. kind: money | percent | duration:<unit>."""
    text = text.replace("’", "'")
    out = []
    for m in MONEY_RE.finditer(text):
        out.append(("money", (to_float(m.group(1) or m.group(2)),), m.group(0).strip()))
    for m in PCT_RE.finditer(text):
        out.append(("percent", (to_float(m.group(1)),), m.group(0).strip()))
    for m in DUR_RE.finditer(text):
        kind = f"duration:{norm_unit(m.group(3))}"
        vals = (to_float(m.group(1)),) + ((to_float(m.group(2)),) if m.group(2) else ())
        out.append((kind, vals, m.group(0).strip()))
    return out


def banned_phrases(tone_text: str) -> list[str]:
    m = re.search(r"^##\s*Banned phrases\s*$(.*?)(?=^##\s|\Z)", tone_text, re.M | re.S | re.I)
    if not m:
        return []
    return [ln.strip()[2:].strip().lower() for ln in m.group(1).splitlines()
            if ln.strip().startswith("- ")]


def check(draft: str, policy: str, tone: str, allow: list[str] | None = None) -> dict:
    """Pure check used by both the CLI and the web app.
    Returns {"passed": bool, "ok": [...], "problems": [...], "warnings": [...]}."""
    policy_figs = {(k, v) for k, vs, _ in extract(policy) for v in vs}
    allowed_any, allowed_exact, warnings = set(), set(), []
    for item in allow or []:
        if not item.strip():
            continue
        figs = extract(item)
        if figs:
            allowed_exact |= {(k, v) for k, vs, _ in figs for v in vs}
        else:
            try:
                allowed_any.add(to_float(item.strip().lstrip("$").rstrip("%")))
            except ValueError:
                warnings.append(f"could not parse allow value '{item}'")

    problems, ok = [], []
    for kind, vals, txt in extract(draft):
        bad = [v for v in vals if (kind, v) not in policy_figs
               and (kind, v) not in allowed_exact and v not in allowed_any]
        if not bad:
            src = "in policy" if all((kind, v) in policy_figs for v in vals) else "allowed (customer data)"
            ok.append(f"{txt!r} -> {src}")
        else:
            problems.append(f"FIGURE NOT IN POLICY: {txt!r}. The current policy has no "
                            f"{' or '.join(f'{v:g}' for v in bad)} for this. Remove it, use the policy's "
                            "figure, or allow it if it comes from the customer's own account.")

    for m in WORD_MONEY_RE.finditer(draft):
        problems.append(f"FIGURE IN WORDS: {m.group(0)!r}. Write money/percentages in digits.")

    low = re.sub(r"\s+", " ", draft.lower().replace("’", "'"))
    for phrase in banned_phrases(tone):
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", low):
            problems.append(f"BANNED PHRASE: {phrase!r}")

    return {"passed": not problems, "ok": ok, "problems": problems, "warnings": warnings}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--policy", required=True)
    ap.add_argument("--tone", default=str(DEFAULT_TONE))
    ap.add_argument("--allow", action="append", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    r = check(Path(a.draft).read_text(encoding="utf-8"),
              Path(a.policy).read_text(encoding="utf-8"),
              Path(a.tone).read_text(encoding="utf-8"), a.allow)
    for w in r["warnings"]:
        print(f"warning: {w}")
    for line in r["ok"]:
        print(f"  ok   {line}")
    if not r["passed"]:
        print("FAIL")
        for p in r["problems"]:
            print(f"  - {p}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
