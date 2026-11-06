"""Query rewriter (Corrective RAG): rephrase a vague question or decompose a multi-part one into sub-questions."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import BaseModel, Field

from .config import get_settings
from .resilience import with_retry
from .state import RequestContext


class Rewrite(BaseModel):
    strategy: Literal["rephrase", "decompose"]
    queries: list[str] = Field(description="1 rephrased query, or 2-4 self-contained sub-questions")
    reason: str


@lru_cache(maxsize=1)
def _llm():
    s = get_settings()
    return ChatOpenAI(model=s.reranker_model, max_retries=s.max_retries).with_structured_output(Rewrite)


@tool
def rewrite_query(question: str, feedback: str, runtime: ToolRuntime) -> Command:
    """Rewrite the search query when retrieval found nothing relevant or the answer failed evaluation.
    feedback: why the previous attempt failed (e.g. 'NO_RELEVANT_RESULTS', 'judge: low faithfulness')."""
    ctx: RequestContext = runtime.context
    attempt = runtime.state.get("rewrite_count", 0) + 1
    result: Rewrite = with_retry(lambda: _llm().invoke([
        ("system", "You improve search queries for an enterprise knowledge base about NetCore SD-WAN (networking) "
                   "and NetCore Meet/Calling (collaboration). Rephrase vague questions with precise product terms, "
                   "or decompose multi-part questions into self-contained sub-questions. Keep error codes verbatim."),
        ("human", f"ORIGINAL QUESTION: {ctx.question}\nCURRENT QUERY: {question}\nWHY IT FAILED: {feedback}"),
    ]), what="rewrite", log=ctx.log)
    ctx.log("Query rewriter", f"#{attempt} {result.strategy}", " | ".join(result.queries))
    content = (f"Rewrite #{attempt} ({result.strategy}): " + " | ".join(result.queries)
               + ". Now search with these queries (choose the route again).")
    return Command(update={"rewrite_count": 1,
                           "messages": [ToolMessage(content=content, tool_call_id=runtime.tool_call_id)]})
