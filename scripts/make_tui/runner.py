"""Run `make ...` as a subprocess, stream its output line by line and stop the whole process tree on demand."""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import subprocess
import sys
from collections.abc import Awaitable, Callable

from make_tui.parser import PROJECT_ROOT

IS_WINDOWS = sys.platform == "win32"


class MakeRunner:
    def __init__(self, cwd=PROJECT_ROOT):
        self.cwd = cwd
        self._proc: asyncio.subprocess.Process | None = None
        self.stopped = False

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def run(self, args: list[str], on_line: Callable[[str], Awaitable[None] | None]) -> int:
        """Run args (args[0] = 'make'), call on_line for every output line, return the exit code."""
        exe = shutil.which(args[0])
        if exe is None:
            raise FileNotFoundError(f"'{args[0]}' was not found on PATH (install GNU make)")
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "FORCE_COLOR": "1"}
        # `uv run tui.py` exports UV=<path to uv.exe>; the Makefile's `UV ?= uv` would pick it up and the shell
        # mangles the Windows backslashes ("C:Python312Scriptsuv.exe: command not found") - let make use `uv`.
        env.pop("UV", None)
        kwargs: dict = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if IS_WINDOWS else \
            {"start_new_session": True}
        self.stopped = False
        self._proc = await asyncio.create_subprocess_exec(
            exe, *args[1:], cwd=self.cwd, env=env, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, **kwargs)
        assert self._proc.stdout is not None
        while True:
            raw = await self._proc.stdout.readline()
            if not raw:
                break
            result = on_line(raw.decode("utf-8", errors="replace").rstrip("\r\n"))
            if asyncio.iscoroutine(result):
                await result
        return await self._proc.wait()

    async def stop(self) -> None:
        """Terminate make and everything it started (servers, docker logs -f, ...)."""
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return
        self.stopped = True
        if IS_WINDOWS:
            killer = await asyncio.create_subprocess_exec(
                "taskkill", "/PID", str(proc.pid), "/T", "/F",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await killer.wait()
        else:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except TimeoutError:
                os.killpg(proc.pid, signal.SIGKILL)
