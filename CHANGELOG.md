# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/).

## [0.10.0] - 2026-11-10

### Added
- **`make publish`** (`scripts/publish_images.py`): builds and pushes `iomega/netcore-rag-{api,mcp,web}` as `:0.10.0` and `:latest` to Docker Hub (token login via `--password-stdin`; `HUB_USER` overridable).
- **Terraform module `iac/`** (AWS provider 6.72, local state):
  - one t3.small Ubuntu 24.04 instance in the default VPC: 30 GiB encrypted gp3, IMDSv2 only, an Elastic IP and a new ED25519 key pair saved to `iac/.keys/`;
  - security group: SSH only from your current public IP (`ssh_cidr` overridable), HTTP 80 from anywhere;
  - cloud-init installs Docker CE + the compose plugin from Docker's apt repository, adds 2 GiB swap and log rotation;
  - deployment over SSH within `terraform apply`: `compose.prod.yaml` (Hub images, memory limits, api/mcp bound to loopback, DBs internal), a `.env` with `AWS_*` / `DOCKERHUB_*` removed, and a snapshot of the local Chroma volume restored on the first deploy. It re-deploys when the version, env or files change.
- Make targets `publish`, `iac-init`, `iac-prepare`, `iac-plan`, `iac-up`, `iac-output`, `iac-ssh` (`CMD=` runs a remote command, also from the TUI) and `iac-down`, all visible in `make help` and the TUI.
- `.gitattributes`: shell scripts and `iac/*.yaml` keep LF line endings.

### Changed
- Version 0.10.0 (API, MCP server, web UI, image tags); the Makefile has a single `VERSION`.
- `.env`: the AWS secret key is read as the standard `AWS_SECRET_ACCESS_KEY`; new `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`.

## [0.9.1] - 2026-11-10

### Added
- **Terminal UI for the make targets** (`uv run tui.py` or `make tui`, Textual 8; code in `scripts/make_tui/`):
  - grouped, searchable target list with badges for destructive (`!`), costly (`$`) and long-running (`~`) targets;
  - a form for each target's parameters (text, drop-downs, checkboxes) with a live command preview, and **Run** blocked until required values are filled;
  - live output with colours, exit code and duration; **Stop** ends the whole process tree; dry run (`make -n`);
  - a confirmation dialog before `[danger]` / `[cost]` targets;
  - run history (last 50, `.make_tui_history.json`, Enter re-runs), container health panel (docker or podman), and every target in the command palette (`Ctrl+P`).
- 17 parser tests (`scripts/make_tui/tests`), including a check that every Makefile target is documented.

### Changed
- Every Makefile target is annotated with `## description [tags] {params}` and `##@` groups. `make help` is now generated from these comments (`python -m make_tui.help`) instead of hand-written `echo` lines.
- `textual` added to the dev dependency group.

## [0.9.0] - 2026-11-10

### Added
- **IT support ticket MCP server** in `netcore_mcp/`: FastMCP 3.4 over streamable HTTP (stateless) on port 9090, hosted by uvicorn, with `/health`.
  - **Tools:** `register_ticket`, `list_my_tickets`, `get_ticket` (everyone, own tickets); `search_tickets` (keyword, product, region, severity, user, date range, status), `resolve_ticket` (remarks required) and `sync_pending_tickets` (admin only).
  - **Identity:** the caller comes from the `X-User-Id` header, mapped to the demo users (alice, bob, carol); RBAC is enforced on the server.
  - **Postgres:** table `itsm.tickets` in its own schema, with its own Alembic chain (`netcore_mcp/alembic.ini`). Ids look like `TKT-000123`, and the Jira id, key and URL are stored on the row.
  - **Jira Cloud mirror** (one-way, REST v3, project KAN, issue type Incident): priority from severity, labels, ADF description header, resolution comment and `Resolved` transition. Postgres is written first; a Jira failure leaves `jira_sync=pending`, retried by a background loop and the admin tool without duplicate issues or comments.
  - 29 tests (in-memory FastMCP client, fake repository, respx-mocked Jira).
- **Agent integration** (`scripts/agentic_rag/tickets.py`, `langchain-mcp-adapters` 0.3):
  - react mode gets the ticket tools; plan mode can plan ticket steps with typed `ticket_args`, run by the executor.
  - Ticket results are cited as `[TKT-000123]` / `[TICKETS]` and judged like KB sources. Ticket runs bypass and never write the semantic cache.
  - Safety: writes only when explicitly asked, never from a re-plan, never repeated within a request; admin steps are skipped for non-admins.
  - If the MCP server is down, KB questions still work and ticket requests report "ticket service unavailable".
  - 19 tests with a fake bridge (`api/tests/test_agent_tickets.py`).
- `compose.yaml` service `mcp` (`localhost/netcore-rag-mcp:0.9.0`, port `MCP_PORT`); `netcore_mcp/Containerfile`.
- Make targets: `mcp-run`, `mcp-test`, `mcp-migrate`, `mcp-build`, `mcp-up`, `mcp-down`, `mcp-logs`.
- `.env` settings: `MCP_HOST`, `MCP_PORT`, `MCP_SERVER_URL`, `MCP_RETRY_SECONDS`, `ATLASSIAN_SITE_URL`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, `JIRA_PROJECT_KEY`, `JIRA_ISSUE_TYPE`, `JIRA_RESOLVE_TRANSITION`, `JIRA_SYNC_INTERVAL_SECONDS`.

### Changed
- Version 0.9.0 (API `__version__`, `web/package.json`, image tags `netcore-rag-api`, `netcore-rag-web`, `netcore-rag-mcp`).
- `make up-all`, `stack-up` and `bootstrap` include the MCP server and the itsm migrations; the `api` container waits for a healthy `mcp`.
- The input guardrail's topic policy allows IT ticket requests; the citation format accepts `[TKT-000123]` and `[TICKETS]` (agent and web UI).
- API plan steps carry `ticket_args`, and step status can be `error`.
- Dependencies: `fastmcp==3.4.11` and `langchain-mcp-adapters` (fastmcp 4.x needs mcp 2.x, which `langchain-mcp-adapters` does not support yet); dev: `respx`.

## [0.8.0] - 2026-11-10

### Added
- **Web UI** in `web/` ("NetCore Assist"): React 18 + Vite, pure JavaScript, built from the approved prototype (`docs/ui-mockups/prototype/`).
  - **Screens:** sign in, new chat, live run (SSE), answer & insights (Plan, Sources, Judge, Tool calls, Trace, Timing), request history, request detail with replay/resume, and admin-only system status. The prototype's error-states screen became reusable components (RFC 9457 problem panel, 429 countdown, 504 / 503 cards, 401 → sign-in).
  - **Streaming:** `@microsoft/fetch-event-source` (POST + `X-API-Key`), a pure SSE reducer and a run store that keeps streams alive across navigation. "Stop watching" detaches; **Resume** sends `Last-Event-ID` and highlights the replayed events.
  - **Extras:** Ctrl/⌘+K new chat, light/dark theme (follows the OS, remembered), copy answer, and citation chips that jump to their source.
  - **Stack:** React Router 7, TanStack Query 5, Tailwind CSS 4 (prototype design tokens), react-markdown (raw HTML disabled), self-hosted fonts (`@fontsource`).
  - **Quality:** ESLint flat config, Prettier, 27 Vitest + Testing Library tests.
- **Nginx gateway** (`web/nginx/`, `web/Containerfile`): `nginxinc/nginx-unprivileged` (non-root) serves the build and proxies `/api/*`, `/health` and `/ready` to the API on the same origin. It is SSE-safe: no buffering and a 330 s read timeout. `/metrics` and `/docs` are not proxied.
- `compose.yaml` service `web` (`localhost/netcore-rag-web:0.8.0`, host port `WEB_PORT`, default 80) that waits for a healthy `api`.
- `GET /api/v1/me`: profile and RBAC levels of the calling API key (used at sign-in), with 5 new tests (53 in total).
- Make targets: `web-install`, `web-dev`, `web-lint`, `web-test`, `web-build`, `web-image`, `web-up`, `web-down`, `web-logs`.
- `make up-all`: the whole stack in dependency order (chroma, redis, postgres, populate, access levels, migrations, api, web). Populate runs only for empty domains; `REPOPULATE=1` forces it.
- `populate_vector_dbs.py --if-empty`: skip domains that already have chunks (no LLM or embedding calls).
- `.env` setting: `WEB_PORT`.

### Changed
- Version 0.8.0 (API `__version__`, image tags `netcore-rag-api:0.8.0` and `netcore-rag-web:0.8.0`).
- `make stack-up` / `stack-down` include the web container.
- The `api` container runs with `TRUST_PROXY_HEADERS=true` (set in `compose.yaml`), so the rate limit sees the real client IP forwarded by Nginx.
- `.dockerignore` excludes `web/` from the API build context.

### Security
- Strict Content-Security-Policy (`default-src 'self'`, no inline scripts, no third-party origins), `nosniff`, `no-referrer`, `frame-ancestors 'none'`, Permissions-Policy.
- The API key is kept in `sessionStorage` (per tab, cleared on close) and is never bundled; every 401 signs the user out.
- Nginx overwrites `X-Forwarded-For` with the connecting address, so clients cannot spoof their IP through the gateway.

## [0.7.0] - 2026-11-09

### Added
- REST API in `api/` (FastAPI + Uvicorn), organised as controllers, services, repositories, schemas, core and middleware:
  - **Endpoints:** `POST /api/v1/agent/ask` and `/ask/stream` (SSE), `GET /health`, `/ready`, `/metrics`.
  - **Docs:** OpenAPI with Swagger UI and ReDoc.
  - **Response:** plan, executed plan, sources, judge details and attempts, unified tool calls, trace, cache info and timings.
  - **Reconnect:** `GET /api/v1/agent/requests` (list), `/{request_id}` (status + result) and `/{request_id}/events` (resume with `Last-Event-ID`). Runs are decoupled from the HTTP connection; events are buffered in Redis Streams for 1 h.
  - **Auth:** `X-API-Key` → demo user (RBAC). Owners see their own requests, the admin sees all, and anyone else gets 404.
  - **Rate limit:** 100 requests/minute per IP; exceeding it blocks the IP for 30 s (429 + `Retry-After`). Redis-backed and fail-open.
  - **Timeouts and retries:** per-request timeout with a hard cap (504); Postgres audit writes retried with backoff.
  - **Errors:** RFC 9457 problem details everywhere.
  - **Logging:** structlog JSON to the console and a rotating file.
  - **Metrics:** Prometheus.
  - **Audit:** Postgres audit of every request plus agent runs (PII-redacted), with Alembic migrations.
  - **Tests:** 48 unit tests (fake agent, fake repositories, fakeredis).
- `scripts/test_agent_api.py` + `make agent-api-test`:
  - Planning smoke test of the running API (blocking `/ask`, URL and key from `.env`), based on `notebooks/agentic-rag-plan.ipynb`.
  - Scenarios: a 1-step plan, a cross-domain multi-step plan (both domains, judge passed, result stored), and a cache repeat.
  - Exit code 1 on failure.
- `Containerfile` (multi-stage uv build, `python:3.12-slim`, non-root, healthcheck; migrations run at start).
- `compose.yaml` with `postgres` and `api` services.
- Docker **or Podman** support: the Makefile auto-detects the engine (`ENGINE=podman` to force) and uses podman-compose.
- Make targets: `db-up`, `db-down`, `db-migrate`, `api-run`, `api-test`, `api-build`, `api-up`, `api-down`, `api-logs`, `stack-up`, `stack-down`, `bootstrap`, `engine`.
- `.env` settings: `API_KEYS`, `API_PORT`, `POSTGRES_*`, `DATABASE_URL`, `RATE_LIMIT_*`, `API_TIMEOUT_*`, `AGENT_MAX_CONCURRENCY`, `EVENT_BUFFER_TTL_SECONDS`, `LOG_LEVEL`, `LOG_FILE`.
- Agent (additive, backward compatible):
  - `ask(..., timeout_seconds=, bypass_cache=, on_event=)`.
  - `AgentResult` gains `tool_calls`, `judge` (attempts with actions), `plan_rationales` and `cache_similarity`.
  - Live `plan`, `step`, `tool_call`, `judge` and `trace` events.

### Changed
- `docker-compose.yml` → `compose.yaml`:
  - Fully-qualified images and named volumes instead of bind mounts.
  - The old file is in `archives/`.
  - `make chroma-reset` now removes the volume.
- **Judge:** RAGAS is replaced by a built-in LLM-as-a-judge in `judge.py`:
  - Same metrics (faithfulness, groundedness, context precision), 0–1 scale, thresholds and `evaluate()` API.
  - Three parallel structured-output calls on `JUDGE_OPENAI_MODEL`.
  - Citation markers are ignored.
  - New setting: `JUDGE_REASONING_EFFORT` (default `low`).
  - `ragas` was removed.
- **Chroma:** the thin HTTP client `chromadb-client` replaces the full `chromadb` package project-wide (uv override). Everything talks to the Chroma server anyway.
- **KB-only packages:** `unstructured` and `reportlab` moved to a `kb` dependency group, and `ipykernel` is dev-only. `uv sync` still installs everything.
- **API image:** the builder strips bundled test suites, type stubs and native debug symbols. Size went from 2.5 GB to **~650 MB** (about **140 MB** compressed).
- `.dockerignore` updated for both engines.

### Fixed
- `langchain-classic` (needed by `rag_search`) is now a declared dependency; it was previously only installed by hand.

## [0.6.0] - 2026-11-07

### Added
- Planning mode (Plan-and-Execute), now the default:
  - `planner.py`: structured plans with up to `MAX_PLAN_STEPS` steps, and re-planning.
  - `executor.py`: deterministic step execution.
  - `PlanExecuteMiddleware`: plan, show, execute, re-plan on failure (each re-plan counts as a rewrite), web fallback, no-info; the model only writes the final answer.
  - A 2nd judge failure triggers a re-plan with the judge's feedback.
- `ask(..., mode="plan"|"react", show_plan=True)`; CLI `--mode`; `make agent-ask M=...`.
- `show_plan` (printed before execution), `show_plan_report` (executed plan in `show_result`), live step status in the trace.
- `notebooks/agentic-rag.ipynb` §7 planning scenarios (sections 1–6 pinned to `mode="react"`).
- `.env`: `MAX_PLAN_STEPS=4`.

### Changed
- `retrieval.py`: `retrieve_relevant()` is the shared retrieve → merge → rerank → threshold pipeline for the tools and the plan executor.

### Fixed
- `judge.py`: the async OpenAI client is closed inside its event loop (no more "Event loop is closed" noise); `.env` is loaded before the judge runs.

## [0.5.0] - 2026-11-07

### Added
- `scripts/agentic_rag/`: an Enterprise Agentic RAG agent on LangChain `create_agent`, covering:
  - input/output guardrails
  - a Redis semantic cache with RBAC hit checks
  - LLM routing between vector, web (Serper) and federated search
  - an LLM reranker
  - a corrective rewrite loop
  - a context optimizer
  - a RAGAS judge with escalation
  - retry, call limits and a timeout budget

  Includes a CLI and rich display helpers.
- `scripts/assign_access_levels.py`: RBAC `access_level` metadata patched in place. `populate_vector_dbs.py` now sets it too.
- `notebooks/agentic-rag.ipynb`: test scenarios only.
- Redis Stack (`redis/redis-stack-server:7.4.0-v8`) service in `docker-compose.yml`.
- Make targets: `redis-up`, `redis-down`, `assign-access-levels`, `agent-ask`.
- `.env` settings: Redis, cache, thresholds, limits, context budget (plus your `SERPER_API_KEY`, `RERANKER_OPENAI_MODEL`, `JUDGE_OPENAI_MODEL`).

### Changed
- `chroma-up` / `chroma-down` / `chroma-reset` now act on the Chroma service only.
- Dependencies: added `langchain` 1.4, `ragas` 0.4.3, `redisvl`, `tiktoken`. Pinned `langchain-community==0.3.31` (RAGAS compatibility) and relaxed `rich` to `>=13.7,<15`.

## [0.4.0] - 2026-11-06

### Added
- `scripts/rag_search.py`: reusable `similarity_search`, `keyword_search` (BM25), `hybrid_search` (EnsembleRetriever / RRF), `search`, `KBRetriever` / `get_retriever`, `format_docs` and `show_results` (defaults: k=4, weights 0.5/0.5).
- `notebooks/naive-rag.ipynb`: Naive (2-step) RAG walkthrough covering retrieval modes, context building, system instructions with citations and superseded-source handling, a step-by-step flow, a streaming LCEL chain with sources, and four demos.
- Dev dependency: `ipykernel`.

## [0.3.0] - 2026-11-06

### Added
- `scripts/test_query_vector_dbs.py`: Chroma connection/database info plus demos of similarity search (distance and relevance), keyword search (`$contains` vs BM25), metadata filtering, hybrid search (EnsembleRetriever, RRF) and a cross-domain query. Output uses rich tables, and `--query` / `--domain` run ad-hoc queries.
- Make targets: `test-query`, `query Q="..." D=...`.
- Dependencies: `rich`, `rank-bm25`.

## [0.2.0] - 2026-11-06

### Added
- `scripts/populate_vector_dbs.py`: the Pre-RAG pipeline. It reads PDF, HTML and MD with LangChain community loaders, merges file and manifest metadata, chunks size-based text (3000/200), writes LLM descriptions of tables and code as separate chunks, embeds with OpenAI, and upserts into one Chroma database per domain.
- `docker-compose.yml` (Chroma 1.5.9 server, `./chroma-data` bind mount, healthcheck) and `.dockerignore`.
- Make targets: `chroma-up`, `chroma-down`, `chroma-logs`, `chroma-reset`, `populate`, `populate-networking`, `populate-meetings`, `db-stats`.
- `.env` / `.env.example` settings: `OPENAI_EMBEDDING_MODEL`, `KB_DATA_DIR`, `CHROMA_*`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `DESCRIBE_CONCURRENCY`.

### Changed
- `make verify` uses project dependencies (no `uv run --with`).
- `.gitignore` now excludes `chroma-data/`.

## [0.1.0] - 2026-11-06

### Added
- `scripts/generate_kb.py`: hybrid (seed catalog + LLM) generator for 20 synthetic NetCore Systems KB articles in two domains (networking, meetings), rendered as PDF, HTML and Markdown, with embedded metadata and a `manifest.json` per domain.
- `scripts/verify_kb.py`: smoke test that uses LangChain document loaders.
- `Makefile` targets: `help`, `install`, `generate*`, `regenerate`, `verify`, `clean`, `clean-data`.
- `.env.example`, README, TROUBLESHOOTING, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, MIT LICENSE.

### Security
- `.env` added to `.gitignore`.
