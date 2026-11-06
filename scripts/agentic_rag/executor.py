"""Deterministic plan executor: runs each plan step's retrieval tool directly and records its outcome."""

from __future__ import annotations

import time

from .planner import Plan
from .retrieval import ROUTE_BY_TOOL, retrieve_relevant
from .state import RequestContext


def plan_to_steps(plan: Plan, version: int) -> list[dict]:
    """Plan (pydantic) -> step records that live in agent state and carry the execution outcome."""
    return [{"id": st.id, "version": version, "goal": st.goal, "tool": st.tool, "domains": list(st.domains),
             "query": st.query, "depends_on": list(st.depends_on), "status": "pending", "relevant": 0,
             "best": 0.0, "seconds": 0.0} for st in plan.steps]


def execute_steps(steps: list[dict], ctx: RequestContext) -> list[dict]:
    """Execute every pending step in order. Mutates the step records; returns all relevant chunks found."""
    found: list[dict] = []
    pending = [st for st in steps if st["status"] == "pending"]
    for n, st in enumerate(pending, start=1):
        if ctx.timed_out:
            st["status"] = "skipped"
            ctx.log("Plan executor", f"step {st['id']} skipped", "time budget exhausted")
            continue
        st["status"] = "running"
        ctx.log("Plan executor", f"step {st['id']} running", f"({n}/{len(pending)}) {st['tool']} "
                                                             f"{st['domains'] or ''} '{st['query']}'")
        started = time.monotonic()
        relevant, best = retrieve_relevant(st["query"], ROUTE_BY_TOOL[st["tool"]], st["domains"], ctx)
        st.update(relevant=len(relevant), best=best, seconds=round(time.monotonic() - started, 1),
                  status="done" if relevant else "no_results")
        ctx.log("Plan executor", f"step {st['id']} {st['status']}", f"{len(relevant)} relevant, best {best}")
        found += relevant
    return found
