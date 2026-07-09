from src.eval.diff import diff_runs
from src.eval.runner import CaseResult, EvalRun


def _run(run_id: str, matches: dict[str, bool]) -> EvalRun:
    results = [
        CaseResult(
            case_id=case_id,
            category_match=match,
            predicted_category="billing" if match else "technical",
            summary_score=5 if match else 2,
            latency_ms=100.0,
            input_tokens=50,
            output_tokens=20,
            error=None,
            difficulty="simple",
        )
        for case_id, match in matches.items()
    ]
    return EvalRun(run_id=run_id, prompt_version="v1", model="gpt-4o-mini", timestamp="2026-07-09T00:00:00Z", results=results)


def test_no_baseline_returns_ok_status():
    current = _run("current", {"a": True, "b": True})
    diff = diff_runs(current, None)
    assert diff.status == "ok"
    assert diff.baseline_run_id is None


def test_detects_regression():
    baseline = _run("baseline", {"a": True, "b": True, "c": True, "d": True, "e": True})
    current = _run("current", {"a": True, "b": False, "c": True, "d": True, "e": True})
    diff = diff_runs(current, baseline)
    assert len(diff.regressions) == 1
    assert diff.regressions[0].case_id == "b"


def test_detects_improvement():
    baseline = _run("baseline", {"a": False})
    current = _run("current", {"a": True})
    diff = diff_runs(current, baseline)
    assert len(diff.improvements) == 1
    assert diff.improvements[0].case_id == "a"


def test_critical_status_on_large_drop():
    baseline = _run("baseline", {f"case-{i}": True for i in range(20)})
    current_matches = {f"case-{i}": True for i in range(20)}
    for i in range(4):
        current_matches[f"case-{i}"] = False
    current = _run("current", current_matches)
    diff = diff_runs(current, baseline)
    assert diff.status == "critical"
