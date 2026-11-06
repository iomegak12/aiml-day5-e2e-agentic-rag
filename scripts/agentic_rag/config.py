"""Settings (.env), demo users and RBAC roles for the agentic RAG agent."""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass, replace
from functools import lru_cache

from populate_vector_dbs import ACCESS_LEVEL_BY_TYPE, ACCESS_LEVELS, Config, load_config

# =============================================================================
# RBAC - roles, demo users, access levels
# =============================================================================

ROLE_ACCESS: dict[str, tuple[str, ...]] = {
    "guest": ("public",),
    "employee": ("public", "internal"),
    "admin": ACCESS_LEVELS,  # public, internal, restricted
}


@dataclass(frozen=True)
class User:
    user_id: str
    name: str
    role: str

    @property
    def allowed_levels(self) -> tuple[str, ...]:
        return ROLE_ACCESS[self.role]

    def can_access(self, level: str) -> bool:
        return level in self.allowed_levels


DEMO_USERS: dict[str, User] = {
    "alice": User("alice", "Alice", "guest"),
    "bob": User("bob", "Bob", "employee"),
    "carol": User("carol", "Carol", "admin"),
}


def get_user(user_id: str) -> User:
    try:
        return DEMO_USERS[user_id]
    except KeyError:
        raise ValueError(f"Unknown user '{user_id}'. Demo users: {', '.join(DEMO_USERS)}") from None


def level_rank(level: str) -> int:
    return ACCESS_LEVELS.index(level) if level in ACCESS_LEVELS else len(ACCESS_LEVELS) - 1


def max_level(levels) -> str:
    """Most sensitive access level in a collection (used to tag cached answers)."""
    levels = list(levels) or ["public"]
    return max(levels, key=level_rank)


# =============================================================================
# Settings
# =============================================================================


@dataclass(frozen=True)
class AgentSettings:
    kb: Config  # Chroma / KB settings shared with the Pre-RAG pipeline
    chat_model: str
    reranker_model: str
    judge_model: str
    embedding_model: str
    serper_api_key: str
    redis_url: str
    cache_name: str
    cache_similarity: float
    cache_ttl: int
    retrieval_k: int
    relevance_threshold: float
    faithfulness_threshold: float
    groundedness_threshold: float
    context_precision_threshold: float
    context_token_budget: int
    max_rewrites: int
    max_retries: int
    timeout_seconds: float
    max_plan_steps: int


_overrides: dict = {}


def get_settings() -> AgentSettings:
    """Settings from .env, with any temporary overrides applied (see override_settings)."""
    base = _base_settings()
    return replace(base, **_overrides) if _overrides else base


@contextmanager
def override_settings(**changes):
    """Temporarily change settings, e.g. stricter judge thresholds for a demo:

        with override_settings(faithfulness_threshold=0.99):
            ask("...")
    """
    unknown = set(changes) - set(AgentSettings.__dataclass_fields__)
    if unknown:
        raise ValueError(f"Unknown settings: {unknown}")
    previous = dict(_overrides)
    _overrides.update(changes)
    try:
        yield get_settings()
    finally:
        _overrides.clear()
        _overrides.update(previous)


@lru_cache(maxsize=1)
def _base_settings() -> AgentSettings:
    kb = load_config()  # also loads .env
    env = os.environ.get
    return AgentSettings(
        kb=kb,
        chat_model=kb.chat_model,
        reranker_model=env("RERANKER_OPENAI_MODEL", kb.chat_model),
        judge_model=env("JUDGE_OPENAI_MODEL", kb.chat_model),
        embedding_model=kb.embedding_model,
        serper_api_key=env("SERPER_API_KEY", ""),
        redis_url=env("REDIS_URL", "redis://localhost:6379"),
        cache_name=env("CACHE_NAME", "netcore_rag_cache"),
        cache_similarity=float(env("CACHE_SIMILARITY_THRESHOLD", "0.90")),
        cache_ttl=int(env("CACHE_TTL_SECONDS", "86400")),
        retrieval_k=int(env("RETRIEVAL_K", "6")),
        relevance_threshold=float(env("RELEVANCE_THRESHOLD", "0.6")),
        faithfulness_threshold=float(env("FAITHFULNESS_THRESHOLD", "0.7")),
        groundedness_threshold=float(env("GROUNDEDNESS_THRESHOLD", "0.7")),
        context_precision_threshold=float(env("CONTEXT_PRECISION_THRESHOLD", "0.6")),
        context_token_budget=int(env("CONTEXT_TOKEN_BUDGET", "6000")),
        max_rewrites=int(env("MAX_REWRITES", "3")),
        max_retries=int(env("MAX_RETRIES", "3")),
        timeout_seconds=float(env("AGENT_TIMEOUT_SECONDS", "90")),
        max_plan_steps=int(env("MAX_PLAN_STEPS", "4")),
    )


__all__ = ["ACCESS_LEVELS", "ACCESS_LEVEL_BY_TYPE", "AgentSettings", "DEMO_USERS", "ROLE_ACCESS", "User",
           "get_settings", "get_user", "level_rank", "max_level", "override_settings"]
