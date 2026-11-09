"""API-key authentication: X-API-Key -> demo user (RBAC role comes from scripts/agentic_rag/config.py)."""

from __future__ import annotations

import hmac

import structlog
from fastapi import Request, Security
from fastapi.security import APIKeyHeader

from agentic_rag.config import DEMO_USERS, User
from app.core.problems import ProblemException

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False,
                              description="Demo API key mapped to a user (alice=guest, bob=employee, carol=admin)")


def resolve_user(api_key: str | None, key_map: dict[str, str]) -> User | None:
    """Constant-time comparison against every configured key (no early exit on the first mismatch)."""
    if not api_key:
        return None
    match = None
    for key, user_id in key_map.items():
        if hmac.compare_digest(api_key.encode(), key.encode()):
            match = user_id
    return DEMO_USERS.get(match) if match else None


async def get_current_user(request: Request, api_key: str | None = Security(api_key_header)) -> User:
    user = resolve_user(api_key, request.app.state.settings.key_map)
    if user is None:
        raise ProblemException("unauthorized", "Send a valid key in the X-API-Key header.",
                               headers={"WWW-Authenticate": 'ApiKey header="X-API-Key"'})
    request.state.user_id = user.user_id
    structlog.contextvars.bind_contextvars(user_id=user.user_id)
    return user
