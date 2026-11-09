"""Agent endpoints: blocking ask and streaming ask (SSE)."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from sse_starlette import EventSourceResponse, ServerSentEvent

from agentic_rag.config import User
from app.controllers.deps import get_agent_service, request_id
from app.core.problems import ProblemException
from app.core.security import get_current_user
from app.middleware.net import client_ip
from app.schemas.agent import AskRequest, AskResponse
from app.schemas.common import PROBLEM_RESPONSES
from app.services.agent_service import AgentService

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])
ERRORS = {c: PROBLEM_RESPONSES[c] for c in (401, 422, 429, 503, 504)}

SSE_DOC = {200: {"description": (
    "Server-Sent Events. Every event has an `id` (use it as `Last-Event-ID` to resume via "
    "GET /api/v1/agent/requests/{request_id}/events). Event types, in order: `accepted` (request_id, result/events "
    "URLs), `plan` (each plan version, before it runs), `step` (plan step running/done), `tool_call`, `trace`, "
    "`judge` (each judge evaluation and the action taken), then `result` (the full AskResponse) or `error` "
    "(RFC 9457 problem), and finally `done`."),
    "content": {"text/event-stream": {"example": 'id: 1731150000000-0\nevent: accepted\ndata: {"request_id": "..."}'
                                                 '\n\n'}}}}


def sse_response(service: AgentService, run_id: str, after_id: str, on_disconnect=None) -> EventSourceResponse:
    async def generator():
        finished = False
        try:
            async for event_id, event_type, data in service.stream(run_id, after_id):
                yield ServerSentEvent(data=json.dumps(data, ensure_ascii=False, default=str), event=event_type,
                                      id=event_id)
            finished = True
        finally:
            if not finished and on_disconnect is not None:
                asyncio.get_running_loop().create_task(on_disconnect())

    return EventSourceResponse(generator(), ping=service.settings.sse_ping_seconds,
                               headers={"Cache-Control": "no-cache",
                                        "X-Accel-Buffering": "no"})


@router.post("/ask", response_model=AskResponse, summary="Ask the agent (blocking)", responses=ERRORS)
async def ask(body: AskRequest, request: Request, user: User = Depends(get_current_user),
              service: AgentService = Depends(get_agent_service), run_id: str = Depends(request_id)) -> AskResponse:
    """Runs the full Enterprise Agentic RAG workflow and returns everything in one response: plan, executed plan,
    sources, judge details, tool calls, trace, cache info and timings. The `X-Request-ID` header is the run id."""
    handle = await service.start(run_id=run_id, user=user, request=body, endpoint="sync",
                                 client_ip=client_ip(request.scope, request.app.state.settings.trust_proxy_headers))
    try:
        outcome = await asyncio.shield(handle.task)
    except asyncio.CancelledError:  # client went away: the run continues in the background
        asyncio.get_running_loop().create_task(service.client_left(run_id))
        raise
    if outcome.response is not None and outcome.status == "completed":
        return outcome.response
    problem = outcome.problem or {}
    slug = "agent-timeout" if outcome.status == "timeout" else "agent-failed"
    raise ProblemException(slug, problem.get("detail"), result_url=f"/api/v1/agent/requests/{run_id}")


@router.post("/ask/stream", summary="Ask the agent (Server-Sent Events)", response_class=EventSourceResponse,
             responses={**SSE_DOC, **ERRORS})
async def ask_stream(body: AskRequest, request: Request, user: User = Depends(get_current_user),
                     service: AgentService = Depends(get_agent_service), run_id: str = Depends(request_id)):
    """Streams the run's progress as it happens. If the connection drops, the run keeps going: reconnect with
    GET /api/v1/agent/requests/{request_id}/events and the `Last-Event-ID` header."""
    await service.start(run_id=run_id, user=user, request=body, endpoint="stream",
                        client_ip=client_ip(request.scope, request.app.state.settings.trust_proxy_headers))
    return sse_response(service, run_id, "0-0", on_disconnect=lambda: service.client_left(run_id))
