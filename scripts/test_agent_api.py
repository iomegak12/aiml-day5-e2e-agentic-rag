"""Smoke test of the agentic RAG REST API in planning mode (Plan-and-Execute), based on
notebooks/agentic-rag-plan.ipynb.

Scenarios (blocking POST /api/v1/agent/ask, mode=plan):
  1. simple       : a single-fact question               -> expect a 1-step plan
  2. cross-domain : the notebook's multi-part question     -> expect a multi-step plan over networking + meetings
  3. cache repeat : scenario 2 asked again                 -> expect a semantic-cache hit (no plan executed)

Each scenario is displayed (plan, executed plan, sources, judge, answer) and checked; a summary table lists every
check as PASS / FAIL / SKIP. Exit code 1 when any check fails.

    make agent-api-test [U=bob] [TRACE=1]
    uv run scripts/test_agent_api.py --user carol --trace

Prerequisites: the API is running (make api-run or make api-up) and the KB is populated.
URL and key default to .env: http://localhost:$API_PORT and the user's key from API_KEYS.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
console = Console()

SIMPLE_Q = "What does alarm NCS-BFD-3004 mean?"
CROSS_Q = ("Our NetCore Meet calls show MTG-MED-4102 packet loss at branch sites. Which SD-WAN QoS settings "
           "and SLA class should we apply, and what does the Meet troubleshooting guide recommend?")


# ---------------------------------------------------------------- checks


@dataclass
class Check:
    scenario: str
    name: str
    status: str  # PASS | FAIL | SKIP
    detail: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def check(self, scenario: str, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append(Check(scenario, name, "PASS" if ok else "FAIL", detail))
        return ok

    def skip(self, scenario: str, name: str, detail: str) -> None:
        self.checks.append(Check(scenario, name, "SKIP", detail))

    @property
    def failed(self) -> int:
        return sum(c.status == "FAIL" for c in self.checks)


# ---------------------------------------------------------------- config / client


def api_settings(args) -> tuple[str, str]:
    load_dotenv(ROOT / ".env")
    url = args.url or os.environ.get("API_URL") or f"http://localhost:{os.environ.get('API_PORT', '8080')}"
    key = args.api_key or os.environ.get("API_KEY")
    if not key:
        pairs = [item.strip().rsplit(":", 1) for item in os.environ.get("API_KEYS", "").split(",") if ":" in item]
        key = next((k for k, u in pairs if u.strip() == args.user), None)
    if not key:
        sys.exit(f"No API key for user '{args.user}': add it to API_KEYS in .env or pass --api-key.")
    return url.rstrip("/"), key


def preflight(client: httpx.Client) -> None:
    try:
        health = client.get("/health")
        ready = client.get("/ready")
    except httpx.HTTPError as exc:
        sys.exit(f"API not reachable at {client.base_url} ({type(exc).__name__}). Start it: make api-run / make api-up")
    console.print(f"API [bold]{client.base_url}[/bold]  version={health.json().get('version')}  "
                  f"ready={ready.status_code == 200}")
    if ready.status_code != 200:
        body = ready.json()
        sys.exit(f"API not ready: {body.get('detail')} {body.get('checks')}")


def ask(client: httpx.Client, question: str, *, bypass_cache: bool, timeout_seconds: int) -> tuple[httpx.Response,
                                                                                                    float]:
    started = time.monotonic()
    response = client.post("/api/v1/agent/ask", json={"question": question, "mode": "plan",
                                                      "timeout_seconds": timeout_seconds,
                                                      "bypass_cache": bypass_cache})
    return response, time.monotonic() - started


# ---------------------------------------------------------------- display


def show(title: str, body: dict, seconds: float, trace: bool) -> None:
    status = f"{body['status']} / {body['agent_status']}"
    console.print(Panel(f"[bold]{escape(body['question'])}[/bold]\nuser={body['user']['id']} "
                        f"({body['user']['role']})  status={status}  routes={body['routes']}  "
                        f"re-plans={body['rewrites']}  cache_hit={body['cache']['hit']}  "
                        f"time={seconds:.1f}s  request_id={body['request_id']}", title=title))
    for version in (body.get("plan") or {}).get("versions", []):
        t = Table(title=f"Plan v{version['version']}: {escape(version['rationale'])}", title_justify="left",
                  header_style="bold magenta")
        for col in ("Step", "Goal", "Tool", "Domains", "Query"):
            t.add_column(col)
        for st in version["steps"]:
            t.add_row(str(st["id"]), escape(st["goal"]), st["tool"], ", ".join(st["domains"]) or "-",
                      escape(st["query"]))
        console.print(t)
    if body["executed_plan"]:
        t = Table(title="Executed plan", title_justify="left", header_style="bold magenta")
        for col in ("Ver", "Step", "Tool", "Status", "Relevant", "Best", "Time (s)"):
            t.add_column(col)
        for st in body["executed_plan"]:
            t.add_row(f"v{st['version']}", str(st["id"]), st["tool"], st["status"], str(st["relevant"]),
                      f"{st['best']:.2f}", str(st["seconds"]))
        console.print(t)
    if body["sources"]:
        t = Table(title="Sources", title_justify="left", header_style="bold cyan")
        for col in ("KB ID", "Relevance", "Access", "Location"):
            t.add_column(col)
        for s in body["sources"]:
            t.add_row(str(s["kb_id"]), "-" if s.get("score") is None else f"{s['score']:.2f}",
                      str(s.get("access_level") or ""), escape(str(s.get("location") or ""))[:60])
        console.print(t)
    judge = body["judge"]
    if judge.get("scores"):
        t = Table(title=f"Judge ({judge.get('model')}) passed={judge.get('passed')}", title_justify="left",
                  header_style="bold cyan")
        for col in ("Metric", "Score", "Threshold"):
            t.add_column(col)
        for metric, score in judge["scores"].items():
            t.add_row(metric, f"{score:.3f}", str(judge["thresholds"].get(metric, "")))
        console.print(t)
        if judge.get("attempts"):
            console.print("Judge attempts: " + ", ".join(f"#{a['attempt']} {a['action']}" for a in judge["attempts"]))
    console.print(Panel(Markdown(body["answer"]), title="Answer"))
    if trace and body["trace"]:
        t = Table(title="Trace", title_justify="left", header_style="bold cyan", expand=True)
        for col in ("t (s)", "Step", "Decision", "Detail"):
            t.add_column(col)
        for e in body["trace"]:
            t.add_row(f"{e['t']:.2f}", e["step"], escape(e["decision"]), escape(e["detail"][:160]))
        console.print(t)


def domains_of(body: dict) -> set[str]:
    ids = [s["kb_id"] or "" for s in body["sources"]]
    return {"networking" for i in ids if i.startswith("KB-NET")} | {"meetings" for i in ids if i.startswith("KB-MTG")}


# ---------------------------------------------------------------- scenarios


def http_detail(response: httpx.Response) -> str:
    """Status code; for errors also the RFC 9457 problem title/detail."""
    if response.status_code == 200:
        return "200"
    try:
        problem = response.json()
        return f"{response.status_code} {problem.get('title', '')}: {problem.get('detail', '')}"
    except ValueError:
        return f"{response.status_code} {response.text[:150]}"


def common_checks(report: Report, sc: str, response: httpx.Response, body: dict) -> None:
    report.check(sc, "HTTP 200", response.status_code == 200, str(response.status_code))
    report.check(sc, "X-Request-ID = request_id", response.headers.get("x-request-id") == body.get("request_id"))
    report.check(sc, "run completed + answered", body["status"] == "completed" and body["agent_status"] == "answered",
                 f"{body['status']} / {body['agent_status']}")


def scenario_simple(client, report: Report, args) -> None:
    sc = "1 simple"
    response, seconds = ask(client, SIMPLE_Q, bypass_cache=True, timeout_seconds=args.timeout)
    if not report.check(sc, "HTTP 200", response.status_code == 200, http_detail(response)):
        return
    body = response.json()
    show("Scenario 1: simple question -> 1-step plan", body, seconds, args.trace)
    report.checks.pop()  # re-added by common_checks
    common_checks(report, sc, response, body)
    versions = (body.get("plan") or {}).get("versions", [])
    first = versions[0]["steps"] if versions else []
    report.check(sc, "plan v1 has 1 step", len(first) == 1, f"{len(first)} steps")
    report.check(sc, "a step executed with results", any(s["status"] == "done" for s in body["executed_plan"]))
    report.check(sc, "tool calls come from the planner",
                 bool(body["tool_calls"]) and all(t["origin"] == "planner" for t in body["tool_calls"]),
                 f"{len(body['tool_calls'])} calls")
    report.check(sc, "networking sources cited", "networking" in domains_of(body), str(sorted(domains_of(body))))
    report.check(sc, "judge passed", body["judge"].get("passed") is True, str(body["judge"].get("scores")))


def scenario_cross(client, report: Report, args) -> dict | None:
    sc = "2 cross-domain"
    response, seconds = ask(client, CROSS_Q, bypass_cache=True, timeout_seconds=args.timeout)
    if not report.check(sc, "HTTP 200", response.status_code == 200, http_detail(response)):
        return None
    body = response.json()
    show("Scenario 2: cross-domain question -> multi-step plan", body, seconds, args.trace)
    report.checks.pop()
    common_checks(report, sc, response, body)
    versions = (body.get("plan") or {}).get("versions", [])
    first = versions[0]["steps"] if versions else []
    report.check(sc, "plan v1 has >= 2 steps", len(first) >= 2, f"{len(first)} steps")
    planned = {d for s in first for d in s["domains"]}
    report.check(sc, "plan covers networking + meetings", {"networking", "meetings"} <= planned, str(sorted(planned)))
    done = [s for s in body["executed_plan"] if s["status"] == "done"]
    report.check(sc, ">= 2 steps found results", len(done) >= 2, f"{len(done)} done")
    report.check(sc, "sources from both domains", {"networking", "meetings"} <= domains_of(body),
                 str(sorted(domains_of(body))))
    report.check(sc, "judge passed", body["judge"].get("passed") is True, str(body["judge"].get("scores")))
    stored = client.get(f"/api/v1/agent/requests/{body['request_id']}")
    report.check(sc, "result stored (GET /requests/{id})",
                 stored.status_code == 200 and (stored.json().get("result") or {}).get("answer") == body["answer"],
                 str(stored.status_code))
    return {"body": body, "seconds": seconds}


def scenario_cache(client, report: Report, args, previous: dict | None) -> None:
    sc = "3 cache repeat"
    if previous is None:
        report.skip(sc, "cache hit", "scenario 2 did not return a result")
        return
    first = previous["body"]
    if not (first["agent_status"] == "answered" and first["judge"].get("passed")):
        report.skip(sc, "cache hit", "scenario 2 was not judge-passed, so it was not cached")
        return
    response, seconds = ask(client, CROSS_Q, bypass_cache=False, timeout_seconds=args.timeout)
    if not report.check(sc, "HTTP 200", response.status_code == 200, http_detail(response)):
        return
    body = response.json()
    show("Scenario 3: same question again -> semantic cache", body, seconds, args.trace)
    report.check(sc, "served from cache", body["agent_status"] == "cache_hit" and body["cache"]["hit"],
                 f"{body['agent_status']} similarity={body['cache'].get('similarity')}")
    report.check(sc, "no plan executed", not body["executed_plan"], f"{len(body['executed_plan'])} steps")
    report.check(sc, "faster than the planned run", seconds < previous["seconds"],
                 f"{seconds:.1f}s vs {previous['seconds']:.1f}s")


# ---------------------------------------------------------------- main


def summary(report: Report) -> None:
    t = Table(title="Agent API planning test", title_justify="left", header_style="bold")
    for col in ("Scenario", "Check", "Result", "Detail"):
        t.add_column(col)
    style = {"PASS": "green", "FAIL": "red", "SKIP": "yellow"}
    for c in report.checks:
        t.add_row(c.scenario, c.name, f"[{style[c.status]}]{c.status}[/{style[c.status]}]", escape(c.detail[:80]))
    console.print(t)
    passed = sum(c.status == "PASS" for c in report.checks)
    skipped = sum(c.status == "SKIP" for c in report.checks)
    colour = "red" if report.failed else "green"
    console.print(f"[bold {colour}]{passed} passed, {report.failed} failed, {skipped} skipped[/bold {colour}]")


def main() -> int:
    parser = argparse.ArgumentParser(description="Planning-mode smoke test of the agentic RAG REST API.")
    parser.add_argument("--user", default="bob", help="demo user whose key from API_KEYS is used (default bob)")
    parser.add_argument("--url", help="API base URL (default http://localhost:$API_PORT)")
    parser.add_argument("--api-key", help="API key (default: the user's key from API_KEYS in .env)")
    parser.add_argument("--timeout", type=int, default=300, help="agent time budget per question (default 300 s)")
    parser.add_argument("--trace", action="store_true", help="also print each run's trace")
    args = parser.parse_args()

    url, key = api_settings(args)
    report = Report()
    # HTTP timeout = agent budget + API grace + margin
    with httpx.Client(base_url=url, headers={"X-API-Key": key}, timeout=args.timeout + 60) as client:
        preflight(client)
        scenario_simple(client, report, args)
        previous = scenario_cross(client, report, args)
        scenario_cache(client, report, args, previous)
    summary(report)
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
