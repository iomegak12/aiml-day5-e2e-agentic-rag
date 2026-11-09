"""PII redaction for audit records: reuses the agent's LangChain PII detectors (agentic_rag.guardrails)."""

from __future__ import annotations

from typing import Any

from agentic_rag.guardrails import PII_DETECTORS

SENSITIVE_HEADERS = {"x-api-key", "authorization", "cookie", "set-cookie", "proxy-authorization"}


def redact_text(text: str) -> str:
    matches = [m for detector in PII_DETECTORS.values() for m in detector(text)]
    for m in sorted(matches, key=lambda m: m["start"], reverse=True):  # replace from the end: offsets stay valid
        text = f"{text[:m['start']]}[REDACTED_{m['type'].upper()}]{text[m['end']:]}"
    return text


def redact(value: Any) -> Any:
    """Recursively redact every string in a JSON-like structure."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: ("[REDACTED]" if k.lower() in SENSITIVE_HEADERS else v) for k, v in headers.items()}
