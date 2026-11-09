"""Prometheus metrics (exposed at GET /metrics)."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency (streams: until the stream ends)",
                         ["method", "route"],
                         buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300))
HTTP_IN_PROGRESS = Gauge("http_requests_in_progress", "HTTP requests in progress")

AGENT_RUNS = Counter("agent_runs_total", "Agent runs by mode, run status and agent status",
                     ["mode", "status", "agent_status"])
AGENT_DURATION = Histogram("agent_run_duration_seconds", "Agent run wall time", ["mode"],
                           buckets=(1, 5, 10, 20, 30, 45, 60, 90, 120, 180, 240, 300))
AGENT_IN_PROGRESS = Gauge("agent_runs_in_progress", "Agent runs currently executing")
AGENT_REPLANS = Counter("agent_rewrites_total", "Query rewrites / re-plans", ["mode"])
AGENT_JUDGE = Counter("agent_judge_evaluations_total", "Judge LLM evaluations", ["result"])
AGENT_CACHE_HITS = Counter("agent_cache_hits_total", "Answers served from the semantic cache")
AGENT_TOOL_CALLS = Counter("agent_tool_calls_total", "Tool calls", ["tool", "origin", "status"])
AGENT_CLIENT_DISCONNECTS = Counter("agent_client_disconnects_total", "Clients that left before the run finished")

RATE_LIMIT_BLOCKS = Counter("rate_limit_blocks_total", "Requests rejected by the rate limiter", ["reason"])
AUDIT_WRITE_FAILURES = Counter("audit_write_failures_total", "Audit writes that failed after all retries", ["kind"])
