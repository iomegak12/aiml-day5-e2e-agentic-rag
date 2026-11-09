"""Planner (Plan-and-Execute): turns the question into a short, ordered retrieval plan - and re-plans on failure."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .config import get_settings
from .resilience import with_retry
from .state import RequestContext

Tool = Literal["search_knowledge_base", "search_web", "federated_search",
               "register_ticket", "list_my_tickets", "get_ticket", "search_tickets", "resolve_ticket"]
Domain = Literal["networking", "meetings"]
SEARCH_STEP_TOOLS = ("search_knowledge_base", "search_web", "federated_search")


class TicketArgs(BaseModel):
    """Arguments of a ticket step (null = not used). Values come from the user's words - never invented."""

    ticket_id: str | None = Field(description="get_ticket / resolve_ticket: e.g. TKT-000123")
    title: str | None = Field(description="register_ticket: short summary")
    description: str | None = Field(description="register_ticket: what happened, impact, error codes")
    product_family: Literal["networking", "meetings"] | None = Field(description="register_ticket / search filter")
    region: Literal["AMER", "EMEA", "APAC"] | None = Field(description="register_ticket / search filter")
    severity: Literal["critical", "high", "medium", "low"] | None = Field(description="register / search filter")
    remarks: str | None = Field(description="resolve_ticket: resolution notes (required)")
    keyword: str | None = Field(description="search_tickets: text in the title or description")
    registered_by: str | None = Field(description="search_tickets: user id, e.g. bob")
    date_from: str | None = Field(description="search_tickets: YYYY-MM-DD")
    date_to: str | None = Field(description="search_tickets: YYYY-MM-DD")
    status: Literal["open", "resolved", "all"] | None = Field(description="list_my_tickets / search_tickets")


class PlanStep(BaseModel):
    id: int
    goal: str = Field(description="What this step must find out or do (one sub-question or one ticket action)")
    tool: Tool
    domains: list[Domain] = Field(description="KB domains for search_knowledge_base / federated_search; "
                                              "empty for search_web and ticket tools")
    query: str = Field(description="Self-contained search query; keep error codes and product names verbatim. "
                                   "For ticket tools: a one-line description of the action")
    ticket_args: TicketArgs | None = Field(description="Arguments for ticket tools; null for search tools")
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
IT support tickets (ticket_args carries the arguments; domains = []):
- list_my_tickets: the user's own tickets (status open | resolved | all).
- get_ticket: one ticket by ticket_id (TKT-000123).
- register_ticket: open a new ticket - needs title, description, product_family, region, severity.
- search_tickets: ADMIN ONLY - all users' tickets with optional filters.
- resolve_ticket: ADMIN ONLY - resolve ticket_id with remarks.

Rules:
- One step per distinct sub-question. A simple question needs exactly ONE step.
- Prefer the internal KB for anything about NetCore products.
- Do NOT add an "answer" or "summarise" step - the final answer is written automatically after the plan runs.
- Queries must be self-contained search queries (no pronouns referring to other steps).
- Use ticket tools only for questions about IT support tickets. Add register_ticket or resolve_ticket ONLY when the
  user explicitly asks to open/raise/log or to resolve/close a ticket, and take every value from the user's words:
  never invent a field. If a required value is missing, do not plan the write (the answer will ask for it).
- search_tickets and resolve_ticket are for admins only: never plan them for a user whose role is not admin."""

REPLAN_PROMPT = """The plan below was executed, but it needs to be revised.
REASON: {reason}

Executed steps and outcomes:
{history}

Write NEW steps (at most {max_steps}) that cover only what is still missing: rephrase the failed queries with more
precise product terms, choose a different domain or tool if appropriate, or decompose the goal differently.
Do not repeat steps that already succeeded. Never plan register_ticket or resolve_ticket in a revised plan.
Number the new steps starting at {next_id}."""


@lru_cache(maxsize=1)
def _llm():
    s = get_settings()
    return ChatOpenAI(model=s.chat_model, max_retries=s.max_retries).with_structured_output(Plan)


def _clean(plan: Plan, max_steps: int, next_id: int) -> Plan:
    """Enforce the step limit, renumber from next_id and clear domains for web steps."""
    steps = plan.steps[:max_steps]
    id_map = {st.id: next_id + i for i, st in enumerate(steps)}
    fixed = [st.model_copy(update={"id": id_map[st.id],
                                   "domains": ([] if st.tool not in ("search_knowledge_base", "federated_search")
                                               else (st.domains or ["networking"])),
                                   "ticket_args": None if st.tool in SEARCH_STEP_TOOLS else st.ticket_args,
                                   "depends_on": [id_map[d] for d in st.depends_on if d in id_map]})
             for st in steps]
    return Plan(rationale=plan.rationale, steps=fixed)


def make_plan(question: str, ctx: RequestContext) -> Plan:
    s = get_settings()
    plan = with_retry(lambda: _llm().invoke([
        ("system", PLANNER_PROMPT.format(max_steps=s.max_plan_steps)),
        ("human", f"USER: {ctx.user.user_id} (role: {ctx.user.role})\nQUESTION: {question}"),
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
        ("human", f"USER: {ctx.user.user_id} (role: {ctx.user.role})\nQUESTION: {question}\n\n"
                  + REPLAN_PROMPT.format(reason=reason, history=history, max_steps=s.max_plan_steps,
                                         next_id=next_id)),
    ]), what="replan", log=ctx.log)
    return _clean(plan, s.max_plan_steps, next_id=next_id)
