"""Retrieval tools the agent routes between (Adaptive RAG): vector DB (with RBAC filter), web (Serper), federated.

Every tool: retrieve -> merge & de-duplicate -> LLM rerank -> keep chunks above RELEVANCE_THRESHOLD.
Relevant chunks go into agent state (`relevant_docs`); the tool message is only a short summary.
"""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from langchain.tools import ToolRuntime, tool
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.documents import Document
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from rag_search import hybrid_search

from .config import get_settings
from .rerank import rerank
from .resilience import with_retry
from .state import RequestContext

Domain = Literal["networking", "meetings"]
NO_RESULTS = "NO_RELEVANT_RESULTS"
WEB_RESULTS = 5

# ---------------------------- Sources ----------------------------


def vector_search(query: str, domains: list[str], ctx: RequestContext) -> list[Document]:
    """Hybrid (BM25 + vector) search per domain, restricted to the user's access levels (RBAC metadata filter)."""
    s = get_settings()
    rbac_filter = {"access_level": {"$in": list(ctx.user.allowed_levels)}}
    docs = []
    for domain in domains:
        found = with_retry(lambda d=domain: hybrid_search(query, d, k=s.retrieval_k, filter=rbac_filter),
                           what=f"vector-search:{domain}", log=ctx.log)
        docs += [doc for doc, _ in found]
    ctx.log("Vector DB search", f"{len(docs)} chunks", f"domains={domains} rbac={list(ctx.user.allowed_levels)}")
    return docs


def web_search(query: str, ctx: RequestContext) -> list[Document]:
    """Online search via Serper (Google results)."""
    serper = GoogleSerperAPIWrapper(serper_api_key=get_settings().serper_api_key, k=WEB_RESULTS)
    results = with_retry(lambda: serper.results(query), what="web-search", log=ctx.log)
    docs = []
    for n, r in enumerate(results.get("organic", [])[:WEB_RESULTS], start=1):
        url = r.get("link", f"{query}#{n}")
        docs.append(Document(id=url, page_content=f"{r.get('title', '')}\n{r.get('snippet', '')}",
                             metadata={"kb_id": ctx.web_id(url), "title": r.get("title", ""), "url": url,
                                       "content_type": "web", "status": "current", "access_level": "public",
                                       "product": "Web", "version": "", "domain": "web"}))
    ctx.log("Online search", f"{len(docs)} results", f"query='{query}'")
    return docs


def merge_dedupe(*doc_lists: list[Document]) -> list[Document]:
    """Merge result lists; drop duplicates by id and by identical content."""
    seen, merged = set(), []
    for doc in (d for lst in doc_lists for d in lst):
        key_id, key_text = doc.id, hashlib.md5(" ".join(doc.page_content.split()).encode()).hexdigest()
        if key_id in seen or key_text in seen:
            continue
        seen.update({key_id, key_text})
        merged.append(doc)
    return merged


# ---------------------------- Shared pipeline (used by the tools AND the plan executor) ----------------------------

ROUTE_BY_TOOL = {"search_knowledge_base": "vector", "search_web": "web", "federated_search": "federated"}


def federated(query: str, domains: list[str], ctx: RequestContext) -> list[Document]:
    """Vector DB + web in parallel, merged and de-duplicated."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        kb_future = pool.submit(vector_search, query, domains, ctx)
        web_future = pool.submit(web_search, query, ctx)
        docs = merge_dedupe(kb_future.result(), web_future.result())
    ctx.log("Merge + de-duplicate", f"{len(docs)} unique", "vector + web")
    return docs


def retrieve_relevant(query: str, route: str, domains: list[str], ctx: RequestContext) -> tuple[list[dict], float]:
    """Retrieve (vector | web | federated) -> merge & de-duplicate -> rerank -> keep chunks above the threshold.

    Returns (relevant chunks serialized for agent state, best relevance score).
    """
    s = get_settings()
    if route == "vector":
        docs = vector_search(query, domains, ctx)
    elif route == "web":
        docs = web_search(query, ctx)
    else:
        docs = federated(query, domains, ctx)
    candidates = merge_dedupe(docs)
    ranked = rerank(query, candidates, log=ctx.log)
    relevant = [(d, sc) for d, sc in ranked if sc >= s.relevance_threshold]
    best = ranked[0][1] if ranked else 0.0
    ctx.log("Rerank + relevance", f"{len(relevant)}/{len(candidates)} pass",
            f"threshold={s.relevance_threshold} best={best}")
    serialized = [{"id": d.id or d.metadata.get("kb_id"), "content": d.page_content, "metadata": d.metadata,
                   "score": sc} for d, sc in relevant]
    return serialized, best


def _tool_result(query: str, route: str, domains: list[str], runtime: ToolRuntime) -> Command:
    """Run the shared pipeline, update agent state and return a short summary to the agent."""
    ctx: RequestContext = runtime.context
    relevant, best = retrieve_relevant(query, route, domains, ctx)
    if relevant:
        summary = (f"Found {len(relevant)} relevant chunks (route={route}): "
                   + ", ".join(f"{d['metadata'].get('kb_id')} ({d['score']})" for d in relevant[:6])
                   + ". They are now in your CONTEXT.")
    else:
        summary = (f"{NO_RESULTS} for '{query}' (route={route}, best relevance {best} < "
                   f"{get_settings().relevance_threshold}).")
    return Command(update={
        "relevant_docs": relevant,
        "routes": [route],
        "web_tried": route in ("web", "federated"),
        "messages": [ToolMessage(content=summary, tool_call_id=runtime.tool_call_id)],
    })


# ---------------------------- Tools (the router = the agent's tool choice) ----------------------------


@tool
def search_knowledge_base(query: str, domains: list[Domain], runtime: ToolRuntime) -> Command:
    """Search the internal NetCore knowledge base (vector DB). Use for NetCore product configuration,
    troubleshooting, policies, error codes and help articles.
    domains: 'networking' (SD-WAN, SLA, BFD, ZTP, QoS, NCS-* alarms) and/or
             'meetings' (NetCore Meet, Calling, recordings, SSO, MTG-* errors)."""
    ctx: RequestContext = runtime.context
    ctx.log("Router", "vector", f"domains={domains} query='{query}'")
    return _tool_result(query, "vector", domains, runtime)


@tool
def search_web(query: str, runtime: ToolRuntime) -> Command:
    """Search the public internet. Use for public or current information that is not NetCore-internal:
    industry standards, RFCs, third-party products, recent events."""
    ctx: RequestContext = runtime.context
    ctx.log("Router", "web", f"query='{query}'")
    return _tool_result(query, "web", [], runtime)


@tool
def federated_search(query: str, domains: list[Domain], runtime: ToolRuntime) -> Command:
    """Search the internal knowledge base AND the public web in parallel. Use when a question needs both
    NetCore-specific facts and public/industry information."""
    ctx: RequestContext = runtime.context
    ctx.log("Router", "federated", f"domains={domains} query='{query}'")
    return _tool_result(query, "federated", domains, runtime)


SEARCH_TOOLS = ("search_knowledge_base", "search_web", "federated_search")
