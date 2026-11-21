# Support Skills Console

Quality checks for a support team, run *before* anything reaches a customer:

| Tab | Checks |
|---|---|
| **Triage** | A ticket's category / team / urgency follows the routing rules |
| **Reply check** | A reply quotes no refund or price that isn't in the current policy, and uses no banned phrases |
| **QA report** | Weekly ticket scores → pass rate and recurring problems |
| **Known issues** | Whether a reported bug is already in the changelog |

![Reply check](webapp/screenshots/1-reply-check-light.png)

## What's in this repo

| Path | What it is |
|---|---|
| `.claude/skills/` | Four Claude Code skills (instructions + checking scripts). The web app runs these same scripts. |
| `company-docs/` | The refund/pricing policy and changelog the checks read on every request |
| `webapp/` | The Flask web app and its tests |
| `DECISIONS.md` | Why each workflow piece is a Skill, an Agent, or neither |
| `render.yaml` | Hosting config for Render |

## Run it on your computer

```bash
pip install -r requirements.txt
python webapp/app.py
```

Then open http://127.0.0.1:5000.

## Run the tests

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
python webapp/run_tests.py
```

## Host it on Render (free)

1. Push this folder to a GitHub repository.
2. Sign in at https://render.com with GitHub.
3. Click **New → Blueprint**, pick the repository, and click **Apply**. Render reads `render.yaml` and builds the app.
4. When the status turns **Live**, open the `https://support-skills-console-….onrender.com` URL it shows.

Every push to GitHub redeploys automatically. Editing `company-docs/refund-pricing-policy.md` and pushing updates the live policy.

> Free Render apps go to sleep after ~15 minutes without visitors. The next visit takes 30–60 seconds to wake it up. The app has no login, so anyone with the URL can use it. It only reads files and never stores what people type.
