---
name: ticket-triage
description: Categorize a new support ticket, pick the owning team and priority from the company routing table, and flag outage/security/legal escalations. Use whenever a new or untriaged support ticket, customer email, or inbox message needs to be classified or routed. Produces a validated JSON triage record.
---

# Ticket Triage

Turn one raw ticket into a triage record that the ticketing tool can act on. You classify; you do **not** reply to the customer.

> Hard keyword escalation (e.g. "breach", "subpoena") is already handled by a deterministic rule in the ticketing tool *before* this skill runs. Your escalation flag is the **semantic second net**: it catches cases the regex can't see ("nobody on my team can load anything since 9am").

## Steps

1. **Read the routing table** at `references/routing.json` (relative to this skill). It is the only valid source of category and team names. Never invent a team.
2. **Check escalation first.** Compare the ticket against each `escalation.*.signals`. Set `escalation` to `outage`, `security`, or `legal` if *any* signal plausibly applies; otherwise `null`. When in doubt between escalating and not escalating, **escalate**: a false alarm costs minutes, a miss costs far more.
   - One user who can't log in is `account_access`, **not** an outage. Several users, a whole workspace, or "is it down?" is an outage.
   - A customer saying "I'll dispute this with my bank" is billing. Naming a lawyer, a regulator or a statute is legal.
3. **Pick exactly one category** whose `covers` best matches the customer's *underlying need*, not their wording:
   - "Refund me, your export is broken" → `bug` (fix the cause; billing can follow).
   - "Too expensive, cancel" → `cancellation` (retention owns intent to leave, even if money is mentioned).
   - API/webhook/SSO-config problems → `integration`, not `bug`.
   - Prospect asking for Enterprise price → `sales`.
4. **Set `team`** to the category's team, or to the escalation team if `escalation` is set.
5. **Set `priority`:**
   - `urgent`: any escalation.
   - `high`: customer is blocked from core work, a payment failed, or they intend to cancel.
   - `normal`: a degraded experience with a workaround available, or a billing question.
   - `low`: how-to questions and feature requests.
6. **Write the record** (below), save it to a file, and validate it:
   ```bash
   python .claude/skills/ticket-triage/scripts/validate_triage.py triage.json
   ```
   Fix whatever the validator reports and re-run it until it prints `OK`.

## Output schema (JSON)

```json
{
  "ticket_id": "string (from input, or 'unknown')",
  "category": "one key of routing.json categories",
  "team": "the category's team, or the escalation team",
  "priority": "urgent | high | normal | low",
  "escalation": "outage | security | legal | null",
  "confidence": 0.0,
  "summary": "one sentence, <= 200 chars, what the customer needs",
  "reasoning": "1-2 sentences citing the words in the ticket that drove the decision"
}
```

Set `confidence` below `0.6` when the ticket is ambiguous or spans several categories. The ticketing tool sends low-confidence records to a human queue, so don't inflate it.

## Example

Input: *"Hi, since this morning none of the 40 people in our workspace can open any boards. Getting a 502. We have a client demo at 2pm!!"*

```json
{"ticket_id":"T-1093","category":"bug","team":"incident-oncall","priority":"urgent","escalation":"outage","confidence":0.92,"summary":"Entire 40-person workspace gets 502 errors opening boards.","reasoning":"'none of the 40 people' and '502' indicate a workspace-wide service failure, which matches the outage signals."}
```
