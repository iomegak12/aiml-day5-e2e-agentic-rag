"""FastAPI application factory.

    uvicorn app.main:create_app --factory --app-dir api --port 8080        (make api-run)

Middleware (outermost first): RequestContext (request id, JSON access log, metrics, audit) -> RateLimit -> routes.
CORS is intentionally not enabled (same-origin only).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.container import Container
from app.controllers import agent, health, me, requests
from app.core.config import ApiSettings, get_api_settings
from app.core.logging import get_logger, setup_logging
from app.core.problems import register_problem_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware

DESCRIPTION = """
REST API for the **NetCore Enterprise Agentic RAG agent** (Plan-and-Execute or ReAct), with guardrails, a semantic
cache, RBAC, an LLM judge and a full trace.

* **Auth**: send `X-API-Key` (each key maps to a demo user: alice = guest, bob = employee, carol = admin).
* **Errors**: RFC 9457 `application/problem+json`.
* **Rate limit**: per client IP; exceeding it blocks the IP for a while (`429` + `Retry-After`).
* **Reconnect**: every run has a `request_id` (`X-Request-ID` header, first `accepted` event). Fetch it with
  `GET /api/v1/agent/requests/{request_id}`, or resume its stream with `/events` + `Last-Event-ID`.
"""

TAGS = [
    {"name": "Agent", "description": "Ask the agent (blocking or streaming)"},
    {"name": "Requests", "description": "Reconnect: list, fetch and resume earlier requests"},
    {"name": "Identity", "description": "Who am I (profile and RBAC levels of the API key)"},
    {"name": "Health", "description": "Liveness, readiness and Prometheus metrics"},
]


def create_app(settings: ApiSettings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_api_settings()
    setup_logging(settings.log_level, settings.log_file, settings.log_max_bytes, settings.log_backup_count)
    log = get_logger("api")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("api_starting", version=settings.version)
        yield
        await app.state.container.close()
        log.info("api_stopped")

    app = FastAPI(title=settings.app_name, version=settings.version, description=DESCRIPTION, openapi_tags=TAGS,
                  lifespan=lifespan, docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json")
    app.state.settings = settings
    app.state.container = container or Container.build(settings)

    register_problem_handlers(app)
    app.add_middleware(RateLimitMiddleware)        # inner
    app.add_middleware(RequestContextMiddleware)   # outer: sees rate-limited responses too
    app.include_router(agent.router)
    app.include_router(requests.router)
    app.include_router(me.router)
    app.include_router(health.router)
    return app
