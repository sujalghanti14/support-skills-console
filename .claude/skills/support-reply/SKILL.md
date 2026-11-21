---
name: support-reply
description: Draft or review an outbound customer support reply in the company's tone of voice, guaranteeing that any refund, pricing, credit, discount, or timeline figure matches the CURRENT refund & pricing policy document. Use for any customer-facing email or ticket reply, especially ones that mention money, refunds, plans, credits, SLAs, or deadlines.
---

# Support Reply

Write replies that sound like us and **never state a figure the policy doc doesn't contain.**

## Inputs
- The customer's message (plus any ticket or account context you were given).
- **The live policy doc**: `company-docs/refund-pricing-policy.md` (or the path the user gives you). It changes often. **Read it fresh every time you draft.** Never rely on figures you remember from earlier, from this skill, or from the customer's message.
- Tone guide: `references/tone-of-voice.md` (relative to this skill).

## Steps

1. **Read both documents** before writing anything.
2. **Work out the answer before the wording.** Decide what we are actually doing (refunding, declining, escalating, explaining) by applying the policy rules to the customer's situation. If the policy doesn't cover the case, or it needs approval (for example a credit above the agent limit), **don't promise anything.** Say you've escalated it and who will follow up.
3. **Draft** following the five rules, the formatting rules and the banned-phrase list in the tone guide.
4. **Figures discipline:**
   - Every price, refund amount, percentage, credit and time window must appear **verbatim in the policy doc**.
   - **Don't calculate customer-specific refund amounts** (prorations, partial months). State the rule ("a prorated refund for the unused full months") and say billing will confirm the exact amount. Arithmetic is where wrong numbers creep in.
   - You may repeat a figure that comes from the **customer's own account or ticket data** (for example "your $87.40 charge on Nov 3"). Pass each one to the checker with `--allow` so it's on record as deliberate.
   - Enterprise pricing is never quoted. Route the customer to Sales.
5. **Run the checker** on the draft (save it to a file first):
   ```bash
   python .claude/skills/support-reply/scripts/check_reply.py draft.txt \
       --policy company-docs/refund-pricing-policy.md [--allow 87.40 ...]
   ```
   It fails on (a) any money, percentage or time-window figure that isn't in the policy doc, (b) money written out in words, and (c) banned phrases. **Fix the draft and re-run until it prints `PASS`.** Never hand back a draft that fails. If you think the checker is wrong, say so explicitly to the user rather than ignoring it.
6. **Return** the final reply text, then a one-line note listing the policy clauses you relied on (for example "Refunds → Monthly plans, 14 days").

## Self-check before returning
- Does the first sentence give the answer?
- Is there exactly one apology, and only if we were at fault?
- Does it end with a concrete next step and owner?
- Did the checker print PASS against the policy doc *as it is right now*?
