"""Generates a self-contained HTML diff report for an eval run."""
from __future__ import annotations

from pathlib import Path

from src.eval.diff import RunDiff
from src.eval.runner import EvalRun

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

_STATUS_COLORS = {"ok": "#2e7d32", "warning": "#f9a825", "critical": "#c62828"}


def _case_rows(current: EvalRun, case_ids: set[str]) -> str:
    rows = []
    by_id = {r.case_id: r for r in current.results}
    for case_id in case_ids:
        r = by_id.get(case_id)
        if r is None:
            continue
        rows.append(
            f"<tr><td>{case_id}</td><td>{r.difficulty}</td>"
            f"<td>{r.predicted_category or 'ERROR: ' + (r.error or 'unknown')}</td>"
            f"<td>{r.summary_score}/5</td></tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='4'>none</td></tr>"


def render_html_report(current: EvalRun, diff: RunDiff) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    color = _STATUS_COLORS[diff.status]
    regression_ids = {r.case_id for r in diff.regressions}
    improvement_ids = {r.case_id for r in diff.improvements}

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Eval Diff Report — {current.run_id[:8]}</title>
<style>
body {{ font-family: -apple-system, Segoe UI, sans-serif; margin: 2rem; color: #1a1a1a; }}
.status {{ display: inline-block; padding: 4px 12px; border-radius: 6px; color: white; background: {color}; font-weight: 600; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 14px; }}
th {{ background: #f5f5f5; }}
.scorecard {{ display: flex; gap: 2rem; margin: 1.5rem 0; }}
.scorecard div {{ background: #f9f9f9; padding: 1rem; border-radius: 8px; }}
</style></head>
<body>
<h1>Model Regression Report</h1>
<p><span class="status">{diff.status.upper()}</span> — prompt {current.prompt_version}, model {current.model}, run {current.timestamp}</p>
<div class="scorecard">
  <div><strong>Pass rate</strong><br>{diff.baseline_pass_rate:.1%} → {diff.current_pass_rate:.1%} ({diff.pass_rate_delta_pct:+.1f}pp)</div>
  <div><strong>Category accuracy delta</strong><br>{diff.category_accuracy_delta_pct:+.1f}pp</div>
  <div><strong>Regressions</strong><br>{len(diff.regressions)}</div>
  <div><strong>Improvements</strong><br>{len(diff.improvements)}</div>
</div>
<h2>Regressed cases (pass → fail)</h2>
<table><tr><th>Case ID</th><th>Difficulty</th><th>Predicted category</th><th>Summary score</th></tr>
{_case_rows(current, regression_ids)}
</table>
<h2>Improved cases (fail → pass)</h2>
<table><tr><th>Case ID</th><th>Difficulty</th><th>Predicted category</th><th>Summary score</th></tr>
{_case_rows(current, improvement_ids)}
</table>
</body></html>"""

    out_path = REPORTS_DIR / f"report_{current.run_id[:8]}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path
