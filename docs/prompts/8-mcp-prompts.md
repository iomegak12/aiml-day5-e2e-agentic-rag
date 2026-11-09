# Phase 8 – IT support tickets: MCP server (FastMCP) + Postgres + Jira, wired into the agent

Your prompts (lightly cleaned), the MCQ clarifications with every option ([x] = your choice), and a one-line outcome.

## Prompt 1

> As part of the business requirement, I now have a new capability to build and integrate with the Agentic AI RAG agent system.
>
> My business wants to add an IT support ticket management feature to the agentic system, which allows the user to:
> - view the tickets registered by the currently signed-in user
> - register a new ticket
> - if the user is an administrator (bob), search and view all open tickets
> - resolve tickets as well
>
> I would like to keep all tickets in the Postgres database.
>
> An IT support ticket may include the following details:
> - Ticket ID
> - Ticket registered date
> - Registered by
> - Title
> - Description
> - Product family
> - Region
> - Severity
> - Status
> - Resolved by
> - Resolved at
> - Remarks
>
> Along with that, I also need to integrate Jira work item management. I have already configured the `.env` file with access to the API (`ATLASSIAN_API_TOKEN`), and there's a team named "My IT Team".
>
> So we now need to build an MCP server that I can easily integrate with the existing Agentic AI system:
> - Python 3.12
> - FastMCP
> - Uvicorn hosting
> - Streamable HTTP protocol
> - No security / authentication needed for now
> - Port: 9090
> - Host: 0.0.0.0
> - For now, other enterprise features such as IP rate limiting, OpenAPI, Swagger and CORS can all be skipped
> - Provision a separate folder named `netcore_mcp` at the workspace root to implement this feature
> - Introduce new make targets
> - Update the compose YAML file
> - Create a separate container file to build the MCP server
> - Jira-specific IDs should also be kept in the database
> - Behind the scenes, it should register tickets both in Postgres and in the Jira workspace
>
> Do you get all my requirements for the MCP server? Let's have a debate with MCQ-based Q&As so we are aligned on what we want to build.
>
> NOTES:
> - Do NOT assume anything on your own; clarify with me.
> - Do NOT generate anything until I review and approve the plan.
> - Do NOT respond in detail until I ask; always be as brief as possible.
>
> Let's go.

### Clarifications

#### Round 1

**You wrote 'administrator (bob)', but in the existing system bob is an employee and carol is the admin. Who gets 'search all open tickets + resolve'?** _(Admin role)_

- [x] **Admin role = carol (Recommended)** – Keep current RBAC: alice=guest, bob=employee, carol=admin. Consistent with API/web.
- [ ] Make bob the admin – Changes existing RBAC; ripples into API, web, docs and tests.
- [ ] bob + carol both – New 'ticket_admin' permission given to both users.

**.env has only ATLASSIAN_API_TOKEN. Jira Cloud also needs the site URL and account email (Basic auth = email:token). How do we add them?** _(Jira config)_

- [ ] Add 3 new vars (Recommended) – ATLASSIAN_SITE_URL, ATLASSIAN_EMAIL, JIRA_PROJECT_KEY in .env/.env.example; you fill values.
- [ ] I'll give values now – You type site URL / email / project key in 'Other'.
- [ ] Token is a Bearer/PAT – Data Center / Server PAT; only URL needed, no email.
- [x] **Other:** "I have updated the .env file with a new key ATLASSIAN_SITE_URL."

**'My IT Team' in Jira is which kind of object?** _(Jira team)_

- [ ] A Jira project – Issues created in that project (need its project key, e.g. ITS).
- [ ] Atlassian Team (Team field) – Issues created in a project and assigned to the team via the Team custom field.
- [x] **Not sure – discover it** – I query the Jira API (read-only) during planning to find it.

**Scope of this phase?** _(Scope)_

- [x] **MCP server + agent wiring (Recommended)** – netcore_mcp server, plus agent consumes its tools via langchain-mcp-adapters (user identity passed in).
- [ ] MCP server only – Standalone server; agent integration in a later phase.
- [ ] Server + agent + API/web – Also ticket screens in the web UI and REST routes.

#### Round 2

**Jira check: the site is Jira Cloud, and the token (ATATT…) needs Basic auth = email + token (Bearer was rejected with 403). Which email belongs to the token?** _(Jira email)_

- [x] **jd.ramkumar@gmail.com** – Add ATLASSIAN_EMAIL=jd.ramkumar@gmail.com to .env, then I read-only discover 'My IT Team'.
- [ ] Different email – Type it in 'Other' (or add ATLASSIAN_EMAIL to .env yourself).

**Where do ticket tables live in Postgres?** _(DB layout)_

- [ ] Same DB, Alembic in api/ (Recommended) – One migration chain (api/alembic), new 'tickets' table in netcore_api. MCP reuses models. Simple; up-all already migrates.
- [x] **Same DB, own schema + Alembic** – netcore_mcp owns schema 'itsm' with its own Alembic chain. Cleaner service boundary, 2 chains.
- [ ] Separate database – New DB netcore_itsm. Strong isolation; extra init script + URL.

**Write order and failure handling for Postgres + Jira?** _(Consistency)_

- [x] **DB first, Jira sync, pending on fail (Recommended)** – Insert ticket, create Jira issue, store key. If Jira fails: jira_sync=pending + retry tool. Ticket never lost.
- [ ] All-or-nothing – Jira fails -> rollback DB, return error. Simple, but Jira outage blocks tickets.
- [ ] Jira first, then DB – Create issue, then insert with key. DB fail leaves orphan Jira issue.

**How does the MCP server know the current user (no auth for now)?** _(Identity)_

- [x] **Agent passes user via header (Recommended)** – Agent's MCP client sends X-User-Id per request; tools read it. LLM can't impersonate; RBAC enforced in server.
- [ ] user_id as tool argument – Simplest; but the LLM fills it, so it could act as another user.
- [ ] Agent injects arg, hidden from LLM – Tool schema hides user_id; agent wrapper injects it. Server trusts the arg.

#### Round 3

**Found it: 'My IT Team' = Jira project KAN (team-managed, empty). Statuses: To Do / In Progress / Waiting for Customer / Resolved. Which issue type for tickets?** _(Issue type)_

- [x] **Incident (Recommended)** – Fits IT support tickets; all tickets created as Incident.
- [ ] Service Request – Request-style tickets.
- [ ] Task – Generic work item.
- [ ] Ticket chooses type – New 'type' field: incident | service_request.

**Severity values (mapped to Jira Priority)?** _(Severity)_

- [x] **critical/high/medium/low (Recommended)** – -> Highest/High/Medium/Low. Readable for users and LLM.
- [ ] S1/S2/S3/S4 – -> Highest/High/Medium/Low. ITSM style.
- [ ] P1..P5 – -> Highest..Lowest, all 5 Jira priorities.

**Product Family and Region values?** _(Enums)_

- [x] **Fixed enums (Recommended)** – Product: networking | meetings (KB domains). Region: AMER | EMEA | APAC. Validated; sent to Jira as labels.
- [ ] Product enum, region free text – Product validated; region any string.
- [ ] Both free text – No validation; LLM decides values.

**Ticket status lifecycle in Postgres (and Jira)?** _(Status)_

- [x] **open / resolved (Recommended)** – Matches your features (register, resolve). Jira: To Do -> Resolved.
- [ ] open / in_progress / resolved – Adds a 'start work' tool. Jira: To Do -> In Progress -> Resolved.
- [ ] Mirror all 4 Jira statuses – Includes waiting_for_customer; more tools.

#### Round 4

**Who may resolve tickets?** _(Resolve)_

- [x] **Admin only (carol) (Recommended)** – Typical IT support: the support team resolves. Users only register/view their own.
- [ ] Admin any + user own – Users may close their own tickets; admin resolves any.

**Can guests (alice) use tickets?** _(Guest access)_

- [x] **Yes, all roles (Recommended)** – alice, bob, carol register + view own tickets; carol searches all.
- [ ] Employees and admin only – alice gets 403-style error from ticket tools.

**How does the agent use the ticket tools?** _(Agent mode)_

- [ ] React mode tools (Recommended) – MCP tools loaded via langchain-mcp-adapters into react mode. Plan mode stays KB-only (planner is search-specific).
- [x] **React + plan mode** – Also extend planner/executor with ticket steps. More changes, more risk.
- [ ] New 'tickets' mode – Separate agent mode just for tickets (M=tickets).

**MCP framework?** _(FastMCP)_

- [x] **fastmcp 4.1.6 (Recommended)** – Standalone FastMCP (latest), richer: headers access, middleware, in-memory test client.
- [ ] mcp 2.3.0 SDK FastMCP – Official SDK's built-in FastMCP; fewer deps, fewer features.

#### Round 5

**The agent runs synchronously in worker threads, but MCP tools are async. How does the agent call the MCP server?** _(MCP client)_

- [x] **langchain-mcp-adapters (Recommended)** – Official LangChain MCP client (0.3.2): load tool schemas from the server, with a small sync bridge and an X-User-Id header per call. Follows the 'latest LangChain' rule.
- [ ] fastmcp Client + own @tool wrappers – Hand-written LangChain tools that call the fastmcp Client. More code, full control.
- [ ] Make the agent async – Switch to ainvoke end-to-end. Cleanest long term, but a big refactor of the agent and the API.

**Write tools (register, resolve) in plan mode run from an LLM-made plan. Safety?** _(Write safety)_

- [x] **Auto-run if explicitly asked (Recommended)** – The planner may add a write step only when the user clearly asks to open or resolve a ticket. RBAC is checked on the server. Every write appears in the plan and the trace.
- [ ] Human confirmation (HITL) – LangGraph interrupt plus a confirm step. Needs API and web changes; bigger scope.
- [ ] Writes in react mode only – Plan mode can only read tickets (list, search).

**Ticket answers have no KB docs. How do the judge and the semantic cache treat them?** _(Judge/cache)_

- [x] **Results as CONTEXT, no cache (Recommended)** – Ticket results become cited context blocks [TKT-...], so the judge still checks grounding. A run that touches tickets is never cached (the data is per user and changes).
- [ ] Skip judge, no cache – Ticket-only answers bypass the judge; mixed KB + ticket answers are still judged.

**Ticket ID format?** _(Ticket ID)_

- [x] **TKT-000123 (Recommended)** – Readable ID from a Postgres sequence; the Jira key (KAN-12) is stored next to it.
- [ ] UUID – Globally unique, but hard to read in chat.
- [ ] Use the Jira key only – Clashes with 'DB first, Jira can be pending'.

#### Round 6

**How is netcore_mcp packaged?** _(Packaging)_

- [ ] Own pyproject, uv workspace (Recommended) – netcore_mcp/pyproject.toml as a workspace member: separate deps and a slim image. The agent depends only on langchain-mcp-adapters.
- [x] **Root pyproject (like api/)** – Add fastmcp to the root deps; one lock and one venv; the image carries every dependency.

**Is remarks required when resolving, and is it synced to Jira?** _(Remarks)_

- [x] **Required; Jira comment (Recommended)** – Resolve needs remarks. Jira gets the comment, then moves to Resolved.
- [ ] Optional; Jira comment if given – Remarks may be empty.

**Which filters does admin 'search open tickets' support?** _(Search, multi-select)_

- [x] **Keyword (title/description)** – Case-insensitive match (ILIKE).
- [x] **Product family / region / severity** – Filters on the enums.
- [x] **Registered by + date range** – Find by user, or by registered-date from/to.
- [x] **Status (open/resolved/all)** – Default open; admin can include resolved.

**Version and startup integration?** _(Release)_

- [x] **0.9.0; in up-all + stack-up (Recommended)** – Image netcore-mcp:0.9.0; api depends on a healthy mcp; mcp-\* make targets.
- [ ] 0.9.0; separate mcp-up only – Not started by up-all or stack-up.

#### Round 7

**How are tickets whose Jira sync is still pending retried?** _(Jira retry)_

- [x] **Background loop + admin tool (Recommended)** – The server retries pending syncs every 60 s; admins also get a sync_pending_tickets tool.
- [ ] Admin tool only – Manual retry by carol through the agent.
- [ ] Retry on next access – Retried lazily when the ticket is read.

**If a ticket is resolved directly in the Jira UI, does Postgres learn about it?** _(Sync dir)_

- [x] **No, one-way (Recommended)** – Postgres is the source of truth and Jira mirrors it. Simple and predictable.
- [ ] Pull on read – list/get refreshes status from Jira (slower, and needs network).
- [ ] Jira webhook – Two-way via a webhook endpoint; needs a public URL, so not workable on localhost.

**How do the MCP tests handle Postgres and Jira?** _(Tests)_

- [x] **Fakes, no network (Recommended)** – In-memory fastmcp Client + fake repository + respx-mocked Jira. Same style as api/tests and fast in CI.
- [ ] Fakes + live smoke script – Plus scripts/test_mcp_server.py against a running server, real Postgres and Jira (creates KAN issues).
- [ ] Real Postgres via compose – Integration tests need the DB running.

**Update the docs too?** _(Docs)_

- [x] **Yes, all 6 + .env.example (Recommended)** – README (MCP section, tools, make targets), CHANGELOG 0.9.0, CONTRIBUTING, TROUBLESHOOTING, SECURITY (no auth, X-User-Id trust), CODE_OF_CONDUCT scope.
- [ ] README + CHANGELOG only – Minimal.

#### Round 8

**All Jira issues are created as the token owner (Ramkumar). How is the real requester recorded in Jira?** _(Jira fields)_

- [x] **Labels + description header (Recommended)** – Labels: netcore-assist, product, region, user-bob. Description: TKT id, registered by, severity, then the text. Priority comes from severity.
- [ ] Description only – No labels.

**Jira client library?** _(Jira lib)_

- [x] **httpx async, REST v3 (Recommended)** – No new dependency; async; easy to mock with respx.
- [ ] atlassian-python-api – Wrapper library; sync, so it needs threads inside the async server.

**What if the MCP server is down when the agent runs?** _(MCP down)_

- [x] **Degrade gracefully (Recommended)** – KB questions still work. Ticket steps and tools return 'ticket service unavailable', and the answer says so.
- [ ] Fail the request – Error 503 for any run.

**In plan mode, how does a ticket step carry its arguments?** _(Plan step)_

- [x] **Typed args on the step (Recommended)** – PlanStep gets an optional 'ticket_args' object (title, severity, ...) validated against the MCP tool schema before running.
- [ ] Separate LLM call per step – The executor asks the LLM to fill args at run time; one extra call per step.

#### Round 9 (during implementation)

**fastmcp 4.1.6 needs mcp 2.x, but langchain-mcp-adapters 0.3.2 (the latest) needs mcp 1.x. They can't both go in one root pyproject. Which way?** _(Dep clash)_

- [x] **fastmcp 3.4.11 + adapters (Recommended)** – Latest 3.x (released 2026-10-20, mcp 1.30). Keeps root pyproject and langchain-mcp-adapters; same APIs we need.
- [ ] fastmcp 4.1.6, no adapters – Agent uses the fastmcp Client with own LangChain @tool wrappers.
- [ ] fastmcp 4.1.6, own pyproject – netcore_mcp gets its own pyproject + uv.lock (separate venv/image); root keeps adapters.

**Outcome:** Built `netcore_mcp/` (v0.9.0): 6 ticket tools with RBAC via `X-User-Id`, `itsm.tickets` with its own Alembic chain, a one-way Jira mirror (KAN, Incident) with pending-sync retry, and agent integration in react and plan modes (cited `[TKT-…]` sources, never cached, graceful when down). Verified live (KAN issues created and resolved); 29 MCP tests + 19 agent-bridge tests.

---

## Prompt 2

> In the MCP Inspector, how can I pass the header? I'm getting this error:
>
> `Missing X-User-Id header: the caller is unknown.`

**Outcome:** Explained how to add the `X-User-Id` custom header (alice / bob / carol) in the Inspector's Authentication section and reconnect, plus the `--cli … --header "X-User-Id: bob"` form.
