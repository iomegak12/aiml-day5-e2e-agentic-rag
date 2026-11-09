"""Ticket enums and the ticket view returned by every tool."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Severity = Literal["critical", "high", "medium", "low"]
ProductFamily = Literal["networking", "meetings"]
Region = Literal["AMER", "EMEA", "APAC"]
Status = Literal["open", "resolved"]
StatusFilter = Literal["open", "resolved", "all"]
JiraSync = Literal["pending", "synced"]

SEVERITIES: tuple[str, ...] = Severity.__args__
PRODUCT_FAMILIES: tuple[str, ...] = ProductFamily.__args__
REGIONS: tuple[str, ...] = Region.__args__
STATUSES: tuple[str, ...] = Status.__args__

# severity -> Jira priority
JIRA_PRIORITY = {"critical": "Highest", "high": "High", "medium": "Medium", "low": "Low"}


class TicketOut(BaseModel):
    ticket_id: str
    registered_at: datetime
    registered_by: str
    title: str
    description: str
    product_family: ProductFamily
    region: Region
    severity: Severity
    status: Status
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    remarks: str | None = None
    jira_key: str | None = None
    jira_url: str | None = None
    jira_sync: JiraSync = "pending"
    jira_error: str | None = None

    model_config = {"from_attributes": True}


class TicketList(BaseModel):
    count: int
    tickets: list[TicketOut]


class SyncReport(BaseModel):
    attempted: int
    synced: int
    still_pending: int
