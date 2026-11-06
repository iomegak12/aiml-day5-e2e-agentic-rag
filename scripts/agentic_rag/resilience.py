"""Retry with exponential backoff (cross-cutting policy) for calls outside the agent's model/tool nodes."""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def with_retry(fn: Callable[[], T], *, attempts: int = 3, initial_delay: float = 1.0, max_delay: float = 8.0,
               what: str = "call", log: Callable[[str, str, str], None] | None = None) -> T:
    """Run fn(); on failure wait 1s, 2s, 4s... (+ jitter) and retry. Re-raises after the last attempt."""
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - transient LLM / search / DB failures
            if attempt == attempts:
                raise
            delay = min(max_delay, initial_delay * 2 ** (attempt - 1)) * (0.8 + random.random() * 0.4)
            if log:
                log("Retry", f"{what} #{attempt}", f"{type(exc).__name__}: {str(exc)[:80]} - waiting {delay:.1f}s")
            time.sleep(delay)
    raise RuntimeError("unreachable")
