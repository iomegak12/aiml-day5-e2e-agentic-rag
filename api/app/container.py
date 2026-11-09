"""Composition root: builds repositories and services once per app (tests pass their own Container)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from redis.asyncio import Redis

from app.core.config import ApiSettings
from app.db import create_engine, create_session_factory
from app.repositories.audit_repository import RequestLogRepository, RunRepository, SqlRequestLogRepository, \
    SqlRunRepository
from app.repositories.event_repository import EventRepository
from app.services.agent_service import AgentRunner, AgentService, langchain_runner
from app.services.audit_service import AuditService
from app.services.health_service import HealthService, chroma_check


@dataclass
class Container:
    settings: ApiSettings
    redis: Redis
    request_logs: RequestLogRepository
    runs: RunRepository
    events: EventRepository
    audit: AuditService
    agent_service: AgentService
    health: HealthService
    resources: list[Any] = field(default_factory=list)  # closed on shutdown

    @classmethod
    def build(cls, settings: ApiSettings, *, redis: Redis | None = None, request_logs: RequestLogRepository | None = None,
              runs: RunRepository | None = None, runner: AgentRunner = langchain_runner,
              health: HealthService | None = None) -> Container:
        resources: list[Any] = []
        if request_logs is None or runs is None:
            engine = create_engine(settings.database_url)
            sessions = create_session_factory(engine)
            request_logs = request_logs or SqlRequestLogRepository(sessions)
            runs = runs or SqlRunRepository(sessions)
            resources.append(engine)
        if redis is None:
            redis = Redis.from_url(settings.redis_url)
            resources.append(redis)
        events = EventRepository(redis, settings.event_buffer_ttl_seconds)
        audit = AuditService(request_logs, runs, attempts=settings.db_retry_attempts)
        agent_service = AgentService(settings, events, audit, runner)
        if health is None:
            async def redis_check() -> None:
                await redis.ping()
            health = HealthService({"chroma": chroma_check(settings.chroma_host, settings.chroma_port),
                                    "redis": redis_check, "postgres": runs.ping})
        return cls(settings, redis, request_logs, runs, events, audit, agent_service, health, resources)

    async def close(self) -> None:
        await self.agent_service.shutdown()
        await self.audit.drain()
        for resource in self.resources:
            if hasattr(resource, "dispose"):
                await resource.dispose()
            elif hasattr(resource, "aclose"):
                await resource.aclose()
