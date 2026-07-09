"""Diffs two eval runs and classifies the delta as ok / warning / critical."""
from __future__ import annotations

import os

from pydantic import BaseModel

from src.eval.runner import EvalRun

WARNING_THRESHOLD_PCT = float(os.getenv("WARNING_THRESHOLD_PCT", "3"))
CRITICAL_THRESHOLD_PCT = float(os.getenv("CRITICAL_THRESHOLD_PCT", "8"))


class FlippedCase(BaseModel):
    case_id: str
    difficulty: str
    direction: str  # "regression" or "improvement"


class RunDiff(BaseModel):
    baseline_run_id: str | None
    current_run_id: str
    baseline_pass_rate: float
    current_pass_rate: float
    pass_rate_delta_pct: float
    category_accuracy_delta_pct: float
    regressions: list[FlippedCase]
    improvements: list[FlippedCase]
    status: str  # "ok" | "warning" | "critical"

    @property
    def headline(self) -> str:
        arrow = "down" if self.pass_rate_delta_pct < 0 else "up"
        return (
            f"{len(self.regressions)} regressions detected, accuracy {arrow} "
            f"from {self.baseline_pass_rate:.1%} to {self.current_pass_rate:.1%}"
        )


def diff_runs(current: EvalRun, baseline: EvalRun | None) -> RunDiff:
    if baseline is None:
        return RunDiff(
            baseline_run_id=None,
            current_run_id=current.run_id,
            baseline_pass_rate=0.0,
            current_pass_rate=current.pass_rate,
            pass_rate_delta_pct=0.0,
            category_accuracy_delta_pct=0.0,
            regressions=[],
            improvements=[],
            status="ok",
        )

    baseline_by_id = {r.case_id: r for r in baseline.results}
    regressions: list[FlippedCase] = []
    improvements: list[FlippedCase] = []

    for result in current.results:
        prev = baseline_by_id.get(result.case_id)
        if prev is None:
            continue
        prev_pass = prev.category_match and prev.summary_score >= 4
        curr_pass = result.category_match and result.summary_score >= 4
        if prev_pass and not curr_pass:
            regressions.append(FlippedCase(case_id=result.case_id, difficulty=result.difficulty, direction="regression"))
        elif not prev_pass and curr_pass:
            improvements.append(FlippedCase(case_id=result.case_id, difficulty=result.difficulty, direction="improvement"))

    pass_rate_delta_pct = (current.pass_rate - baseline.pass_rate) * 100
    category_accuracy_delta_pct = (current.category_accuracy - baseline.category_accuracy) * 100

    magnitude = abs(pass_rate_delta_pct)
    if magnitude >= CRITICAL_THRESHOLD_PCT and pass_rate_delta_pct < 0:
        status = "critical"
    elif magnitude >= WARNING_THRESHOLD_PCT and pass_rate_delta_pct < 0:
        status = "warning"
    else:
        status = "ok"

    return RunDiff(
        baseline_run_id=baseline.run_id,
        current_run_id=current.run_id,
        baseline_pass_rate=baseline.pass_rate,
        current_pass_rate=current.pass_rate,
        pass_rate_delta_pct=pass_rate_delta_pct,
        category_accuracy_delta_pct=category_accuracy_delta_pct,
        regressions=regressions,
        improvements=improvements,
        status=status,
    )
