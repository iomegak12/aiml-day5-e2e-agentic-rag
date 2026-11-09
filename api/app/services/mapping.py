"""AgentResult (scripts/agentic_rag) -> AskResponse DTO."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.schemas.agent import AskResponse

PLAN_FIELDS = ("id", "version", "goal", "tool", "domains", "query", "depends_on")


def user_info(user) -> dict[str, Any]:
    return {"id": user.user_id, "name": user.name, "role": user.role, "allowed_levels": list(user.allowed_levels)}


def plan_details(steps: list[dict], rationales: dict[int, str]) -> dict[str, Any] | None:
    if not steps:
        return None
    versions: dict[int, list[dict]] = {}
    for st in steps:
        versions.setdefault(st["version"], []).append({k: st[k] for k in PLAN_FIELDS if k in st})
    return {"versions": [{"version": v, "rationale": rationales.get(v, ""), "steps": s}
                         for v, s in sorted(versions.items())],
            "replans": max(len(versions) - 1, 0)}


def to_ask_response(*, run_id: str, run_status: str, result, include_trace: bool, started_at: datetime,
                    finished_at: datetime, total_s: float, queued_s: float) -> AskResponse:
    judge = result.judge or {"scores": result.judge_scores}
    return AskResponse.model_validate({
        "request_id": run_id,
        "status": run_status,
        "agent_status": result.status,
        "mode": result.mode,
        "question": result.question,
        "user": user_info(result.user),
        "answer": result.answer,
        "plan": plan_details(result.plan, result.plan_rationales),
        "executed_plan": result.plan,
        "sources": result.sources,
        "judge": judge,
        "tool_calls": result.tool_calls if include_trace else [],
        "trace": [{"t": e.t, "step": e.step, "decision": e.decision, "detail": e.detail} for e in result.trace]
        if include_trace else [],
        "cache": {"hit": result.status == "cache_hit", "similarity": result.cache_similarity,
                  "cached_question": result.cached_question},
        "routes": result.routes,
        "rewrites": result.rewrites,
        "timings": {"total_s": round(total_s, 2), "agent_s": result.elapsed, "queued_s": round(queued_s, 2),
                    "started_at": started_at, "finished_at": finished_at},
    })
