"""Audit writes to Postgres: PII-redacted, retried with exponential backoff, never failing the API response."""

from __future__ import annotations

import asyncio
from typing import Any

from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.core.metrics import AUDIT_WRITE_FAILURES
from app.repositories.audit_repository import RequestLogRepository, RunRepository
from app.services.redaction import redact

log = get_logger("api.audit")


class AuditService:
    def __init__(self, request_logs: RequestLogRepository, runs: RunRepository, attempts: int = 3,
                 max_wait: float = 2.0) -> None:
        self.request_logs, self.runs = request_logs, runs
        self._attempts, self._max_wait = attempts, max_wait
        self._tasks: set[asyncio.Task] = set()

    async def _retry(self, kind: str, fn, *args) -> bool:
        try:
            async for attempt in AsyncRetrying(stop=stop_after_attempt(self._attempts),
                                               wait=wait_exponential(multiplier=0.2, max=self._max_wait),
                                               retry=retry_if_exception_type(Exception), reraise=True):
                with attempt:
                    if attempt.retry_state.attempt_number > 1:
                        log.warning("audit_retry", kind=kind, attempt=attempt.retry_state.attempt_number)
                    await fn(*args)
            return True
        except Exception as exc:  # noqa: BLE001 - audit must never break the request
            AUDIT_WRITE_FAILURES.labels(kind).inc()
            log.error("audit_write_failed", kind=kind, error=f"{type(exc).__name__}: {exc}"[:300])
            return False

    def spawn(self, coro) -> None:
        """Fire-and-forget (keeps a reference so the task is not garbage-collected)."""
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self, timeout: float = 5.0) -> None:
        if self._tasks:
            await asyncio.wait(self._tasks, timeout=timeout)

    # ---- HTTP request audit ----
    async def log_request(self, entry: dict[str, Any]) -> bool:
        entry = {**entry, "request_body": redact(entry.get("request_body")),
                 "response_body": redact(entry.get("response_body")),
                 "query_string": redact(entry.get("query_string"))}
        return await self._retry("request", self.request_logs.add, entry)

    # ---- agent runs ----
    async def create_run(self, run: dict[str, Any]) -> bool:
        return await self._retry("run_create", self.runs.create, {**run, "question": redact(run["question"])})

    async def finish_run(self, run_id: str, values: dict[str, Any]) -> bool:
        values = {**values, "result": redact(values.get("result")), "error": redact(values.get("error"))}
        return await self._retry("run_finish", self.runs.finish, run_id, values)

    async def mark_disconnected(self, run_id: str) -> bool:
        return await self._retry("run_disconnect", self.runs.mark_disconnected, run_id)
