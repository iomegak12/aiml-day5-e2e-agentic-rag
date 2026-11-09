"""FastMCP server: IT support ticket tools over streamable HTTP (POST/GET /mcp) plus GET /health.

The caller is identified by the `X-User-Id` header (see identity.py). RBAC:
  everyone : register_ticket, list_my_tickets, get_ticket (own tickets)
  admin    : search_tickets, resolve_ticket, sync_pending_tickets, get_ticket (any ticket)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from netcore_mcp import __version__
from netcore_mcp.config import get_settings
from netcore_mcp.identity import current_caller
from netcore_mcp.jira import JiraClient
from netcore_mcp.repository import SqlTicketRepository, TicketQuery
from netcore_mcp.schemas import (
    ProductFamily,
    Region,
    Severity,
    StatusFilter,
    SyncReport,
    TicketList,
    TicketOut,
)
from netcore_mcp.service import TicketService, require_admin, sync_loop

log = logging.getLogger("netcore_mcp")

INSTRUCTIONS = """NetCore IT support tickets. Tickets are stored in Postgres and mirrored to Jira (project KAN).
Only register or resolve a ticket when the user explicitly asks for it. Never invent field values: ask the user
for missing ones. Ticket ids look like TKT-000123."""

READ_ONLY = {"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False}
WRITE = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True}

TicketId = Annotated[str, Field(description="Ticket id, e.g. TKT-000123", min_length=1, max_length=16)]
Limit = Annotated[int, Field(ge=1, le=100, description="Maximum number of tickets to return")]


def create_server(service: TicketService | None = None) -> FastMCP:
    """Build the server. Tests pass a ready `service`; otherwise the lifespan connects Postgres and Jira and
    starts the background Jira sync loop."""
    holder: dict[str, TicketService] = {}

    @contextlib.asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[dict]:
        if service is not None:
            holder["service"] = service
            yield {}
            return
        settings = get_settings()
        repo = SqlTicketRepository.from_url(settings.database_url)
        jira = JiraClient(settings)
        holder["service"] = svc = TicketService(repo, jira)
        if not jira.enabled:
            log.warning("Jira is not configured: tickets are stored with jira_sync=pending")
        loop_task = (asyncio.create_task(sync_loop(svc, settings.jira_sync_interval_seconds))
                     if settings.jira_sync_interval_seconds > 0 else None)
        log.info("netcore-tickets %s ready (Jira project %s)", __version__, settings.jira_project_key)
        try:
            yield {}
        finally:
            if loop_task:
                loop_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await loop_task
            await jira.aclose()
            await repo.dispose()

    mcp = FastMCP("netcore-tickets", instructions=INSTRUCTIONS, version=__version__, lifespan=lifespan,
                  mask_error_details=True)

    def svc() -> TicketService:
        return holder["service"]

    @mcp.tool(annotations=WRITE, tags={"tickets", "write"})
    async def register_ticket(
        title: Annotated[str, Field(min_length=3, max_length=200, description="Short summary of the problem")],
        description: Annotated[str, Field(min_length=3, max_length=4000,
                                          description="What happened, impact and any error codes")],
        product_family: Annotated[ProductFamily, Field(description="networking (SD-WAN, edges, QoS, ...) or "
                                                                   "meetings (Meet, Calling, ...)")],
        region: Annotated[Region, Field(description="AMER, EMEA or APAC")],
        severity: Annotated[Severity, Field(description="critical, high, medium or low")],
    ) -> TicketOut:
        """Register a new IT support ticket for the calling user. Use ONLY when the user explicitly asks to open,
        raise or log a ticket. The ticket is stored and mirrored to Jira (jira_sync=pending if Jira is down)."""
        return await svc().register(current_caller(), title=title, description=description,
                                    product_family=product_family, region=region, severity=severity)

    @mcp.tool(annotations=READ_ONLY, tags={"tickets", "read"})
    async def list_my_tickets(status: StatusFilter = "open", limit: Limit = 20) -> TicketList:
        """List the tickets registered by the calling user, newest first. status: open (default), resolved or all."""
        return await svc().list_mine(current_caller(), status, limit)

    @mcp.tool(annotations=READ_ONLY, tags={"tickets", "read"})
    async def get_ticket(ticket_id: TicketId) -> TicketOut:
        """Show one ticket with its Jira link and resolution. Users see their own tickets; admins see any."""
        return await svc().get(current_caller(), ticket_id)

    @mcp.tool(annotations=READ_ONLY, tags={"tickets", "read", "admin"})
    async def search_tickets(
        keyword: Annotated[str | None, Field(max_length=100, description="Text in the title or description")] = None,
        product_family: ProductFamily | None = None,
        region: Region | None = None,
        severity: Severity | None = None,
        registered_by: Annotated[str | None, Field(max_length=64, description="User id, e.g. bob")] = None,
        date_from: Annotated[date | None, Field(description="Registered on or after (YYYY-MM-DD)")] = None,
        date_to: Annotated[date | None, Field(description="Registered on or before (YYYY-MM-DD)")] = None,
        status: StatusFilter = "open",
        limit: Limit = 20,
    ) -> TicketList:
        """ADMIN ONLY. Search all users' tickets (default: open ones), newest first, with optional filters."""
        query = TicketQuery(status=status, keyword=keyword or None, product_family=product_family, region=region,
                            severity=severity, registered_by=(registered_by or "").lower() or None,
                            date_from=date_from, date_to=date_to, limit=limit)
        return await svc().search(current_caller(), query)

    @mcp.tool(annotations=WRITE, tags={"tickets", "write", "admin"})
    async def resolve_ticket(
        ticket_id: TicketId,
        remarks: Annotated[str, Field(min_length=3, max_length=2000,
                                      description="Resolution notes (required); added to Jira as a comment")],
    ) -> TicketOut:
        """ADMIN ONLY. Resolve an open ticket with remarks. Use ONLY when the user explicitly asks to resolve or
        close it. Jira gets the remarks as a comment and moves to Resolved."""
        return await svc().resolve(current_caller(), ticket_id, remarks)

    @mcp.tool(annotations={**WRITE, "idempotentHint": True}, tags={"tickets", "admin"})
    async def sync_pending_tickets() -> SyncReport:
        """ADMIN ONLY. Retry the Jira sync of tickets whose sync is still pending; returns the counts."""
        require_admin(current_caller(), "sync tickets with Jira")
        return await svc().sync_pending()

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        """Liveness + database check (used by the container healthcheck)."""
        service_ = holder.get("service")
        body = {"status": "ok", "version": __version__, "jira_configured": get_settings().jira_enabled}
        try:
            if service_ is None:
                raise RuntimeError("starting")
            await asyncio.wait_for(service_.repo.ping(), timeout=3)
        except Exception as exc:  # noqa: BLE001
            return JSONResponse({**body, "status": "unavailable", "detail": type(exc).__name__}, status_code=503)
        return JSONResponse(body)

    return mcp
