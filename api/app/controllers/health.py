"""Liveness, readiness and Prometheus metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.container import Container
from app.controllers.deps import get_container
from app.core.problems import PROBLEM_TYPES, problem_body, problem_response
from app.schemas.common import PROBLEM_RESPONSES, Health, Readiness

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=Health, summary="Liveness probe (no dependency checks)")
async def health(request: Request) -> Health:
    return Health(status="ok", version=request.app.state.settings.version)


@router.get("/ready", response_model=Readiness, summary="Readiness probe: Chroma, Redis and Postgres",
            responses={503: PROBLEM_RESPONSES[503]})
async def ready(request: Request, container: Container = Depends(get_container)):
    ok, checks = await container.health.readiness()
    if ok:
        return Readiness(status="ready", checks=checks)
    title, status = PROBLEM_TYPES["not-ready"]
    down = [name for name, c in checks.items() if c["status"] != "up"]
    return problem_response(problem_body(slug="not-ready", title=title, status=status,
                                         detail=f"Unavailable: {', '.join(down)}", instance=request.url.path,
                                         request_id=request.state.request_id,
                                         base_uri=request.app.state.settings.problem_base_uri, checks=checks))


@router.get("/metrics", summary="Prometheus metrics", response_class=Response,
            responses={200: {"content": {CONTENT_TYPE_LATEST: {}}}})
async def prometheus_metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
