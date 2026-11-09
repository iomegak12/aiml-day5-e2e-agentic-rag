"""Jira client details (retry, errors, missing transition, disabled config) and the X-User-Id mapping."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from fastmcp.exceptions import ToolError

from netcore_mcp.config import McpSettings
from netcore_mcp.identity import resolve_caller
from netcore_mcp.jira import JiraClient, JiraError, adf, issue_fields
from netcore_mcp.service import normalize_ticket_id

from .conftest import SITE

TICKET = SimpleNamespace(ticket_id="TKT-000007", registered_by="bob", title="Meet echo", severity="critical",
                         description="Line one\n\nLine two", product_family="meetings", region="AMER")


def test_issue_fields_maps_severity_and_labels(settings):
    fields = issue_fields(TICKET, settings)
    assert fields["priority"] == {"name": "Highest"}
    assert fields["labels"] == ["netcore-assist", "meetings", "amer", "user-bob"]
    texts = [p["content"][0]["text"] for p in fields["description"]["content"]]
    assert texts == ["TKT-000007 | Registered by: bob | Severity: critical | Product: meetings | Region: AMER",
                     "Line one", "Line two"]


def test_adf_never_empty():
    assert adf("")["content"][0]["content"][0]["text"] == "-"


async def test_retries_once_on_503_then_succeeds(settings, monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(201, json={"id": "1", "key": "KAN-9"})

    monkeypatch.setattr("netcore_mcp.jira.asyncio.sleep", _no_sleep)
    jira = JiraClient(settings, transport=httpx.MockTransport(handler))
    issue = await jira.create_issue(TICKET)
    assert issue.key == "KAN-9" and issue.url == f"{SITE}/browse/KAN-9" and len(calls) == 2
    await jira.aclose()


async def test_auth_error_is_reported_without_retry(settings):
    calls = []

    def handler(request):
        calls.append(1)
        assert request.headers["authorization"].startswith("Basic ")
        return httpx.Response(401, json={"errorMessages": ["Client must be authenticated"]})

    jira = JiraClient(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(JiraError, match="HTTP 401: Client must be authenticated"):
        await jira.create_issue(TICKET)
    assert len(calls) == 1
    await jira.aclose()


async def test_missing_transition_lists_available(settings):
    def handler(request):
        return httpx.Response(200, json={"transitions": [{"id": "1", "name": "Done", "to": {"name": "Done"}}]})

    jira = JiraClient(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(JiraError, match="available: Done"):
        await jira.resolve("KAN-1")
    await jira.aclose()


async def test_disabled_when_not_configured():
    jira = JiraClient(McpSettings(_env_file=None, atlassian_site_url="", atlassian_api_token=""))
    assert not jira.enabled
    with pytest.raises(JiraError, match="not configured"):
        await jira.create_issue(TICKET)
    await jira.aclose()


def test_resolve_caller():
    assert resolve_caller(" Carol ").is_admin
    assert resolve_caller("bob").role == "employee"
    for bad in (None, "", "mallory"):
        with pytest.raises(ToolError):
            resolve_caller(bad)


@pytest.mark.parametrize("raw,expected", [("TKT-000123", "TKT-000123"), ("tkt-123", "TKT-000123"),
                                          ("123", "TKT-000123"), ("TKT123", "TKT-000123")])
def test_normalize_ticket_id(raw, expected):
    assert normalize_ticket_id(raw) == expected


async def _no_sleep(_seconds):
    return None
