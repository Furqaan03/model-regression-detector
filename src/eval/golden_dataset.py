"""Loads the versioned golden dataset."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "golden_dataset"


class GoldenCase(BaseModel):
    id: str
    input: str
    expected_category: str
    expected_summary: str
    difficulty: str
    notes: str


class GoldenDataset(BaseModel):
    dataset_version: str
    created_at: str
    cases: list[GoldenCase]

    @classmethod
    def load(cls, version: str = "v1") -> "GoldenDataset":
        path = DATASET_DIR / f"{version}.json"
        return cls(**json.loads(path.read_text(encoding="utf-8")))
