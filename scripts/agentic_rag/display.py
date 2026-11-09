"""Rich rendering for the CLI and the notebook (results, trace, users, settings)."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from .config import DEMO_USERS, get_settings

STATUS_STYLE = {"answered": "green", "cache_hit": "cyan", "low_confidence": "yellow", "no_info": "yellow",
                "blocked": "red", "refused": "red", "timeout": "red", "error": "red"}


def _console() -> Console:
    return Console()


STEP_STYLE = {"done": "green", "no_results": "yellow", "replanned": "dim", "skipped": "red", "pending": "white",
              "running": "cyan"}


def show_plan(steps: list[dict], version: int, rationale: str) -> None:
    """Show a (re-)plan as soon as it is created - before it is executed."""
    t = Table(title=f"Plan v{version}: {escape(rationale)}", title_justify="left", header_style="bold magenta")
    for col in ("Step", "Goal", "Tool", "Domains", "Query", "Depends on"):
        t.add_column(col)
    for st in steps:
        t.add_row(str(st["id"]), escape(st["goal"]), st["tool"], ", ".join(st["domains"]) or "-",
                  escape(st["query"]), ", ".join(map(str, st["depends_on"])) or "-")
    _console().print(t)


def show_plan_report(plan: list[dict]) -> None:
    """Executed plan: every version's steps with their outcome."""
    t = Table(title="Executed plan", title_justify="left", header_style="bold magenta")
    for col in ("Ver", "Step", "Goal", "Tool", "Status", "Relevant", "Best", "Time (s)"):
        t.add_column(col)
    for st in plan:
        style = STEP_STYLE.get(st["status"], "white")
        t.add_row(f"v{st['version']}", str(st["id"]), escape(st["goal"][:60]), st["tool"],
                  f"[{style}]{st['status']}[/{style}]", str(st["relevant"]), f"{st['best']:.2f}", str(st["seconds"]))
    _console().print(t)


def show_result(result, show_trace: bool = True) -> None:
    c = _console()
    style = STATUS_STYLE.get(result.status, "white")
    header = (f"[bold]{escape(result.question)}[/bold]\nuser=[bold]{result.user.user_id}[/bold] "
              f"(role {result.user.role})  mode={result.mode}  status=[{style}]{result.status}[/{style}]  "
              f"routes={result.routes or '-'}  rewrites/re-plans={result.rewrites}  time={result.elapsed}s")
    if result.cached_question:
        header += f"\n[cyan]served from cache[/cyan] (cached question: {escape(result.cached_question)})"
    c.print(Panel(header, border_style=style))
    c.print(Panel(Markdown(result.answer), title="Answer", border_style=style))
    if result.plan:
        show_plan_report(result.plan)

    if result.sources:
        t = Table(title="Sources", title_justify="left", header_style="bold cyan")
        for col in ("KB ID", "Relevance", "Access", "Status", "Location"):
            t.add_column(col)
        for s in result.sources:
            t.add_row(str(s["kb_id"]), "-" if s.get("score") is None else f"{s['score']:.2f}", s.get("access_level", ""),
                      s.get("status", ""), escape(str(s.get("location", ""))[:60]))
        c.print(t)
    if result.judge_scores:
        cfg = get_settings()
        thresholds = {"faithfulness": cfg.faithfulness_threshold, "groundedness": cfg.groundedness_threshold,
                      "context_precision": cfg.context_precision_threshold}
        t = Table(title=f"Judge LLM ({cfg.judge_model})", title_justify="left", header_style="bold cyan")
        for col in ("Metric", "Score", "Threshold", "Result"):
            t.add_column(col)
        for metric, score in result.judge_scores.items():
            ok = score >= thresholds.get(metric, 0)
            t.add_row(metric, f"{score:.3f}", f"{thresholds.get(metric, 0):.2f}",
                      "[green]pass[/green]" if ok else "[red]fail[/red]")
        c.print(t)
    if show_trace:
        show_trace_table(result)


def show_trace_table(result) -> None:
    t = Table(title="Trace", title_justify="left", header_style="bold cyan", expand=True)
    t.add_column("t (s)", justify="right", width=7)
    t.add_column("Step", width=20)
    t.add_column("Decision", width=22)
    t.add_column("Detail", ratio=1)
    for e in result.trace:
        t.add_row(f"{e.t:.2f}", e.step, escape(e.decision), escape(e.detail[:200]))
    _console().print(t)


def show_guardrail_check(label: str, text: str, result) -> None:
    """Show a standalone guardrail check (e.g. check_output on a sample answer)."""
    verdict = "[green]allowed[/green]" if result.allowed else f"[red]blocked {escape(str(result.violations))}[/red]"
    _console().print(Panel(f"{escape(text)}\n\n{verdict}  {escape(result.reason)}", title=label))


def show_users() -> None:
    t = Table(title="Demo users (RBAC)", title_justify="left", header_style="bold cyan")
    for col in ("User", "Name", "Role", "Allowed access levels"):
        t.add_column(col)
    for u in DEMO_USERS.values():
        t.add_row(u.user_id, u.name, u.role, ", ".join(u.allowed_levels))
    _console().print(t)


def show_settings() -> None:
    s = get_settings()
    t = Table(title="Agent settings (.env)", title_justify="left", header_style="bold cyan", show_header=False)
    rows = [("Orchestrator model", s.chat_model), ("Reranker / guardrail model", s.reranker_model),
            ("Judge model", s.judge_model), ("Embedding model", s.embedding_model),
            ("Chroma", f"{s.kb.chroma_host}:{s.kb.chroma_port} {s.kb.databases}"), ("Redis cache", s.redis_url),
            ("Cache similarity", s.cache_similarity), ("Relevance threshold", s.relevance_threshold),
            ("Faithfulness / groundedness / precision",
             f"{s.faithfulness_threshold} / {s.groundedness_threshold} / {s.context_precision_threshold}"),
            ("Context token budget", s.context_token_budget), ("Max rewrites / retries", f"{s.max_rewrites} / {s.max_retries}"),
            ("Timeout budget (s)", s.timeout_seconds), ("Max plan steps", s.max_plan_steps)]
    for k, v in rows:
        t.add_row(k, str(v))
    _console().print(t)
