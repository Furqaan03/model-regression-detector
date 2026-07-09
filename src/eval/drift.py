"""Rolling-average drift detection: catches gradual degradation across runs."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "eval_runs.db"


def moving_average_pass_rate(window: int = 7) -> float | None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS eval_runs (
            run_id TEXT PRIMARY KEY, prompt_version TEXT, model TEXT,
            timestamp TEXT, pass_rate REAL, category_accuracy REAL, raw_json TEXT
        )"""
    )
    rows = conn.execute(
        "SELECT pass_rate FROM eval_runs ORDER BY timestamp DESC LIMIT ?", (window,)
    ).fetchall()
    conn.close()
    if not rows:
        return None
    return sum(r[0] for r in rows) / len(rows)


def check_drift(threshold: float = 0.85, window: int = 7) -> tuple[bool, float | None]:
    """Returns (is_drifting, moving_average). Drifting if the N-run average is below threshold
    even though no single run may have crossed the per-run alert threshold."""
    avg = moving_average_pass_rate(window)
    if avg is None:
        return False, None
    return avg < threshold, avg
