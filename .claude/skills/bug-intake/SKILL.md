---
name: bug-intake
description: Handle a customer-reported bug by checking whether it is already a known or fixed issue in the product changelog, and, if not, writing an engineering-ready bug report with repro steps. Use when a ticket describes something broken (errors, crashes, wrong data, features not working) and you need to decide "known issue or new bug?" or write it up for engineering.
---

# Bug Intake

You turn a customer bug report into one of three outcomes:

| Outcome | Meaning | Deliverable |
|---|---|---|
| **KNOWN_OPEN** | Matches an entry under *Known issues* | KI id + workaround for support to share |
| **FIXED** | Matches an entry under *Fixed* | Fix version. Either the customer needs to update, or it's a **regression** and you file it as a new bug, referencing the old KI |
| **NEW** | No real match | A filled bug report from `references/bug-template.md` |

## Steps

1. **Pull out the symptom.** From the ticket, note the component, the platform/browser/version, what the customer did, what they expected, what happened (exact error text), how many users are affected, and any concrete data (file size, row count, timezone).
   - If many users or a whole workspace are affected, or there's data loss or a security impact, **stop. This is an incident (S1), not a bug report.** Tell the user to escalate.
2. **Search the changelog** (default `company-docs/CHANGELOG.md`):
   ```bash
   python .claude/skills/bug-intake/scripts/search_changelog.py company-docs/CHANGELOG.md "csv export timeout large workspace"
   ```
   Run it 2–3 times with different phrasings (the customer's words, then product terms, then the error text). The script ranks candidates by keyword overlap. **It does not decide the outcome. You do.**
3. **Judge each top candidate** against the symptom. A match needs the **same component, same trigger and same platform constraints.** "Export is slow" is not KI-412 if the workspace has 2,000 rows (KI-412 needs more than 50,000). Write down why each close candidate does or doesn't match.
4. **Decide the outcome:**
   - KNOWN_OPEN → give the KI id, the workaround quoted from the changelog, and the planned fix version if one is listed.
   - FIXED → compare against the customer's version if it's known. If they're on an older release, tell them to update. If they're on the fixed release or newer, treat it as a **regression**: file a NEW report and put "Possible regression of KI-xxx" in the title.
   - NEW → fill in the template from `references/bug-template.md` exactly, following its repro-step rules and severity table. List any missing facts under "Questions for customer" instead of inventing them.
5. **Return** a block that starts with `Outcome: KNOWN_OPEN | FIXED | NEW`, then the changelog evidence (entries considered and why they did or didn't match), then the deliverable.
