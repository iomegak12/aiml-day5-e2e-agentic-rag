# Plan: REST API for the Enterprise Agentic RAG Agent (`api/`)

## Context
The agent in `scripts/agentic_rag/` (plan/react modes, guardrails, cache, judge, trace) runs from the notebook and CLI only. The business needs a production-style REST API that exposes it, returning the plan, executed plan, sources, judge details, trace, tool calls, the result and timings, with enterprise concerns: auth/RBAC, rate limiting, timeouts, JSON logs, metrics, a Postgres audit log, RFC 9457 errors, Docker and unit tests.

## Decisions (agreed via MCQs)
| Topic | Decision |
|---|---|
| Stack | FastAPI + Uvicorn, OpenAPI at `/openapi.json`, Swagger at `/docs` (ReDoc at `/redoc`) |
| Location | Top-level `api/` (controllers / services / repositories / schemas / core / middleware) + `api/tests/` |
| Streaming | **SSE**. Events: `accepted`, `plan`, `step`, `trace`, `judge`, `result`, `error`, `done`. No token streaming |
| Identity | `X-API-Key` → demo user (alice/bob/carol) map from `.env`, constant-time compare |
| Rate limit | Per IP, 100 req/min (Redis); on breach the IP is **blocked for 30 s** (429 + `Retry-After`). Health/ready/metrics/docs exempt |
| CORS | No CORS middleware (same-origin only) |
| Timeout | Client `timeout_seconds` (bounded, e.g. 10–300) → agent budget; API hard cap = budget + grace → RFC 9457 **504** |
| Retry | Postgres audit writes (tenacity, exponential backoff). Audit failure never fails the response |
| Logging | structlog JSON → console + rotating file; `request_id`, user, IP bound via contextvars |
| Metrics | Prometheus `/metrics`: HTTP count/latency/status + agent status, mode, re-plans, judge pass, cache hits, rate-limit blocks |
| DB | SQLAlchemy 2 async + asyncpg + **Alembic**; JSONB request/response bodies, **PII-redacted** (reuse `guardrails.detect_pii`) |
| Disconnect | Stream disconnect → agent finishes in its worker thread; audit row status `client_disconnected` |
| Errors | RFC 9457 `application/problem+json` (type, title, status, detail, instance, + `request_id`, `errors[]` for validation) |
| Endpoints | The requested ones, plus reconnect/retrieval: get by id, list mine, resume SSE |
| Event buffer | Redis Streams, 1 h TTL; final results permanent in Postgres |
| Access to past requests | Owner only; admin sees all; others get 404 |
| Request options | `question`, `mode` (plan\|react), `timeout_seconds`, `include_trace`, `bypass_cache` |
| Tool calls | **Unified list**: react = real LLM tool calls; plan = each executed step as a tool call (`origin="planner"`) |
| Compose | Extend existing `docker-compose.yml` with `postgres` + `api` |
| Tests | pytest + httpx `AsyncClient`, everything mocked (dependency_overrides, fakeredis) |

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness, no dependency checks |
| GET | `/ready` | Chroma, Redis, Postgres probes → 200 / 503 (problem+json) |
| GET | `/metrics` | Prometheus text |
| POST | `/api/v1/agent/ask` | Blocking; returns the full `AskResponse` |
| POST | `/api/v1/agent/ask/stream` | SSE; same final payload in the `result` event |

| GET | `/api/v1/agent/requests` | Caller's history: `status`, `limit`, `cursor` (cursor pagination, newest first) |
| GET | `/api/v1/agent/requests/{request_id}` | Status (`running`/`completed`/`failed`/`timeout`/`client_disconnected`) plus the full `AskResponse` once finished |
| GET | `/api/v1/agent/requests/{request_id}/events` | SSE resume: `Last-Event-ID` → replays missed events, then tails live until `done` |

**Reconnect design**
- The run is **decoupled from the HTTP connection**: the service starts the agent as a background task (thread), so a disconnect never stops it.
- An audit row is inserted at start (`running`) and updated at the end with the result.
- Every event is written with XADD to a Redis Stream `agent:events:{request_id}`, kept for **1 h** (`EVENT_BUFFER_TTL_SECONDS=3600`). The stream ID becomes the SSE `id`, and `Last-Event-ID` maps to XREAD.
- When the buffer has expired, the `/events` endpoint replays a synthetic `result` + `done` from Postgres.
- **Access:** owners see their own requests and the admin (carol) sees all of them. Other users get **404** (no ID leak).
- The client learns the `request_id` from the `X-Request-ID` response header and the first `accepted` event.

`AskResponse`: `request_id`, `status`, `mode`, `user{id,role}`, `answer`, `plan{versions[], rationale}`, `executed_plan[]`, `sources[]`, `judge{passed, scores, thresholds, attempts[]}`, `tool_calls[]`, `trace[]`, `cache{hit, similarity, cached_question}`, `routes`, `rewrites`, `timings{total_s, agent_s}`.

## Layout (`api/`)
```
api/app/main.py               app factory, lifespan (DB engine, Redis, logging), routers, exception handlers
api/app/core/                 config (pydantic-settings), logging (structlog), security (API key → User), problems (RFC 9457)
api/app/middleware/           request_id + access log, rate_limit (Redis penalty box), metrics
api/app/controllers/          health.py, agent.py (thin: validate → service → DTO / SSE)
api/app/services/             agent_service.py (runs ask() in threadpool, timeout, event queue → SSE), audit_service.py (redact + retry)
api/app/repositories/         audit_repository.py (SQLAlchemy async)
api/app/models/               ORM: api_request (id, ts, ip, user, method, path, status, latency, request/response JSONB, agent status, error)
api/app/schemas/              Pydantic DTOs: AskRequest, AskResponse, Plan/Step/ToolCall/Judge/Trace, SSE event models, Problem
api/alembic/ + alembic.ini    initial migration
api/tests/                    test_health, test_ask, test_stream, test_auth, test_rate_limit, test_errors, test_audit_service, test_mapping, test_requests (get/list/404 scoping), test_resume (Last-Event-ID replay, Postgres fallback)
```

## Additive changes in `scripts/agentic_rag/` (backward compatible)
- `state.py` `RequestContext`: `on_event` callback (called from `log()`, the plan callback and step updates); `tool_calls` list; `judge_attempts` list.
- `retrieval.py` / `executor.py`: record tool calls (name, args, result summary, duration, origin).
- `middleware.py` AnswerQuality: append each judge attempt (scores, passed, action); SemanticCache: honour `bypass_cache`.
- `agent.py`: `ask(..., bypass_cache=False, timeout_seconds=None, on_event=None)`; `AgentResult` gains `tool_calls`, `judge`, `rationale`. The notebook and CLI keep their output unchanged.

## Infra and config
- `Containerfile` (multi-stage: `uv` builder → `python:3.12-slim` runtime, non-root, healthcheck on `/health`); `.dockerignore` updated (tests, notebooks).
- `compose.yaml` (renamed from `docker-compose.yml`): `postgres:17-alpine` (named volume `pg-data`, healthcheck) + `api` (depends_on healthy chroma/redis/postgres; `CHROMA_HOST=chroma`, `REDIS_URL=redis://redis:6379` overrides).
- `.env` / `.env.example`: `API_KEYS`, `API_PORT`, `DATABASE_URL`, `POSTGRES_*`, `RATE_LIMIT_PER_MINUTE=100`, `RATE_LIMIT_BLOCK_SECONDS=30`, `API_TIMEOUT_MIN/MAX/DEFAULT`, `API_TIMEOUT_GRACE`, `LOG_LEVEL`, `LOG_FILE`, `EVENT_BUFFER_TTL_SECONDS=3600`.
- Dependencies: `fastapi`, `uvicorn[standard]`, `sse-starlette`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `structlog`, `prometheus-client`, `tenacity`, `pydantic-settings`; dev: `pytest`, `pytest-asyncio`, `httpx`, `fakeredis`, `asgi-lifespan`. I'll check the current docs and versions before implementing.
- Makefile: `api-run` (uvicorn --reload), `api-up/down/logs`, `db-up`, `db-migrate`, `api-test`.
- `.gitignore`: `pg-data/`, `logs/`.
- Docs: README (API section), CHANGELOG 0.7.0, TROUBLESHOOTING, SECURITY (API keys, rate limit, PII redaction, no CORS), CONTRIBUTING (tests, migrations), CODE_OF_CONDUCT (contact/enforcement touch-up only).

## Docker + Podman support (infra only; the API design is unchanged)
| Topic | Decision |
|---|---|
| Engine | The Makefile auto-detects (`docker`, else `podman`), and `ENGINE=podman` overrides. `COMPOSE` becomes `docker compose` or `podman-compose` to match |
| Podman compose | **podman-compose** (`uv tool install podman-compose`), so no Docker binaries are needed. The compose file stays within its supported subset (healthcheck `depends_on`, no profiles or extends) |
| File names | `Dockerfile` → **`Containerfile`**, `docker-compose.yml` → **`compose.yaml`**. The Makefile always passes `-f Containerfile` |
| Images | Fully qualified (`docker.io/chromadb/chroma:1.5.9`, `docker.io/redis/redis-stack-server:7.4.0-v8`, `docker.io/library/postgres:17-alpine`, `docker.io/library/python:3.12-slim`) |
| Volumes | **Named volumes** (`chroma-data`, `redis-data`, `pg-data`) instead of bind mounts, so there are no rootless UID or SELinux issues |
| Migration | Fresh volumes. `make chroma-reset` becomes `volume rm`. A new `make bootstrap` runs up, `populate`, `assign-access-levels` and `db-migrate`. The Redis cache starts empty |
| Rootless-safe | Host ports above 1024 only; the API container runs as non-root; healthchecks use tools inside each image; the API reaches services by name (`chroma`, `redis`, `postgres`), never `host.docker.internal` |
| Updated | The Makefile (every docker call goes through `$(ENGINE)`/`$(COMPOSE)`), `.dockerignore` (works for both engines), `.gitignore` (bind-mount folders removed) |
| Docs | README "Docker or Podman" section (Windows/macOS `podman machine init/start`, Linux rootless); TROUBLESHOOTING entries: short-name prompt, `podman machine` not running, podman-compose version, ports, and the old `./chroma-data` folder; CHANGELOG |

## Verification
1. `make api-test`: all unit tests pass (no network/Docker).
2. `make db-up db-migrate`, then `make api-run`. Check `/docs`, `/health` and `/ready`, then a curl `ask` and `ask/stream` as bob (plan mode), and confirm the plan/steps/judge/result events arrive.
3. Verify a 401 problem+json for a bad key, a 422 for validation, 429 + `Retry-After: 30` after 101 requests (lowered limit via `.env` for the check), and a 504 with a tiny timeout.
4. Start a stream, kill curl mid-run, then run `GET /requests/{id}`, which shows `running` and later `completed`. `GET /events` with `Last-Event-ID` replays only the missed events. Another user gets 404. After the TTL, the result is served from Postgres.
5. `/metrics` shows the counters; an audit row exists in Postgres with redacted PII; the JSON log file is written.
6. `make api-up` (Docker): the image builds slim, the container is healthy and serves `/ready` 200. `make -n api-up ENGINE=podman` shows the podman/podman-compose commands. I can only run the Podman path for real if Podman is installed on this machine; otherwise I'll say so.
7. Re-run notebook §7 cell 24 to confirm the agent changes are backward compatible.
