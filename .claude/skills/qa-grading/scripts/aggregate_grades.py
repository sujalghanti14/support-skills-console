#!/usr/bin/env python3
"""Validate QA grades against the rubric and aggregate them into a report skeleton.

Usage: python aggregate_grades.py grades.json [--rubric rubric.md] [--out qa-report.md]

The rubric markdown is the single source of truth: criteria ids/weights come from
headings like '### accuracy — Accuracy (weight 3)', tags from lines like
'- `tag_id` — (auto-fail) description'.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_RUBRIC = Path(__file__).resolve().parent.parent / "references" / "rubric.md"
PASS_THRESHOLD = 3.0
PATTERN_MIN_COUNT = 2
PATTERN_MIN_SHARE = 0.10


def parse_rubric(text: str):
    criteria = {m.group(1): int(m.group(2)) for m in
                re.finditer(r"^###\s+(\w+)\s+—.*\(weight\s+(\d+)\)", text, re.M)}
    tags, autofail = set(), set()
    for m in re.finditer(r"^-\s+`(\w+)`\s+—\s+(.*)$", text, re.M):
        tags.add(m.group(1))
        if "(auto-fail)" in m.group(2):
            autofail.add(m.group(1))
    if not criteria or not tags:
        raise ValueError("could not parse criteria/tags from rubric")
    return criteria, tags, autofail


def validate(g: dict, i: int, criteria, tags) -> list[str]:
    tid = g.get("ticket_id", f"#{i}")
    errs = []
    for k in ("ticket_id", "team", "agent", "scores", "tags", "evidence"):
        if k not in g:
            errs.append(f"{tid}: missing '{k}'")
    if errs:
        return errs
    for c in criteria:
        s = g["scores"].get(c)
        if isinstance(s, bool) or not isinstance(s, int) or not 1 <= s <= 4:
            errs.append(f"{tid}: score '{c}' must be an integer 1-4 (got {s!r})")
    for c in g["scores"]:
        if c not in criteria:
            errs.append(f"{tid}: unknown criterion '{c}'")
    for t in g["tags"]:
        if t not in tags:
            errs.append(f"{tid}: unknown tag '{t}'")
        elif not str(g["evidence"].get(t, "")).strip():
            errs.append(f"{tid}: tag '{t}' has no evidence quote")
    if g["scores"].get("accuracy") == 1 and "wrong_policy_figure" not in g["tags"] \
            and "inaccurate_product_info" not in g["tags"]:
        errs.append(f"{tid}: accuracy=1 requires tag 'wrong_policy_figure'")
    return errs


def parse_grades(raw: str) -> list:
    """Accept a JSON array or JSON Lines. Raises ValueError on bad JSON."""
    raw = raw.strip()
    try:
        data = json.loads(raw) if raw.startswith("[") else [json.loads(l) for l in raw.splitlines() if l.strip()]
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON: {e}") from e
    return data


def aggregate(grades: list, rubric_text: str) -> dict:
    """Pure aggregation used by the CLI and the web app.
    Returns {"errors": [...]} on validation failure, else
    {"errors": [], "n", "passes", "patterns", "report_md"}."""
    criteria, tags, autofail = parse_rubric(rubric_text)
    if not grades:
        return {"errors": ["no grades supplied"]}
    errs = []
    for i, g in enumerate(grades):
        if not isinstance(g, dict):
            errs.append(f"#{i}: each grade must be a JSON object")
            continue
        types_ok = (isinstance(g.get("scores", {}), dict) and isinstance(g.get("tags", []), list)
                    and isinstance(g.get("evidence", {}), dict))
        if not types_ok:
            errs.append(f"{g.get('ticket_id', f'#{i}')}: scores/evidence must be objects, tags a list")
            continue
        errs.extend(validate(g, i, criteria, tags))
    if errs:
        return {"errors": errs}

    total_w = sum(criteria.values())
    n = len(grades)
    rows, tag_count, tag_examples = [], Counter(), defaultdict(list)
    crit_sum = Counter()
    by_team = defaultdict(lambda: [0, 0])
    by_agent = defaultdict(lambda: [0, 0])
    for g in grades:
        wavg = sum(g["scores"][c] * w for c, w in criteria.items()) / total_w
        af = sorted(set(g["tags"]) & autofail)
        passed = wavg >= PASS_THRESHOLD and min(g["scores"].values()) > 1 and not af
        rows.append((g, wavg, passed, af))
        for c in criteria:
            crit_sum[c] += g["scores"][c]
        for t in g["tags"]:
            tag_count[t] += 1
            tag_examples[t].append((g["ticket_id"], g["evidence"][t]))
        for bucket, key in ((by_team, g["team"]), (by_agent, g["agent"])):
            bucket[key][0] += 1
            bucket[key][1] += passed

    passes = sum(r[2] for r in rows)
    patterns = [t for t, c in tag_count.items()
                if c >= PATTERN_MIN_COUNT or c / n >= PATTERN_MIN_SHARE]
    patterns.sort(key=lambda t: (t not in autofail, -tag_count[t], t))

    L = []
    L.append("# Weekly Support QA Report\n")
    L.append(f"**Sample:** {n} tickets · **Pass rate:** {passes}/{n} ({passes / n:.0%}) · "
             f"**Auto-fails:** {sum(1 for r in rows if r[3])}\n")
    L.append("## Recurring failure patterns\n")
    L.append("<!-- NARRATIVE: write per-pattern analysis + coaching fix here -->\n")
    L.append("| Tag | Tickets | Share | Auto-fail | Examples |")
    L.append("|---|---|---|---|---|")
    for t in patterns:
        ex = "; ".join(f"{tid}: \"{q}\"" for tid, q in tag_examples[t][:2])
        L.append(f"| `{t}` | {tag_count[t]} | {tag_count[t] / n:.0%} | "
                 f"{'yes' if t in autofail else ''} | {ex} |")
    if not patterns:
        L.append("| _none met the pattern threshold_ | | | | |")
    L.append("\n## Criterion averages (1-4)\n")
    L.append("| Criterion | Weight | Avg |")
    L.append("|---|---|---|")
    for c, w in criteria.items():
        L.append(f"| {c} | {w} | {crit_sum[c] / n:.2f} |")
    for title, bucket in (("Team", by_team), ("Agent", by_agent)):
        L.append(f"\n## Pass rate by {title.lower()}\n")
        L.append(f"| {title} | Passed | Graded |")
        L.append("|---|---|---|")
        for k, (tot, ok) in sorted(bucket.items(), key=lambda kv: kv[1][1] / kv[1][0]):
            L.append(f"| {k} | {ok} | {tot} |")
    L.append("\n## Per-ticket results\n")
    L.append("| Ticket | Team | Agent | " + " | ".join(criteria) + " | Weighted | Result | Tags |")
    L.append("|---" * (len(criteria) + 6) + "|")
    for g, wavg, passed, af in sorted(rows, key=lambda r: r[1]):
        sc = " | ".join(str(g["scores"][c]) for c in criteria)
        res = "PASS" if passed else ("FAIL (auto)" if af else "FAIL")
        L.append(f"| {g['ticket_id']} | {g['team']} | {g['agent']} | {sc} | {wavg:.2f} | {res} | "
                 f"{', '.join(g['tags'])} |")

    return {"errors": [], "n": n, "passes": passes, "patterns": patterns,
            "report_md": "\n".join(L) + "\n"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("grades")
    ap.add_argument("--rubric", default=str(DEFAULT_RUBRIC))
    ap.add_argument("--out", default="qa-report.md")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    try:
        grades = parse_grades(Path(a.grades).read_text(encoding="utf-8"))
        r = aggregate(grades, Path(a.rubric).read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    if r["errors"]:
        print("VALIDATION FAILED")
        for e in r["errors"]:
            print(f"  - {e}")
        return 1
    Path(a.out).write_text(r["report_md"], encoding="utf-8")
    print(f"OK: {r['n']} tickets, {r['passes']} passed. Patterns: {', '.join(r['patterns']) or 'none'}")
    print(f"Report skeleton written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
