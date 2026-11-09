"""Test fixtures: everything external is faked (agent, Postgres, Redis, Chroma). No network, no Docker."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import fakeredis
import httpx
import pytest

from agentic_rag.agent import AgentResult
from agentic_rag.config import DEMO_USERS
from agentic_rag.state import TraceEvent
from app.container import Container
from app.core.config import ApiSettings
from app.main import create_app
from app.repositories.audit_repository import decode_cursor, encode_cursor
from app.services.health_service import HealthService

KEYS = {"alice": "k-alice", "bob": "k-bob", "carol": "k-carol"}


def headers(user: str = "bob") -> dict[str, str]:
    return {"X-API-Key": KEYS[user]}


# ---------------------------------------------------------------- fake agent


def make_result(question: str, user_id: str, mode: str = "plan", status: str = "answered") -> AgentResult:
    plan = [] if mode == "react" else [
        {"id": 1, "version": 1, "goal": "Find BFD troubleshooting", "tool": "search_knowledge_base",
         "domains": ["networking"], "query": "BFD flap", "depends_on": [], "status": "no_results", "relevant": 0,
         "best": 0.3, "seconds": 1.2},
        {"id": 2, "version": 2, "goal": "Retry with alarm code", "tool": "search_knowledge_base",
         "domains": ["networking"], "query": "NCS-BFD-3004", "depends_on": [], "status": "done", "relevant": 2,
         "best": 0.9, "seconds": 1.0},
    ]
    tool_calls = [{"seq": 1, "name": "search_knowledge_base", "args": {"query": "BFD flap"},
                   "origin": "agent" if mode == "react" else "planner", "status": "ok", "result": "2 relevant",
                   "seconds": 1.0, "t": 2.0}]
    judge = {"model": "judge-model", "passed": True, "scores": {"faithfulness": 0.9},
             "thresholds": {"faithfulness": 0.7},
             "attempts": [{"attempt": 1, "scores": {"faithfulness": 0.9}, "passed": True, "failed": [],
                           "action": "accept", "error": None, "seconds": 3.0}]}
    return AgentResult(question=question, user=DEMO_USERS[user_id], answer="Check BFD timers [KB-NET-1005, p. 2].",
                       status=status, routes=["vector", "vector"], rewrites=1, judge_scores={"faithfulness": 0.9},
                       sources=[{"kb_id": "KB-NET-1005", "score": 0.9, "location": "p. 2", "access_level": "internal",
                                 "status": "current"}],
                       elapsed=4.2, trace=[TraceEvent(0.1, "Request", user_id, "q"), TraceEvent(4.2, "Response",
                                                                                              status, "ok")],
                       mode=mode, plan=plan, plan_rationales={1: "single lookup", 2: "retry"} if plan else {},
                       tool_calls=tool_calls, judge=judge)


class FakeRunner:
    """Stands in for agentic_rag.ask: emits the same event types, returns an AgentResult."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.delay = 0.0
        self.status = "answered"
        self.raises: Exception | None = None
        self.gate: threading.Event | None = None  # when set, the run waits for it

    def __call__(self, *, question, user_id, mode, timeout_seconds, bypass_cache, on_event):
        self.calls.append({"question": question, "user_id": user_id, "mode": mode,
                           "timeout_seconds": timeout_seconds, "bypass_cache": bypass_cache})
        on_event("trace", {"t": 0.0, "step": "Request", "decision": user_id, "detail": question})
        if mode == "plan":
            on_event("plan", {"version": 1, "label": "plan", "rationale": "single lookup", "steps": []})
            on_event("step", {"id": 1, "status": "running"})
            on_event("step", {"id": 1, "status": "done"})
        on_event("tool_call", {"seq": 1, "name": "search_knowledge_base", "origin": "planner", "status": "ok"})
        on_event("judge", {"attempt": 1, "passed": True, "action": "accept"})
        if self.gate is not None:
            self.gate.wait(10)
        if self.delay:
            time.sleep(self.delay)
        if self.raises:
            raise self.raises
        return make_result(question, user_id, mode, self.status)


# ---------------------------------------------------------------- fake repositories


class FakeRequestLogs:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    async def add(self, entry: dict[str, Any]) -> None:
        self.entries.append(entry)


class FakeRuns:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}
        self._clock = datetime(2026, 11, 9, tzinfo=timezone.utc)

    async def create(self, run: dict[str, Any]) -> None:
        self._clock += timedelta(seconds=1)
        self.rows[run["id"]] = {"created_at": self._clock, "finished_at": None, "agent_status": None,
                                "client_disconnected": False, "elapsed_s": None, "result": None, "error": None,
                                **run}

    async def finish(self, run_id: str, values: dict[str, Any]) -> None:
        if run_id in self.rows:
            self.rows[run_id].update(values, finished_at=datetime.now(timezone.utc))

    async def mark_disconnected(self, run_id: str) -> None:
        if run_id in self.rows:
            self.rows[run_id]["client_disconnected"] = True

    async def get(self, run_id: str):
        row = self.rows.get(run_id)
        return {**row, "id": run_id} if row else None

    async def list(self, user_id, status, limit, cursor):
        rows = [{**r, "id": rid} for rid, r in self.rows.items()
                if (user_id is None or r["user_id"] == user_id) and (status is None or r["status"] == status)]
        rows.sort(key=lambda r: (r["created_at"], r["id"]), reverse=True)
        if cursor:
            created, rid = decode_cursor(cursor)
            rows = [r for r in rows if (r["created_at"], r["id"]) < (created, str(rid))]
        page = rows[:limit]
        nxt = encode_cursor(page[-1]["created_at"], page[-1]["id"]) if len(rows) > limit else None
        return page, nxt

    async def ping(self) -> None:
        return None


# ---------------------------------------------------------------- app / client


def make_settings(**overrides) -> ApiSettings:
    values = {"api_keys": ",".join(f"{k}:{u}" for u, k in KEYS.items()), "log_file": "", "log_level": "WARNING",
              "api_timeout_min": 1, "api_timeout_default": 10, "api_timeout_grace": 1, "api_timeout_max": 30,
              "rate_limit_per_minute": 1000, "rate_limit_block_seconds": 30}
    values.update(overrides)
    return ApiSettings(_env_file=None, **values)


class Harness:
    def __init__(self, **settings_overrides) -> None:
        self.settings = make_settings(**settings_overrides)
        self.runner = FakeRunner()
        self.redis = fakeredis.FakeAsyncRedis()
        self.request_logs, self.runs = FakeRequestLogs(), FakeRuns()
        self.checks = {"chroma": True, "redis": True, "postgres": True}

        def check(name):
            async def run() -> None:
                if not self.checks[name]:
                    raise ConnectionError(f"{name} down")
            return run

        self.container = Container.build(self.settings, redis=self.redis, request_logs=self.request_logs,
                                         runs=self.runs, runner=self.runner,
                                         health=HealthService({n: check(n) for n in self.checks}))
        self.app = create_app(self.settings, self.container)

    def client(self, ip: str = "10.0.0.1") -> httpx.AsyncClient:
        transport = httpx.ASGITransport(app=self.app, client=(ip, 5000))
        return httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30)


@pytest.fixture
def harness() -> Harness:
    return Harness()


@pytest.fixture
async def client(harness):
    async with harness.client() as c:
        yield c


def parse_sse(text: str) -> list[dict]:
    """SSE wire format -> [{'id', 'event', 'data'}] (comments/pings skipped)."""
    events = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        event: dict[str, Any] = {}
        for line in block.split("\n"):
            if not line or line.startswith(":"):
                continue
            key, _, value = line.partition(":")
            event[key] = value[1:] if value.startswith(" ") else value
        if "data" in event:
            event["data"] = json.loads(event["data"])
            events.append(event)
    return events
