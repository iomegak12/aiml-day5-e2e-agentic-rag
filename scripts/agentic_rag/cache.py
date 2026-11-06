"""Redis semantic cache (RedisVL). Each entry records the most sensitive access level of its sources (RBAC)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import OpenAITextVectorizer

from .config import get_settings
from .resilience import with_retry


@dataclass
class CacheHit:
    question: str  # the cached (similar) question
    answer: str
    max_access_level: str  # most sensitive source used -> who may SEE the answer
    scope: str  # highest level the generating user could retrieve -> how COMPLETE the answer can be
    sources: list[str]
    similarity: float


@lru_cache(maxsize=1)
def _cache() -> SemanticCache:
    s = get_settings()
    vectorizer = OpenAITextVectorizer(model=s.embedding_model, api_config={"api_key": os.environ["OPENAI_API_KEY"]})
    return SemanticCache(name=s.cache_name, distance_threshold=round(1 - s.cache_similarity, 4), ttl=s.cache_ttl,
                         vectorizer=vectorizer, redis_url=s.redis_url)


def lookup(question: str, num_results: int = 3, log=None) -> list[CacheHit]:
    """Cached answers for similar questions (cosine similarity >= threshold), most similar first.

    Several entries can exist for one question (e.g. one answered for an employee, one for a guest);
    the caller serves the first one the user is allowed to see.
    """
    hits = with_retry(lambda: _cache().check(prompt=question, num_results=num_results,
                                             return_fields=["prompt", "response", "metadata", "vector_distance"]),
                      what="cache-lookup", log=log)
    results = []
    for hit in hits:
        meta = hit.get("metadata") or {}
        if isinstance(meta, str):
            meta = json.loads(meta)
        results.append(CacheHit(question=hit["prompt"], answer=hit["response"],
                                max_access_level=meta.get("max_access_level", "restricted"),
                                scope=meta.get("scope", "public"), sources=meta.get("sources", []),
                                similarity=round(1 - float(hit.get("vector_distance", 0)), 4)))
    return results


def store(question: str, answer: str, max_access_level: str, scope: str, sources: list[str], scores: dict,
          log=None) -> None:
    metadata = {"max_access_level": max_access_level, "scope": scope, "sources": sources, "judge_scores": scores}
    with_retry(lambda: _cache().store(prompt=question, response=answer, metadata=metadata),
               what="cache-store", log=log)


def clear_cache() -> None:
    """Remove every cached answer (keeps the index)."""
    _cache().clear()
