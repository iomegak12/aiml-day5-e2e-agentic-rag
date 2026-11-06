"""Planner (Plan-and-Execute): turns the question into a short, ordered retrieval plan - and re-plans on failure."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .config import get_settings
from .resilience import with_retry
from .state import RequestContext

Tool = Literal["search_knowledge_base", "search_web", "federated_search"]
Domain = Literal["networking", "meetings"]


class PlanStep(BaseModel):
    id: int
    goal: str = Field(description="What this step must find out (one sub-question)")
    tool: Tool
    domains: list[Domain] = Field(description="KB domains for search_knowledge_base / federated_search; "
                                              "empty for search_web")
    query: str = Field(description="Self-contained search query; keep error codes and product names verbatim")
    depends_on: list[int] = Field(description="Ids of earlier steps whose results this step builds on")


class Plan(BaseModel):
    rationale: str = Field(description="One or two sentences: how the plan answers the question")
    steps: list[PlanStep]


PLANNER_PROMPT = """You are the planning module of the NetCore Systems enterprise support agent.
Create a short, ordered RETRIEVAL plan (at most {max_steps} steps) for the user's question.

Tools:
- search_knowledge_base: internal NetCore KB. domains: "networking" (NetCore SD-WAN, SLA classes and breach policy,
  BFD, ZTP, QoS, NCS-* alarms) and/or "meetings" (NetCore Meet, NetCore Calling, recordings, SSO, MTG-* errors).
- search_web: public or current information that is not NetCore-specific (standards, RFCs, third-party products).
- federated_search: both at once, when one sub-question needs NetCore facts AND public information.

Rules:
- One step per distinct sub-question. A simple question needs exactly ONE step.
- Prefer the internal KB for anything about NetCore products.
- Do NOT add an "answer" or "summarise" step - the final answer is written automatically after the plan runs.
- Queries must be self-contained search queries (no pronouns referring to other steps)."""

REPLAN_PROMPT = """The plan below was executed, but it needs to be revised.
REASON: {reason}

Executed steps and outcomes:
{history}

Write NEW steps (at most {max_steps}) that cover only what is still missing: rephrase the failed queries with more
precise product terms, choose a different domain or tool if appropriate, or decompose the goal differently.
Do not repeat steps that already succeeded. Number the new steps starting at {next_id}."""


@lru_cache(maxsize=1)
def _llm():
    s = get_settings()
    return ChatOpenAI(model=s.chat_model, max_retries=s.max_retries).with_structured_output(Plan)


def _clean(plan: Plan, max_steps: int, next_id: int) -> Plan:
    """Enforce the step limit, renumber from next_id and clear domains for web steps."""
    steps = plan.steps[:max_steps]
    id_map = {st.id: next_id + i for i, st in enumerate(steps)}
    fixed = [st.model_copy(update={"id": id_map[st.id],
                                   "domains": [] if st.tool == "search_web" else (st.domains or ["networking"]),
                                   "depends_on": [id_map[d] for d in st.depends_on if d in id_map]})
             for st in steps]
    return Plan(rationale=plan.rationale, steps=fixed)


def make_plan(question: str, ctx: RequestContext) -> Plan:
    s = get_settings()
    plan = with_retry(lambda: _llm().invoke([
        ("system", PLANNER_PROMPT.format(max_steps=s.max_plan_steps)),
        ("human", f"QUESTION: {question}"),
    ]), what="plan", log=ctx.log)
    return _clean(plan, s.max_plan_steps, next_id=1)


def replan(question: str, executed: list[dict], reason: str, ctx: RequestContext) -> Plan:
    """Revise the plan: `executed` holds every step so far with its status and best relevance."""
    s = get_settings()
    history = "\n".join(f"- step {st['id']} (v{st['version']}) [{st['status']}] {st['tool']} {st['domains']} "
                        f"query='{st['query']}' -> {st['relevant']} relevant, best {st['best']}" for st in executed)
    next_id = max((st["id"] for st in executed), default=0) + 1
    plan = with_retry(lambda: _llm().invoke([
        ("system", PLANNER_PROMPT.format(max_steps=s.max_plan_steps)),
        ("human", f"QUESTION: {question}\n\n" + REPLAN_PROMPT.format(reason=reason, history=history,
                                                                    max_steps=s.max_plan_steps, next_id=next_id)),
    ]), what="replan", log=ctx.log)
    return _clean(plan, s.max_plan_steps, next_id=next_id)
