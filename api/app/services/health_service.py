"""Readiness checks: Chroma (heartbeat), Redis (PING), Postgres (SELECT 1) - run concurrently, 3 s each."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

import httpx

Check = Callable[[], Awaitable[None]]


class HealthService:
    def __init__(self, checks: dict[str, Check], timeout: float = 3.0) -> None:
        self.checks, self.timeout = checks, timeout

    async def _run(self, check: Check) -> dict:
        started = time.monotonic()
        try:
            await asyncio.wait_for(check(), timeout=self.timeout)
            return {"status": "up", "ms": round((time.monotonic() - started) * 1000, 1)}
        except Exception as exc:  # noqa: BLE001
            return {"status": "down", "ms": round((time.monotonic() - started) * 1000, 1),
                    "error": f"{type(exc).__name__}: {exc}"[:200]}

    async def readiness(self) -> tuple[bool, dict[str, dict]]:
        names = list(self.checks)
        results = await asyncio.gather(*(self._run(self.checks[n]) for n in names))
        report = dict(zip(names, results))
        return all(r["status"] == "up" for r in results), report


def chroma_check(host: str, port: int) -> Check:
    async def check() -> None:
        async with httpx.AsyncClient(timeout=3.0) as client:
            (await client.get(f"http://{host}:{port}/api/v2/heartbeat")).raise_for_status()
    return check
