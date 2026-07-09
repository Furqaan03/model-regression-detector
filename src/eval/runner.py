"""Test runner: executes the golden dataset against a PromptConfig, scores every case."""
from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel

from src.classifier import classify_email
from src.eval.golden_dataset import GoldenCase, GoldenDataset
from src.eval.judge import score_summary
from src.prompt_config import PromptConfig

DB_PATH = Path(__file__).resolve().parent.parent.parent / "eval_runs.db"


class CaseResult(BaseModel):
    case_id: str
    category_match: bool
    predicted_category: str | None
    summary_score: int
    latency_ms: float
    input_tokens: int
    output_tokens: int
    error: str | None
    difficulty: str


class EvalRun(BaseModel):
    run_id: str
    prompt_version: str
    model: str
    timestamp: str
    results: list[CaseResult]

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        passes = sum(1 for r in self.results if r.category_match and r.summary_score >= 4)
        return passes / len(self.results)

    @property
    def category_accuracy(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.category_match) / len(self.results)

    def category_accuracy_by(self, key: str, value: str) -> float | None:
        subset = [r for r in self.results if getattr(r, key) == value]
        if not subset:
            return None
        return sum(1 for r in subset if r.category_match) / len(subset)


def _run_one_case(case: GoldenCase, config: PromptConfig, client: OpenAI) -> CaseResult:
    response = classify_email(case.input, config, client=client)
    if response.result is None:
        return CaseResult(
            case_id=case.id,
            category_match=False,
            predicted_category=None,
            summary_score=1,
            latency_ms=response.latency_ms,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            error=response.error,
            difficulty=case.difficulty,
        )

    category_match = response.result.category == case.expected_category
    summary_score, _reasoning = score_summary(response.result.summary, case.expected_summary, client=client)

    return CaseResult(
        case_id=case.id,
        category_match=category_match,
        predicted_category=response.result.category,
        summary_score=summary_score,
        latency_ms=response.latency_ms,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        error=None,
        difficulty=case.difficulty,
    )


async def run_eval(prompt_version: str, dataset_version: str = "v1", concurrency: int = 5) -> EvalRun:
    """Runs every golden case through the classifier under `prompt_version`, async-batched."""
    config = PromptConfig.load(prompt_version)
    dataset = GoldenDataset.load(dataset_version)
    client = OpenAI()

    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_run(case: GoldenCase) -> CaseResult:
        async with semaphore:
            return await asyncio.to_thread(_run_one_case, case, config, client)

    results = await asyncio.gather(*(bounded_run(case) for case in dataset.cases))

    run = EvalRun(
        run_id=str(uuid.uuid4()),
        prompt_version=prompt_version,
        model=config.model,
        timestamp=datetime.now(timezone.utc).isoformat(),
        results=list(results),
    )
    _persist_run(run)
    return run


def _persist_run(run: EvalRun) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS eval_runs (
            run_id TEXT PRIMARY KEY,
            prompt_version TEXT,
            model TEXT,
            timestamp TEXT,
            pass_rate REAL,
            category_accuracy REAL,
            raw_json TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO eval_runs VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            run.run_id,
            run.prompt_version,
            run.model,
            run.timestamp,
            run.pass_rate,
            run.category_accuracy,
            run.model_dump_json(),
        ),
    )
    conn.commit()
    conn.close()


def get_previous_run(exclude_run_id: str) -> EvalRun | None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS eval_runs (
            run_id TEXT PRIMARY KEY, prompt_version TEXT, model TEXT,
            timestamp TEXT, pass_rate REAL, category_accuracy REAL, raw_json TEXT
        )"""
    )
    row = conn.execute(
        "SELECT raw_json FROM eval_runs WHERE run_id != ? ORDER BY timestamp DESC LIMIT 1",
        (exclude_run_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return EvalRun(**json.loads(row[0]))
