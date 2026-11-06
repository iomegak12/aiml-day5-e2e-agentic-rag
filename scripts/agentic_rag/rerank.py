"""LLM reranker (RERANKER_OPENAI_MODEL): scores every candidate chunk 0-1 for relevance to the question."""

from __future__ import annotations

from functools import lru_cache

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .config import get_settings
from .resilience import with_retry

MAX_CHARS_PER_CHUNK = 1500


class ChunkScore(BaseModel):
    index: int
    score: float = Field(ge=0, le=1, description="1 = directly answers the question, 0 = unrelated")


class RerankResult(BaseModel):
    scores: list[ChunkScore]


@lru_cache(maxsize=1)
def _llm():
    s = get_settings()
    return ChatOpenAI(model=s.reranker_model, max_retries=s.max_retries).with_structured_output(RerankResult)


def rerank(question: str, docs: list[Document], log=None) -> list[tuple[Document, float]]:
    """Return (doc, relevance) sorted best first. One LLM call scores all candidates."""
    if not docs:
        return []
    listing = "\n\n".join(f"[{i}] ({d.metadata.get('kb_id', '')}) {d.page_content[:MAX_CHARS_PER_CHUNK]}"
                          for i, d in enumerate(docs))
    result: RerankResult = with_retry(lambda: _llm().invoke([
        ("system", "You are a search relevance judge. Score EVERY numbered chunk for how well it helps answer "
                   "the question (0.0-1.0). Exact error codes, product names and versions matter."),
        ("human", f"QUESTION: {question}\n\nCHUNKS:\n{listing}"),
    ]), what="rerank", log=log)
    scores = {s.index: s.score for s in result.scores}
    ranked = [(d, round(scores.get(i, 0.0), 3)) for i, d in enumerate(docs)]
    return sorted(ranked, key=lambda x: x[1], reverse=True)
