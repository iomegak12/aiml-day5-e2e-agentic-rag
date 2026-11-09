"""Ticket persistence: the Postgres repository (async SQLAlchemy) behind a small interface the tests can fake."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Protocol

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from netcore_mcp.models import Ticket


@dataclass(frozen=True)
class TicketQuery:
    """Filters for list/search. None = no filter. status 'all' = open and resolved."""

    status: str = "open"
    registered_by: str | None = None
    keyword: str | None = None
    product_family: str | None = None
    region: str | None = None
    severity: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    limit: int = 20


class TicketRepository(Protocol):
    async def add(self, **fields: Any) -> Ticket: ...
    async def get(self, ticket_id: str) -> Ticket | None: ...
    async def find(self, query: TicketQuery) -> list[Ticket]: ...
    async def update(self, ticket_id: str, **fields: Any) -> Ticket: ...
    async def pending_sync(self, limit: int = 50) -> list[Ticket]: ...
    async def ping(self) -> None: ...


def day_bounds(d_from: date | None, d_to: date | None) -> tuple[datetime | None, datetime | None]:
    """Inclusive date range -> [from 00:00 UTC, to+1 00:00 UTC)."""
    start = datetime.combine(d_from, time.min, tzinfo=timezone.utc) if d_from else None
    end = datetime.combine(d_to + timedelta(days=1), time.min, tzinfo=timezone.utc) if d_to else None
    return start, end


class SqlTicketRepository:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self._sessions = async_sessionmaker(engine, expire_on_commit=False)

    @classmethod
    def from_url(cls, database_url: str) -> SqlTicketRepository:
        return cls(create_async_engine(database_url, pool_pre_ping=True, pool_size=5, max_overflow=5))

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def ping(self) -> None:
        async with self._sessions() as session:
            await session.execute(select(1))

    async def add(self, **fields: Any) -> Ticket:
        async with self._sessions() as session, session.begin():
            ticket = Ticket(**fields)
            session.add(ticket)
            await session.flush()
            await session.refresh(ticket)  # load server-side values: ticket_id, registered_at, ...
            return ticket

    async def get(self, ticket_id: str) -> Ticket | None:
        async with self._sessions() as session:
            return await session.scalar(select(Ticket).where(Ticket.ticket_id == ticket_id.upper()))

    async def find(self, query: TicketQuery) -> list[Ticket]:
        stmt = select(Ticket)
        if query.status != "all":
            stmt = stmt.where(Ticket.status == query.status)
        for column, value in ((Ticket.registered_by, query.registered_by), (Ticket.product_family,
                              query.product_family), (Ticket.region, query.region), (Ticket.severity, query.severity)):
            if value:
                stmt = stmt.where(column == value)
        if query.keyword:
            pattern = f"%{query.keyword}%"
            stmt = stmt.where(or_(Ticket.title.ilike(pattern), Ticket.description.ilike(pattern)))
        start, end = day_bounds(query.date_from, query.date_to)
        if start:
            stmt = stmt.where(Ticket.registered_at >= start)
        if end:
            stmt = stmt.where(Ticket.registered_at < end)
        stmt = stmt.order_by(Ticket.registered_at.desc(), Ticket.id.desc()).limit(query.limit)
        async with self._sessions() as session:
            return list(await session.scalars(stmt))

    async def update(self, ticket_id: str, **fields: Any) -> Ticket:
        async with self._sessions() as session, session.begin():
            ticket = await session.scalar(select(Ticket).where(Ticket.ticket_id == ticket_id).with_for_update())
            if ticket is None:
                raise KeyError(ticket_id)
            for name, value in fields.items():
                setattr(ticket, name, value)
            await session.flush()
            await session.refresh(ticket)
            return ticket

    async def pending_sync(self, limit: int = 50) -> list[Ticket]:
        stmt = select(Ticket).where(Ticket.jira_sync == "pending").order_by(Ticket.id).limit(limit)
        async with self._sessions() as session:
            return list(await session.scalars(stmt))
