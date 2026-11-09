"""IT support tickets: the agent's bridge to the netcore_mcp MCP server (langchain-mcp-adapters).

- Tool schemas are loaded from the server (MultiServerMCPClient, streamable HTTP). If the server is down, the
  agent keeps working without them and retries the load later (MCP_RETRY_SECONDS).
- The agent runs synchronously in worker threads, so every MCP call runs in its own asyncio.run().
- The caller's identity travels as the `X-User-Id` header, added per call by a tool interceptor.
- Results become "ticket docs" in agent state (relevant_docs), so the answer cites them ([TKT-000123] or
  [TICKETS]) and the judge checks grounding as for KB chunks. Errors become docs too (never exceptions).
- Writes (register / resolve / sync) with identical arguments run at most once per request.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.types import Command

from .state import RequestContext

TICKET_TOOLS = ("register_ticket", "list_my_tickets", "get_ticket", "search_tickets", "resolve_ticket",
                "sync_pending_tickets")
WRITE_TOOLS = frozenset({"register_ticket", "resolve_ticket", "sync_pending_tickets"})
ADMIN_TOOLS = frozenset({"search_tickets", "resolve_ticket", "sync_pending_tickets"})
ROUTE = "tickets"
UNAVAILABLE = "TICKET_SERVICE_UNAVAILABLE"
USER_HEADER = "X-User-Id"

_caller: ContextVar[str | None] = ContextVar("ticket_caller", default=None)


def server_url() -> str:
    return os.environ.get("MCP_SERVER_URL", "http://localhost:9090/mcp")


async def _with_user(request, handler):
    """Tool-call interceptor: send the calling user's id as a header (read from this task's context)."""
    return await handler(request.override(headers={USER_HEADER: _caller.get() or ""}))


@dataclass
class TicketResult:
    tool: str
    ok: bool
    data: dict | None = None  # structured tool output (TicketOut / TicketList / SyncReport)
    error: str = ""
    seconds: float = 0.0

    @property
    def summary(self) -> str:
        if not self.ok:
            return f"{self.tool} failed: {self.error}"
        d = self.data or {}
        if "tickets" in d:
            ids = ", ".join(t["ticket_id"] for t in d["tickets"][:8])
            return f"{self.tool}: {d['count']} ticket(s){': ' + ids if ids else ''}"
        if "ticket_id" in d:
            return (f"{self.tool}: {d['ticket_id']} status={d['status']} jira={d.get('jira_key') or '-'} "
                    f"({d.get('jira_sync')})")
        return f"{self.tool}: {json.dumps(d)}"


@dataclass
class TicketBridge:
    url: str
    retry_seconds: float = 30.0
    call_timeout: float = 45.0  # a register/resolve waits for Jira (15 s timeout + one retry)
    _tools: dict[str, BaseTool] | None = None
    _failed_at: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _client(self):
        from langchain_mcp_adapters.client import MultiServerMCPClient

        return MultiServerMCPClient(
            {"tickets": {"transport": "streamable_http", "url": self.url, "timeout": timedelta(seconds=10),
                         "sse_read_timeout": timedelta(seconds=self.call_timeout)}},
            tool_interceptors=[_with_user])

    def tools(self) -> dict[str, BaseTool]:
        """MCP tools by name ({} while the server is unreachable; retried after retry_seconds)."""
        with self._lock:
            if self._tools is not None:
                return self._tools
            if self._failed_at and time.monotonic() - self._failed_at < self.retry_seconds:
                return {}
            try:
                loaded = asyncio.run(asyncio.wait_for(self._client().get_tools(), timeout=10))
                self._tools = {t.name: t for t in loaded if t.name in TICKET_TOOLS}
                return self._tools
            except Exception:  # noqa: BLE001 - unreachable server: run without ticket tools for now
                self._failed_at = time.monotonic()
                return {}

    def call(self, name: str, args: dict, user_id: str) -> TicketResult:
        started = time.monotonic()
        tool = self.tools().get(name)
        if tool is None:
            return TicketResult(name, False, error=f"{UNAVAILABLE}: the IT ticket service is not reachable "
                                                  f"right now", seconds=time.monotonic() - started)
        clean = {k: v for k, v in args.items() if v is not None}

        async def run():
            _caller.set(user_id)
            return await asyncio.wait_for(tool.coroutine(**clean), timeout=self.call_timeout)

        try:
            _content, artifact = asyncio.run(run())
            data = (artifact or {}).get("structured_content") if isinstance(artifact, dict) else \
                getattr(artifact, "structured_content", None)
            return TicketResult(name, True, data=data or {}, seconds=time.monotonic() - started)
        except ToolException as exc:  # the server refused: permission, validation, not found
            return TicketResult(name, False, error=_tool_error_text(exc), seconds=time.monotonic() - started)
        except Exception as exc:  # noqa: BLE001 - network / timeout: the service is unavailable
            with self._lock:
                self._tools = None  # reload the schemas on the next call (server may have restarted)
                self._failed_at = time.monotonic()
            return TicketResult(name, False, error=f"{UNAVAILABLE}: {type(exc).__name__}",
                                seconds=time.monotonic() - started)


def _tool_error_text(exc: Exception) -> str:
    content = exc.args[0] if exc.args else str(exc)
    if isinstance(content, list):  # MCP content blocks
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict)).strip() or "tool error"
    return str(content)


_bridge: TicketBridge | None = None


def get_bridge() -> TicketBridge:
    global _bridge
    if _bridge is None:
        _bridge = TicketBridge(server_url(), retry_seconds=float(os.environ.get("MCP_RETRY_SECONDS", "30")))
    return _bridge


def set_bridge(bridge: TicketBridge | None) -> None:
    """Replace the bridge (tests)."""
    global _bridge
    _bridge = bridge


# ---------------------------- results -> CONTEXT docs ----------------------------


def _ticket_text(t: dict) -> str:
    lines = [f"{t['ticket_id']}: {t['title']}",
             f"status: {t['status']} | severity: {t['severity']} | product: {t['product_family']} | "
             f"region: {t['region']} | registered by {t['registered_by']} at {t['registered_at']}",
             f"description: {t['description']}"]
    if t.get("status") == "resolved":
        lines.append(f"resolved by {t.get('resolved_by')} at {t.get('resolved_at')} | remarks: {t.get('remarks')}")
    jira = t.get("jira_key") or "not created yet"
    lines.append(f"Jira: {jira} {t.get('jira_url') or ''} (sync: {t.get('jira_sync')}"
                 f"{', error: ' + t['jira_error'] if t.get('jira_error') else ''})")
    return "\n".join(lines)


def _doc(seq: int, kb_id: str, title: str, content: str, tool: str, url: str = "") -> dict:
    return {"id": f"ticket:{seq}:{kb_id}", "content": content, "score": 1.0,
            "metadata": {"kb_id": kb_id, "title": title, "content_type": "ticket", "tool": tool, "url": url,
                         "access_level": "", "status": "current"}}


def result_docs(result: TicketResult, args: dict, seq: int) -> list[dict]:
    """A ticket tool result as citable CONTEXT docs: one per ticket, or one TICKETS doc for lists / errors."""
    shown_args = ", ".join(f"{k}={v}" for k, v in args.items() if v not in (None, ""))
    if not result.ok:
        return [_doc(seq, "TICKETS", f"{result.tool} failed", f"Ticket tool {result.tool}({shown_args}) failed: "
                     f"{result.error}", result.tool)]
    d = result.data or {}
    if "ticket_id" in d:
        verb = {"register_ticket": "Registered", "resolve_ticket": "Resolved"}.get(result.tool, "Ticket")
        return [_doc(seq, d["ticket_id"], f"{verb}: {d['title']}", _ticket_text(d), result.tool,
                     d.get("jira_url") or "")]
    if "tickets" in d:
        header = f"{result.tool}({shown_args}) returned {d['count']} ticket(s)."
        docs = [_doc(seq, "TICKETS", f"{result.tool} result", header + (
            " Listed: " + ", ".join(t["ticket_id"] for t in d["tickets"]) if d["tickets"] else ""), result.tool)]
        docs += [_doc(seq, t["ticket_id"], t["title"], _ticket_text(t), result.tool, t.get("jira_url") or "")
                 for t in d["tickets"][:10]]
        return docs
    return [_doc(seq, "TICKETS", f"{result.tool} result", f"{result.tool}: {json.dumps(d)}", result.tool)]


# ---------------------------- one entry point for react tools and the plan executor ----------------------------


def run_ticket_tool(name: str, args: dict, ctx: RequestContext) -> tuple[TicketResult, list[dict]]:
    """Call a ticket tool as the request's user, log it and return (result, docs for agent state)."""
    ctx.used_tickets = True
    key = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
    if name in WRITE_TOOLS and key in ctx.ticket_writes:  # e.g. a judge-triggered retry: never write twice
        result = ctx.ticket_writes[key]
        ctx.log("Tickets", f"{name} reused", "identical write already done in this request")
    else:
        result = get_bridge().call(name, args, ctx.user.user_id)
        if name in WRITE_TOOLS and result.ok:
            ctx.ticket_writes[key] = result
        ctx.log("Tickets", f"{name} {'ok' if result.ok else 'FAILED'}", result.summary[:150])
    with ctx._lock:
        ctx.ticket_seq += 1
        seq = ctx.ticket_seq
    return result, result_docs(result, args, seq)


def _make_tool(mcp_tool: BaseTool) -> StructuredTool:
    """Sync LangChain tool with the MCP tool's name, description and schema; updates agent state."""
    name = mcp_tool.name

    def call(runtime: ToolRuntime, **kwargs: Any) -> Command:
        ctx: RequestContext = runtime.context
        result, docs = run_ticket_tool(name, kwargs, ctx)
        note = " They are now in your CONTEXT; cite them as [TKT-xxxxxx] or [TICKETS]."
        return Command(update={"relevant_docs": docs, "routes": [ROUTE],
                               "messages": [ToolMessage(content=result.summary + note,
                                                        tool_call_id=runtime.tool_call_id)]})

    return StructuredTool(name=name, description=mcp_tool.description, args_schema=mcp_tool.args_schema, func=call)


_wrapped: dict[int, list[StructuredTool]] = {}


def langchain_tools() -> list[StructuredTool]:
    """Ticket tools for react mode ([] while the MCP server is unreachable). Wrapped once per loaded tool set."""
    loaded = get_bridge().tools()
    if not loaded:
        return []
    key = id(loaded)
    if key not in _wrapped:
        _wrapped.clear()
        _wrapped[key] = [_make_tool(t) for t in loaded.values()]
    return _wrapped[key]
