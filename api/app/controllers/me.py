"""Who am I: the profile behind the X-API-Key (used by the web UI at sign-in)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agentic_rag.config import User
from app.core.security import get_current_user
from app.schemas.agent import UserInfo
from app.schemas.common import PROBLEM_RESPONSES

router = APIRouter(prefix="/api/v1", tags=["Identity"])


@router.get("/me", response_model=UserInfo, summary="Profile and RBAC levels of the calling API key",
            responses={c: PROBLEM_RESPONSES[c] for c in (401, 429)})
async def me(user: User = Depends(get_current_user)) -> UserInfo:
    return UserInfo(id=user.user_id, name=user.name, role=user.role, allowed_levels=list(user.allowed_levels))
