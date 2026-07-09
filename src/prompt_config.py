"""Loads and validates versioned prompt configs from /prompts."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class FewShotExample(BaseModel):
    input: str
    output: str


class PromptConfig(BaseModel):
    version: str
    created_at: str
    model: str
    system_prompt: str
    few_shot_examples: list[FewShotExample] = Field(default_factory=list)

    @classmethod
    def load(cls, version: str) -> "PromptConfig":
        path = PROMPTS_DIR / f"{version}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"No prompt file for version '{version}' at {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(**data)

    @classmethod
    def latest(cls) -> "PromptConfig":
        versions = sorted(p.stem for p in PROMPTS_DIR.glob("v*.yaml"))
        if not versions:
            raise FileNotFoundError(f"No prompt versions found in {PROMPTS_DIR}")
        return cls.load(versions[-1])
