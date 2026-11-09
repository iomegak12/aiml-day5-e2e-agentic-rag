"""Fixtures: in-memory ticket repository, respx-mocked Jira Cloud and an in-memory FastMCP client.

No network, Postgres or Jira needed. The caller is chosen with `client.as_user("bob")`, which feeds the
X-User-Id header lookup (in-memory transport has no HTTP headers).
"""

from __future__ import annotations

import itertools
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
import respx
from fastmcp import Client

from netcore_mcp import identity
from netcore_mcp.config import McpSettings
from netcore_mcp.jira import JiraClient
from netcore_mcp.repository import TicketQuery, day_bounds
from netcore_mcp.server import create_server
from netcore_mcp.service import TicketService

SITE = "https://example.atlassian.net"


class FakeTicketRepository:
    """Mimics SqlTicketRepository (identity id, computed TKT-id, server defaults, ordering)."""

    def __init__(self):
        self.rows: dict[str, SimpleNamespace] = {}
        self._ids = itertools.count(1)
        self.clock: datetime | None = None  # fixed registered_at for date-filter tests

    async def ping(self) -> None:
        return None

    async def add(self, **fields) -> SimpleNamespace:
        n = next(self._ids)
        now = self.clock or datetime.now(timezone.utc)
        row = SimpleNamespace(id=n, ticket_id=f"TKT-{n:06d}", registered_at=now, updated_at=now, resolved_by=None,
                              resolved_at=None, remarks=None, jira_id=None, jira_key=None, jira_url=None,
                              jira_status=None, jira_comment_id=None, jira_error=None, **fields)
        self.rows[row.ticket_id] = row
        return SimpleNamespace(**vars(row))

    async def get(self, ticket_id: str):
        row = self.rows.get(ticket_id.upper())
        return SimpleNamespace(**vars(row)) if row else None

    async def find(self, q: TicketQuery) -> list:
        start, end = day_bounds(q.date_from, q.date_to)
        out = [r for r in self.rows.values()
               if (q.status == "all" or r.status == q.status)
               and (not q.registered_by or r.registered_by == q.registered_by)
               and (not q.product_family or r.product_family == q.product_family)
               and (not q.region or r.region == q.region)
               and (not q.severity or r.severity == q.severity)
               and (not q.keyword or q.keyword.lower() in (r.title + " " + r.description).lower())
               and (not start or r.registered_at >= start) and (not end or r.registered_at < end)]
        out.sort(key=lambda r: (r.registered_at, r.id), reverse=True)
        return [SimpleNamespace(**vars(r)) for r in out[: q.limit]]

    async def update(self, ticket_id: str, **fields):
        row = self.rows[ticket_id]
        for k, v in fields.items():
            setattr(row, k, v)
        return SimpleNamespace(**vars(row))

    async def pending_sync(self, limit: int = 50) -> list:
        return [SimpleNamespace(**vars(r)) for r in self.rows.values() if r.jira_sync == "pending"][:limit]


class FakeJira:
    """respx routes for the Jira REST v3 calls the server makes; records every request body."""

    def __init__(self, router: respx.Router):
        self.router = router
        self.issues = itertools.count(1)
        self.fail = False  # True -> every call returns 503 (Jira outage)
        self.created: list[dict] = []
        self.comments: list[tuple[str, dict]] = []
        self.transitions: list[tuple[str, str]] = []
        router.post(f"{SITE}/rest/api/3/issue").mock(side_effect=self._create)
        router.post(url__regex=rf"{SITE}/rest/api/3/issue/(?P<key>[A-Z]+-\d+)/comment").mock(side_effect=self._comment)
        router.get(url__regex=rf"{SITE}/rest/api/3/issue/(?P<key>[A-Z]+-\d+)/transitions").mock(
            side_effect=self._list_transitions)
        router.post(url__regex=rf"{SITE}/rest/api/3/issue/(?P<key>[A-Z]+-\d+)/transitions").mock(
            side_effect=self._transition)

    def _outage(self):
        return httpx.Response(503, json={"errorMessages": ["Service unavailable"]}) if self.fail else None

    def _create(self, request):
        if r := self._outage():
            return r
        self.created.append(json.loads(request.content)["fields"])
        n = next(self.issues)
        return httpx.Response(201, json={"id": str(10000 + n), "key": f"KAN-{n}", "self": f"{SITE}/x"})

    def _comment(self, request, key):
        if r := self._outage():
            return r
        self.comments.append((key, json.loads(request.content)["body"]))
        return httpx.Response(201, json={"id": str(500 + len(self.comments))})

    def _list_transitions(self, request, key):
        if r := self._outage():
            return r
        return httpx.Response(200, json={"transitions": [
            {"id": "11", "name": "To Do", "to": {"name": "To Do"}},
            {"id": "31", "name": "Resolved", "to": {"name": "Resolved"}}]})

    def _transition(self, request, key):
        if r := self._outage():
            return r
        self.transitions.append((key, json.loads(request.content)["transition"]["id"]))
        return httpx.Response(204)


@pytest.fixture
def settings() -> McpSettings:
    return McpSettings(_env_file=None, atlassian_site_url=SITE, atlassian_email="it@example.com",
                       atlassian_api_token="token", jira_project_key="KAN", jira_issue_type="Incident",
                       jira_sync_interval_seconds=0)


@pytest.fixture
def jira_mock():
    with respx.mock(assert_all_called=False) as router:
        yield FakeJira(router)


@pytest.fixture
def repo() -> FakeTicketRepository:
    return FakeTicketRepository()


@pytest.fixture
async def service(repo, settings, jira_mock, monkeypatch):
    monkeypatch.setattr("netcore_mcp.jira.asyncio.sleep", _no_sleep)  # no 1 s retry pause in tests
    jira = JiraClient(settings)
    yield TicketService(repo, jira)
    await jira.aclose()


async def _no_sleep(_seconds):
    return None


class TicketClient:
    """Calls the tools through a real FastMCP client (in-memory transport) as a chosen demo user."""

    def __init__(self, client: Client, caller: dict):
        self._client, self._caller = client, caller

    def as_user(self, user_id: str | None) -> TicketClient:
        self._caller["id"] = user_id
        return self

    async def call(self, tool: str, **args):
        result = await self._client.call_tool(tool, args)
        return result.structured_content

    async def call_raw(self, tool: str, **args):
        return await self._client.call_tool(tool, args, raise_on_error=False)

    async def list_tools(self):
        return await self._client.list_tools()


@pytest.fixture
async def mcp_client(service, monkeypatch):
    caller: dict = {"id": "bob"}
    monkeypatch.setattr(identity, "get_http_headers",
                        lambda: {identity.USER_HEADER: caller["id"]} if caller["id"] else {})
    async with Client(create_server(service)) as client:
        yield TicketClient(client, caller)


def ticket_args(**overrides) -> dict:
    base = {"title": "SD-WAN edge loses BFD", "description": "Edge NCX-1000 in Pune flaps BFD every 5 minutes.",
            "product_family": "networking", "region": "APAC", "severity": "high"}
    return {**base, **overrides}

