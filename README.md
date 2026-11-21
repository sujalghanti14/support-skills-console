# Support Skills Console

[![tests](https://github.com/sujalghanti14/support-skills-console/actions/workflows/tests.yml/badge.svg)](https://github.com/sujalghanti14/support-skills-console/actions/workflows/tests.yml)

**Live demo:** https://support-skills-console.onrender.com *(free hosting: the first visit after a quiet spell takes up to ~50 s to wake)*

**Submission documents:** Project report ([PDF](submission/Project-Report.pdf) · [Word](submission/Project-Report.docx)) · [Presentation (.pptx)](submission/Presentation.pptx)

**New here?** Jump to **[How to use it](#how-to-use-it)**.

---

## The brief

A mid-size SaaS company handles support manually through one shared inbox. Leadership wants an AI assistant to take over five workflows:

1. Triage and route new tickets in minutes, and escalate outages and legal/security issues immediately.
2. Keep every reply on-brand, and never quote a refund or price that isn't in the current (often-changing) policy.
3. Build a one-page briefing for "at-risk" customers from three systems (billing, usage logs, past tickets).
4. Grade a weekly sample of closed tickets against a rubric and summarise the recurring failures.
5. Check reported bugs against the changelog, and write up new ones for engineering.

**Task:** decide which pieces need a **Skill**, an **Agent**, or **Neither**, justify each, and build the skills. Agents could be skipped, and no orchestration was needed.

## Decisions

| Workflow piece | Decision | One-line reason |
|---|---|---|
| Keyword escalation (outage / legal / security) | **Neither**: a ticketing-tool rule | Must be instant and can't miss; a regex is deterministic and auditable |
| Categorise + route | **Skill**: `ticket-triage` | One-pass judgment that needs company know-how (taxonomy, team ownership) |
| On-brand, policy-safe replies | **Skill**: `support-reply` | Voice rules are stable know-how; figures are checked by a script against the *live* policy |
| At-risk account briefing | **Agent** *(designed, not built)* | Three systems, dependent queries, lots of raw data to keep out of the main context |
| Weekly sampling + schedule | **Neither**: cron + query | Deterministic and reproducible |
| Rubric grading + pattern summary | **Skill**: `qa-grading` | The rubric is the knowledge; a script does the arithmetic |
| Known-issue check + bug write-up | **Skill**: `bug-intake` | Bounded search of one document plus a house template |

The full reasoning is in **[DECISIONS.md](DECISIONS.md)**.

**Rule of thumb:** no judgment needed → *Neither*. Judgment with company know-how, on input that fits in context → *Skill*. Exploring several systems and digesting lots of raw data → *Agent*.

## How it fits together

```mermaid
flowchart LR
    subgraph Skills [".claude/skills (Claude Code)"]
        S1[ticket-triage<br/>SKILL.md + routing.json]
        S2[support-reply<br/>SKILL.md + tone guide]
        S3[qa-grading<br/>SKILL.md + rubric]
        S4[bug-intake<br/>SKILL.md + template]
    end
    subgraph Scripts ["Deterministic checks (Python)"]
        P1[validate_triage.py]
        P2[check_reply.py]
        P3[aggregate_grades.py]
        P4[search_changelog.py]
    end
    D[(company-docs/<br/>policy + changelog<br/>read live)]
    S1 --> P1
    S2 --> P2
    S3 --> P3
    S4 --> P4
    P2 --> D
    P4 --> D
    W[Web app<br/>Flask + 4-tab UI] --> P1 & P2 & P3 & P4
    CLI[Command line] --> P1 & P2 & P3 & P4
```

Each skill pairs **instructions for the model** (`SKILL.md`: the procedure, rules and output format) with a **script for the parts that must be exact** (figures, scores, schema checks). The CLI and the web app call the same functions, so they always agree.

## The four skills

| Skill | What the model does | What the script guarantees |
|---|---|---|
| [`ticket-triage`](.claude/skills/ticket-triage/SKILL.md) | Picks category, team, priority; flags escalations a regex would miss | Valid category/team pairing, escalations routed to the right team and marked urgent |
| [`support-reply`](.claude/skills/support-reply/SKILL.md) | Drafts the reply in the company voice | Every $, %, and time window exists in the current policy; no money in words; no banned phrases |
| [`qa-grading`](.claude/skills/qa-grading/SKILL.md) | Scores each ticket on 5 criteria with quoted evidence | Rubric-valid grades, pass rule, pass rates, recurring patterns |
| [`bug-intake`](.claude/skills/bug-intake/SKILL.md) | Decides KNOWN_OPEN / FIXED / NEW and writes the engineering report | Ranked changelog candidates with match scores |

## Web app

![Reply check](webapp/screenshots/1-reply-check-light.png)

A small Flask app with one tab per skill. Each tab has a **Load example** button and a plain-language **How to use this** guide. It supports dark mode and phone screens, and is hosted on Render (`render.yaml`).

## How to use it

There are three ways to use the tool. You don't need to install anything for the first one.

### 1. In the web app (easiest)

1. Open **https://support-skills-console.onrender.com**. If it hasn't been used for a while, the first load takes up to ~50 seconds.
2. Pick one of the four tabs at the top.
3. Paste your text, or press **Load example** to fill in a ready-made one.
4. Press the purple button and read the coloured result:
   - **Green ✓**: all good.
   - **Red ✕**: problems to fix, each listed with a label like `BANNED PHRASE`.
   - **Amber !**: worth a look.

Every tab also has a **How to use this** box that explains it in plain words.

| Tab | Paste this | Press | You get | Try this |
|---|---|---|---|---|
| **Triage** | The triage record (JSON) the triage skill produced | **Validate** | Whether category, team and priority follow the routing rules | Load the example, change `"team"` to `"billing-ops"`, then Validate: it says an outage must go to `incident-oncall` |
| **Reply check** | A reply you're about to send. Optionally, put amounts from the customer's own account (e.g. `87.40`) in the second box | **Check reply** | PASS, or each figure not in the current policy, money written in words, and banned phrases | Type `Dear customer, you can get a full refund within 30 days.` The policy says 14 days, so it's flagged, and so is "dear customer" |
| **QA report** | The week's ticket grades (JSON array or JSON Lines) | **Build report** | Pass rate, recurring problems, a downloadable `.md` report | Press Load example, then Build report: 1 of 4 tickets passes, with 3 patterns |
| **Known issues** | A short description of the bug | **Search** | Matching changelog entries marked `KNOWN_OPEN` (share the workaround) or `FIXED` (customer may need to update), with a match % | Type `android app crashes when attaching a photo`: it finds KI-409 |

**Show current policy** (on the Reply check tab) displays the rules every figure is checked against. The policy is read fresh on every check, so after someone edits `company-docs/refund-pricing-policy.md`, the next check uses the new rules.

### 2. In Claude Code (how the skills are meant to be used)

The four folders in `.claude/skills/` are Claude Code skills. Open this repository in [Claude Code](https://claude.com/claude-code) and Claude picks them up automatically. Then just ask in plain English:

| You say | Claude uses | What happens |
|---|---|---|
| "Triage this ticket: *none of our 40 users can open boards, we get a 502*" | `ticket-triage` | Writes a triage record (flagged as an outage, urgent) and runs the validator until it passes |
| "Draft a reply to this customer asking for a refund after 20 days on a monthly plan" | `support-reply` | Reads the live policy, writes an on-brand reply, and runs the figure check before giving it to you |
| "Grade these closed tickets and write the weekly QA summary" | `qa-grading` | Scores each ticket against the rubric with quoted evidence, then builds the report |
| "A customer says CSV export times out on 80k rows. Is this known?" | `bug-intake` | Searches the changelog, decides KNOWN_OPEN / FIXED / NEW, and writes an engineering bug report if it's new |

You can also call a skill by name, e.g. type `/support-reply`.

### 3. From the command line

Each skill's checking script runs on its own (Python 3.12, no extra packages):

```bash
# Is this triage record valid?
python .claude/skills/ticket-triage/scripts/validate_triage.py samples/triage-good.json

# Does this reply quote anything not in the policy? (exit code 1 = problems found)
python .claude/skills/support-reply/scripts/check_reply.py samples/reply-bad.txt --policy company-docs/refund-pricing-policy.md

# Build the weekly QA report from grades
python .claude/skills/qa-grading/scripts/aggregate_grades.py samples/grades.json --out qa-report.md

# Is this bug already in the changelog?
python .claude/skills/bug-intake/scripts/search_changelog.py company-docs/CHANGELOG.md "csv export timeout"
```

The `samples/` folder has a good and a bad example input for each one.

## Testing

**73 automated tests**, run on every push by GitHub Actions:

| Suite | Count | Covers |
|---|---|---|
| Unit | 35 | Each script's logic: ranges, bool-as-int, word boundaries, live policy changes, pass rule, pattern threshold |
| API | 23 | Every endpoint, bad input (400/404/405/413), security headers, policy re-read on each request |
| Browser (Playwright) | 15 | Every tab end to end, keyboard navigation, HTML injection, server failure, download, phone width, zero console errors |

Testing caught and fixed real bugs, for example: `"fifty dollar"` slipping past the words check, a range like `3-5 days` half-passing, `true` accepted as a score, and the QA script calling `sys.exit` (which would kill a web server).

## Run it yourself

```bash
pip install -r requirements.txt
python webapp/app.py
```

Then open http://127.0.0.1:5000.

To run the tests:

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
python webapp/run_tests.py
```

Each skill script also runs on its own, for example:

```bash
python .claude/skills/support-reply/scripts/check_reply.py samples/reply-bad.txt --policy company-docs/refund-pricing-policy.md
```

## Repository layout

| Path | Contents |
|---|---|
| `.claude/skills/` | The four skills: instructions, references, scripts |
| `company-docs/` | Refund/pricing policy and changelog the checks read on every run |
| `samples/` | Example inputs for each skill (good and bad) |
| `webapp/` | Flask app, static UI, tests, screenshots |
| `submission/` | Project report (PDF and Word) and presentation |
| `DECISIONS.md` | Skill vs Agent vs Neither reasoning |
| `render.yaml`, `requirements*.txt` | Hosting and dependencies |
| `.github/workflows/tests.yml` | CI: runs every test on each push |

## Known limitations

- The reply checker confirms a figure *exists* in the policy, not that it's used for the *right clause* ("25% annual discount" passes because 25% is an outage credit). The skill makes the model cite the clause it relied on to cover this.
- The at-risk briefing agent is designed but not built, as the brief allowed.
- The hosted demo has no login. It is read-only and stores nothing people type.
