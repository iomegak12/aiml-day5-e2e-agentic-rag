"""Middleware = the deterministic workflow rules around the agent loop (create_agent).

Hook order for one request:
  before_agent : InputGuardrailMiddleware -> SemanticCacheMiddleware (lookup + RBAC + output check)
  before_model : TimeoutMiddleware (budget) -> mode-specific:
                   react: CorrectiveRAGMiddleware (no-info exit)
                   plan : PlanExecuteMiddleware (plan -> show -> execute -> re-plan on failure -> no-info exit)
  wrap_model   : react: CorrectiveRAGMiddleware (force retrieve / rewrite / web fallback) | plan: synthesis only
                 (both: Context Optimizer + Prompt Builder)
  after_model  : PII redaction (built-in) -> AnswerQualityMiddleware (LLM judge escalation, output guardrails)
  wrap_tool    : TimeoutMiddleware (skip tools when the budget is gone)
  after_agent  : SemanticCacheMiddleware (write only judge-passed answers)
Retry with exponential backoff: built-in ModelRetryMiddleware / ToolRetryMiddleware (see agent.py).
"""

from __future__ import annotations

import re
import time
from typing import Any

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage

from . import cache, executor, judge, planner
from .config import get_settings, level_rank, max_level
from .context import build_system_prompt, optimize_context
from .guardrails import DISCLAIMER, NO_INFO, SAFE_REFUSAL, check_input, check_output
from .retrieval import NO_RESULTS, ROUTE_BY_TOOL
from .state import RAGState, RequestContext

# IT ticket requests read or change live, per-user data: never answered from the semantic cache
TICKET_QUESTION = re.compile(r"\bticket|\bTKT-?\d|\bjira\b", re.IGNORECASE)

TIMEOUT_APOLOGY = ("I'm sorry - I couldn't complete this request within the time budget. "
                   "Please try again or narrow the question.")


def _ctx(runtime) -> RequestContext:
    return runtime.context


def _last_round_tool_messages(messages: list) -> list[ToolMessage]:
    """Tool results produced after the most recent AI message."""
    out = []
    for m in reversed(messages):
        if isinstance(m, ToolMessage):
            out.append(m)
        elif isinstance(m, AIMessage):
            break
    return out


def _last_search_empty(state: dict) -> bool:
    """True when the last tool round was searching and every search came back without relevant chunks."""
    tools = _last_round_tool_messages(state["messages"])
    return bool(tools) and all(str(t.content).startswith((NO_RESULTS, "TIMEOUT")) for t in tools)


def _tool_result_text(result) -> str:
    """Summary text of a tool result (a ToolMessage, or a Command carrying one)."""
    if isinstance(result, ToolMessage):
        return str(result.content)
    update = getattr(result, "update", None)
    messages = update.get("messages", []) if isinstance(update, dict) else []
    return str(messages[-1].content) if messages else str(result)[:500]


# =============================================================================
# 1. Input guardrails
# =============================================================================


class InputGuardrailMiddleware(AgentMiddleware):
    state_schema = RAGState

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: RAGState, runtime) -> dict[str, Any] | None:
        ctx = _ctx(runtime)
        result = check_input(ctx.question, log=ctx.log)
        if result.allowed:
            ctx.log("Input guardrails", "allowed", result.reason)
            return None
        ctx.log("Input guardrails", "BLOCKED", f"{result.violations} - {result.reason}")
        ctx.log("Safe refusal", "returned")
        return {"messages": [AIMessage(SAFE_REFUSAL)], "status": "blocked", "jump_to": "end"}


# =============================================================================
# 2. Semantic cache (lookup + hit checks, and write-back)
# =============================================================================


class SemanticCacheMiddleware(AgentMiddleware):
    state_schema = RAGState

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: RAGState, runtime) -> dict[str, Any] | None:
        if state.get("status"):  # already blocked by the input guardrails
            return None
        ctx = _ctx(runtime)
        if ctx.bypass_cache:
            ctx.log("Semantic cache", "bypassed", "requested by the client")
            return None
        if TICKET_QUESTION.search(ctx.question):
            ctx.log("Semantic cache", "bypassed", "IT ticket request: live, per-user data")
            return None
        hits = cache.lookup(ctx.question, log=ctx.log)
        if not hits:
            ctx.log("Semantic cache", "miss")
            return None
        user_scope = level_rank(max_level(ctx.user.allowed_levels))
        hit = None
        for h in hits:
            ctx.log("Semantic cache", "hit", f"similarity={h.similarity} level={h.max_access_level} "
                                             f"scope={h.scope} cached_q='{h.question}'")
            if not ctx.user.can_access(h.max_access_level):  # would leak content above the user's level
                ctx.log("Cache hit checks", "FAIL: RBAC", f"role '{ctx.user.role}' may not see "
                                                          f"'{h.max_access_level}' content")
            elif level_rank(h.scope) < user_scope:  # generated with narrower permissions -> possibly incomplete
                ctx.log("Cache hit checks", "skip: scope", f"answer was generated for scope '{h.scope}'; "
                                                           f"role '{ctx.user.role}' can retrieve more")
            elif hit is None:
                hit = h
        if hit is None:
            ctx.log("Cache hit checks", "no usable hit", "retrieve with the user's own permissions")
            return None
        out = check_output(ctx.question, hit.answer, log=ctx.log)
        if not out.allowed:
            ctx.log("Cache hit checks", "FAIL: output", f"{out.violations}")
            return None
        ctx.log("Cache hit checks", "pass", "RBAC + output guardrails")
        ctx.cache_hit = hit
        return {"messages": [AIMessage(hit.answer)], "status": "cache_hit", "jump_to": "end"}

    def after_agent(self, state: RAGState, runtime) -> dict[str, Any] | None:
        ctx = _ctx(runtime)
        status = state.get("status", "")
        if status == "cache_hit":
            return None
        if ctx.used_tickets:
            ctx.log("Cache write", "skipped", "the answer uses IT ticket data (per user, changes over time)")
            return None
        if status != "answered" or not state.get("judge_passed"):
            ctx.log("Cache write", "skipped", f"status={status or 'n/a'} (only judge-passed answers are cached)")
            return None
        docs = state.get("relevant_docs", [])
        level = max_level(d["metadata"].get("access_level", "public") for d in docs)
        sources = sorted({d["metadata"].get("kb_id", "") for d in docs})
        scope = max_level(ctx.user.allowed_levels)
        cache.store(ctx.question, state["messages"][-1].text, level, scope, sources, state.get("judge_scores", {}),
                    log=ctx.log)
        ctx.log("Cache write", "stored", f"max_access_level={level} scope={scope} sources={sources}")
        return None


# =============================================================================
# 3. Global timeout budget
# =============================================================================


class TimeoutMiddleware(AgentMiddleware):
    state_schema = RAGState

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: RAGState, runtime) -> dict[str, Any] | None:
        ctx = _ctx(runtime)
        if not ctx.timed_out:
            return None
        docs = state.get("relevant_docs", [])
        if docs:  # best partial answer: point to the most relevant sources found so far
            lines = [f"- {d['metadata'].get('kb_id')}: {d['metadata'].get('title', '')}" for d in docs[:3]]
            message = ("I ran out of time before completing a verified answer. The most relevant sources found are:\n"
                       + "\n".join(lines))
        else:
            message = TIMEOUT_APOLOGY
        ctx.log("Timeout budget", "exceeded", f"{ctx.elapsed:.1f}s > {ctx.timeout_seconds}s -> graceful response")
        return {"messages": [AIMessage(message)], "status": "timeout", "jump_to": "end"}

    def wrap_tool_call(self, request, handler):
        """Skips tools once the budget is gone, and records every LLM tool call (react mode)."""
        ctx = _ctx(request.runtime)
        name, args = request.tool_call["name"], dict(request.tool_call.get("args", {}))
        if ctx.timed_out:
            ctx.log("Timeout budget", "tool skipped", request.tool_call["name"])
            ctx.record_tool_call(name, args, "agent", "skipped: time budget exceeded", 0.0, status="skipped")
            return ToolMessage("TIMEOUT: time budget exceeded; tool skipped.", tool_call_id=request.tool_call["id"])
        started = time.monotonic()
        try:
            result = handler(request)
        except Exception as exc:
            ctx.record_tool_call(name, args, "agent", f"{type(exc).__name__}: {exc}", time.monotonic() - started,
                                 status="error")
            raise
        text = _tool_result_text(result)
        ctx.record_tool_call(name, args, "agent", text, time.monotonic() - started,
                             status="no_results" if text.startswith(NO_RESULTS) else "ok")
        return result


# =============================================================================
# 4. Corrective RAG loop + Context Optimizer + Prompt Builder
# =============================================================================


class CorrectiveRAGMiddleware(AgentMiddleware):
    """Enforces: retrieve before answering; rewrite (max MAX_REWRITES) when nothing relevant is found;
    then one online-search fallback; then the 'no reliable information' exit."""

    state_schema = RAGState

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: RAGState, runtime) -> dict[str, Any] | None:
        ctx, s = _ctx(runtime), get_settings()
        update: dict[str, Any] = {}
        last_tools = _last_round_tool_messages(state["messages"])
        if state.get("force_rewrite") and any(str(t.content).startswith("Rewrite #") for t in last_tools):
            update["force_rewrite"] = False  # the re-retrieve request has been served
        if (not state.get("relevant_docs") and _last_search_empty(state)
                and state.get("rewrite_count", 0) >= s.max_rewrites and state.get("web_tried")):
            ctx.log("Corrective RAG", "no information", f"{s.max_rewrites} rewrites + online search exhausted")
            return {**update, "messages": [AIMessage(NO_INFO)], "status": "no_info", "jump_to": "end"}
        return update or None

    def wrap_model_call(self, request, handler):
        state, ctx, s = request.state, _ctx(request.runtime), get_settings()
        docs = state.get("relevant_docs", [])
        rewrites = state.get("rewrite_count", 0)
        tools, tool_choice = list(request.tools), request.tool_choice

        def only(name: str) -> None:
            nonlocal tools, tool_choice
            tools = [t for t in tools if getattr(t, "name", None) == name]
            tool_choice = name

        if rewrites >= s.max_rewrites:  # rewrite budget used up
            tools = [t for t in tools if getattr(t, "name", None) != "rewrite_query"]
        if not docs:
            if _last_search_empty(state):
                if rewrites < s.max_rewrites:
                    ctx.log("Corrective RAG", f"rewrite {rewrites + 1}/{s.max_rewrites}", "no relevant chunks")
                    only("rewrite_query")
                elif not state.get("web_tried"):
                    ctx.log("Corrective RAG", "web fallback", "rewrite limit reached -> online search")
                    only("search_web")
            else:
                tool_choice = "any"  # nothing retrieved yet: the model must route to a search tool
        elif state.get("force_rewrite"):
            if rewrites < s.max_rewrites:
                only("rewrite_query")
            else:
                tool_choice = "any"

        context, blocks = optimize_context(docs, ctx) if docs else ("", [])
        ctx.context_blocks = blocks
        system = SystemMessage(build_system_prompt(context, ctx.user))
        return handler(request.override(system_message=system, tools=tools, tool_choice=tool_choice))


# =============================================================================
# 4b. Planning mode: Plan -> show -> Execute (deterministic) -> Re-plan on failure -> synthesis prompt
# =============================================================================


class PlanExecuteMiddleware(AgentMiddleware):
    """Plan-and-Execute. Runs in before_model so a judge 're-retrieve' request (force_rewrite) re-enters it.

    Step finds nothing -> re-plan (each re-plan counts as one rewrite, max MAX_REWRITES)
                       -> then one web-fallback step -> then 'no reliable information'.
    Some steps succeeded, others still empty after the re-plans -> answer with partial evidence.
    """

    state_schema = RAGState

    @staticmethod
    def _announce(ctx: RequestContext, steps: list[dict], version: int, rationale: str, label: str) -> None:
        ctx.log("Planner", f"{label} v{version}", f"{len(steps)} steps - {rationale}")
        ctx.plan_rationales[version] = rationale
        ctx.emit("plan", {"version": version, "label": label, "rationale": rationale,
                          "steps": [dict(st) for st in steps]})
        for st in steps:
            ctx.log("Plan", f"step {st['id']}", f"{st['tool']} {st['domains'] or ''} '{st['query']}'")
        if ctx.on_plan:
            ctx.on_plan(steps, version, rationale)

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: RAGState, runtime) -> dict[str, Any] | None:
        ctx, s = _ctx(runtime), get_settings()
        steps = [dict(st) for st in state.get("plan", [])]
        already_executed = {st["id"] for st in steps if st["status"] != "pending"}
        version = state.get("plan_version", 0)
        rewrites_used, web_tried = 0, bool(state.get("web_tried"))

        if not steps:  # first model call: create the plan
            plan = planner.make_plan(ctx.question, ctx)
            version = 1
            steps = executor.plan_to_steps(plan, version)
            self._announce(ctx, steps, version, plan.rationale, "plan")
        elif state.get("force_rewrite"):  # judge's 2nd failure: re-plan with the judge feedback
            scores = state.get("judge_scores", {})
            plan = planner.replan(ctx.question, steps, f"the answer failed the quality judge {scores}; "
                                                       "find more precise or additional evidence", ctx)
            version += 1
            new = executor.plan_to_steps(plan, version)
            steps += new
            rewrites_used += 1
            self._announce(ctx, new, version, plan.rationale, "re-plan (judge)")
        else:
            return None  # regeneration of the answer only: nothing to plan or execute

        found = executor.execute_steps(steps, ctx)
        have_docs = bool(found or state.get("relevant_docs"))

        # Corrective loop: re-plan the failed steps
        while any(st["status"] == "no_results" for st in steps) and not ctx.timed_out:
            failed = [st for st in steps if st["status"] == "no_results"]
            if state.get("rewrite_count", 0) + rewrites_used < s.max_rewrites:
                plan = planner.replan(ctx.question, steps, f"steps {[st['id'] for st in failed]} found no "
                                                           "relevant information", ctx)
                for st in failed:
                    st["status"] = "replanned"
                version += 1
                rewrites_used += 1
                new = executor.plan_to_steps(plan, version)
                steps += new
                self._announce(ctx, new, version, plan.rationale, f"re-plan {rewrites_used}")
                found += executor.execute_steps(steps, ctx)
                have_docs = have_docs or bool(found)
            elif have_docs:
                ctx.log("Corrective RAG", "partial evidence", f"steps {[st['id'] for st in failed]} still empty "
                                                              "- answering with what was found")
                break
            elif not web_tried:
                for st in failed:
                    st["status"] = "replanned"
                version += 1
                web_step = {"id": max(st["id"] for st in steps) + 1, "version": version, "goal": "Web fallback",
                            "tool": "search_web", "domains": [], "query": ctx.question, "depends_on": [],
                            "status": "pending", "relevant": 0, "best": 0.0, "seconds": 0.0}
                steps.append(web_step)
                web_tried = True
                self._announce(ctx, [web_step], version, "rewrite limit reached -> online search", "web fallback")
                found += executor.execute_steps(steps, ctx)
                have_docs = bool(found)
            else:
                break

        executed_now = [st for st in steps if st["id"] not in already_executed
                        and st["status"] in ("done", "no_results", "replanned", "error", "skipped")]
        update: dict[str, Any] = {
            "plan": steps, "plan_version": version, "force_rewrite": False,
            "relevant_docs": found,                      # reducer merges with earlier evidence
            "rewrite_count": rewrites_used,              # reducer adds (each re-plan = one rewrite)
            "routes": [ROUTE_BY_TOOL[st["tool"]] for st in executed_now],  # reducer appends
            "web_tried": web_tried or any(st["tool"] in ("search_web", "federated_search") for st in executed_now),
        }
        if not have_docs:
            ctx.log("Corrective RAG", "no information", f"{s.max_rewrites} re-plans + online search exhausted")
            return {**update, "messages": [AIMessage(NO_INFO)], "status": "no_info", "jump_to": "end"}
        return update

    def wrap_model_call(self, request, handler):
        """Synthesis call: no tools; system prompt = executed plan + answer rules + optimized CONTEXT."""
        state, ctx = request.state, _ctx(request.runtime)
        docs = state.get("relevant_docs", [])
        context, blocks = optimize_context(docs, ctx) if docs else ("", [])
        ctx.context_blocks = blocks
        system = SystemMessage(build_system_prompt(context, ctx.user, plan_steps=state.get("plan", [])))
        return handler(request.override(system_message=system, tools=[], tool_choice=None))


# =============================================================================
# 5. Judge (LLM-as-a-judge) escalation + output guardrails
# =============================================================================


class AnswerQualityMiddleware(AgentMiddleware):
    """Judge failures: 1st -> regenerate, 2nd -> re-retrieve, 3rd -> low-confidence disclaimer.
    Output guardrail failure: regenerate once, then safe refusal."""

    state_schema = RAGState

    @hook_config(can_jump_to=["model", "end"])
    def after_model(self, state: RAGState, runtime) -> dict[str, Any] | None:
        ctx = _ctx(runtime)
        message = state["messages"][-1]
        if not isinstance(message, AIMessage) or message.tool_calls:
            return None  # still planning / retrieving
        answer, update, status = message.text, {}, "answered"

        # ---------------- Judge LLM evaluation ----------------
        if state.get("relevant_docs"):
            failures = state.get("judge_failures", 0)
            started = time.monotonic()
            attempt = {"attempt": len(ctx.judge_attempts) + 1, "scores": {}, "passed": False, "failed": [],
                       "action": "", "error": None, "seconds": 0.0}
            ctx.judge_attempts.append(attempt)
            try:
                result = judge.evaluate(ctx.question, answer, ctx.context_blocks, timeout=max(15.0, ctx.remaining))
                update["judge_scores"] = result.scores
                attempt.update(scores=result.scores, passed=result.passed, failed=result.failed)
                ctx.log("Judge LLM", "pass" if result.passed else f"FAIL {result.failed}", str(result.scores))
            except Exception as exc:  # noqa: BLE001 - judge unavailable/timeout -> cannot verify
                result = None
                attempt["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                ctx.log("Judge LLM", "error", f"{type(exc).__name__}: {str(exc)[:100]}")
            attempt["seconds"] = round(time.monotonic() - started, 2)
            if result and result.passed:
                update["judge_passed"] = True
                attempt["action"] = "accept"
                ctx.emit("judge", dict(attempt))
            else:
                failures += 1
                update["judge_failures"] = failures
                remove = RemoveMessage(id=message.id)
                if result and failures == 1:
                    ctx.log("Judge escalation", "1st: regenerate")
                    attempt["action"] = "regenerate"
                    ctx.emit("judge", dict(attempt))
                    feedback = (f"[Evaluator] Your answer failed grounding checks {result.failed} {result.scores}. "
                                "Regenerate it using ONLY facts stated in the CONTEXT, with citations.")
                    return {**update, "messages": [remove, HumanMessage(feedback)], "jump_to": "model"}
                if result and failures == 2:
                    ctx.log("Judge escalation", "2nd: re-retrieve")
                    attempt["action"] = "re-retrieve"
                    ctx.emit("judge", dict(attempt))
                    feedback = (f"[Evaluator] The answer still failed {result.failed}. The context is probably "
                                "insufficient: rewrite the query, search again, then answer.")
                    return {**update, "force_rewrite": True, "messages": [remove, HumanMessage(feedback)],
                            "jump_to": "model"}
                ctx.log("Judge escalation", "3rd: give up" if result else "judge unavailable",
                        "add low-confidence disclaimer")
                attempt["action"] = "disclaimer"
                ctx.emit("judge", dict(attempt))
                answer, status = answer + DISCLAIMER, "low_confidence"

        # ---------------- Output guardrails ----------------
        out = check_output(ctx.question, answer, log=ctx.log)
        if out.allowed:
            ctx.log("Output guardrails", "pass", out.reason)
            return {**update, "status": status, "messages": [AIMessage(answer, id=message.id)]}
        if not state.get("output_regenerated"):
            ctx.log("Output guardrails", "FAIL -> regenerate", f"{out.violations} {out.reason}")
            feedback = (f"[Output policy] Your answer was rejected: {out.violations} ({out.reason}). "
                        "Rewrite it to comply: cite sources, no personal data, no commitments not in the CONTEXT.")
            return {**update, "output_regenerated": True,
                    "messages": [RemoveMessage(id=message.id), HumanMessage(feedback)], "jump_to": "model"}
        ctx.log("Output guardrails", "FAIL -> safe refusal", f"{out.violations}")
        return {**update, "status": "refused", "messages": [AIMessage(SAFE_REFUSAL, id=message.id)]}
