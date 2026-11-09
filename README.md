# NetCore KB Generator

Generates a realistic, **synthetic** knowledge base for an Enterprise RAG / Agentic AI course. It covers two domains, and each domain feeds its own vector database:

| Domain | Product (fictional) | Topics |
|---|---|---|
| `networking` | NetCore SD-WAN | SLA classes, SLA breach policies, BFD, ZTP, QoS, alarm codes |
| `meetings` | NetCore Meet / NetCore Calling | SSO, dial plans, calling features, recording policy, help articles, error codes |

The generator writes 10 articles per domain, spread evenly across **PDF, HTML and Markdown**, and adds a `manifest.json` per domain.

> "NetCore Systems" and all of its products, codes and values are fictional.

## Quick Start

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), GNU make, Docker **or** Podman ([details](#docker-or-podman)), an OpenAI API key. Node.js 22 LTS only for web UI development ([details](#web-ui-web)).

```bash
cp .env.example .env      # then set OPENAI_API_KEY (and review the other settings)
make install              # uv sync
make generate             # 1. write missing KB articles to data/raw/
make verify               #    load every article with LangChain loaders
make chroma-up            # 2. start the Chroma server (docker compose / podman-compose)
make populate             #    Pre-RAG pipeline -> one Chroma database per domain
make db-stats             #    check what was stored
```

Can't remember a target? `make help` lists them all, and `uv run tui.py` opens the [terminal UI](#terminal-ui-tuipy).

## Make Targets

| Target | What it does |
|---|---|
| `make help` | List targets (default), generated from the `##` comments in the Makefile |
| `make tui` | Terminal UI for all targets (same as `uv run tui.py`) |
| `make install` | Sync dependencies |
| `make generate` | Generate missing articles for both domains (skips existing files) |
| `make generate-networking` / `make generate-meetings` | Generate one domain only |
| `make regenerate` | Overwrite all 20 articles (20 LLM calls) |
| `make verify` | Smoke-test loading, KB IDs and vendor-name leaks |
| `make clean` / `make clean-data` | Remove caches / delete `data/raw` |
| `make chroma-up` / `chroma-down` / `chroma-logs` | Start / stop / follow the Chroma server |
| `make chroma-reset` | Stop the server and delete its `chroma-data` volume |
| `make populate` | Run the Pre-RAG pipeline for both domains (upserts, safe to re-run) |
| `make populate-networking` / `populate-meetings` | Populate one database |
| `make db-stats` | Chunk counts by type/format/status, plus sample metadata |
| `make test-query` | DB info, then similarity, keyword, metadata-filter, hybrid and cross-domain demos |
| `make query Q="..." [D=meetings]` | Ad-hoc query: similarity, BM25 and hybrid results |
| `make redis-up` / `redis-down` | Start / stop the Redis Stack semantic cache |
| `make assign-access-levels` | Patch RBAC `access_level` into the Chroma metadata (no re-embedding) |
| `make agent-ask Q="..." U=bob [M=react]` | Ask the agentic RAG agent as a demo user, with a live trace (default `M=plan`) |
| `make db-up` / `db-down` / `db-migrate` | Start / stop Postgres; apply Alembic migrations |
| `make api-run` | Run the REST API locally with auto-reload (`/docs`) |
| `make api-test` | API unit tests (no network or containers) |
| `make agent-api-test [U=bob] [TRACE=1]` | Planning smoke test against the running API: 1-step plan, cross-domain multi-step plan, cache repeat; PASS/FAIL table, exit 1 on failure |
| `make api-build` / `api-up` / `api-down` / `api-logs` | Build the image / run the API container |
| `make stack-up` / `stack-down` | Start / stop chroma, redis, postgres, mcp, api and web together |
| `make web-install` / `web-dev` | Install the web UI (Node 22, `npm ci`) / Vite dev server on :5173 (proxies `/api` to :8080) |
| `make web-lint` / `web-test` / `web-build` | ESLint + Prettier check / Vitest / production build into `web/dist` |
| `make web-image` / `web-up` / `web-down` / `web-logs` | Build the web image / run the Nginx gateway container on http://localhost/ |
| `make mcp-run` / `mcp-test` / `mcp-migrate` | IT ticket MCP server: run locally on :9090 / tests (no network) / itsm schema migrations |
| `make mcp-build` / `mcp-up` / `mcp-down` / `mcp-logs` | Build the image / run the MCP server container |
| `make bootstrap` | First run: infrastructure + populate + access levels + both migration chains |
| `make up-all [REPOPULATE=1]` | Whole stack in dependency order: chroma, redis, postgres → populate (only empty domains, unless `REPOPULATE=1`) → access levels → api + itsm migrations → mcp → api → web (http://localhost/) |
| `make engine` | Show the detected container engine (`ENGINE=podman` to force) |
| `make publish` | Build and push the api, mcp and web images to Docker Hub (`iomega/netcore-rag-*:<VERSION>` + `:latest`) |
| `make iac-init` / `iac-plan` / `iac-up` / `iac-output` / `iac-ssh` / `iac-down` | Terraform on AWS: init / plan / create the EC2 instance and deploy / outputs / SSH (`CMD=...`) / destroy |

## Terminal UI ([tui.py](tui.py))

Don't want to remember the targets? `uv run tui.py` (or `make tui`) opens a [Textual](https://textual.textualize.io/) console UI that lists every make target. It is grouped and searchable, has a form for each target's parameters, and runs the target with live output.

```
┌ NetCore make ─────────────────────────────────────────────────────────────────────┐
│ / search…        │ agent-ask   Agentic RAG   costs API calls  │ Containers         │
│ ▾ Agentic RAG    │ Ask the agent as a demo user               │ api      ● healthy │
│   redis-up       │ Q *  [How do I fix BFD flaps?_________]    │ mcp      ● healthy │
│   agent-ask $    │ U    [bob ▾]      M  [plan ▾]              │ …                  │
│ ▾ REST API       │ $ make agent-ask Q="How do I…" U=bob …     │ History            │
│   api-run ~      │ [Run F5] [Dry run d] [Stop s] [engine ▾]   │ ✓ up-all    0  62s │
│                  │ live output (colours kept) … exit 0 · 14 s │ ■ mcp-logs stop 4s │
└───────────────────────────────────────────────────────────────────────────────────┘
```

| Key | Action |
|---|---|
| `/` | Search targets (name, group, description, tags) |
| `↑` `↓`, `Enter` | Pick a target; `Enter` jumps to its first parameter (or to **Run**) |
| `F5` (or `Enter` in a parameter field) | Run. `[danger]` and `[cost]` targets ask for confirmation first |
| `d` | Dry run (`make -n`): show the commands without running them |
| `s` | Stop: ends make and everything it started (servers, `logs -f`) |
| `r` / `h` | Re-run the last command / focus the history (`Enter` re-runs a past run) |
| `c`, `q`, `Ctrl+P` | Clear the log, quit, command palette (every target as `make <name>`) |

Badges in the list: `!` destructive, `$` costs API calls (OpenAI or Jira), `~` runs until stopped. The container panel (docker or podman, refreshed every 10 s) shows the health of the `netcore-*` containers. The last 50 runs are kept in `.make_tui_history.json` (git-ignored).

**One source of truth.** The TUI and `make help` both read the `##` comments in the [Makefile](Makefile):

```make
##@ Agentic RAG                                                     <- group
agent-ask:  ## Ask the agent as a demo user [cost] {Q! U=bob:alice|bob|carol M=plan:plan|react}
```

| Syntax | Meaning |
|---|---|
| `[danger]` / `[cost]` / `[long]` | Deletes or overwrites data / calls OpenAI or creates Jira issues / runs until stopped |
| `NAME!` | Required text (the form blocks **Run** until it is filled) |
| `NAME=default` | Optional text with a default |
| `NAME=default:a\|b\|c` | Choice (drop-down) |
| `NAME?` | Flag (checkbox), passed as `NAME=1` |

The implementation lives in [scripts/make_tui/](scripts/make_tui/): `parser.py` (pure Python, also used by `make help`), `app.py`, `widgets.py`, `screens.py`, `runner.py`, `history.py`, `status.py` and `app.tcss`. Textual is a dev dependency, so it is not in any image.

## Query Demos ([scripts/test_query_vector_dbs.py](scripts/test_query_vector_dbs.py))

| Section | Shows |
|---|---|
| 1. Connection & DB info | Heartbeat, versions, tenant, databases, collections, counts, metadata keys |
| 2. Similarity | Rank, L2 distance (lower = closer), relevance score (0-1) |
| 3. Keyword | Chroma `$contains` (exact, case-sensitive, unranked) vs `BM25Retriever` (ranked) |
| 4. Metadata filters | `status=current` (removes superseded 4.2), `content_type in [table, code]`, `version`, `kb_id` |
| 5. Hybrid | `EnsembleRetriever` (BM25 + vector, RRF), with each source's rank and the fused score |
| 6. Cross-domain | The same question against both databases |

## Naive RAG Notebook ([notebooks/naive-rag.ipynb](notebooks/naive-rag.ipynb))

Prerequisites: `make chroma-up` (and `make populate` once). Open the notebook in VS Code and select the `.venv` kernel.

| Section | Shows |
|---|---|
| 1–2 | Similarity, keyword (BM25) and hybrid retrieval, then building the citable context |
| 3 | System instructions: answer only from context, cite `[KB-ID, location]`, flag superseded sources |
| 4–5 | Naive (2-step) RAG step by step, then as a streaming LCEL chain that returns its sources |
| 6 | Demos: LLM alone vs RAG, retrieval-mode comparison, `status=current` filter, out-of-scope question |
| 7 | Limitations of Naive RAG, as a lead-in to Advanced RAG |

## Enterprise Agentic RAG Agent ([scripts/agentic_rag/](scripts/agentic_rag/))

Built on LangChain `create_agent`. **Tools** do the routing and retrieval; **middleware** enforces the workflow rules deterministically.

```bash
make chroma-up redis-up assign-access-levels      # once
make agent-ask Q="How do I troubleshoot BFD tunnel flaps?" U=bob    # alice=guest, bob=employee, carol=admin
```

| Flowchart step | Implementation |
|---|---|
| Input guardrails | LangChain PII detectors and an LLM classifier (injection, toxicity, topic), with a safe refusal |
| Semantic cache | Redis Stack + RedisVL. Hits are checked against RBAC (`max_access_level`) and the output guardrails; only judge-passed answers are written |
| Router (Adaptive RAG) | The agent's tool choice: `search_knowledge_base` (RBAC filter), `search_web` (Serper), `federated_search` |
| Rerank and relevance check | LLM reranker (`RERANKER_OPENAI_MODEL`), `RELEVANCE_THRESHOLD` |
| Corrective RAG | `rewrite_query` tool. Middleware forces up to `MAX_REWRITES` rewrites, then one web fallback, then "no reliable information" |
| Context optimizer and prompt builder | tiktoken budget, LLM summary of the overflow, lost-in-the-middle reordering; citations and superseded-source rules |
| Judge | LLM-as-a-judge (`JUDGE_OPENAI_MODEL`): faithfulness (supported claims / claims), groundedness (0/1/2 rating) and context precision (average precision of useful chunks), each 0–1. Failures escalate: regenerate, then re-retrieve, then a disclaimer |
| Output guardrails | PII, citations, LLM toxicity/policy check, plus built-in `PIIMiddleware` redaction. A failing answer is regenerated once, then refused |
| Cross-cutting | `ModelRetryMiddleware` / `ToolRetryMiddleware` (exponential backoff), `ModelCallLimitMiddleware`, `TimeoutMiddleware` (`AGENT_TIMEOUT_SECONDS`) |

**Two modes** (`ask(..., mode=...)`, `make agent-ask M=...`):

| Mode | How it retrieves |
|---|---|
| `plan` (default) | **Plan-and-Execute**: the planner (`OPENAI_MODEL`) writes up to `MAX_PLAN_STEPS` retrieval steps, and the plan is **shown** before it runs. A deterministic executor then runs each step (KB / web / federated → rerank). A step that finds nothing triggers a **re-plan** (counts as a rewrite, max 3), then a web fallback, then "no info". The model only writes the final answer. A 2nd judge failure triggers a re-plan with the judge's feedback |
| `react` | The agent routes with tools (`search_*`, `rewrite_query`, IT ticket tools) under `CorrectiveRAGMiddleware` |

Both modes can also work with **IT support tickets** through the MCP server ([below](#it-support-tickets-mcp-server-netcore_mcp)).

RBAC: `access_level` is derived from `article_type` (faq/help = public; config/runbook/reference = internal; policy = restricted). guest sees public; employee sees public + internal; admin sees everything.

Test scenarios: [notebooks/agentic-rag.ipynb](notebooks/agentic-rag.ipynb) (scenarios only; all code lives in the package).

The reusable retrieval functions live in [scripts/rag_search.py](scripts/rag_search.py): `similarity_search`, `keyword_search`, `hybrid_search`, `search`, `get_retriever` (a LangChain `BaseRetriever`), `format_docs` and `show_results`. Smoke test: `uv run scripts/rag_search.py`.

## REST API ([api/](api/))

FastAPI service that exposes the agent with all of its details: plan, executed plan, sources, judge result and attempts, tool calls, trace, cache info, the answer and timings.

```bash
make bootstrap        # first run: chroma, redis, postgres + populate + access levels + DB migrations
make api-run          # local, auto-reload -> http://localhost:8080/docs
# or, fully containerised:
make api-up           # build the image (Containerfile) and start it with its dependencies
```

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness: Chroma, Redis, Postgres (503 problem when one is down) |
| GET | `/metrics` | Prometheus metrics (HTTP + agent: runs, re-plans, judge, cache hits, tool calls, rate-limit blocks) |
| GET | `/api/v1/me` | Profile behind the `X-API-Key`: `id`, `name`, `role`, `allowed_levels` (used by the web UI at sign-in) |
| POST | `/api/v1/agent/ask` | Ask, blocking: the full `AskResponse` |
| POST | `/api/v1/agent/ask/stream` | Ask, Server-Sent Events: `accepted`, `plan`, `step`, `tool_call`, `trace`, `judge`, `result` / `error`, `done` |
| GET | `/api/v1/agent/requests` | My earlier requests (admin: everyone's), cursor pagination |
| GET | `/api/v1/agent/requests/{request_id}` | Status + the stored result |
| GET | `/api/v1/agent/requests/{request_id}/events` | Resume a stream after `Last-Event-ID` (replay, then live) |

Swagger UI: `/docs` · ReDoc: `/redoc` · OpenAPI: `/openapi.json`

```bash
curl -s localhost:8080/api/v1/agent/ask -H "X-API-Key: <bob's key from API_KEYS>" \
     -H "Content-Type: application/json" \
     -d '{"question": "What does alarm NCS-BFD-3004 mean?", "mode": "plan"}'
curl -N localhost:8080/api/v1/agent/ask/stream -H "X-API-Key: ..." -H "Content-Type: application/json" \
     -d '{"question": "...", "include_trace": false}'
```

| Concern | Implementation |
|---|---|
| Layout | `controllers/` (routes) → `services/` (agent, audit, health) → `repositories/` (Postgres, Redis Streams); `schemas/` DTOs; `core/` config, logging, security, problems, metrics; `middleware/` |
| Auth / RBAC | `X-API-Key` → demo user (`API_KEYS` in `.env`); the agent applies the user's access levels |
| Request options | `question`, `mode` (`plan` \| `react`), `timeout_seconds`, `include_trace`, `bypass_cache` |
| Errors | RFC 9457 `application/problem+json` (`type`, `title`, `status`, `detail`, `instance`, `request_id`, `errors[]`) |
| Rate limit | Per client IP, `RATE_LIMIT_PER_MINUTE=100`; the request that exceeds it blocks the IP for `RATE_LIMIT_BLOCK_SECONDS=30` (429 + `Retry-After`). Redis-backed, fail-open; probes exempt |
| Timeout | Agent budget `timeout_seconds` (bounded by `API_TIMEOUT_MIN/MAX`), hard cap = budget + `API_TIMEOUT_GRACE` → 504 |
| Retry | Postgres audit writes (tenacity, exponential backoff). An audit failure never fails a response. The agent keeps its own LLM/tool retries |
| Reconnect | Runs are decoupled from the HTTP connection. Events go to a Redis Stream (`EVENT_BUFFER_TTL_SECONDS=3600`); after expiry the stored result is replayed from Postgres. Others' requests return 404 |
| Audit | Postgres `api_requests` (every request: metadata + PII-redacted bodies; API keys masked) and `agent_runs` (status + result). Alembic migrations |
| Logging | structlog JSON to the console and `LOG_FILE` (rotating), with `request_id`, user, IP |
| CORS | Not enabled (same-origin only): the web UI reaches the API through its Nginx gateway |
| Tests | `make api-test`: pytest + httpx with a fake agent, fake repositories and fakeredis (no network, no containers) |

## Web UI ([web/](web/))

**NetCore Assist**: a React 18 + Vite single-page app (pure JavaScript), built from the approved prototype in [docs/ui-mockups/prototype/](docs/ui-mockups/prototype/). The browser never calls the API directly: one Nginx container serves the build **and** reverse-proxies the API on the same origin.

```
browser ──► http://localhost/  (netcore-web: nginx-unprivileged, :8080 in the container)
              ├─ /              React build (SPA fallback to index.html)
              ├─ /api/*         ──► api:8080   (SSE: proxy_buffering off, 330 s read timeout)
              └─ /health /ready ──► api:8080   (/metrics, /docs are NOT proxied)
```

```bash
make up-all               # everything, incl. populate (if empty), access levels, migrations -> http://localhost/
make stack-up             # containers only (data already in place); WEB_PORT in .env
# or, for UI development with hot reload against a running API (make api-run / api-up):
make web-install
make web-dev              # http://localhost:5173 - Vite proxies /api, /health, /ready to :8080
```

Sign in with a key from `API_KEYS` (alice = guest, bob = employee, carol = admin).

| Screen | Route | API |
|---|---|---|
| Sign in | `/sign-in` | `GET /api/v1/me` validates the key; the key is kept in `sessionStorage` |
| New chat | `/` | `POST /ask/stream`: mode (Plan / ReAct) and options (time budget, trace, bypass cache) |
| Live run | `/runs/:id/live` | SSE: plan steps, live trace, judge, raw event log; **Stop watching** detaches |
| Answer & insights | `/runs/:id` | Markdown answer with citation chips → Plan, Sources, Judge, Tool calls, Trace, Timing tabs |
| Requests | `/requests` | `GET /requests`: status (server) / mode / text filters, cursor "Load more" |
| Request detail | `/requests/:id` | Event timeline replayed from `/events`; **Resume** sends `Last-Event-ID` and marks missed events |
| System status (admin) | `/status` | `/health` + `/ready`, refreshed every 15 s |
| Error states | (everywhere) | RFC 9457 problem panel, 429 `Retry-After` countdown, 504 / 503 cards, 401 → sign-in |

Extras: <kbd>Ctrl</kbd>/<kbd>⌘</kbd>+<kbd>K</kbd> new chat, light/dark theme (follows the OS, toggle remembered), copy answer, citation jump to its source.

| Concern | Implementation |
|---|---|
| Stack | React 18.3, Vite 8, React Router 7, TanStack Query 5, `@microsoft/fetch-event-source` (POST + header SSE), Tailwind CSS 4 (prototype tokens in `@theme`), react-markdown (no raw HTML) |
| Layout | Feature folders: `src/features/{auth,chat,run,requests,status}`, shared `src/api` (fetch client, `ApiError`, SSE), `src/components`, `src/hooks`, `src/lib` |
| Live runs | `features/run/runStore.js` keeps each stream outside React (survives navigation); a pure reducer folds the SSE events |
| Security | Strict CSP (`default-src 'self'`, self-hosted fonts via `@fontsource`), `nosniff`, `no-referrer`, `frame-ancestors 'none'`; non-root Nginx; no secrets in the bundle |
| Caching | `index.html` no-cache; hashed `/assets/*` cached 1 year (`immutable`); gzip |
| Tests | `make web-test`: Vitest + Testing Library (API client, SSE reducer and store, sign-in, guards, 429 countdown) |
| Image | `web/Containerfile`: `node:22.22-alpine` build → `nginxinc/nginx-unprivileged:1.30.6-alpine`, HEALTHCHECK `/healthz` |

## IT Support Tickets: MCP Server ([netcore_mcp/](netcore_mcp/))

Users can register IT support tickets and list their own through the agent. The admin (carol) can also search all tickets and resolve them. The ticket logic is a separate **MCP server** (FastMCP 3, streamable HTTP, port 9090). Postgres is the source of truth, and every ticket is mirrored one-way to **Jira Cloud** (project **KAN**, "My IT Team", issue type Incident).

```
agent (react / plan) ──langchain-mcp-adapters──► netcore-mcp :9090/mcp   (header X-User-Id = calling user)
                                                    ├─ Postgres  netcore_api, schema itsm (tickets)   ← source of truth
                                                    └─ Jira Cloud REST v3 (KAN)                        ← one-way mirror
```

```bash
make mcp-migrate          # itsm schema (own Alembic chain); up-all / bootstrap run it too
make mcp-run              # local server -> http://localhost:9090/mcp  (or: make mcp-up for the container)
make agent-ask M=react U=bob Q="Open a ticket: title 'Meet calls drop', description '...', meetings, EMEA, high"
make agent-ask U=carol Q="Search open meetings tickets in EMEA, then resolve TKT-000002 with remarks '...'"
```

| Tool | Who | What it does |
|---|---|---|
| `register_ticket(title, description, product_family, region, severity)` | everyone | Insert in Postgres, then create the Jira issue (stores `jira_key`, `jira_url`) |
| `list_my_tickets(status=open\|resolved\|all)` | everyone | The caller's own tickets, newest first |
| `get_ticket(ticket_id)` | owner or admin | One ticket (someone else's ticket reads as "not found") |
| `search_tickets(keyword, product_family, region, severity, registered_by, date_from, date_to, status)` | admin | All users' tickets (default: open) |
| `resolve_ticket(ticket_id, remarks)` | admin | Remarks required. The Jira issue gets a comment, then the `Resolved` transition |
| `sync_pending_tickets()` | admin | Retry Jira now (a background loop also retries every `JIRA_SYNC_INTERVAL_SECONDS`) |

| Concern | Implementation |
|---|---|
| Ticket record | `itsm.tickets`: `TKT-000123` (generated from an identity column), registered at/by, title, description, product family (`networking` / `meetings`), region (`AMER` / `EMEA` / `APAC`), severity (`critical` / `high` / `medium` / `low` → Jira Highest/High/Medium/Low), status (`open` / `resolved`), resolved by/at, remarks, plus `jira_id`, `jira_key`, `jira_url`, `jira_sync` (`pending` / `synced`), `jira_error` |
| Consistency | Postgres first, then Jira. If Jira fails the ticket is kept with `jira_sync=pending`; each finished Jira step is saved at once, so a retry never creates a second issue or comment |
| Jira issue | Summary `[TKT-…] title`, priority from severity, labels `netcore-assist`, product, region, `user-<id>`, and a description header with the ticket id and requester (issues are created by the token owner) |
| Identity / RBAC | The agent sends the caller as `X-User-Id`; the server maps it to the demo users and enforces the rules above. **No authentication yet** (see [SECURITY](SECURITY.md)) |
| Agent: react | The MCP tools (schemas loaded with `langchain-mcp-adapters`) become sync LangChain tools; the prompt allows writes only when the user explicitly asks |
| Agent: plan | The planner can add ticket steps with typed `ticket_args`. The executor calls them directly: they end `done` / `error` (never re-planned), writes run only from the first plan, and admin steps are skipped for non-admins |
| Answers | Ticket results become CONTEXT sources cited as `[TKT-000123]` or `[TICKETS]`, so the judge checks them like KB chunks. Ticket runs are never cached (live, per-user data) |
| Degradation | MCP down → KB questions still work; ticket steps answer "ticket service unavailable" |
| Tests | `make mcp-test`: in-memory FastMCP client, fake repository, respx-mocked Jira. Agent side: `api/tests/test_agent_tickets.py` (fake bridge) |
| Image | `netcore_mcp/Containerfile` (python:3.12-slim + uv, non-root); runs `alembic upgrade head` (itsm), then `python -m netcore_mcp` |

## Deploy to AWS ([iac/](iac/))

`make publish` pushes the three project images to Docker Hub. `make iac-up` then uses Terraform to create one EC2 instance and runs the whole stack there from those images.

```
you ──ssh :22 (your IP only)──►┐
browser ──http :80 (public)──► EC2 t3.small · Ubuntu 24.04 · Docker CE · 2 GiB swap · EIP
                                 └ compose: web (Nginx :80) → api → mcp / chroma / redis / postgres
                                   api :8080 and mcp :9090 bound to 127.0.0.1 (SSH tunnel), DBs internal
```

```bash
# .env: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, DOCKERHUB_USERNAME, DOCKERHUB_TOKEN
make publish              # build + push iomega/netcore-rag-{api,mcp,web}:0.10.0 and :latest
make iac-init             # once: terraform providers
make iac-plan             # optional: what will be created (7 resources)
make iac-up               # create the instance + deploy (~3 min) -> prints web_url, ssh_command, tunnel_command
make iac-ssh              # shell on the instance (or CMD="docker ps")
make iac-down             # destroy everything
```

| Concern | Implementation |
|---|---|
| Images | `scripts/publish_images.py`: `docker login --password-stdin` with `DOCKERHUB_TOKEN`, tags `localhost/netcore-rag-*:<VERSION>` as `<HUB_USER>/…:<VERSION>` and `:latest`, pushes (public repos, `linux/amd64`) |
| Infra | Default VPC, security group (22 from your current public IP, 80 from anywhere), new ED25519 key pair (`tls_private_key` → `aws_key_pair`, private key in `iac/.keys/`), t3.small, 30 GiB encrypted gp3, IMDSv2, Elastic IP |
| Bootstrap | `iac/cloud-init.yaml`: Docker CE + compose plugin from download.docker.com, 2 GiB swap, log rotation |
| Deploy | `terraform_data` SSH provisioner uploads `iac/compose.prod.yaml`, `deploy.sh`, a **filtered** `.env` (no `AWS_*` / `DOCKERHUB_*`) and a snapshot of the local Chroma volume; `deploy.sh` restores Chroma on the first deploy, pulls and starts with `--wait`. It re-runs when the version, the env or these files change |
| Data | The knowledge base comes from your local `chroma-data` volume (no OpenAI cost; `CHROMA_REFRESH=1` re-exports it). Postgres (audit, runs, tickets) and Redis start empty on the server |
| Access | `/docs` and the MCP server: `terraform -chdir=iac output -raw tunnel_command`, then http://localhost:8080/docs |
| State | Local (`iac/terraform.tfstate`, git-ignored; it contains the private key). Run `make iac-*` from this machine |
| Cost | About US$0.03/h in ap-south-1 (t3.small, public IPv4, 30 GiB gp3), roughly US$22 a month. `make iac-down` stops all charges |

## Docker or Podman

Every container target works with either engine. The Makefile uses `docker` when it is installed, otherwise `podman` (`make engine` shows the choice; force it with `ENGINE=podman`).

| | Docker | Podman (no Docker / Docker Desktop needed) |
|---|---|---|
| Install | Docker Engine or Desktop | Podman 5+, plus `uv tool install podman-compose` (>= 1.3) |
| Windows / macOS | — | `podman machine init` then `podman machine start` |
| Compose | `docker compose` | `podman-compose` (same `compose.yaml`) |
| Image build | `docker build -f Containerfile` | `podman build -f Containerfile --format docker` (keeps the HEALTHCHECK) |
| Web on port 80 | works as is | rootless Podman cannot bind ports < 1024: set `WEB_PORT=3000` or see [TROUBLESHOOTING](TROUBLESHOOTING.md) |

`compose.yaml` (chroma, redis, postgres, mcp, api, web) uses fully-qualified image names and **named volumes** (`chroma-data`, `redis-data`, `pg-data`, `api-logs`), so rootless Podman has no UID or SELinux permission issues. The previous `docker-compose.yml` (bind mounts) is in `archives/`. When you switch, the vector DB starts empty: remove the old containers (`docker rm -f netcore-chroma netcore-redis`), then run `make bootstrap`.

## Pre-RAG Pipeline ([scripts/populate_vector_dbs.py](scripts/populate_vector_dbs.py))

| Stage | Implementation |
|---|---|
| Data source | `KB_DATA_DIR/<domain>/`, one Chroma **database** per domain (`networking_kb`, `meetings_kb`), collection `kb_articles` |
| Readers | `PyPDFLoader` (per page), `UnstructuredHTMLLoader`, `UnstructuredMarkdownLoader` |
| Metadata | Taken from the file (PDF keywords / HTML `<meta>` / MD frontmatter), with `manifest.json` as fallback. Adds `product_family`, `content_type`, `page`, `chunk_index`, `source_file` |
| Chunking | `RecursiveCharacterTextSplitter`, `CHUNK_SIZE=3000`, `CHUNK_OVERLAP=200` |
| Tables & code | Detected with pdfplumber, BeautifulSoup or regex. The LLM writes a description, stored as a **separate chunk** (`content_type=table\|code`) with document, page/section and table references |
| Embeddings | `OpenAIEmbeddings(OPENAI_EMBEDDING_MODEL)` |
| Store | `langchain_chroma.Chroma` on `chromadb.HttpClient`. Deterministic IDs (`KB-NET-1003::table::01`), so re-runs upsert |

All settings live in `.env` (see [.env.example](.env.example)).

## How It Works

1. A **seed catalog** in [scripts/generate_kb.py](scripts/generate_kb.py) fixes each article's ID, title, type, format and version, plus a set of shared domain facts.
2. **LangChain** runs `ChatPromptTemplate | ChatOpenAI.with_structured_output(Article)` and calls `.batch()` to write all bodies in parallel.
3. **Renderers** produce Markdown (YAML frontmatter), HTML (`<meta>` tags) and PDF (ReportLab, metadata stored in document properties).
4. A **manifest.json** per domain lists every article together with its metadata.

## Built-in RAG Teaching Hooks

- **Superseded articles:** KB-NET-1004 and KB-MTG-2004 (release 4.2) conflict with their 5.0 replacements, which shows why metadata filters and recency matter.
- **Exact-match terms:** error and alarm codes such as `NCS-SLA-2001` and `MTG-JOIN-1007` make a good hybrid-search (BM25 + vector) demo.
- **Cross-references:** articles cite each other by KB ID ("see KB-NET-1003").
- **Structured content:** tables, CLI blocks and sample outputs let students compare chunking strategies.

## Project Layout

```
data/raw/<domain>/              generated articles + manifest.json
docs/plans/                     planning notes
docs/ui-mockups/                Stitch mockups + clickable prototype (UI reference)
scripts/generate_kb.py          KB generator
scripts/verify_kb.py            loader smoke test
scripts/populate_vector_dbs.py  Pre-RAG pipeline -> Chroma
scripts/test_query_vector_dbs.py  query demos (similarity, keyword, filters, hybrid)
scripts/rag_search.py           reusable retrieval functions + LangChain retriever
notebooks/naive-rag.ipynb       Naive RAG walkthrough
scripts/agentic_rag/            Enterprise Agentic RAG agent (package)
scripts/assign_access_levels.py RBAC access_level metadata patch
notebooks/agentic-rag.ipynb     Agentic RAG test scenarios
api/app/                        REST API (FastAPI): controllers, services, repositories, schemas
api/alembic/                    database migrations (audit tables)
api/tests/                      API unit tests (+ agent ticket bridge tests)
netcore_mcp/                    IT ticket MCP server (FastMCP): server, service, Jira client, repository
netcore_mcp/alembic/            itsm schema migrations (own chain)
netcore_mcp/tests/              MCP server tests (fakes, no network)
netcore_mcp/Containerfile       MCP server image
web/src/                        Web UI (React 18 + Vite): features/, components/, api/, hooks/, lib/
web/nginx/                      Nginx gateway config (SPA + /api proxy, security headers)
web/Containerfile               web image (Node build -> non-root Nginx)
compose.yaml                    chroma, redis, postgres, mcp, api, web (Docker or Podman)
Containerfile                   API image (multi-stage, slim, non-root)
archives/                       previous docker-compose.yml
Makefile                        command entry points (## comments = help + TUI metadata)
tui.py                          terminal UI launcher (uv run tui.py)
scripts/publish_images.py       Docker Hub publish (make publish)
iac/                            Terraform: EC2 + Docker CE + deployment (compose.prod.yaml, cloud-init, deploy.sh)
scripts/make_tui/               terminal UI (Textual): Makefile parser, app, widgets, runner
```

## Documentation

[TROUBLESHOOTING](TROUBLESHOOTING.md) · [CHANGELOG](CHANGELOG.md) · [CONTRIBUTING](CONTRIBUTING.md) · [CODE OF CONDUCT](CODE_OF_CONDUCT.md) · [SECURITY](SECURITY.md)

## License

[MIT](LICENSE) © 2026 Ramkumar
