"""Agent state (graph state with reducers) and per-request runtime context (user, deadline, trace)."""

from __future__ import annotations

import operator
import threading
import time
from dataclasses import dataclass, field
from typing import Annotated, Any

from langchain.agents.middleware import AgentState
from typing_extensions import NotRequired

from .config import User

MAX_DOCS_IN_STATE = 12


def merge_docs(left: list[dict] | None, right: list[dict] | None) -> list[dict]:
    """Reducer: merge retrieved docs from (possibly parallel) tool calls - de-duplicate by id, keep best score."""
    by_id: dict[str, dict] = {d["id"]: d for d in (left or [])}
    for d in right or []:
        if d["id"] not in by_id or d["score"] > by_id[d["id"]]["score"]:
            by_id[d["id"]] = d
    return sorted(by_id.values(), key=lambda d: d["score"], reverse=True)[:MAX_DOCS_IN_STATE]


class RAGState(AgentState):
    """Messages + the counters and flags that the middleware uses to enforce the workflow rules."""

    # written by tools (reducers make parallel tool calls safe)
    relevant_docs: NotRequired[Annotated[list[dict], merge_docs]]  # reranked chunks above the threshold
    routes: NotRequired[Annotated[list[str], operator.add]]  # vector | web | federated, in order
    rewrite_count: NotRequired[Annotated[int, operator.add]]
    web_tried: NotRequired[Annotated[bool, operator.or_]]
    # written by middleware only (sequential hooks)
    force_rewrite: NotRequired[bool]
    judge_failures: NotRequired[int]
    judge_scores: NotRequired[dict]
    judge_passed: NotRequired[bool]
    output_regenerated: NotRequired[bool]
    status: NotRequired[str]  # answered | low_confidence | blocked | cache_hit | no_info | refused | timeout
    # planning mode (written by PlanExecuteMiddleware only)
    plan: NotRequired[list[dict]]  # every step of every plan version, with its execution outcome
    plan_version: NotRequired[int]


@dataclass
class TraceEvent:
    t: float  # seconds since request start
    step: str
    decision: str
    detail: str = ""


@dataclass
class RequestContext:
    """Per-request runtime context (LangChain `context_schema`): who is asking, time budget and the trace."""

    user: User
    question: str
    timeout_seconds: float
    verbose: bool = True
    started: float = field(default_factory=time.monotonic)
    trace: list[TraceEvent] = field(default_factory=list)
    context_blocks: list[str] = field(default_factory=list)  # last optimized context (for the judge)
    cache_hit: Any = None  # CacheHit served for this request, if any
    on_plan: Any = None  # callback(steps, version, rationale) - shows a plan as soon as it is created
    on_event: Any = None  # callback(event_type, data) - live progress for API clients (SSE); must be thread-safe
    bypass_cache: bool = False  # skip the semantic-cache lookup for this request
    tool_calls: list[dict] = field(default_factory=list)  # every tool call (react: LLM; plan: executor steps)
    judge_attempts: list[dict] = field(default_factory=list)  # every judge evaluation with the action taken
    plan_rationales: dict[int, str] = field(default_factory=dict)  # plan version -> planner rationale
    _lock: Any = field(default_factory=threading.Lock, repr=False)  # parallel tool calls append concurrently
    web_seq: int = 0  # running number for WEB-n citations (unique across searches in one request)
    _web_ids: dict[str, str] = field(default_factory=dict)  # url -> WEB-n

    def web_id(self, url: str) -> str:
        """Stable, request-unique citation id for a web result."""
        if url not in self._web_ids:
            self.web_seq += 1
            self._web_ids[url] = f"WEB-{self.web_seq}"
        return self._web_ids[url]
    _context_cache: dict[Any, tuple[str, list[str]]] = field(default_factory=dict)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started

    @property
    def remaining(self) -> float:
        return self.timeout_seconds - self.elapsed

    @property
    def timed_out(self) -> bool:
        return self.remaining <= 0

    def log(self, step: str, decision: str, detail: str = "") -> None:
        """Structured console trace: [  3.21s] Step                 decision        detail"""
        event = TraceEvent(round(self.elapsed, 2), step, decision, detail)
        self.trace.append(event)
        if self.verbose:
            print(f"[{event.t:6.2f}s] {step:<20} {decision:<16} {detail[:150]}", flush=True)
        self.emit("trace", {"t": event.t, "step": step, "decision": decision, "detail": detail})

    def emit(self, event_type: str, data: dict) -> None:
        """Forward a progress event to the on_event callback (API streaming). Never breaks the agent."""
        if self.on_event is None:
            return
        try:
            self.on_event(event_type, data)
        except Exception:  # noqa: BLE001 - a broken listener must not fail the request
            pass

    def record_tool_call(self, name: str, args: dict, origin: str, result: str, seconds: float,
                         status: str = "ok") -> None:
        """Unified tool-call log. origin: 'agent' (LLM tool call, react) or 'planner' (plan executor step)."""
        with self._lock:
            call = {"seq": len(self.tool_calls) + 1, "name": name, "args": args, "origin": origin,
                    "status": status, "result": result[:500], "seconds": round(seconds, 2),
                    "t": round(self.elapsed, 2)}
            self.tool_calls.append(call)
        self.emit("tool_call", call)
