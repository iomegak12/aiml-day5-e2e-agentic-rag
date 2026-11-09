"""ORM models: one row per HTTP request (audit) and one row per agent run (results, reconnect)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONType


class ApiRequestLog(Base):
    """Request metadata + (PII-redacted) request/response bodies for every audited HTTP request."""

    __tablename__ = "api_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # = X-Request-ID
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(512), index=True)
    route: Mapped[str | None] = mapped_column(String(256))
    query_string: Mapped[str | None] = mapped_column(Text)
    client_ip: Mapped[str | None] = mapped_column(String(64), index=True)
    user_agent: Mapped[str | None] = mapped_column(String(512))
    user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    status_code: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[float] = mapped_column(Float)
    request_headers: Mapped[dict | None] = mapped_column(JSONType)
    request_body: Mapped[dict | list | str | None] = mapped_column(JSONType)
    response_headers: Mapped[dict | None] = mapped_column(JSONType)
    response_body: Mapped[dict | list | str | None] = mapped_column(JSONType)
    body_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128))


class AgentRun(Base):
    """One agent run (POST /ask or /ask/stream). The id equals the HTTP request id of the call that started it."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(32))
    client_ip: Mapped[str | None] = mapped_column(String(64))
    endpoint: Mapped[str] = mapped_column(String(16))  # sync | stream
    mode: Mapped[str] = mapped_column(String(16))
    question: Mapped[str] = mapped_column(Text)  # PII-redacted
    options: Mapped[dict] = mapped_column(JSONType)
    status: Mapped[str] = mapped_column(String(32))  # running | completed | failed | timeout | client_disconnected
    agent_status: Mapped[str | None] = mapped_column(String(32))  # answered | cache_hit | no_info | blocked | ...
    client_disconnected: Mapped[bool] = mapped_column(Boolean, default=False)
    elapsed_s: Mapped[float | None] = mapped_column(Float)
    result: Mapped[dict | None] = mapped_column(JSONType)  # AskResponse (PII-redacted)
    error: Mapped[dict | None] = mapped_column(JSONType)  # RFC 9457 problem

    __table_args__ = (
        Index("ix_agent_runs_user_created", "user_id", "created_at"),
        Index("ix_agent_runs_status", "status"),
    )
