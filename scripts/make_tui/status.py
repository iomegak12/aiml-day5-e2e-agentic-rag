"""Container status of the netcore-* containers (docker or podman ps)."""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class Container:
    name: str
    state: str  # running | exited | created | ...
    status: str  # e.g. "Up 2 hours (healthy)"

    @property
    def health(self) -> str:
        """healthy | unhealthy | starting | running | stopped"""
        text = self.status.lower()
        for word in ("unhealthy", "healthy", "starting"):
            if f"({word}" in text:
                return word
        return "running" if self.state == "running" else "stopped"


def detect_engine(choice: str = "auto") -> str | None:
    """The engine to query: the user's choice, else docker if installed, else podman."""
    if choice != "auto":
        return choice if shutil.which(choice) else None
    return next((e for e in ("docker", "podman") if shutil.which(e)), None)


async def containers(engine: str) -> list[Container]:
    proc = await asyncio.create_subprocess_exec(
        engine, "ps", "-a", "--filter", "name=netcore-", "--format", "{{.Names}}\t{{.State}}\t{{.Status}}",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    out, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
    rows = []
    for line in out.decode("utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            rows.append(Container(*parts))
    return sorted(rows, key=lambda c: c.name)
