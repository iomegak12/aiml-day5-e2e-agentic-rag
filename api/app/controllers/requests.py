"""Reconnect / retrieval endpoints: list my runs, get one run, resume its event stream."""

from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from sse_starlette import EventSourceResponse, ServerSentEvent

from agentic_rag.config import User
from app.container import Container
from app.controllers.agent import SSE_DOC, sse_response
from app.controllers.deps import get_container
from app.core.problems import ProblemException
from app.core.security import get_current_user
from app.schemas.agent import RunDetail, RunPage, RunStatus, RunSummary
from app.schemas.common import PROBLEM_RESPONSES

router = APIRouter(prefix="/api/v1/agent/requests", tags=["Requests"])
ERRORS = {c: PROBLEM_RESPONSES[c] for c in (401, 404, 422, 429, 503)}
STREAM_ID = re.compile(r"^\d+-\d+$")


def _summary(run: dict[str, Any]) -> dict[str, Any]:
    return {"request_id": str(run["id"]), "status": run["status"], "agent_status": run.get("agent_status"),
            "mode": run["mode"], "endpoint": run["endpoint"], "question": run["question"], "user_id": run["user_id"],
            "created_at": run.get("created_at"), "finished_at": run.get("finished_at"),
            "elapsed_s": run.get("elapsed_s"), "client_disconnected": bool(run.get("client_disconnected"))}


async def _owned_run(container: Container, request_id: str, user: User) -> dict[str, Any]:
    """Owner or admin only. Anything else is 404, so request ids of other users do not leak."""
    try:
        uuid.UUID(request_id)
    except ValueError:
        raise ProblemException("not-found", f"Request {request_id} not found") from None
    try:
        run = await container.runs.get(request_id)
    except Exception as exc:  # noqa: BLE001
        raise ProblemException("not-ready", f"Run store unavailable ({type(exc).__name__})") from exc
    if run is None or (run["user_id"] != user.user_id and user.role != "admin"):
        raise ProblemException("not-found", f"Request {request_id} not found")
    return run


@router.get("", response_model=RunPage, summary="List my agent requests (admin: everyone's)", responses=ERRORS)
async def list_requests(user: User = Depends(get_current_user), container: Container = Depends(get_container),
                        status: RunStatus | None = Query(None), limit: int = Query(20, ge=1, le=100),
                        cursor: str | None = Query(None, description="next_cursor from the previous page")) -> RunPage:
    try:
        rows, next_cursor = await container.runs.list(None if user.role == "admin" else user.user_id, status, limit,
                                                      cursor)
    except ValueError:
        raise ProblemException("validation-error", "Invalid cursor", status=422,
                               errors=[{"pointer": "/cursor", "location": "query", "message": "invalid cursor",
                                        "type": "value_error"}]) from None
    except Exception as exc:  # noqa: BLE001
        raise ProblemException("not-ready", f"Run store unavailable ({type(exc).__name__})") from exc
    return RunPage(items=[RunSummary(**_summary(r)) for r in rows], next_cursor=next_cursor)


@router.get("/{request_id}", response_model=RunDetail, summary="Get one request: status, and the result once done",
            responses=ERRORS)
async def get_request(request_id: str, user: User = Depends(get_current_user),
                      container: Container = Depends(get_container)) -> RunDetail:
    run = await _owned_run(container, request_id, user)
    events_url = f"/api/v1/agent/requests/{request_id}/events"
    return RunDetail(**_summary(run), result=run.get("result"), error=run.get("error"), events_url=events_url,
                     links={"self": f"/api/v1/agent/requests/{request_id}", "events": events_url})


@router.get("/{request_id}/events", summary="Resume (or replay) a request's event stream",
            response_class=EventSourceResponse, responses={**SSE_DOC, **ERRORS})
async def request_events(request_id: str, request: Request, user: User = Depends(get_current_user),
                         container: Container = Depends(get_container),
                         last_event_id: str | None = Header(None, alias="Last-Event-ID",
                                                            description="Resume after this event id"),
                         after: str | None = Query(None, description="Same as Last-Event-ID (for clients that "
                                                                     "cannot set headers)")):
    """Replays the events after `Last-Event-ID` (all events when absent), then follows the live run until `done`.
    Events are buffered for EVENT_BUFFER_TTL_SECONDS (1 h); after that, the stored result is replayed as
    `result` + `done` from Postgres."""
    run = await _owned_run(container, request_id, user)
    after_id = last_event_id or after or "0-0"
    if not STREAM_ID.match(after_id):
        after_id = "0-0" if after_id.startswith("db-") else after_id
    if not STREAM_ID.match(after_id):
        raise ProblemException("validation-error", "Last-Event-ID must be an event id from this stream", status=422,
                               errors=[{"pointer": "/Last-Event-ID", "location": "header",
                                        "message": "expected <ms>-<seq>", "type": "value_error"}])
    service = container.agent_service
    try:
        buffered = await container.events.exists(request_id)
    except Exception:  # noqa: BLE001 - Redis down: fall back to the stored result
        buffered = False
    if buffered or service.is_running(request_id):
        return sse_response(service, request_id, after_id)

    # Buffer expired (or never written): replay the final state from Postgres
    async def from_store():
        n = 0
        if run.get("error"):
            n += 1
            yield ServerSentEvent(data=_json(run["error"]), event="error", id=f"db-{n}")
        if run.get("result"):
            n += 1
            yield ServerSentEvent(data=_json(run["result"]), event="result", id=f"db-{n}")
        if run["status"] == "running":
            n += 1
            yield ServerSentEvent(data=_json({"request_id": request_id, "status": "running",
                                              "detail": "The run is not active on this server and its event buffer "
                                                        "has expired; poll the result URL."}),
                                  event="error", id=f"db-{n}")
        yield ServerSentEvent(data=_json({"request_id": request_id, "status": run["status"]}), event="done",
                              id=f"db-{n + 1}")

    return EventSourceResponse(from_store(), headers={"Cache-Control": "no-cache"})


def _json(data: Any) -> str:
    import json
    return json.dumps(data, ensure_ascii=False, default=str)
