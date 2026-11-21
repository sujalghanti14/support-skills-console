#!/usr/bin/env python3
"""Rank changelog entries against a bug description by keyword overlap.

Usage: python search_changelog.py CHANGELOG.md "symptom description" [--top 5]

Changelog format expected: '## <version> — <date>' release headings,
'### Known issues' / '### Fixed' sections, and '- ' bullet entries.
Outputs ranked candidates; the caller decides whether any truly match.
"""
import argparse
import re
import sys
from pathlib import Path

STOP = set("""a an the and or but of to in on for with when after before is are was were be
been it its this that my our we you your i can cant cannot not no up down
from by as at than then until may might user users get gets see out about have has
keep keeps keeps still just any some all also only very really please help hi hello
thanks issue problem broken working work doesnt dont""".split())
SYNONYMS = {
    "timeout": "time", "timing": "time", "slow": "time", "hang": "time", "hangs": "time",
    "crash": "crash", "crashes": "crash", "crashing": "crash", "closes": "crash",
    "blank": "blank", "white": "blank", "empty": "blank",
    "login": "login", "log": "login", "signin": "login", "sign": "login",
    "2fa": "twofactor", "two": "twofactor", "mfa": "twofactor", "otp": "twofactor",
    "photo": "image", "picture": "image", "image": "image", "attachment": "attach",
    "duplicate": "duplicate", "twice": "duplicate", "double": "duplicate",
    "email": "email", "emails": "email", "mail": "email",
    "pdf": "invoice", "invoice": "invoice", "invoices": "invoice", "bill": "invoice",
}


def tokens(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP or len(w) < 2:
            continue
        w = SYNONYMS.get(w, w)
        for suf in ("ing", "ed", "es", "s"):
            if len(w) > 4 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        out.add(w)
    return out


def parse(changelog: str):
    version, section, entries = None, None, []
    for line in changelog.splitlines():
        if m := re.match(r"^##\s+(.+)$", line):
            version, section = m.group(1).strip(), None
        elif m := re.match(r"^###\s+(.+)$", line):
            section = m.group(1).strip()
        elif line.strip().startswith("- ") and version:
            text = line.strip()[2:]
            ki = re.match(r"(KI-\d+)", text)
            entries.append({"version": version, "section": section or "",
                            "ki": ki.group(1) if ki else "", "text": text})
    return entries


WEAK_THRESHOLD = 0.3


def search(changelog_text: str, query: str, top: int = 5) -> dict:
    """Pure search used by the CLI and the web app.
    Returns {"terms": [...], "weak": bool, "results": [{score, status, version, ki, text, matched}]}."""
    q = tokens(query)
    if not q:
        return {"terms": [], "weak": True, "results": []}
    scored = []
    for e in parse(changelog_text):
        hits = q & tokens(e["text"])
        if hits:
            scored.append((len(hits) / len(q), sorted(hits), e))
    scored.sort(key=lambda x: -x[0])
    results = []
    for score, hits, e in scored[:max(top, 0)]:
        sec = e["section"].lower()
        status = "KNOWN_OPEN" if "known" in sec else "FIXED" if "fix" in sec else e["section"]
        results.append({"score": round(score, 4), "status": status, "version": e["version"],
                        "ki": e["ki"], "text": e["text"], "matched": hits})
    return {"terms": sorted(q), "weak": not scored or scored[0][0] < WEAK_THRESHOLD,
            "results": results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("changelog")
    ap.add_argument("query")
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    r = search(Path(a.changelog).read_text(encoding="utf-8"), a.query, a.top)
    if not r["terms"]:
        print("Query has no searchable terms.")
        return 1
    print(f"Query terms: {', '.join(r['terms'])}")
    if not r["results"]:
        print("No candidate entries. Likely NEW (confirm by trying other phrasings).")
        return 0
    if r["weak"]:
        print("All candidates are weak (<30% term overlap): probably NEW, but read them to confirm.")
    for x in r["results"]:
        print(f"\n[{x['score']:.0%}] {x['status']} | {x['version']} | {x['ki'] or '-'}")
        print(f"  {x['text']}")
        print(f"  matched: {', '.join(x['matched'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
