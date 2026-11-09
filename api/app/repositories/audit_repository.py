"""Postgres repositories: HTTP request audit log and agent runs (SQLAlchemy 2 async)."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import and_, or_, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import AgentRun, ApiRequestLog


class RequestLogRepository(Protocol):
    async def add(self, entry: dict[str, Any]) -> None: ...


class RunRepository(Protocol):
    async def create(self, run: dict[str, Any]) -> None: ...
    async def finish(self, run_id: str, values: dict[str, Any]) -> None: ...
    async def mark_disconnected(self, run_id: str) -> None: ...
    async def get(self, run_id: str) -> dict[str, Any] | None: ...
    async def list(self, user_id: str | None, status: str | None, limit: int,
                   cursor: str | None) -> tuple[list[dict[str, Any]], str | None]: ...
    async def ping(self) -> None: ...


def _row(run: AgentRun) -> dict[str, Any]:
    return {c.name: getattr(run, c.name) for c in AgentRun.__table__.columns}


def encode_cursor(created_at: datetime, run_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{created_at.isoformat()}|{run_id}".encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        created, rid = base64.urlsafe_b64decode(cursor.encode()).decode().split("|", 1)
        return datetime.fromisoformat(created), uuid.UUID(rid)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid cursor") from exc


class SqlRequestLogRepository:
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def add(self, entry: dict[str, Any]) -> None:
        async with self._sessions() as session, session.begin():
            session.add(ApiRequestLog(**{**entry, "id": uuid.UUID(entry["id"])}))


class SqlRunRepository:
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, run: dict[str, Any]) -> None:
        async with self._sessions() as session, session.begin():
            session.add(AgentRun(**{**run, "id": uuid.UUID(run["id"])}))

    async def finish(self, run_id: str, values: dict[str, Any]) -> None:
        values = {**values, "finished_at": datetime.now(timezone.utc)}
        async with self._sessions() as session, session.begin():
            await session.execute(update(AgentRun).where(AgentRun.id == uuid.UUID(run_id)).values(**values))

    async def mark_disconnected(self, run_id: str) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(update(AgentRun).where(AgentRun.id == uuid.UUID(run_id))
                                  .values(client_disconnected=True))

    async def get(self, run_id: str) -> dict[str, Any] | None:
        async with self._sessions() as session:
            run = await session.get(AgentRun, uuid.UUID(run_id))
            return _row(run) if run else None

    async def list(self, user_id: str | None, status: str | None, limit: int,
                   cursor: str | None) -> tuple[list[dict[str, Any]], str | None]:
        query = select(AgentRun).order_by(AgentRun.created_at.desc(), AgentRun.id.desc()).limit(limit + 1)
        if user_id:
            query = query.where(AgentRun.user_id == user_id)
        if status:
            query = query.where(AgentRun.status == status)
        if cursor:
            created, rid = decode_cursor(cursor)
            query = query.where(or_(AgentRun.created_at < created,
                                    and_(AgentRun.created_at == created, AgentRun.id < rid)))
        async with self._sessions() as session:
            rows = list((await session.scalars(query)).all())
        next_cursor = encode_cursor(rows[limit - 1].created_at, rows[limit - 1].id) if len(rows) > limit else None
        return [_row(r) for r in rows[:limit]], next_cursor

    async def ping(self) -> None:
        async with self._sessions() as session:
            await session.execute(text("SELECT 1"))
