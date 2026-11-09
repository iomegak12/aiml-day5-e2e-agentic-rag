"""Shared DTOs: RFC 9457 problem (documentation model) and health/readiness."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Problem(BaseModel):
    """RFC 9457 Problem Details (media type application/problem+json)."""

    model_config = ConfigDict(extra="allow", json_schema_extra={"examples": [{
        "type": "https://netcore.example/problems/rate-limited", "title": "Too many requests", "status": 429,
        "detail": "Rate limit of 100 requests/minute exceeded; blocked for 30 s.", "instance": "/api/v1/agent/ask",
        "request_id": "6f1c7f0e-4c1e-4a43-9a52-0f7b1f3c2d11"}]})

    type: str = Field(description="URI identifying the problem type")
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    request_id: str | None = None
    errors: list[dict[str, Any]] | None = Field(None, description="Validation errors (422 only)")


class Health(BaseModel):
    status: str
    version: str


class Readiness(BaseModel):
    status: str
    checks: dict[str, dict[str, Any]]


PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem, "content": {"application/problem+json": {}}, "description": desc}
    for code, desc in {401: "Missing or invalid API key", 404: "Not found (or not yours)",
                       422: "Validation error", 429: "Rate limited (see Retry-After)",
                       500: "Internal error", 503: "Agent or dependency unavailable",
                       504: "Agent timeout"}.items()
}
