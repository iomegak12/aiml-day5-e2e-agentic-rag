"""Agent <-> ticket MCP bridge: result docs, write de-duplication, plan executor guards, react tool wrapper,
cache/citation rules. A fake bridge replaces the MCP server (no network)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from agentic_rag import executor, tickets
from agentic_rag.config import get_user
from agentic_rag.guardrails import CITATION
from agentic_rag.middleware import TICKET_QUESTION
from agentic_rag.planner import Plan, PlanStep, TicketArgs, _clean
from agentic_rag.state import RequestContext
from agentic_rag.tickets import TicketBridge, TicketResult, result_docs, run_ticket_tool
from langchain_core.tools import StructuredTool

TICKET = {"ticket_id": "TKT-000042", "title": "BFD flaps", "description": "Edge in Pune", "status": "open",
          "severity": "high", "product_family": "networking", "region": "APAC", "registered_by": "bob",
          "registered_at": "2026-11-10T09:00:00Z", "jira_key": "KAN-7", "jira_url": "https://x/browse/KAN-7",
          "jira_sync": "synced", "jira_error": None}


class FakeBridge:
    def __init__(self, results: dict[str, TicketResult] | None = None, available: bool = True):
        self.results = results or {}
        self.calls: list[tuple[str, dict, str]] = []
        self.available = available
        self._tools = {"list_my_tickets": SimpleNamespace(
            name="list_my_tickets", description="List my tickets",
            args_schema={"type": "object", "properties": {"status": {"type": "string"}}})}

    def tools(self):  # like TicketBridge: the same dict while loaded
        return self._tools if self.available else {}

    def call(self, name, args, user_id):
        self.calls.append((name, args, user_id))
        if not self.available:
            return TicketResult(name, False, error=f"{tickets.UNAVAILABLE}: ConnectError")
        return self.results.get(name, TicketResult(name, True, data={"count": 1, "tickets": [TICKET]}))


@pytest.fixture
def bridge():
    fake = FakeBridge({"register_ticket": TicketResult("register_ticket", True, data=TICKET)})
    tickets.set_bridge(fake)
    tickets._wrapped.clear()
    yield fake
    tickets.set_bridge(None)
    tickets._wrapped.clear()


def ctx_for(user: str) -> RequestContext:
    return RequestContext(user=get_user(user), question="q", timeout_seconds=60, verbose=False)


def step(tool: str, version: int = 1, **args) -> dict:
    return {"id": 1, "version": version, "goal": "g", "tool": tool, "domains": [], "query": "q", "depends_on": [],
            "status": "pending", "relevant": 0, "best": 0.0, "seconds": 0.0, "ticket_args": args}


# ---------------------------- result docs ----------------------------


def test_single_ticket_becomes_one_citable_doc():
    [doc] = result_docs(TicketResult("register_ticket", True, data=TICKET), {}, seq=3)
    assert doc["metadata"]["kb_id"] == "TKT-000042" and doc["metadata"]["content_type"] == "ticket"
    assert doc["metadata"]["url"] == "https://x/browse/KAN-7" and doc["score"] == 1.0
    assert "Jira: KAN-7" in doc["content"] and doc["id"] == "ticket:3:TKT-000042"


def test_list_gives_summary_doc_plus_one_per_ticket():
    docs = result_docs(TicketResult("list_my_tickets", True, data={"count": 1, "tickets": [TICKET]}),
                       {"status": "open"}, seq=1)
    assert [d["metadata"]["kb_id"] for d in docs] == ["TICKETS", "TKT-000042"]
    assert "returned 1 ticket(s)" in docs[0]["content"]


def test_empty_list_and_errors_are_still_citable():
    [empty] = result_docs(TicketResult("list_my_tickets", True, data={"count": 0, "tickets": []}), {}, seq=1)
    assert empty["metadata"]["kb_id"] == "TICKETS" and "0 ticket(s)" in empty["content"]
    [err] = result_docs(TicketResult("search_tickets", False, error="Permission denied: ..."), {}, seq=2)
    assert "Permission denied" in err["content"]


# ---------------------------- bridge entry point ----------------------------


def test_run_ticket_tool_sends_the_request_user_and_marks_the_request(bridge):
    ctx = ctx_for("alice")
    result, docs = run_ticket_tool("list_my_tickets", {"status": "open"}, ctx)
    assert result.ok and bridge.calls == [("list_my_tickets", {"status": "open"}, "alice")]
    assert ctx.used_tickets and docs


def test_identical_write_runs_once_per_request(bridge):
    ctx = ctx_for("bob")
    args = {"title": "BFD flaps", "description": "Edge in Pune", "product_family": "networking", "region": "APAC",
            "severity": "high"}
    run_ticket_tool("register_ticket", args, ctx)
    run_ticket_tool("register_ticket", dict(args), ctx)  # e.g. after a judge-triggered retry
    assert [c[0] for c in bridge.calls] == ["register_ticket"]


def test_unreachable_server_degrades_to_unavailable():
    bridge = TicketBridge("http://127.0.0.1:9/mcp", retry_seconds=60)
    assert bridge.tools() == {}
    result = bridge.call("list_my_tickets", {}, "bob")
    assert not result.ok and result.error.startswith(tickets.UNAVAILABLE)
    assert bridge._failed_at  # not retried before retry_seconds


# ---------------------------- plan executor ----------------------------


def test_executor_runs_ticket_steps(bridge):
    ctx = ctx_for("bob")
    steps = [step("list_my_tickets", status="open")]
    docs = executor.execute_steps(steps, ctx)
    assert steps[0]["status"] == "done" and steps[0]["best"] == 1.0
    assert {d["metadata"]["kb_id"] for d in docs} == {"TICKETS", "TKT-000042"}
    assert ctx.tool_calls[0]["name"] == "list_my_tickets" and ctx.tool_calls[0]["origin"] == "planner"


def test_executor_skips_writes_from_a_replan(bridge):
    ctx = ctx_for("carol")
    steps = [step("resolve_ticket", version=2, ticket_id="TKT-000042", remarks="done")]
    docs = executor.execute_steps(steps, ctx)
    assert steps[0]["status"] == "skipped" and not bridge.calls
    assert "first plan" in docs[0]["content"]


def test_executor_skips_admin_tools_for_non_admins(bridge):
    ctx = ctx_for("bob")
    steps = [step("search_tickets", keyword="BFD")]
    executor.execute_steps(steps, ctx)
    assert steps[0]["status"] == "skipped" and not bridge.calls


def test_executor_marks_unavailable_service_as_error_not_no_results():
    fake = FakeBridge(available=False)
    tickets.set_bridge(fake)
    try:
        ctx = ctx_for("bob")
        steps = [step("list_my_tickets")]
        docs = executor.execute_steps(steps, ctx)
        assert steps[0]["status"] == "error"  # never re-planned
        assert tickets.UNAVAILABLE in docs[0]["content"]
    finally:
        tickets.set_bridge(None)


def test_planner_clean_keeps_ticket_args_only_on_ticket_steps():
    no_args = TicketArgs(ticket_id=None, title=None, description=None, product_family=None, region=None,
                         severity=None, remarks=None, keyword=None, registered_by=None, date_from=None, date_to=None,
                         status=None)
    plan = Plan(rationale="r", steps=[
        PlanStep(id=7, goal="kb", tool="search_knowledge_base", domains=[], query="BFD", depends_on=[],
                 ticket_args=no_args.model_copy(update={"title": "x"})),
        PlanStep(id=8, goal="t", tool="list_my_tickets", domains=["networking"], query="mine", depends_on=[7],
                 ticket_args=no_args.model_copy(update={"status": "open"}))])
    kb, tk = _clean(plan, max_steps=4, next_id=1).steps
    assert kb.ticket_args is None and kb.domains == ["networking"]
    assert tk.domains == [] and tk.ticket_args.status == "open" and tk.depends_on == [1]
    steps = executor.plan_to_steps(_clean(plan, 4, 1), version=1)
    assert steps[1]["ticket_args"] == {"status": "open"} and steps[0]["ticket_args"] == {}


# ---------------------------- react tools, cache and citations ----------------------------


def test_react_wrapper_reads_user_from_runtime_and_updates_state(bridge):
    [tool] = tickets.langchain_tools()
    assert isinstance(tool, StructuredTool) and tool.name == "list_my_tickets"
    ctx = ctx_for("carol")
    runtime = SimpleNamespace(context=ctx, tool_call_id="call-1")
    command = tool.func(runtime=runtime, status="all")
    assert bridge.calls == [("list_my_tickets", {"status": "all"}, "carol")]
    assert command.update["routes"] == ["tickets"]
    assert command.update["messages"][0].tool_call_id == "call-1"
    assert tickets.langchain_tools()[0] is tool  # wrapped once per loaded tool set


def test_no_react_tools_while_server_is_down():
    tickets.set_bridge(FakeBridge(available=False))
    try:
        assert tickets.langchain_tools() == []
    finally:
        tickets.set_bridge(None)


@pytest.mark.parametrize("question,is_ticket", [
    ("Show my open tickets", True), ("What is the status of TKT-000042?", True), ("Is KAN-7 in Jira?", True),
    ("How do I configure BFD timers?", False), ("Explain SLA breach policy", False)])
def test_ticket_questions_bypass_the_semantic_cache(question, is_ticket):
    assert bool(TICKET_QUESTION.search(question)) is is_ticket


def test_ticket_citations_satisfy_the_output_format_rule():
    assert CITATION.search("Your ticket is open [TKT-000042].")
    assert CITATION.search("You have no open tickets [TICKETS].")
    assert not CITATION.search("Ticket TKT-42 is open.")
