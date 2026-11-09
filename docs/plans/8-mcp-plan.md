# Plan: IT support tickets via an MCP server (`netcore_mcp/`), v0.9.0

## Context
The business wants IT support tickets inside the Agentic RAG assistant:
- every user can register tickets and view their own;
- the admin (carol) can search all tickets and resolve them.

Postgres is the source of truth. Every ticket is mirrored one-way to Jira Cloud, in project **KAN** ("My IT Team"), as an **Incident**.

The ticket logic lives in a new **FastMCP** server (`netcore_mcp/`, streamable HTTP, port 9090). The agent uses it in both react and plan modes.

**Jira facts found (read-only probe)**
- Site: `jdramkumar-…atlassian.net` (Cloud). Auth is Basic with `jd.ramkumar@gmail.com` plus the token; it works.
- KAN statuses: To Do, In Progress, Waiting for Customer, Resolved.
- Priorities: Highest, High, Medium, Low, Lowest. The project is empty.

## Decisions (MCQ rounds)
| Topic | Decision |
|---|---|
| Admin | carol (`admin` role). bob stays an employee. |
| Access | Every role can register a ticket and list or get their own. **Admin only**: search all, resolve, sync. |
| Jira target | Project KAN, issue type Incident. One-way sync (Postgres to Jira). |
| Jira auth | Add `ATLASSIAN_EMAIL` to `.env`, next to `ATLASSIAN_SITE_URL` and `ATLASSIAN_API_TOKEN`. |
| DB | Same `netcore_api` database, own schema **`itsm`**, own Alembic chain (version table in `itsm`) |
| Consistency | Write to the DB first, then Jira. If Jira fails: `jira_sync=pending`, then a background retry loop (60 s) plus an admin tool `sync_pending_tickets` |
| Identity | The agent sends an **`X-User-Id`** header on each call, and the server applies RBAC. There is no auth, as requested. |
| Enums | severity: critical/high/medium/low (Highest/High/Medium/Low in Jira). product_family: networking/meetings. region: AMER/EMEA/APAC. status: open/resolved. |
| Ticket ID | `TKT-000123`, from a Postgres sequence. The Jira key, id and URL are stored on the row. |
| Resolve | `remarks` is required. Jira gets a comment, then the transition to Resolved. |
| Admin search | keyword (ILIKE on title or description), product/region/severity, registered_by, date range, status (default open) |
| Jira issue | Summary is the title; priority comes from severity. Labels: `netcore-assist`, product, region, `user-<id>`. The description (ADF) starts with a header: TKT id, registered by, severity. |
| Libraries | `fastmcp` 4.1.6, uvicorn, Jira over httpx async (REST v3), `langchain-mcp-adapters` 0.3.2 in the agent |
| Packaging | **Root `pyproject.toml`**, like `api/`. Own `netcore_mcp/Containerfile`. |
| Agent | **react + plan** modes. Writes (register or resolve) run only when the user explicitly asks. |
| Judge/cache | Ticket results become cited CONTEXT blocks, so the judge still checks grounding. A run that touches tickets is **never cached**. |
| MCP down | The agent degrades: KB answers still work, and ticket tools return "ticket service unavailable". |
| Tests | Fakes only: in-memory fastmcp Client, fake repository, respx-mocked Jira |
| Release | **0.9.0**. MCP is part of `up-all` and `stack-up`; the api waits for a healthy mcp. |
| Docs | README, CHANGELOG, CONTRIBUTING, TROUBLESHOOTING, SECURITY, CODE_OF_CONDUCT, plus `.env.example` |

## 1. MCP server: `netcore_mcp/`
```
netcore_mcp/
  __init__.py      __version__ = "0.9.0"
  __main__.py      uvicorn.run(app, host=MCP_HOST 0.0.0.0, port=MCP_PORT 9090)
  config.py        pydantic-settings (root .env): DATABASE_URL, ATLASSIAN_SITE_URL/EMAIL/API_TOKEN,
                   JIRA_PROJECT_KEY=KAN, JIRA_ISSUE_TYPE=Incident, JIRA_SYNC_INTERVAL_SECONDS=60, MCP_HOST, MCP_PORT
  server.py        FastMCP("netcore-tickets"), tools, lifespan (engine + Jira client + sync loop), /health route
  identity.py      X-User-Id -> User (reuse agentic_rag.config.DEMO_USERS/get_user); missing/unknown -> ToolError
  schemas.py       Pydantic enums + tool inputs/outputs (TicketOut includes jira_key, jira_url, jira_sync)
  models.py        SQLAlchemy Ticket (schema itsm), own Base/metadata
  repository.py    insert / get / list_by_user / search / resolve / list_pending_sync
  service.py       TicketService: RBAC + DB-first + Jira sync orchestration
  jira.py          JiraClient (httpx.AsyncClient, Basic auth): create_issue (ADF), add_comment,
                   resolve (look up the transition named "Resolved"), with timeouts and one retry
  sync.py          background loop: pending create -> create issue; resolved-but-not-synced -> comment + transition
  alembic.ini, alembic/env.py (async, version_table_schema="itsm"), alembic/versions/20261110_0001_itsm_tickets.py
  Containerfile
  tests/           conftest (fake repo, respx Jira, in-memory Client with X-User-Id), test_tools, test_service, test_jira
```
**`itsm.tickets` columns**
- Identity and dates: `id` bigint (seq), `ticket_id` (`TKT-%06d`, unique), `registered_at`, `registered_by`
- Content: `title`, `description`, `product_family`, `region`, `severity`, `status`
- Resolution: `resolved_by`, `resolved_at`, `remarks`
- Jira: `jira_key`, `jira_id`, `jira_url`, `jira_sync` (pending|synced), `jira_error`, `jira_attempts`, `updated_at`

Enums are stored as VARCHAR with CHECK constraints. Indexes on (`registered_by`, `status`) and on `status`.

**Tools** (FastMCP; the user comes from the header)
| Tool | Who | Notes |
|---|---|---|
| `register_ticket(title, description, product_family, region, severity)` | all | Insert, then create in Jira. Returns the ticket and its Jira key, or `pending`. |
| `list_my_tickets(status="open"\|"resolved"\|"all")` | all | Own tickets only |
| `get_ticket(ticket_id)` | owner or admin | |
| `search_tickets(keyword?, product_family?, region?, severity?, registered_by?, date_from?, date_to?, status="open", limit=20)` | admin | |
| `resolve_ticket(ticket_id, remarks)` | admin | Updates the DB, then adds the Jira comment and transition (pending on failure) |
| `sync_pending_tickets()` | admin | Retries now and returns counts |

## 2. Agent integration: `scripts/agentic_rag/`
- **New `tickets.py`**
  - Loads the MCP tools with `langchain-mcp-adapters` (`MultiServerMCPClient`, `streamable_http`, `MCP_SERVER_URL`).
  - **Sync bridge:** the agent runs in worker threads, so each call runs through `asyncio.run`.
  - **User header:** `X-User-Id` is added per call from `runtime.context.user`, using the adapters' tool-call interceptor. Fallback: a per-call session with headers; the 0.3.2 API is checked during implementation.
  - **Results:** each tool result becomes a "ticket doc" in `relevant_docs` (`kb_id=TKT-…`/`TICKETS`, `location="tickets"`), so it is cited and judged.
  - **Errors:** an error or an unreachable server becomes an "unavailable" doc, never an exception.
  - **Loading:** if loading fails, it is retried on a later request rather than cached.
- **react mode** (`agent.py:49`): ticket tools are added to the tool list. `ORCHESTRATOR_PROMPT` gets ticket rules: writes only when explicitly asked, never invent field values, ask for missing ones.
- **plan mode**
  - `planner.py`:
    - `Tool` gains the ticket tools, and `PlanStep` gets `ticket_args: TicketArgs | None`, which is validated.
    - The prompt gets a tools section and the user's role, with this rule: a write step only when the user explicitly asks; admin tools only for admins.
  - `executor.py`: a ticket step calls the bridge. Its status is `done` or `error`, and it is never "no_results", so it is not re-planned.
  - `retrieval.ROUTE_BY_TOOL` gains the `tickets` route. `middleware.py:345` `web_tried` is fixed so that ticket steps don't count as web steps.
- **Cache**: `SemanticCacheMiddleware.after_agent` skips the write when the `tickets` route was used (`ctx.used_tickets`).
- **Config**: `MCP_SERVER_URL`, defaulting to `http://localhost:9090/mcp`; compose sets it to `http://mcp:9090/mcp`.
- **Web UI**: no code change. Ticket calls already show in the Tool calls, Trace and Plan tabs. To verify: citation chips for `TKT-…`.

## 3. Containers, compose, Make, deps
- **Dependencies** (`pyproject.toml`): `fastmcp==4.1.6` (exact pin to avoid surprise majors) and `langchain-mcp-adapters>=0.3.2`; dev adds `respx`. Pytest `testpaths` adds `netcore_mcp/tests`, and `pythonpath` adds `.`.
- **`netcore_mcp/Containerfile`**: the same pattern as the root `Containerfile` (python:3.12-slim with the uv builder, slim venv, non-root uid 10001). It copies `netcore_mcp/` plus `scripts/agentic_rag/config.py` dependencies. `HEALTHCHECK` hits `/health`; `CMD` runs `alembic upgrade head` (itsm), then `python -m netcore_mcp`.
- **`compose.yaml`**
  - New service `mcp`:
    - image `localhost/netcore-rag-mcp:0.9.0`, container `netcore-mcp`
    - ports `${MCP_PORT:-9090}:9090`, with `env_file .env` and `DATABASE_URL` pointing at `postgres`
    - waits for a healthy postgres; has a healthcheck and `restart: unless-stopped`
  - api: adds `MCP_SERVER_URL` and waits for a healthy `mcp`.
- **Makefile**
  - Variables `MCP_IMAGE` and `MCP_PORT ?= 9090`.
  - Targets: `mcp-run` (local), `mcp-test`, `mcp-migrate`, `mcp-build`, `mcp-up`, `mcp-down`, `mcp-logs`.
  - `up-all` also builds mcp, runs `mcp-migrate` after the api migration, and starts `mcp` before api and web (healthy waits).
  - `stack-up` builds mcp; `bootstrap` adds `mcp-migrate`. Help text updated.
- **Versions**: 0.9.0 for the API `__version__`, the api/web/mcp image tags and `web/package.json`.
- **Env files**
  - `.env.example`: new section `# --- MCP server (netcore_mcp/) ---` with `MCP_HOST`, `MCP_PORT`, `MCP_SERVER_URL`, `ATLASSIAN_SITE_URL`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, `JIRA_PROJECT_KEY=KAN`, `JIRA_ISSUE_TYPE=Incident` and `JIRA_SYNC_INTERVAL_SECONDS`.
  - `.env`: add `ATLASSIAN_EMAIL=jd.ramkumar@gmail.com` and `JIRA_PROJECT_KEY=KAN`.

## 4. Docs
| File | Change |
|---|---|
| README | MCP section: architecture (agent → MCP → Postgres + Jira), tools and RBAC table, ticket schema, run steps, make targets, compose ports, layout |
| CHANGELOG | 0.9.0: Added (MCP server, tools, itsm schema, Jira sync, agent integration), Changed (versions, up-all/stack-up) |
| CONTRIBUTING | How to add an MCP tool, run tests, migrations for the itsm chain |
| TROUBLESHOOTING | Jira 401/403 (email + token), transition not found, `jira_sync=pending`, MCP unreachable, missing `X-User-Id`, port 9090 in use |
| SECURITY | No auth on MCP (demo), so `X-User-Id` is trusted and must not be exposed publicly; Jira token handling; one-way sync |
| CODE_OF_CONDUCT | Scope now includes the MCP server |

## 5. Verification
1. `make mcp-test`: the tools work through the in-memory client, including RBAC denials (bob resolving or searching is refused; alice cannot get bob's ticket), Jira failure leading to `pending` and then sync, and the ADF payload and labels. `make api-test` must still pass (53 tests), plus planner and executor ticket-step tests with a fake bridge.
2. `make up-all`: mcp is healthy, then api, then web. `itsm.tickets` exists.
3. Live checks (they create real KAN issues and use OpenAI credits):
   - `make agent-ask M=react U=bob Q="Open a high severity ticket: …"` creates a row and a KAN-n issue.
   - `M=plan U=carol`: search open tickets, then resolve one with remarks. The Jira issue gets the comment and moves to Resolved.
   - alice lists her own tickets. bob asking to resolve is refused.
   - `make mcp-down`, then a KB question still answers and a ticket request reports the service as unavailable.
4. Through the web UI (http://localhost/): a ticket question streams. Ticket tool calls appear in the Plan and Tool calls tabs, and the citations render.
5. No commit unless asked.
