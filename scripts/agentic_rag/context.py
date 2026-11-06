"""Context Optimizer (token budget: trim, summarise overflow, reorder) and Prompt Builder (system prompt)."""

from __future__ import annotations

from functools import lru_cache

import tiktoken
from langchain_openai import ChatOpenAI
from rag_search import location

from .config import User, get_settings
from .resilience import with_retry
from .state import RequestContext

FULL_DOCS_SHARE = 0.8  # share of the budget for full chunks; the rest for summarised overflow

ORCHESTRATOR_PROMPT = """You are the NetCore Systems Enterprise Support Agent. You plan and execute retrieval, then answer.

ROUTING (choose the tool that fits the question - this is your routing decision):
- search_knowledge_base: internal NetCore knowledge (configuration, troubleshooting, policies, error codes, help).
  Pick the domain(s): networking (SD-WAN, SLA, BFD, ZTP, QoS, NCS-* alarms) and/or meetings (Meet, Calling, MTG-*).
- search_web: public or current information that is not NetCore-specific.
- federated_search: questions that need both NetCore facts and public information.
You may call several searches (e.g. one per sub-question). If a search returns NO_RELEVANT_RESULTS, call
rewrite_query and search again. Answer only when the CONTEXT section below contains what you need."""

ANSWER_RULES = """ANSWER RULES (apply when you write the final answer):
1. Answer ONLY from the CONTEXT. Never use outside knowledge for NetCore facts.
2. Cite every fact inline as [KB-ID, location] or [WEB-n] using the source headers, e.g. [KB-NET-1003, Table 1].
3. Prefer status "current". If the CONTEXT contains a SUPERSEDED source on the same topic, add a final line
   starting with "Note: superseded source" naming the old article, its release and the current replacement.
4. Be concise: short paragraphs or bullets; copy commands, codes and values verbatim.
5. The user is {user_name} (role: {role}). Never mention access levels or documents outside the CONTEXT."""


@lru_cache(maxsize=1)
def _encoder():
    return tiktoken.get_encoding("o200k_base")


def count_tokens(text: str) -> int:
    return len(_encoder().encode(text))


def _header(n: int, doc: dict) -> str:
    m = doc["metadata"]
    if m.get("content_type") == "web":
        return f"[Source {n}] {m['kb_id']} | {m.get('title', '')} | {m.get('url', '')} | relevance {doc['score']}"
    status = f"SUPERSEDED by {m.get('superseded_by')}" if m.get("status") == "superseded" else m.get("status")
    return (f"[Source {n}] {m.get('kb_id')} | {m.get('title')} | {m.get('product')} {m.get('version')} | "
            f"status: {status} | location: {location(m)} | relevance {doc['score']}")


def _lost_in_the_middle(items: list) -> list:
    """Best items at the start and end, weakest in the middle: [1, 3, 5, ..., 6, 4, 2]."""
    return items[0::2] + items[1::2][::-1]


@lru_cache(maxsize=1)
def _summariser():
    s = get_settings()
    return ChatOpenAI(model=s.reranker_model, max_retries=s.max_retries)


def optimize_context(docs: list[dict], ctx: RequestContext) -> tuple[str, list[str]]:
    """Fit the reranked chunks into CONTEXT_TOKEN_BUDGET. Returns (context text, context blocks for the judge)."""
    key = tuple(d["id"] for d in docs)
    if key in ctx._context_cache:  # same docs as the previous model call -> reuse (no extra LLM call)
        return ctx._context_cache[key]

    budget = get_settings().context_token_budget
    ranked = sorted(docs, key=lambda d: d["score"], reverse=True)
    kept, overflow, used = [], [], 0
    for n, d in enumerate(ranked, start=1):
        block = f"{_header(n, d)}\n{d['content'].strip()}"
        tokens = count_tokens(block)
        if used + tokens <= budget * FULL_DOCS_SHARE:
            kept.append(block)
            used += tokens
        else:
            overflow.append(block)

    blocks = _lost_in_the_middle(kept)
    if overflow:
        remaining = budget - used
        summary = with_retry(lambda: _summariser().invoke([
            ("system", f"Summarise these knowledge-base sources into compact bullet notes (max ~{remaining} tokens). "
                       "Keep every fact's source tag exactly as [KB-ID, location] or [WEB-n]."),
            ("human", "\n\n".join(overflow)),
        ]).content, what="context-summary", log=ctx.log)
        blocks.append(f"[Summarised additional sources]\n{summary}")
    ctx.log("Context optimizer", f"{len(kept)} full + {len(overflow)} summarised",
            f"~{used} tokens of {budget}; reordered for lost-in-the-middle")
    result = ("\n\n---\n\n".join(blocks), blocks)
    ctx._context_cache[key] = result
    return result


SYNTHESIS_PROMPT = """You are the NetCore Systems Enterprise Support Agent. A research plan was created for the user's
question and executed; its results are in the CONTEXT below. Write the final answer now (no tools are available).
Cover every goal of the plan; if a goal found no relevant information, say so briefly instead of guessing."""


def _plan_summary(steps: list[dict]) -> str:
    latest = [st for st in steps if st["status"] != "replanned"]
    return "\n".join(f"- step {st['id']}: {st['goal']} -> {st['status']} ({st['relevant']} relevant chunks)"
                     for st in latest)


def build_system_prompt(context: str, user: User, plan_steps: list[dict] | None = None) -> str:
    """Prompt Builder: instructions (routing, or plan synthesis) + answer rules + CONTEXT with citable headers."""
    rules = ANSWER_RULES.format(user_name=user.name, role=user.role)
    if plan_steps is not None:  # planning mode: synthesis only
        return (f"{SYNTHESIS_PROMPT}\n\nEXECUTED PLAN:\n{_plan_summary(plan_steps)}\n\n{rules}\n\n"
                f"CONTEXT:\n{context or '(empty)'}")
    return f"{ORCHESTRATOR_PROMPT}\n\n{rules}\n\nCONTEXT:\n{context or '(empty - you must search first)'}"
