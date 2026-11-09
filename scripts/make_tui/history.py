"""Run history: the last runs in .make_tui_history.json at the project root (git-ignored)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from make_tui.parser import PROJECT_ROOT

HISTORY_FILE = PROJECT_ROOT / ".make_tui_history.json"
MAX_ENTRIES = 50


@dataclass(frozen=True)
class Run:
    target: str
    args: list[str]  # argv, e.g. ["make", "agent-ask", "Q=...", "U=bob"]
    exit_code: int | None  # None = stopped by the user
    seconds: float
    at: str  # ISO timestamp (local time)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class History:
    def __init__(self, path: Path = HISTORY_FILE, limit: int = MAX_ENTRIES):
        self.path, self.limit = path, limit
        self.runs: list[Run] = self._load()

    def _load(self) -> list[Run]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [Run(**item) for item in data][: self.limit]
        except (OSError, ValueError, TypeError):
            return []  # missing or unreadable file: start empty

    def add(self, run: Run) -> None:
        self.runs = [run, *self.runs][: self.limit]  # newest first
        try:
            self.path.write_text(json.dumps([asdict(r) for r in self.runs], indent=1), encoding="utf-8")
        except OSError:
            pass  # history is a convenience: never break a run because of it
