# Skill vs Agent vs Neither — Support Automation

## The test I applied

| Build a… | When the work is… |
|---|---|
| **Skill** | Know-how the model needs to do a bounded task *the company's way*: house rules, a taxonomy, a rubric, a template, plus small scripts for the parts that must be exact. It runs inline, needs no special tools, and the input fits easily in context. |
| **Agent** | Open-ended, multi-step work: it has to *go and get* things with its own tools and permissions, often from several systems, and pulls in a lot of raw data that should stay out of the caller's context. What comes back is a short distilled result. |
| **Neither** | Deterministic, latency-critical, or pure plumbing: keyword rules, schedules, sampling queries, lookups. An LLM adds cost, latency and a chance of being wrong, with nothing gained. Use code, config or the ticketing tool's own automation. |

Two questions decide most cases: *"Does it need judgment on unstructured text?"* (if not, Neither) and *"Does it need to explore several systems and absorb lots of raw data before it can answer?"* (if so, Agent; otherwise Skill).

---

## 1. New-ticket triage, routing and escalation → split: **Neither + Skill**

| Piece | Decision | Why |
|---|---|---|
| Immediate escalation on outage / legal / security **keywords** | **Neither.** A rule in the ticketing tool or a webhook, e.g. regex on `breach`, `GDPR`, `lawyer`, `subpoena`, `down for everyone`, `500 error` → page on-call / legal. | "Immediate, not queued" is a latency and reliability requirement. A keyword match is deterministic: it can't hallucinate, it runs in milliseconds, and you can audit it. Putting an LLM in front of a legal or security escalation makes the guarantee *weaker*. |
| Categorize and route everything else ("within minutes") | **Skill: `ticket-triage`** | This needs judgment on free text (a "refund" may really be a billing bug), but it is a single-pass classification. There is nothing to go and fetch, so no agent is needed. What the model lacks is *company knowledge*: the category taxonomy, which team owns what, and the tie-break rules. That is exactly what a skill carries. It also gives a semantic second net for escalations the regex misses ("none of my team can log in since 9am"). |
| Routing table itself | **Neither (config)** | Kept as a data file the skill reads, so ops can edit it without touching the prompt. |

## 2. Outbound replies: tone of voice and policy-accurate figures → **Skill: `support-reply`**

- The tone of voice is a stable, company-specific standard. That is textbook skill content (voice rules, banned phrases, before/after examples).
- "Never state a refund/pricing figure that isn't in the current policy doc" has two parts:
  - **The policy doc must not be baked into the skill.** It changes often, and a copy inside the skill would go stale silently. The skill tells the model to *read the live doc at draft time*.
  - **The check must be deterministic.** A bundled script pulls every money amount, percentage and time window out of the draft and fails if any of them is missing from the current policy doc. "Never" is a hard constraint, so it gets a hard check rather than a model promising to be careful.
- Not an agent: drafting a reply is bounded, inline work. Retrieval is a single file read.

## 3. "At-risk" customer briefing → **Agent** (not built, per the brief)

- It has to pull from **three separate systems** (billing, product usage logs, ticket history). Each needs its own credentials or tools, and the queries depend on what earlier ones return (e.g. a usage drop in March → look at March tickets).
- The raw data is large and noisy (usage logs especially). It belongs in an isolated context, and only the one-page briefing comes back.
- It is autonomous and multi-step with a clear deliverable, which is the agent pattern. (A briefing *template* could later be a small skill that the agent loads, but the work itself is agentic.)

## 4. Weekly QA grading of closed tickets → split: **Neither + Skill**

| Piece | Decision | Why |
|---|---|---|
| Weekly schedule and rolling sample | **Neither** | A cron job plus a sampling query (e.g. stratified random N per team, excluding already-graded tickets). That is deterministic and has to be reproducible. |
| Grading against the rubric and writing the failure-pattern summary | **Skill: `qa-grading`** | The rubric *is* the knowledge: criteria, score anchors, failure tags. Consistency from week to week matters more than anything else, so the rubric, scoring anchors and a fixed output schema live in the skill, and a script does the aggregation so the counts are arithmetic rather than guesses. Each ticket is graded independently and doesn't need exploration, so there is no agent. If the volume gets large, the caller can fan the work out. That is orchestration and outside this scope. |

## 5. Bug reports: known-issue check and engineering write-up → **Skill: `bug-intake`**

- Checking the changelog is a bounded search of one document. A bundled script ranks changelog entries against the reported symptoms, and the model makes the final "is this the same issue?" call.
- The engineering write-up follows a house template (repro steps, expected vs actual, environment, severity). That is template knowledge, so it is a skill.
- It would become an **agent** only if it had to reproduce the bug in a staging environment or search several trackers. That isn't asked for, so don't pay for it.

---

## Summary

| Workflow piece | Decision |
|---|---|
| Keyword escalation (outage/legal/security) | Neither: ticketing-tool rule / webhook |
| Categorize + route | **Skill**: `ticket-triage` |
| On-brand, policy-safe replies | **Skill**: `support-reply` (live policy doc + figure-check script) |
| At-risk account briefing | **Agent** (not built) |
| Weekly sampling + schedule | Neither: cron + query |
| Rubric grading + failure-pattern summary | **Skill**: `qa-grading` |
| Known-issue check + bug write-up | **Skill**: `bug-intake` |

## Known limitation

`check_reply.py` checks that each **figure exists** in the policy. It does not check that the figure is used for the **right clause**. "Annual plans get a 25% discount" passes, because 25% does appear in the policy (as an SLA credit). The skill covers that gap by making the model cite the clause it relied on for each figure. A stricter version would compare figure-plus-context pairs.

## What's in this folder

```
.claude/skills/
  ticket-triage/   SKILL.md, references/routing.json, scripts/validate_triage.py
  support-reply/   SKILL.md, references/tone-of-voice.md, scripts/check_reply.py
  qa-grading/      SKILL.md, references/rubric.md, scripts/aggregate_grades.py
  bug-intake/      SKILL.md, references/bug-template.md, scripts/search_changelog.py
company-docs/      live documents the skills READ at runtime (not copied into them)
  refund-pricing-policy.md
  CHANGELOG.md
samples/           test inputs used to check each skill on its own
webapp/            web UI that runs the same skill scripts, plus unit/API/browser tests
submission/        project report (.docx) and presentation (.pptx)
```
