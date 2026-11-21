# Weekly Support QA Report

**Sample:** 5 tickets · **Pass rate:** 1/5 (20%) · **Auto-fails:** 1

## Recurring failure patterns

<!-- NARRATIVE: write per-pattern analysis + coaching fix here -->

| Tag | Tickets | Share | Auto-fail | Examples |
|---|---|---|---|---|
| `wrong_policy_figure` | 1 | 20% | yes | T-2202: "full refund within 30 days" |
| `banned_phrase` | 2 | 40% |  | T-2203: "we apologize for any inconvenience"; T-2204: "kindly share" |
| `no_next_step` | 2 | 40% |  | T-2203: "Thanks for reaching out."; T-2205: "we'll look into it" |
| `excessive_back_and_forth` | 1 | 20% |  | T-2204: "could you send your workspace id" |

## Criterion averages (1-4)

| Criterion | Weight | Avg |
|---|---|---|
| resolution | 3 | 3.00 |
| accuracy | 3 | 2.80 |
| tone | 2 | 2.80 |
| ownership | 1 | 2.80 |
| efficiency | 1 | 2.80 |

## Pass rate by team

| Team | Passed | Graded |
|---|---|---|
| tier1-support | 0 | 2 |
| tier2-support | 0 | 1 |
| billing-ops | 1 | 2 |

## Pass rate by agent

| Agent | Passed | Graded |
|---|---|---|
| lee | 0 | 1 |
| ana | 0 | 2 |
| raj | 0 | 1 |
| sam | 1 | 1 |

## Per-ticket results

| Ticket | Team | Agent | resolution | accuracy | tone | ownership | efficiency | Weighted | Result | Tags |
|---|---|---|---|---|---|---|---|---|---|---|
| T-2202 | billing-ops | lee | 3 | 1 | 3 | 3 | 3 | 2.40 | FAIL (auto) | wrong_policy_figure |
| T-2203 | tier1-support | ana | 2 | 3 | 2 | 2 | 3 | 2.40 | FAIL | banned_phrase, no_next_step |
| T-2204 | tier1-support | ana | 3 | 3 | 2 | 3 | 2 | 2.70 | FAIL | banned_phrase, excessive_back_and_forth |
| T-2205 | tier2-support | raj | 3 | 3 | 3 | 2 | 3 | 2.90 | FAIL | no_next_step |
| T-2201 | billing-ops | sam | 4 | 4 | 4 | 4 | 3 | 3.90 | PASS |  |
