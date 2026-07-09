"""CLI entry point: run eval, diff against baseline, generate report, alert."""
from __future__ import annotations

import argparse
import asyncio
import sys

from dotenv import load_dotenv

from src.alerting.report import render_html_report
from src.alerting.slack import send_slack_alert
from src.eval.diff import diff_runs
from src.eval.drift import check_drift
from src.eval.runner import get_previous_run, run_eval

load_dotenv()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run the eval suite against a prompt version.")
    parser.add_argument("--prompt-version", default="v1")
    parser.add_argument("--dataset-version", default="v1")
    parser.add_argument("--slack", action="store_true", help="Send a Slack alert on warning/critical")
    parser.add_argument("--fail-on-critical", action="store_true", help="Exit non-zero on critical regressions (for CI)")
    args = parser.parse_args()

    print(f"Running eval: prompt={args.prompt_version} dataset={args.dataset_version}")
    current = await run_eval(args.prompt_version, args.dataset_version)
    baseline = get_previous_run(exclude_run_id=current.run_id)
    diff = diff_runs(current, baseline)

    report_path = render_html_report(current, diff)
    print(f"Status: {diff.status.upper()} | {diff.headline}")
    print(f"Report: {report_path}")

    is_drifting, moving_avg = check_drift()
    if is_drifting:
        print(f"DRIFT WARNING: 7-run moving average pass rate is {moving_avg:.1%}, below threshold")

    if args.slack and diff.status != "ok":
        send_slack_alert(diff, str(report_path))
        print("Slack alert sent.")

    if args.fail_on_critical and diff.status == "critical":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
