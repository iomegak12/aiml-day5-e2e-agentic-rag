"""Deterministic plan executor: runs each plan step's tool directly and records its outcome.

Search steps run the retrieval pipeline. Ticket steps call the MCP server (tickets.py); they end 'done' or
'error' (never 'no_results'), so they are not re-planned. Ticket writes run only from the first plan version.
"""

from __future__ import annotations

import time

from .planner import Plan
from .retrieval import ROUTE_BY_TOOL, retrieve_relevant
from .state import RequestContext
from .tickets import ADMIN_TOOLS, TICKET_TOOLS, WRITE_TOOLS, TicketResult, result_docs, run_ticket_tool


def plan_to_steps(plan: Plan, version: int) -> list[dict]:
    """Plan (pydantic) -> step records that live in agent state and carry the execution outcome."""
    return [{"id": st.id, "version": version, "goal": st.goal, "tool": st.tool, "domains": list(st.domains),
             "query": st.query, "depends_on": list(st.depends_on), "status": "pending", "relevant": 0,
             "best": 0.0, "seconds": 0.0,
             "ticket_args": (st.ticket_args.model_dump(exclude_none=True) if st.ticket_args else {})}
            for st in plan.steps]


def _ticket_guard(st: dict, ctx: RequestContext) -> str | None:
    """Reason to skip a ticket step, or None. The MCP server enforces RBAC as well (defence in depth)."""
    if st["tool"] in WRITE_TOOLS and st["version"] > 1:
        return "ticket writes run only from the first plan (never from a re-plan)"
    if st["tool"] in ADMIN_TOOLS and ctx.user.role != "admin":
        return f"'{st['tool']}' is for administrators only"
    return None


def _run_ticket_step(st: dict, ctx: RequestContext) -> list[dict]:
    started = time.monotonic()
    args = dict(st.get("ticket_args") or {})
    if reason := _ticket_guard(st, ctx):
        st.update(status="skipped", seconds=0.0)
        ctx.log("Plan executor", f"step {st['id']} skipped", reason)
        ctx.emit("step", dict(st))
        ctx.record_tool_call(st["tool"], {**args, "step": st["id"]}, origin="planner",
                             result=f"skipped: {reason}", seconds=0.0, status="skipped")
        ctx.used_tickets = True
        with ctx._lock:
            ctx.ticket_seq += 1
            seq = ctx.ticket_seq
        return result_docs(TicketResult(st["tool"], False, error=f"not run: {reason}"), args, seq)
    result, docs = run_ticket_tool(st["tool"], args, ctx)
    st.update(relevant=len(docs), best=1.0 if result.ok else 0.0, seconds=round(time.monotonic() - started, 1),
              status="done" if result.ok else "error")
    ctx.log("Plan executor", f"step {st['id']} {st['status']}", result.summary[:150])
    ctx.emit("step", dict(st))
    ctx.record_tool_call(st["tool"], {**args, "step": st["id"], "plan_version": st["version"]}, origin="planner",
                         result=result.summary, seconds=st["seconds"], status="ok" if result.ok else "error")
    return docs


def execute_steps(steps: list[dict], ctx: RequestContext) -> list[dict]:
    """Execute every pending step in order. Mutates the step records; returns all relevant chunks found."""
    found: list[dict] = []
    pending = [st for st in steps if st["status"] == "pending"]
    for n, st in enumerate(pending, start=1):
        if ctx.timed_out:
            st["status"] = "skipped"
            ctx.log("Plan executor", f"step {st['id']} skipped", "time budget exhausted")
            ctx.emit("step", dict(st))
            continue
        st["status"] = "running"
        ctx.emit("step", dict(st))
        if st["tool"] in TICKET_TOOLS:
            ctx.log("Plan executor", f"step {st['id']} running", f"({n}/{len(pending)}) {st['tool']} "
                                                                 f"{st.get('ticket_args') or ''}")
            found += _run_ticket_step(st, ctx)
            continue
        ctx.log("Plan executor", f"step {st['id']} running", f"({n}/{len(pending)}) {st['tool']} "
                                                             f"{st['domains'] or ''} '{st['query']}'")
        started = time.monotonic()
        relevant, best = retrieve_relevant(st["query"], ROUTE_BY_TOOL[st["tool"]], st["domains"], ctx)
        st.update(relevant=len(relevant), best=best, seconds=round(time.monotonic() - started, 1),
                  status="done" if relevant else "no_results")
        ctx.log("Plan executor", f"step {st['id']} {st['status']}", f"{len(relevant)} relevant, best {best}")
        ctx.emit("step", dict(st))
        ctx.record_tool_call(st["tool"], {"query": st["query"], "domains": st["domains"], "step": st["id"],
                                          "plan_version": st["version"]}, origin="planner",
                             result=f"{len(relevant)} relevant chunks, best relevance {best}",
                             seconds=st["seconds"], status=st["status"])
        found += relevant
    return found
