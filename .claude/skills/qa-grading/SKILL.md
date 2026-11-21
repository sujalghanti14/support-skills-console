---
name: qa-grading
description: Grade closed support tickets against the company QA rubric and write the weekly summary of recurring failure patterns. Use when asked to grade, score, audit, or QA-review support tickets or transcripts, or to produce the weekly support quality report from a sample of closed tickets.
---

# QA Grading

You receive a sample of closed tickets, already selected by the weekly sampling job (you do not choose the sample). You grade each ticket the same way every week and turn the results into a short, evidence-backed report.

## Inputs
- The ticket transcripts (a file or folder of closed tickets, each including the ticket id, team, agent and full thread).
- The rubric: `references/rubric.md` (relative to this skill). It defines the criteria, the 1–4 anchors, the weights, the pass rule and the allowed failure tags.
- If you're judging `accuracy`, the refund/pricing policy doc (`company-docs/refund-pricing-policy.md`) so you can check every figure an agent quoted.

## Steps

1. **Read the rubric in full** before grading the first ticket.
2. **Grade each ticket on its own merits.** Don't compare it with other tickets in the batch, because that causes drift. For each ticket:
   - Score all five criteria using the **anchor descriptions**, not gut feel.
   - Apply every failure tag that fits, using **only** tag ids from the rubric.
   - For every tag, give `evidence`: a short **verbatim quote** from the transcript. No quote means no tag.
   - For any score of 2 or lower, the tag or the note must explain why.
3. **Write all grades** to `grades.json` as a JSON array (schema below).
4. **Run the aggregator.** It validates every grade against the rubric, applies the pass rule and computes the statistics:
   ```bash
   python .claude/skills/qa-grading/scripts/aggregate_grades.py grades.json --out qa-report.md
   ```
   If it reports validation errors (an unknown tag, a missing criterion, a tag with no evidence), fix `grades.json` and re-run. **Don't do the arithmetic yourself. Use the script's numbers.**
5. **Write the narrative** at the top of `qa-report.md` under `## Recurring failure patterns`:
   - A **pattern** is a tag that appears on 2 or more tickets *or* on 10% or more of the sample. The script lists these.
   - For each pattern (ranked by frequency, auto-fail tags first): what's going wrong, 1–2 quoted examples with ticket ids, which team or agents are involved, and **one concrete coaching or process fix**.
   - Then add one paragraph on what went well, so the report isn't only negative.
   - Keep it to one page. Leadership reads the first 10 lines.
6. Return the path to the report and a 3-bullet summary.

## Grade schema (one object per ticket)

```json
{
  "ticket_id": "T-2210",
  "team": "billing-ops",
  "agent": "sam",
  "scores": {"resolution": 3, "accuracy": 1, "tone": 3, "ownership": 4, "efficiency": 3},
  "tags": ["wrong_policy_figure"],
  "evidence": {"wrong_policy_figure": "you'll get a full refund within 30 days"},
  "notes": "Policy refund window for monthly plans is 14 days."
}
```

## Calibration reminders
- Only a wrong *money/policy* figure is `accuracy: 1`. Other factual slips are a 2.
- A polite reply that didn't solve the problem still scores low on `resolution`. Tone and resolution are scored separately.
- If the transcript is missing context you'd need (for example the SLA clock), say so in `notes` rather than guessing.
