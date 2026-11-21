# Engineering Bug Report Template

Fill every section. If you don't know something, write `Unknown — asked customer` (and actually ask them) rather than guessing.

```markdown
## [BUG] <component>: <symptom in ≤ 10 words>

**Source ticket:** <ticket id> · **Reported:** <date> · **Customer plan:** <plan>
**Severity:** S1 | S2 | S3 | S4   (see table below)
**Affected users:** <one user / N users / whole workspace / unknown>
**Changelog check:** Searched <changelog version range>; closest entries: <KI ids or "none"> — <why they don't match>

### Environment
- App surface: web / desktop / iOS / Android / API
- Browser or OS + version:
- App version / release:
- Workspace id:

### Steps to reproduce
1. <starting state, e.g. "Logged in as workspace admin on Growth plan">
2. <single action per step>
3. ...

### Expected result
<what should happen>

### Actual result
<what happens; exact error text in quotes>

### Frequency
Always / Intermittent (~x of y tries) / Once

### Evidence
- Customer quote: "<verbatim>"
- Screenshots / logs / request ids: <links or "none provided">

### Workaround
<known workaround, or "none known">
```

## Severity

| Sev | Definition |
|---|---|
| S1 | Data loss, security impact, or core feature down for many customers. **This should have been escalated as an incident. Stop and escalate instead of filing.** |
| S2 | Core workflow blocked for this customer, with no workaround |
| S3 | Feature broken or degraded, with a workaround available |
| S4 | Cosmetic or minor annoyance |

## Repro-step rules
- One action per step, in the imperative ("Click **Export → CSV**").
- Step 1 always states the starting state: role, plan, platform.
- Include concrete data that matters (file size, row count, timezone), because those details are usually the trigger.
- Never invent a step the customer didn't describe. Mark inferred steps with `(inferred)`.
