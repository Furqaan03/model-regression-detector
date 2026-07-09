"""LLM-as-judge scoring for summary relevance (1-5)."""
from __future__ import annotations

import json

from openai import OpenAI

JUDGE_SYSTEM_PROMPT = """You are grading a customer-support email summary for relevance and
accuracy against a reference summary. Score 1-5:
1 = unrelated or wrong, 3 = partially captures the gist, 5 = matches the reference summary's
meaning even if worded differently.

Respond with strict JSON: {"score": <1-5 integer>, "reasoning": "<one sentence>"}"""


def score_summary(candidate_summary: str, reference_summary: str, client: OpenAI | None = None) -> tuple[int, str]:
    client = client or OpenAI()
    user_prompt = (
        f"Reference summary: {reference_summary}\n"
        f"Candidate summary: {candidate_summary}\n"
        "Score the candidate."
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    parsed = json.loads(response.choices[0].message.content or "{}")
    return int(parsed.get("score", 1)), parsed.get("reasoning", "")
