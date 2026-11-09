"""SQLAlchemy model: itsm.tickets (own metadata and Alembic chain, separate from the API's tables)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    Identity,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA = "itsm"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # readable id derived from the identity sequence: TKT-000123
    ticket_id: Mapped[str] = mapped_column(String(16), Computed("'TKT-' || lpad(id::text, 6, '0')", persisted=True),
                                           unique=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    registered_by: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    product_family: Mapped[str] = mapped_column(String(32))
    region: Mapped[str] = mapped_column(String(8))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), server_default="open")
    resolved_by: Mapped[str | None] = mapped_column(String(64))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remarks: Mapped[str | None] = mapped_column(Text)
    # Jira mirror (one-way: Postgres -> Jira)
    jira_id: Mapped[str | None] = mapped_column(String(32))
    jira_key: Mapped[str | None] = mapped_column(String(32))
    jira_url: Mapped[str | None] = mapped_column(String(300))
    jira_status: Mapped[str | None] = mapped_column(String(32))  # status last set in Jira by us
    jira_comment_id: Mapped[str | None] = mapped_column(String(32))  # resolution comment (avoids duplicates)
    jira_sync: Mapped[str] = mapped_column(String(16), server_default="pending")
    jira_error: Mapped[str | None] = mapped_column(Text)
    jira_attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())

    __table_args__ = (
        CheckConstraint(_in("product_family", ("networking", "meetings")), name="ck_tickets_product_family"),
        CheckConstraint(_in("region", ("AMER", "EMEA", "APAC")), name="ck_tickets_region"),
        CheckConstraint(_in("severity", ("critical", "high", "medium", "low")), name="ck_tickets_severity"),
        CheckConstraint(_in("status", ("open", "resolved")), name="ck_tickets_status"),
        CheckConstraint(_in("jira_sync", ("pending", "synced")), name="ck_tickets_jira_sync"),
        Index("ix_tickets_registered_by_status", "registered_by", "status"),
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_jira_sync", "jira_sync"),
    )
