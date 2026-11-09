"""Caller identity: the agent sends `X-User-Id` on every MCP request (no authentication yet - demo only).

The users and roles mirror DEMO_USERS in scripts/agentic_rag/config.py (kept local so the MCP image does not
need the agent code). Keep both lists in step.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers

USER_HEADER = "x-user-id"


@dataclass(frozen=True)
class Caller:
    user_id: str
    name: str
    role: str  # guest | employee | admin

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


USERS: dict[str, Caller] = {
    "alice": Caller("alice", "Alice", "guest"),
    "bob": Caller("bob", "Bob", "employee"),
    "carol": Caller("carol", "Carol", "admin"),
}


def resolve_caller(user_id: str | None) -> Caller:
    """Map a header value to a known user; anything else is refused."""
    uid = (user_id or "").strip().lower()
    if not uid:
        raise ToolError("Missing X-User-Id header: the caller is unknown.")
    caller = USERS.get(uid)
    if caller is None:
        raise ToolError(f"Unknown user '{uid}'.")
    return caller


def current_caller() -> Caller:
    """The caller of the current MCP request (from the HTTP header)."""
    return resolve_caller(get_http_headers().get(USER_HEADER))
