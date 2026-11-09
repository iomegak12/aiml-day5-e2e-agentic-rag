"""RFC 9457 Problem Details (application/problem+json) for every error the API returns."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

PROBLEM_MEDIA_TYPE = "application/problem+json"
log = get_logger("api.errors")

# slug -> (title, default status). The type URI is <PROBLEM_BASE_URI><slug>.
PROBLEM_TYPES: dict[str, tuple[str, int]] = {
    "unauthorized": ("Missing or invalid API key", 401),
    "validation-error": ("Request validation failed", 422),
    "not-found": ("Resource not found", 404),
    "rate-limited": ("Too many requests", 429),
    "agent-timeout": ("Agent did not finish within the time budget", 504),
    "agent-failed": ("Agent failed to process the request", 503),
    "not-ready": ("Service dependencies are not ready", 503),
    "internal-error": ("Internal server error", 500),
}


class ProblemException(Exception):
    """Raise anywhere in the API to return an RFC 9457 problem."""

    def __init__(self, slug: str, detail: str | None = None, status: int | None = None,
                 headers: dict[str, str] | None = None, **extensions: Any) -> None:
        title, default_status = PROBLEM_TYPES.get(slug, (HTTPStatus(status or 500).phrase, status or 500))
        self.slug, self.title, self.status = slug, title, status or default_status
        self.detail, self.headers, self.extensions = detail, headers or {}, extensions
        super().__init__(detail or title)


def problem_body(*, slug: str | None, title: str, status: int, detail: str | None, instance: str | None,
                 request_id: str | None, base_uri: str, **extensions: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": f"{base_uri}{slug}" if slug else "about:blank",
        "title": title,
        "status": status,
    }
    if detail:
        body["detail"] = detail
    if instance:
        body["instance"] = instance
    if request_id:
        body["request_id"] = request_id
    body.update({k: v for k, v in extensions.items() if v is not None})
    return body


def problem_from_exception(exc: ProblemException, instance: str | None, request_id: str | None,
                           base_uri: str) -> dict[str, Any]:
    return problem_body(slug=exc.slug, title=exc.title, status=exc.status, detail=exc.detail, instance=instance,
                        request_id=request_id, base_uri=base_uri, **exc.extensions)


def problem_response(body: dict[str, Any], headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(body, status_code=body["status"], headers=headers, media_type=PROBLEM_MEDIA_TYPE)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _base(request: Request) -> str:
    return request.app.state.settings.problem_base_uri


def register_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemException)
    async def _problem(request: Request, exc: ProblemException):
        return problem_response(problem_from_exception(exc, request.url.path, _request_id(request), _base(request)),
                                exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = [{"pointer": "/" + "/".join(str(p) for p in e.get("loc", ()) if p != "body"),
                   "location": (e.get("loc") or ["body"])[0], "message": e.get("msg", ""), "type": e.get("type", "")}
                  for e in exc.errors()]
        body = problem_body(slug="validation-error", title=PROBLEM_TYPES["validation-error"][0], status=422,
                            detail=f"{len(errors)} validation error(s) in the request", instance=request.url.path,
                            request_id=_request_id(request), base_uri=_base(request), errors=errors)
        return problem_response(body)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        status = exc.status_code
        body = problem_body(slug="not-found" if status == 404 else None, title=HTTPStatus(status).phrase,
                            status=status, detail=str(exc.detail) if exc.detail else None, instance=request.url.path,
                            request_id=_request_id(request), base_uri=_base(request))
        return problem_response(body, getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled_error", error=type(exc).__name__)
        body = problem_body(slug="internal-error", title=PROBLEM_TYPES["internal-error"][0], status=500,
                            detail="An unexpected error occurred. Quote the request_id when contacting support.",
                            instance=request.url.path, request_id=_request_id(request), base_uri=_base(request))
        return problem_response(body)
