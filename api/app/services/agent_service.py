"""Runs agent requests decoupled from the HTTP connection and publishes their progress as replayable events.

    start()  : audit row (running) -> 'accepted' event -> background task
    _execute : waits for a free worker thread -> agentic_rag.ask() in the thread (hard cap = budget + grace)
               -> 'result' or 'error' event -> audit row (final status) -> 'done' event
    stream() : SSE source for both POST /ask/stream (live) and GET /requests/{id}/events (resume):
               replays the Redis Stream after Last-Event-ID, then tails it until 'done'.

A client that disconnects never stops the run: the result is still stored and can be fetched by request_id.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from app.core import metrics
from app.core.config import ApiSettings
from app.core.logging import get_logger
from app.core.problems import ProblemException, problem_body
from app.repositories.event_repository import EventRepository
from app.schemas.agent import AskRequest, AskResponse
from app.services.audit_service import AuditService
from app.services.mapping import to_ask_response

log = get_logger("api.agent")

TRACE_EVENTS = {"trace", "tool_call"}  # dropped from the stream when include_trace=false
TERMINAL = "done"


class AgentRunner(Protocol):
    def __call__(self, *, question: str, user_id: str, mode: str, timeout_seconds: float, bypass_cache: bool,
                 on_event: Callable[[str, dict], None]) -> Any: ...


def langchain_runner(*, question: str, user_id: str, mode: str, timeout_seconds: float, bypass_cache: bool,
                     on_event: Callable[[str, dict], None]):
    """The real agent (scripts/agentic_rag). Imported lazily: loading the agent stack is slow."""
    from agentic_rag import ask
    return ask(question, user_id, verbose=False, mode=mode, show_plan=False, timeout_seconds=timeout_seconds,
               bypass_cache=bypass_cache, on_event=on_event)


@dataclass
class Outcome:
    status: str  # completed | failed | timeout
    response: AskResponse | None = None
    problem: dict[str, Any] | None = None


@dataclass
class RunHandle:
    run_id: str
    task: asyncio.Task | None = None
    disconnected: bool = False  # the client left before the run finished
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class AgentService:
    def __init__(self, settings: ApiSettings, events: EventRepository, audit: AuditService,
                 runner: AgentRunner = langchain_runner) -> None:
        self.settings, self.events, self.audit, self.runner = settings, events, audit, runner
        self._pool = ThreadPoolExecutor(max_workers=settings.agent_max_concurrency, thread_name_prefix="agent")
        self.active: dict[str, RunHandle] = {}

    # ------------------------------------------------------------------ budget
    def budget(self, requested: int | None) -> int:
        s = self.settings
        value = requested if requested is not None else s.api_timeout_default
        if not s.api_timeout_min <= value <= s.api_timeout_max:
            raise ProblemException("validation-error", f"timeout_seconds must be between {s.api_timeout_min} and "
                                                       f"{s.api_timeout_max}", status=422,
                                   errors=[{"pointer": "/timeout_seconds", "location": "body",
                                            "message": f"must be between {s.api_timeout_min} and "
                                                       f"{s.api_timeout_max}", "type": "range"}])
        return value

    # ------------------------------------------------------------------ start
    async def start(self, *, run_id: str, user, request: AskRequest, client_ip: str | None,
                    endpoint: str) -> RunHandle:
        budget = self.budget(request.timeout_seconds)
        options = {"mode": request.mode, "timeout_seconds": budget, "include_trace": request.include_trace,
                   "bypass_cache": request.bypass_cache}
        await self.audit.create_run({"id": run_id, "user_id": user.user_id, "role": user.role, "client_ip": client_ip,
                                     "endpoint": endpoint, "mode": request.mode, "question": request.question,
                                     "options": options, "status": "running"})
        handle = RunHandle(run_id)
        self.active[run_id] = handle
        publisher = asyncio.create_task(self._publish(handle, request.include_trace))
        handle.queue.put_nowait(("accepted", {
            "request_id": run_id, "user": {"id": user.user_id, "role": user.role}, "options": options,
            "result_url": f"/api/v1/agent/requests/{run_id}", "events_url": f"/api/v1/agent/requests/{run_id}/events",
        }))
        handle.task = asyncio.create_task(self._execute(handle, user, request, budget, publisher))
        return handle

    async def _publish(self, handle: RunHandle, include_trace: bool) -> None:
        """Single consumer per run, so events keep their order in the Redis Stream."""
        while True:
            item = await handle.queue.get()
            if item is None:
                return
            event_type, data = item
            if not include_trace and event_type in TRACE_EVENTS:
                continue
            try:
                await self.events.append(handle.run_id, event_type, data)
            except Exception as exc:  # noqa: BLE001 - live stream degrades; the result is still stored
                log.error("event_publish_failed", run_id=handle.run_id, event=event_type, error=str(exc)[:200])

    # ------------------------------------------------------------------ execute
    async def _execute(self, handle: RunHandle, user, request: AskRequest, budget: int,
                       publisher: asyncio.Task) -> Outcome:
        loop = asyncio.get_running_loop()
        run_id, s = handle.run_id, self.settings
        accepted_at, t0 = datetime.now(timezone.utc), time.monotonic()
        started = asyncio.Event()
        queued = {"s": 0.0}

        def on_event(event_type: str, data: dict) -> None:  # called from the agent thread
            loop.call_soon_threadsafe(handle.queue.put_nowait, (event_type, data))

        def work():
            queued["s"] = time.monotonic() - t0
            loop.call_soon_threadsafe(started.set)
            return self.runner(question=request.question, user_id=user.user_id, mode=request.mode,
                               timeout_seconds=budget, bypass_cache=request.bypass_cache, on_event=on_event)

        outcome: Outcome
        future = loop.run_in_executor(self._pool, work)
        metrics.AGENT_IN_PROGRESS.inc()
        try:
            try:
                await asyncio.wait_for(started.wait(), timeout=s.api_timeout_max)  # waiting for a free worker
            except TimeoutError:
                future.cancel()
                raise TimeoutError("all agent workers are busy") from None
            result = await asyncio.wait_for(future, timeout=budget + s.api_timeout_grace)
            finished_at = datetime.now(timezone.utc)
            run_status = "failed" if result.status == "error" else "completed"
            response = to_ask_response(run_id=run_id, run_status=run_status, result=result,
                                       include_trace=request.include_trace, started_at=accepted_at,
                                       finished_at=finished_at, total_s=time.monotonic() - t0, queued_s=queued["s"])
            problem = None
            if run_status == "failed":
                problem = self._problem("agent-failed", "The agent could not complete the request (model, search or "
                                                        "database error after retries).", run_id)
            outcome = Outcome(run_status, response, problem)
            if handle.disconnected and run_status == "completed":
                outcome.status = response.status = "client_disconnected"  # result still stored and retrievable
            self._record_metrics(result, outcome.status, time.monotonic() - t0)
        except TimeoutError as exc:
            detail = (str(exc) if "busy" in str(exc) else
                      f"No result within {budget}+{s.api_timeout_grace} s. The run may still finish in the "
                      f"background; check the result URL later.")
            outcome = Outcome("timeout", problem=self._problem("agent-timeout", detail, run_id))
            metrics.AGENT_RUNS.labels(request.mode, "timeout", "n/a").inc()
        except Exception as exc:  # noqa: BLE001
            log.exception("agent_run_failed", run_id=run_id)
            outcome = Outcome("failed", problem=self._problem("agent-failed", f"{type(exc).__name__}", run_id))
            metrics.AGENT_RUNS.labels(request.mode, "failed", "n/a").inc()
        finally:
            metrics.AGENT_IN_PROGRESS.dec()

        response_json = outcome.response.model_dump(mode="json") if outcome.response else None
        if outcome.problem:
            handle.queue.put_nowait(("error", outcome.problem))
        if response_json:
            handle.queue.put_nowait(("result", response_json))
        await self.audit.finish_run(run_id, {"status": outcome.status, "result": response_json,
                                             "error": outcome.problem,
                                             "agent_status": outcome.response.agent_status if outcome.response else None,
                                             "elapsed_s": round(time.monotonic() - t0, 2)})
        handle.queue.put_nowait((TERMINAL, {"request_id": run_id, "status": outcome.status}))
        handle.queue.put_nowait(None)
        await publisher
        self.active.pop(run_id, None)
        log.info("agent_run_finished", run_id=run_id, status=outcome.status, mode=request.mode,
                 agent_status=outcome.response.agent_status if outcome.response else None,
                 seconds=round(time.monotonic() - t0, 2))
        return outcome

    def _problem(self, slug: str, detail: str, run_id: str) -> dict[str, Any]:
        from app.core.problems import PROBLEM_TYPES
        title, status = PROBLEM_TYPES[slug]
        return problem_body(slug=slug, title=title, status=status, detail=detail,
                            instance=f"/api/v1/agent/requests/{run_id}", request_id=run_id,
                            base_uri=self.settings.problem_base_uri)

    @staticmethod
    def _record_metrics(result, run_status: str, seconds: float) -> None:
        metrics.AGENT_RUNS.labels(result.mode, run_status, result.status).inc()
        metrics.AGENT_DURATION.labels(result.mode).observe(seconds)
        if result.rewrites:
            metrics.AGENT_REPLANS.labels(result.mode).inc(result.rewrites)
        if result.status == "cache_hit":
            metrics.AGENT_CACHE_HITS.inc()
        for attempt in (result.judge or {}).get("attempts", []):
            metrics.AGENT_JUDGE.labels("error" if attempt.get("error") else
                                       "pass" if attempt.get("passed") else "fail").inc()
        for call in result.tool_calls:
            metrics.AGENT_TOOL_CALLS.labels(call["name"], call["origin"], call["status"]).inc()

    # ------------------------------------------------------------------ disconnects
    async def client_left(self, run_id: str) -> None:
        """Called when a client disconnects before the run finished: the run continues; flag it."""
        handle = self.active.get(run_id)
        if handle is not None:
            handle.disconnected = True
            metrics.AGENT_CLIENT_DISCONNECTS.inc()
            log.info("client_disconnected", run_id=run_id)
            await self.audit.mark_disconnected(run_id)

    def is_running(self, run_id: str) -> bool:
        return run_id in self.active

    # ------------------------------------------------------------------ events (SSE source)
    async def stream(self, run_id: str, after_id: str = "0-0",
                     deadline_s: float | None = None) -> AsyncIterator[tuple[str, str, dict]]:
        """Replay events after `after_id`, then tail live ones until 'done' (or the deadline)."""
        deadline = time.monotonic() + (deadline_s or self.settings.api_timeout_max + self.settings.api_timeout_grace
                                       + 60)
        last = after_id
        while time.monotonic() < deadline:
            batch = await self.events.read(run_id, last, block_ms=2000)
            for event_id, event_type, data in batch:
                last = event_id
                yield event_id, event_type, data
                if event_type == TERMINAL:
                    return
        yield "timeout", "error", self._problem("agent-timeout", "The event stream ended before the run finished; "
                                                                 "fetch the result URL later.", run_id)

    async def shutdown(self) -> None:
        tasks = [h.task for h in self.active.values() if h.task]
        if tasks:
            await asyncio.wait(tasks, timeout=5)
        self._pool.shutdown(wait=False, cancel_futures=True)
