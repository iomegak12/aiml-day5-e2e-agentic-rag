"""Ticket tools through a FastMCP client: RBAC, validation, Jira mirroring and the pending-sync path."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from .conftest import ticket_args

pytestmark = pytest.mark.asyncio


async def test_tools_are_listed_with_enums(mcp_client):
    tools = {t.name: t for t in await mcp_client.list_tools()}
    assert set(tools) == {"register_ticket", "list_my_tickets", "get_ticket", "search_tickets", "resolve_ticket",
                          "sync_pending_tickets"}
    props = tools["register_ticket"].inputSchema["properties"]
    assert props["severity"]["enum"] == ["critical", "high", "medium", "low"]
    assert props["region"]["enum"] == ["AMER", "EMEA", "APAC"]
    assert tools["list_my_tickets"].annotations.readOnlyHint is True


async def test_register_creates_row_and_jira_issue(mcp_client, jira_mock, repo):
    out = await mcp_client.as_user("bob").call("register_ticket", **ticket_args())
    assert out["ticket_id"] == "TKT-000001"
    assert out["registered_by"] == "bob" and out["status"] == "open"
    assert out["jira_key"] == "KAN-1" and out["jira_sync"] == "synced"
    assert out["jira_url"].endswith("/browse/KAN-1")
    fields = jira_mock.created[0]
    assert fields["project"] == {"key": "KAN"} and fields["issuetype"] == {"name": "Incident"}
    assert fields["priority"] == {"name": "High"}
    assert fields["summary"] == "[TKT-000001] SD-WAN edge loses BFD"
    assert fields["labels"] == ["netcore-assist", "networking", "apac", "user-bob"]
    header = fields["description"]["content"][0]["content"][0]
    assert "TKT-000001" in header["text"] and "Registered by: bob" in header["text"]
    assert repo.rows["TKT-000001"].jira_status == "To Do"


async def test_register_keeps_ticket_when_jira_is_down(mcp_client, jira_mock, repo):
    jira_mock.fail = True
    out = await mcp_client.as_user("alice").call("register_ticket", **ticket_args(severity="low"))
    assert out["ticket_id"] == "TKT-000001" and out["jira_key"] is None
    assert out["jira_sync"] == "pending" and "HTTP 503" in out["jira_error"]
    assert repo.rows["TKT-000001"].jira_attempts == 1

    jira_mock.fail = False
    report = await mcp_client.as_user("carol").call("sync_pending_tickets")
    assert report == {"attempted": 1, "synced": 1, "still_pending": 0}
    assert repo.rows["TKT-000001"].jira_key == "KAN-1" and repo.rows["TKT-000001"].jira_error is None


async def test_validation_rejects_unknown_enum(mcp_client):
    result = await mcp_client.call_raw("register_ticket", **ticket_args(region="LATAM"))
    assert result.is_error


async def test_list_my_tickets_only_returns_own(mcp_client):
    await mcp_client.as_user("bob").call("register_ticket", **ticket_args(title="Bob ticket"))
    await mcp_client.as_user("alice").call("register_ticket", **ticket_args(title="Alice ticket"))
    mine = await mcp_client.as_user("alice").call("list_my_tickets")
    assert mine["count"] == 1 and mine["tickets"][0]["title"] == "Alice ticket"


async def test_get_ticket_hides_other_users_tickets(mcp_client):
    await mcp_client.as_user("bob").call("register_ticket", **ticket_args())
    denied = await mcp_client.as_user("alice").call_raw("get_ticket", ticket_id="TKT-000001")
    assert denied.is_error and "not found" in denied.content[0].text
    own = await mcp_client.as_user("bob").call("get_ticket", ticket_id="tkt-1")  # id is normalised
    assert own["ticket_id"] == "TKT-000001"
    admin = await mcp_client.as_user("carol").call("get_ticket", ticket_id="1")
    assert admin["registered_by"] == "bob"


@pytest.mark.parametrize("tool,args", [
    ("search_tickets", {}),
    ("resolve_ticket", {"ticket_id": "TKT-000001", "remarks": "Fixed the BFD timers"}),
    ("sync_pending_tickets", {}),
])
@pytest.mark.parametrize("user", ["alice", "bob"])
async def test_admin_tools_are_refused_for_non_admins(mcp_client, tool, args, user):
    await mcp_client.as_user("bob").call("register_ticket", **ticket_args())
    result = await mcp_client.as_user(user).call_raw(tool, **args)
    assert result.is_error and "Permission denied" in result.content[0].text


async def test_missing_or_unknown_user_is_refused(mcp_client):
    for user in (None, "mallory"):
        result = await mcp_client.as_user(user).call_raw("list_my_tickets")
        assert result.is_error


async def test_search_filters(mcp_client, repo):
    repo.clock = datetime(2026, 11, 1, 9, tzinfo=timezone.utc)
    await mcp_client.as_user("bob").call("register_ticket", **ticket_args(title="BFD flaps", severity="critical"))
    repo.clock = datetime(2026, 11, 5, 9, tzinfo=timezone.utc)
    await mcp_client.as_user("alice").call("register_ticket", **ticket_args(
        title="Meet audio drops", description="Calls drop after 10 minutes", product_family="meetings",
        region="EMEA", severity="medium"))
    admin = mcp_client.as_user("carol")
    assert (await admin.call("search_tickets"))["count"] == 2
    audio = await admin.call("search_tickets", keyword="audio")
    assert [t["title"] for t in audio["tickets"]] == ["Meet audio drops"]
    assert (await admin.call("search_tickets", product_family="networking", severity="critical"))["count"] == 1
    assert (await admin.call("search_tickets", registered_by="Alice"))["count"] == 1
    assert (await admin.call("search_tickets", date_from="2026-11-02", date_to="2026-11-05"))["count"] == 1
    assert (await admin.call("search_tickets", region="AMER"))["count"] == 0
    bad = await admin.call_raw("search_tickets", date_from="2026-11-05", date_to="2026-11-01")
    assert bad.is_error


async def test_resolve_updates_db_and_jira(mcp_client, jira_mock, repo):
    await mcp_client.as_user("bob").call("register_ticket", **ticket_args())
    out = await mcp_client.as_user("carol").call("resolve_ticket", ticket_id="TKT-000001",
                                                  remarks="BFD timers aligned to 300 ms")
    assert out["status"] == "resolved" and out["resolved_by"] == "carol" and out["resolved_at"]
    assert out["remarks"] == "BFD timers aligned to 300 ms" and out["jira_sync"] == "synced"
    key, body = jira_mock.comments[0]
    assert key == "KAN-1" and body["content"][1]["content"][0]["text"] == "BFD timers aligned to 300 ms"
    assert jira_mock.transitions == [("KAN-1", "31")]
    assert repo.rows["TKT-000001"].jira_status == "Resolved"
    # open list no longer shows it; resolved list does
    assert (await mcp_client.as_user("bob").call("list_my_tickets"))["count"] == 0
    assert (await mcp_client.as_user("bob").call("list_my_tickets", status="resolved"))["count"] == 1
    again = await mcp_client.as_user("carol").call_raw("resolve_ticket", ticket_id="TKT-000001", remarks="again")
    assert again.is_error and "already resolved" in again.content[0].text


async def test_resolve_requires_remarks(mcp_client):
    await mcp_client.as_user("bob").call("register_ticket", **ticket_args())
    result = await mcp_client.as_user("carol").call_raw("resolve_ticket", ticket_id="TKT-000001", remarks="")
    assert result.is_error


async def test_resolve_during_jira_outage_syncs_later_without_duplicates(mcp_client, jira_mock, repo):
    await mcp_client.as_user("bob").call("register_ticket", **ticket_args())
    jira_mock.fail = True
    out = await mcp_client.as_user("carol").call("resolve_ticket", ticket_id="TKT-000001", remarks="Replaced edge")
    assert out["status"] == "resolved" and out["jira_sync"] == "pending"  # Postgres is the source of truth
    jira_mock.fail = False
    await mcp_client.as_user("carol").call("sync_pending_tickets")
    await mcp_client.as_user("carol").call("sync_pending_tickets")  # nothing left: no second comment
    assert len(jira_mock.created) == 1 and len(jira_mock.comments) == 1
    assert jira_mock.transitions == [("KAN-1", "31")]
    assert repo.rows["TKT-000001"].jira_sync == "synced"


async def test_unknown_ticket(mcp_client):
    result = await mcp_client.as_user("carol").call_raw("resolve_ticket", ticket_id="TKT-000099", remarks="n/a")
    assert result.is_error and "not found" in result.content[0].text
    bad = await mcp_client.as_user("carol").call_raw("get_ticket", ticket_id="KAN-1")
    assert bad.is_error and "Invalid ticket id" in bad.content[0].text
