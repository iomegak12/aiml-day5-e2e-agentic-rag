"""FastAPI dependencies: services come from the app's container (swap them in tests)."""

from __future__ import annotations

from fastapi import Request

from app.container import Container
from app.services.agent_service import AgentService


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_agent_service(request: Request) -> AgentService:
    return request.app.state.container.agent_service


def request_id(request: Request) -> str:
    return request.state.request_id
