"""The Enterprise Agentic RAG agent: create_agent + tools (routing/retrieval/rewrite) + middleware (policies)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    PIIMiddleware,
    ToolRetryMiddleware,
)
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .config import User, get_settings, get_user
from .context import ORCHESTRATOR_PROMPT
from .middleware import (
    TIMEOUT_APOLOGY,
    AnswerQualityMiddleware,
    CorrectiveRAGMiddleware,
    InputGuardrailMiddleware,
    PlanExecuteMiddleware,
    SemanticCacheMiddleware,
    TimeoutMiddleware,
)
from .retrieval import federated_search, search_knowledge_base, search_web
from .rewrite import rewrite_query
from .state import RAGState, RequestContext, TraceEvent


Mode = Literal["plan", "react"]


@lru_cache(maxsize=2)
def build_agent(mode: Mode = "plan"):
    """Compile the agent graph once per mode.

    plan  : Plan-and-Execute - planner + deterministic executor (PlanExecuteMiddleware); the model only synthesises.
    react : the model routes itself with tools (search / rewrite) under CorrectiveRAGMiddleware.
    """
    s = get_settings()
    if mode == "plan":
        tools, core = [], [PlanExecuteMiddleware()]
    else:
        tools = [search_knowledge_base, search_web, federated_search, rewrite_query]
        core = [CorrectiveRAGMiddleware(), ToolRetryMiddleware(max_retries=1, backoff_factor=2.0, initial_delay=1.0)]
    return create_agent(
        model=ChatOpenAI(model=s.chat_model),
        tools=tools,
        system_prompt=ORCHESTRATOR_PROMPT,
        state_schema=RAGState,
        context_schema=RequestContext,
        middleware=[
            InputGuardrailMiddleware(),        # before_agent
            SemanticCacheMiddleware(),         # before_agent (lookup) / after_agent (write)
            TimeoutMiddleware(),               # before_model / wrap_tool_call
            *core,                             # plan: plan + execute | react: corrective tool loop
            AnswerQualityMiddleware(),         # after_model: judge + output guardrails
            # cross-cutting built-ins: retry with exponential backoff, loop cap, PII redaction of the output
            ModelRetryMiddleware(max_retries=s.max_retries, backoff_factor=2.0, initial_delay=1.0),
            ModelCallLimitMiddleware(run_limit=20, exit_behavior="end"),
            PIIMiddleware("email", strategy="redact", apply_to_input=False, apply_to_output=True),
            PIIMiddleware("credit_card", strategy="redact", apply_to_input=False, apply_to_output=True),
        ],
    )


@dataclass
class AgentResult:
    question: str
    user: User
    answer: str
    status: str
    routes: list[str] = field(default_factory=list)
    rewrites: int = 0
    judge_scores: dict = field(default_factory=dict)
    sources: list[dict] = field(default_factory=list)
    cached_question: str | None = None
    elapsed: float = 0.0
    trace: list[TraceEvent] = field(default_factory=list)
    mode: str = "plan"
    plan: list[dict] = field(default_factory=list)  # every plan version's steps with their outcome
    plan_rationales: dict[int, str] = field(default_factory=dict)  # plan version -> planner rationale
    tool_calls: list[dict] = field(default_factory=list)  # unified: LLM tool calls (react) + executor steps (plan)
    judge: dict = field(default_factory=dict)  # model, passed, scores, thresholds, attempts[]
    cache_similarity: float | None = None


def ask(question: str, user_id: str = "bob", verbose: bool = True, mode: Mode = "plan",
        show_plan: bool = True, *, timeout_seconds: float | None = None, bypass_cache: bool = False,
        on_event=None) -> AgentResult:
    """Run one request through the full Enterprise RAG workflow as a demo user (alice | bob | carol).

    mode='plan'  : create a plan, show it (show_plan=True), execute it, re-plan on failure, then answer.
    mode='react' : the agent routes and rewrites by itself with tools (no explicit plan).
    timeout_seconds : per-request time budget (default AGENT_TIMEOUT_SECONDS).
    bypass_cache    : skip the semantic-cache lookup.
    on_event        : callback(event_type, data) for live progress (plan, step, tool_call, judge, trace).
    """
    s = get_settings()
    user = get_user(user_id)
    ctx = RequestContext(user=user, question=question, timeout_seconds=timeout_seconds or s.timeout_seconds,
                         verbose=verbose, on_event=on_event, bypass_cache=bypass_cache)
    if show_plan:
        from .display import show_plan as _show_plan
        ctx.on_plan = _show_plan
    ctx.log("Request", user.user_id, f"role={user.role} mode={mode} q='{question}'")
    state: dict = {}
    try:
        # Each loop pass visits ~11 graph nodes (middleware hooks + model + tools); loops are really bounded by
        # ModelCallLimitMiddleware, MAX_REWRITES and the timeout budget, so the graph step limit is only a backstop.
        state = build_agent(mode).invoke({"messages": [HumanMessage(question)]}, context=ctx,
                                         config={"recursion_limit": 300})
        answer = next(m.text for m in reversed(state["messages"]) if isinstance(m, AIMessage) and not m.tool_calls)
        status = state.get("status", "answered")
    except Exception as exc:  # noqa: BLE001 - never surface a stack trace to the user
        ctx.log("Error", type(exc).__name__, str(exc)[:150])
        answer, status = TIMEOUT_APOLOGY, "error"

    if ctx.cache_hit:
        sources = [{"kb_id": k, "score": None, "location": "cached", "access_level": ctx.cache_hit.max_access_level}
                   for k in ctx.cache_hit.sources]
    else:
        from rag_search import location
        sources = [{"kb_id": d["metadata"].get("kb_id"), "score": d["score"],
                    "location": d["metadata"].get("url") or location(d["metadata"]),
                    "access_level": d["metadata"].get("access_level", ""), "status": d["metadata"].get("status", "")}
                   for d in state.get("relevant_docs", [])]
    ctx.log("Response", status, f"{len(answer)} chars in {ctx.elapsed:.1f}s")
    judge_info = {"model": s.judge_model, "passed": bool(state.get("judge_passed")) if ctx.judge_attempts else None,
                  "scores": state.get("judge_scores", {}),
                  "thresholds": {"faithfulness": s.faithfulness_threshold, "groundedness": s.groundedness_threshold,
                                 "context_precision": s.context_precision_threshold},
                  "attempts": list(ctx.judge_attempts)}
    return AgentResult(question=question, user=user, answer=answer, status=status, routes=state.get("routes", []),
                       rewrites=state.get("rewrite_count", 0), judge_scores=state.get("judge_scores", {}),
                       sources=sources, cached_question=ctx.cache_hit.question if ctx.cache_hit else None,
                       elapsed=round(ctx.elapsed, 1), trace=ctx.trace, mode=mode, plan=state.get("plan", []),
                       plan_rationales=dict(ctx.plan_rationales), tool_calls=list(ctx.tool_calls), judge=judge_info,
                       cache_similarity=ctx.cache_hit.similarity if ctx.cache_hit else None)
