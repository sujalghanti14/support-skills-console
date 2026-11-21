# Support QA Rubric (v3)

Score every criterion from **1 to 4** using the anchors below. Score what's in the transcript, not what the agent probably meant. Use the full scale: a 4 should be the exception, not the default.

## Criteria

### resolution — Resolution (weight 3)
- **4**: The customer's actual problem was solved (or correctly handed off with full context) in the fewest sensible steps.
- **3**: Solved, but with an avoidable detour or a missing piece the customer had to ask for.
- **2**: Partly solved; the customer was left with unresolved questions, or was routed without context.
- **1**: Not solved, wrong solution, or closed while the customer was still waiting.

### accuracy — Accuracy & policy compliance (weight 3)
- **4**: Every product fact, figure and policy statement is correct and current.
- **3**: Correct, with one minor imprecision that didn't mislead.
- **2**: A factual error that could mislead, but no wrong money or policy figure.
- **1**: Any refund, pricing, credit or SLA figure not in the policy doc in force at the time, or any wrong policy commitment. (Always tag `wrong_policy_figure`.)

### tone — Tone of voice (weight 2)
- **4**: Leads with the answer, plain and warm, one apology only if warranted, human sign-off.
- **3**: On-voice with small lapses (a long-winded opener, a stiff phrase).
- **2**: Noticeably off-voice: robotic, over-apologetic, or uses banned phrases.
- **1**: Rude, dismissive, blaming the customer, or sarcastic.

### ownership — Ownership & next steps (weight 1)
- **4**: Every reply ends with a clear next step, an owner and a timeline from policy or SLA.
- **3**: Next step is clear, but owner or timeline is missing.
- **2**: Vague ("we'll look into it").
- **1**: No next step, or the customer was left to chase.

### efficiency — Efficiency (weight 1)
- **4**: First response within SLA; no unnecessary back-and-forth.
- **3**: Within SLA, but one avoidable round-trip (asked for info that was already given).
- **2**: SLA missed by under 2×, or two or more avoidable round-trips.
- **1**: SLA missed by 2× or more, or the ticket bounced between teams 3+ times.

## Pass rule
A ticket **passes** when its weighted average is **≥ 3.0**, **no** criterion scored 1, and **no** auto-fail tag applies.

## Failure tags
Apply every tag that fits, and back each one with a short verbatim quote from the transcript as evidence. Tags marked **(auto-fail)** fail the ticket regardless of score.

- `wrong_policy_figure` — (auto-fail) stated a refund/price/credit/SLA figure not in the policy doc
- `missed_escalation` — (auto-fail) outage, security or legal signal was not escalated
- `security_data_exposed` — (auto-fail) shared account data with an unverified requester
- `misrouted` — sent to the wrong team, or bounced between teams
- `didnt_answer_question` — the customer's main question went unanswered
- `premature_close` — closed or marked solved while the customer was still waiting
- `no_next_step` — reply ended without a next step or owner
- `banned_phrase` — used a phrase from the tone-guide banned list
- `robotic_tone` — templated, stiff or impersonal wording
- `over_apology` — more than one apology, or apologized for something that isn't our fault
- `excessive_back_and_forth` — asked for info already provided, or needless clarifying loops
- `sla_breach` — first response or resolution outside the SLA
- `inaccurate_product_info` — wrong statement about product behavior or features
