# Support Skills Console

A web UI over the four support skills' scripts. It imports the scripts directly, so the UI and the command line always give the same answer. The policy doc and changelog are re-read on every request, so edits to `company-docs/` take effect immediately.

## Run

```bash
python webapp/app.py
```

Open http://127.0.0.1:5000. It needs Flask.

## Tabs

| Tab | Calls | Does |
|---|---|---|
| Triage | `POST /api/triage/validate` | Checks a triage record against `routing.json` |
| Reply check | `POST /api/reply/check` | Flags figures not in the live policy, money written in words, and banned phrases |
| QA report | `POST /api/qa/aggregate` | Validates grades against the rubric and builds the report (downloadable .md) |
| Known issues | `POST /api/bugs/search` | Ranks changelog entries against a symptom |

## Tests

```bash
python webapp/run_tests.py
```

Run a single suite with `python webapp/run_tests.py unit`, `api` or `e2e`.

- **unit** (`tests/test_units.py`): the scripts' pure functions, including edge cases (ranges, bool-as-int, word boundaries, live policy change).
- **api** (`tests/test_api.py`): every endpoint (and the security headers) through Flask's test client, including bad input (400/404/405/413), and checks the policy is reloaded live.
- **e2e** (`tests/test_e2e.py`): starts the real server on a random port and drives headless Chromium with Playwright. Covers every tab's happy and error paths, keyboard navigation, persistence across reload, an HTML-injection attempt, a simulated server 500, the download, mobile width, and fails on any browser console error.

They use the standard library's `unittest`. The e2e suite needs `playwright` with Chromium installed.
