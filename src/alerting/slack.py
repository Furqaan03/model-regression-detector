"""Sends a structured Slack alert via incoming webhook."""
from __future__ import annotations

import os

import httpx

from src.eval.diff import RunDiff

_EMOJI = {"ok": ":white_check_mark:", "warning": ":warning:", "critical": ":rotating_light:"}


def send_slack_alert(diff: RunDiff, report_path: str) -> None:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("SLACK_WEBHOOK_URL is not set")

    emoji = _EMOJI[diff.status]
    text = (
        f"{emoji} *Eval run {diff.status.upper()}* — {diff.headline}\n"
        f"Report: {report_path}"
    )
    payload = {"text": text}

    with httpx.Client(timeout=10) as client:
        response = client.post(webhook_url, json=payload)
        response.raise_for_status()
