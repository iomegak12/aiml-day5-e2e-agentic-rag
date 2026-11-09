"""Ticket use cases: RBAC, Postgres first (source of truth), then the one-way Jira mirror."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

from fastmcp.exceptions import ToolError

from netcore_mcp.identity import Caller
from netcore_mcp.jira import JiraClient, JiraError
from netcore_mcp.repository import TicketQuery, TicketRepository
from netcore_mcp.schemas import SyncReport, TicketList, TicketOut

log = logging.getLogger("netcore_mcp")

_ID = re.compile(r"^(?:TKT-?)?0*(\d{1,9})$", re.IGNORECASE)


def normalize_ticket_id(value: str) -> str:
    """'TKT-000123', 'tkt-123' and '123' -> 'TKT-000123'."""
    match = _ID.match(value.strip())
    if not match:
        raise ToolError(f"Invalid ticket id '{value}'. Expected the form TKT-000123.")
    return f"TKT-{int(match.group(1)):06d}"


def require_admin(caller: Caller, action: str) -> None:
    if not caller.is_admin:
        raise ToolError(f"Permission denied: only administrators can {action}. "
                        f"'{caller.user_id}' has the role '{caller.role}'.")


class TicketService:
    def __init__(self, repo: TicketRepository, jira: JiraClient):
        self.repo = repo
        self.jira = jira
        self._sync_lock = asyncio.Lock()  # one Jira sync at a time: no duplicate issues (single-process server)

    # ---------------------------- use cases ----------------------------

    async def register(self, caller: Caller, *, title: str, description: str, product_family: str, region: str,
                       severity: str) -> TicketOut:
        ticket = await self.repo.add(registered_by=caller.user_id, title=title.strip(),
                                     description=description.strip(), product_family=product_family, region=region,
                                     severity=severity, status="open", jira_sync="pending", jira_attempts=0)
        log.info("ticket %s registered by %s", ticket.ticket_id, caller.user_id)
        return TicketOut.model_validate(await self.sync_ticket(ticket))

    async def list_mine(self, caller: Caller, status: str = "open", limit: int = 20) -> TicketList:
        tickets = await self.repo.find(TicketQuery(status=status, registered_by=caller.user_id, limit=limit))
        return _list(tickets)

    async def get(self, caller: Caller, ticket_id: str) -> TicketOut:
        ticket = await self.repo.get(normalize_ticket_id(ticket_id))
        # same message for "missing" and "someone else's": does not reveal that another user's ticket exists
        if ticket is None or (ticket.registered_by != caller.user_id and not caller.is_admin):
            raise ToolError(f"Ticket {normalize_ticket_id(ticket_id)} not found.")
        return TicketOut.model_validate(ticket)

    async def search(self, caller: Caller, query: TicketQuery) -> TicketList:
        require_admin(caller, "search all tickets")
        if query.date_from and query.date_to and query.date_from > query.date_to:
            raise ToolError("date_from must be on or before date_to.")
        return _list(await self.repo.find(query))

    async def resolve(self, caller: Caller, ticket_id: str, remarks: str) -> TicketOut:
        require_admin(caller, "resolve tickets")
        tid = normalize_ticket_id(ticket_id)
        ticket = await self.repo.get(tid)
        if ticket is None:
            raise ToolError(f"Ticket {tid} not found.")
        if ticket.status == "resolved":
            raise ToolError(f"Ticket {tid} is already resolved (by {ticket.resolved_by}).")
        ticket = await self.repo.update(tid, status="resolved", resolved_by=caller.user_id,
                                        resolved_at=datetime.now(timezone.utc), remarks=remarks.strip(),
                                        jira_sync="pending")
        log.info("ticket %s resolved by %s", tid, caller.user_id)
        return TicketOut.model_validate(await self.sync_ticket(ticket))

    async def sync_pending(self, limit: int = 50) -> SyncReport:
        pending = await self.repo.pending_sync(limit)
        synced = 0
        for ticket in pending:
            synced += (await self.sync_ticket(ticket)).jira_sync == "synced"
        return SyncReport(attempted=len(pending), synced=synced, still_pending=len(pending) - synced)

    # ---------------------------- Jira mirror ----------------------------

    async def sync_ticket(self, ticket: Any) -> Any:
        """Bring Jira in line with the ticket. Each finished step is saved at once, so a retry never repeats it
        (no duplicate issues or comments). On failure the ticket stays 'pending' with the error recorded."""
        async with self._sync_lock:
            ticket = await self.repo.get(ticket.ticket_id) or ticket  # latest state (the loop may have synced it)
            if ticket.jira_sync == "synced":
                return ticket
            tid = ticket.ticket_id
            try:
                if not ticket.jira_key:
                    issue = await self.jira.create_issue(ticket)
                    ticket = await self.repo.update(tid, jira_id=issue.id, jira_key=issue.key, jira_url=issue.url,
                                                    jira_status="To Do")
                    log.info("ticket %s -> Jira %s", tid, issue.key)
                if ticket.status == "resolved":
                    if not ticket.jira_comment_id:
                        comment_id = await self.jira.add_comment(
                            ticket.jira_key, ticket.remarks or "-",
                            header=f"Resolved by {ticket.resolved_by} ({tid})")
                        ticket = await self.repo.update(tid, jira_comment_id=comment_id)
                    if ticket.jira_status != self.jira.settings.jira_resolve_transition:
                        new_status = await self.jira.resolve(ticket.jira_key)
                        ticket = await self.repo.update(tid, jira_status=new_status)
                return await self.repo.update(tid, jira_sync="synced", jira_error=None,
                                              jira_attempts=ticket.jira_attempts + 1)
            except JiraError as exc:
                log.warning("ticket %s: Jira sync pending - %s", tid, exc)
                return await self.repo.update(tid, jira_sync="pending", jira_error=str(exc)[:500],
                                              jira_attempts=ticket.jira_attempts + 1)


def _list(tickets: list) -> TicketList:
    return TicketList(count=len(tickets), tickets=[TicketOut.model_validate(t) for t in tickets])


async def sync_loop(service: TicketService, interval: int) -> None:
    """Background retry of pending Jira syncs (started by the server lifespan)."""
    while True:
        await asyncio.sleep(interval)
        try:
            report = await service.sync_pending()
            if report.attempted:
                log.info("Jira sync loop: %s", report.model_dump())
        except Exception:  # noqa: BLE001 - keep the loop alive (DB restart, ...)
            log.exception("Jira sync loop failed")
