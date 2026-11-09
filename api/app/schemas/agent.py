"""Request / response DTOs for the agent endpoints (they define the OpenAPI schema)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal["running", "completed", "failed", "timeout", "client_disconnected"]


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [
        {"question": "How do I troubleshoot BFD tunnel flaps on an NCX edge?", "mode": "plan"}]})

    question: str = Field(min_length=3, max_length=2000, description="The user's question")
    mode: Literal["plan", "react"] = Field("plan", description="plan = Plan-and-Execute; react = tool-routing agent")
    timeout_seconds: int | None = Field(None, description="Agent time budget (bounded by API_TIMEOUT_MIN/MAX); "
                                                          "default API_TIMEOUT_DEFAULT")
    include_trace: bool = Field(True, description="Include trace and tool calls (set false for smaller responses)")
    bypass_cache: bool = Field(False, description="Skip the semantic-cache lookup")


class UserInfo(BaseModel):
    id: str
    name: str
    role: str
    allowed_levels: list[str]


class PlanStep(BaseModel):
    id: int
    version: int
    goal: str
    tool: str
    domains: list[str] = []
    query: str
    depends_on: list[int] = []
    ticket_args: dict[str, Any] = Field({}, description="Arguments of an IT ticket step (MCP ticket tools)")


class ExecutedStep(PlanStep):
    status: str = Field(description="done | no_results | replanned | skipped | error | pending")
    relevant: int = Field(0, description="Relevant chunks found")
    best: float = Field(0.0, description="Best rerank relevance score")
    seconds: float = 0.0


class PlanVersion(BaseModel):
    version: int
    rationale: str = ""
    steps: list[PlanStep]


class PlanDetails(BaseModel):
    versions: list[PlanVersion] = Field(description="v1 = initial plan; later versions = re-plans")
    replans: int = 0


class Source(BaseModel):
    kb_id: str | None
    score: float | None = None
    location: str | None = None
    access_level: str | None = None
    status: str | None = None


class JudgeAttempt(BaseModel):
    attempt: int
    scores: dict[str, float] = {}
    passed: bool = False
    failed: list[str] = []
    action: str = Field("", description="accept | regenerate | re-retrieve | disclaimer")
    error: str | None = None
    seconds: float = 0.0


class JudgeDetails(BaseModel):
    model: str | None = None
    passed: bool | None = Field(None, description="null when the judge did not run (cache hit, blocked, no info)")
    scores: dict[str, float] = {}
    thresholds: dict[str, float] = {}
    attempts: list[JudgeAttempt] = []


class ToolCall(BaseModel):
    seq: int
    name: str
    args: dict[str, Any] = {}
    origin: Literal["agent", "planner"] = Field(description="agent = LLM tool call (react); planner = plan step")
    status: str
    result: str = ""
    seconds: float = 0.0
    t: float = Field(0.0, description="Seconds since the request started")


class TraceEvent(BaseModel):
    t: float
    step: str
    decision: str
    detail: str = ""


class CacheInfo(BaseModel):
    hit: bool
    similarity: float | None = None
    cached_question: str | None = None


class Timings(BaseModel):
    total_s: float = Field(description="API wall time from acceptance to result")
    agent_s: float = Field(description="Time spent inside the agent")
    queued_s: float = Field(0.0, description="Time waiting for a free agent worker")
    started_at: datetime
    finished_at: datetime


class AskResponse(BaseModel):
    request_id: str
    status: RunStatus
    agent_status: str = Field(description="answered | cache_hit | low_confidence | no_info | blocked | refused | "
                                          "timeout | error")
    mode: str
    question: str
    user: UserInfo
    answer: str
    plan: PlanDetails | None = Field(None, description="Plan details (plan mode)")
    executed_plan: list[ExecutedStep] = Field([], description="Every step of every plan version with its outcome")
    sources: list[Source] = []
    judge: JudgeDetails
    tool_calls: list[ToolCall] = []
    trace: list[TraceEvent] = []
    cache: CacheInfo
    routes: list[str] = []
    rewrites: int = Field(0, description="Query rewrites (react) or re-plans (plan)")
    timings: Timings


class RunSummary(BaseModel):
    request_id: str
    status: RunStatus
    agent_status: str | None = None
    mode: str
    endpoint: str
    question: str
    user_id: str
    created_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_s: float | None = None
    client_disconnected: bool = False


class RunDetail(RunSummary):
    result: AskResponse | None = Field(None, description="Full response once the run has finished")
    error: dict[str, Any] | None = Field(None, description="RFC 9457 problem when the run failed or timed out")
    events_url: str
    links: dict[str, str] = {}


class RunPage(BaseModel):
    items: list[RunSummary]
    next_cursor: str | None = Field(None, description="Pass as ?cursor= to get the next page")
