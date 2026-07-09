"""The LLM feature under test: a customer support email classifier."""
from __future__ import annotations

import json
import time

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from src.prompt_config import PromptConfig

CATEGORIES = {"billing", "technical", "account", "general"}


class ClassificationResult(BaseModel):
    category: str
    summary: str


class ClassifierResponse(BaseModel):
    result: ClassificationResult | None
    raw_output: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    error: str | None = None


def _build_messages(config: PromptConfig, email_text: str) -> list[dict]:
    messages = [{"role": "system", "content": config.system_prompt}]
    for ex in config.few_shot_examples:
        messages.append({"role": "user", "content": ex.input})
        messages.append({"role": "assistant", "content": ex.output})
    messages.append({"role": "user", "content": email_text})
    return messages


def classify_email(email_text: str, config: PromptConfig, client: OpenAI | None = None) -> ClassifierResponse:
    """Runs one email through the classifier feature and returns a typed response."""
    client = client or OpenAI()
    messages = _build_messages(config, email_text)

    start = time.perf_counter()
    response = client.chat.completions.create(
        model=config.model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )
    latency_ms = (time.perf_counter() - start) * 1000

    raw = response.choices[0].message.content or ""
    usage = response.usage

    try:
        parsed = json.loads(raw)
        result = ClassificationResult(**parsed)
        if result.category not in CATEGORIES:
            raise ValueError(f"Unknown category '{result.category}'")
        error = None
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        result = None
        error = str(exc)

    return ClassifierResponse(
        result=result,
        raw_output=raw,
        latency_ms=latency_ms,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        error=error,
    )
