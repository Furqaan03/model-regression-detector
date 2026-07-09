# Model Regression Detection System

CI/CD for LLM behavior. Runs a customer-support email classifier against a
hand-labeled golden dataset on every prompt change, diffs the results against
the previous baseline, flags regressions above a configurable threshold, and
posts a Slack alert with a link to a full HTML diff report — before a bad
prompt reaches production.

## Why this exists

Teams ship prompt changes blind. There's no equivalent of a test suite for
"did this prompt change make the model worse at its job." This is that test
suite, wired into GitHub Actions so it runs automatically on every PR that
touches `/prompts`.

## Architecture

```
prompts/v*.yaml          versioned prompt configs (system prompt + few-shot examples)
golden_dataset/v*.json   hand-labeled test cases (12 cases: simple, ambiguous, typo'd,
                          mixed-language, sarcastic, adversarial, multi-issue)
src/classifier.py        the feature under test — email -> {category, summary}
src/eval/runner.py       async test runner, multi-dimensional scoring, SQLite persistence
src/eval/judge.py        LLM-as-judge scoring for summary relevance (1-5)
src/eval/diff.py         baseline comparison, regression/improvement detection, thresholds
src/eval/drift.py        7-run rolling average — catches slow degradation single-run diffs miss
src/alerting/report.py   self-contained HTML diff report generator
src/alerting/slack.py    Slack incoming-webhook alerting
src/cli.py               orchestrates run -> diff -> report -> alert, used by CI
.github/workflows/       GitHub Action: triggers on prompt/dataset changes, blocks merge
                          on critical regressions
```

## Design decisions

- **Golden dataset is hand-labeled, not LLM-generated.** The entire point is
  a ground truth that doesn't share the model's blind spots. It seeds from 12
  hand-written cases and is meant to grow from real production failures over
  time (see Project 13 for the automated version of that growth loop).
- **Two-dimensional pass criteria**: a case only "passes" if both the category
  match is exact AND the LLM-judge summary score is >= 4/5. Category accuracy
  alone hides regressions in summary quality.
- **Slow drift is tracked separately from per-run regressions.** A single run
  might drop 2% (under the 3% warning threshold) but if that keeps happening
  for 7 runs straight, the moving average check fires even though no
  individual run tripped an alert. This catches gradual degradation that
  per-run diffing is blind to.
- **Statistical thresholds are configurable**, not hardcoded: warning at 3%
  pass-rate delta, critical at 8%, both overridable via env vars.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # then fill in OPENAI_API_KEY and SLACK_WEBHOOK_URL
```

## Running an eval

```bash
python -m src.cli --prompt-version v1
python -m src.cli --prompt-version v1 --slack             # also alert Slack on warning/critical
python -m src.cli --prompt-version v1 --fail-on-critical   # exit 1 on critical (used in CI)
```

Reports land in `reports/report_<run_id>.html`. Run history is in `eval_runs.db`
(SQLite, gitignored).

## Adding a new test case to the golden dataset

Add an entry to `golden_dataset/v1.json` with a unique `id`, the raw email
`input`, hand-verified `expected_category` / `expected_summary`, a `difficulty`
tag (`simple` / `moderate` / `hard` / `adversarial`), and a `notes` field
explaining why the case matters. Do not generate these with an LLM.

## Adjusting thresholds

Set `WARNING_THRESHOLD_PCT` / `CRITICAL_THRESHOLD_PCT` in `.env` (percentage-point
pass-rate drop that triggers each severity). Drift window/threshold are
arguments to `check_drift()` in `src/eval/drift.py`.

## Tests

```bash
pytest tests/ -v
```

## Docker

```bash
docker build -t model-regression-detector .
docker run --env-file .env model-regression-detector --prompt-version v1
```

## Status

Phases 1-5 complete (feature, golden dataset, eval engine, alerting/reporting,
CI wiring). Phase 6 (Loom walkthrough) is a manual recording step, not code.
