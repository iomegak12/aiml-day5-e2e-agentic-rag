# Contributing

Thanks for helping improve the course material.

## Setup

```bash
cp .env.example .env   # add your own OpenAI key
make install
make web-install       # web UI only: Node.js 22 LTS + npm
```

## Common Changes

- **Add or edit an article:** update `SEEDS` in [scripts/generate_kb.py](scripts/generate_kb.py), then run `make generate`.
- **Change shared facts** (thresholds, error codes): edit `DOMAIN_FACTS`, then run `make regenerate` so every article stays consistent.
- **Change layout or styling:** edit the `render_md`, `render_html` or `render_pdf` functions.
- **Change the REST API:** keep the layers. Routes stay thin in `api/app/controllers/`, logic goes in `services/`, and data access goes in `repositories/`. DTOs live in `schemas/`, and errors are raised as `ProblemException` (RFC 9457).
- **Change the database schema:** edit `api/app/models/`, then add a migration with `uv run alembic -c api/alembic.ini revision --autogenerate -m "..."` and review it before `make db-migrate`.
- **Add or change a ticket tool:** tools live in [netcore_mcp/server.py](netcore_mcp/server.py) (thin, typed with `Annotated` + `Field` so the LLM gets a precise schema). Put rules and RBAC in `service.py`, SQL in `repository.py` and Jira calls in `jira.py`. Raise `ToolError` for messages the user may see. Add a test in `netcore_mcp/tests/` (in-memory client, `FakeTicketRepository`, respx Jira). If plan mode should use the tool, add it to `Tool` / `TicketArgs` in `scripts/agentic_rag/planner.py`.
- **Change the ticket schema:** edit `netcore_mcp/models.py`, then `uv run alembic -c netcore_mcp/alembic.ini revision --autogenerate -m "..."`, review it and run `make mcp-migrate`. This chain owns only the `itsm` schema; the API's chain owns `public`.
- **Add or change a make target:** give it a `##` comment: `name: deps  ## Description [tags] {params}` under the right `##@` group. Use the tags `[danger]` (deletes or overwrites data), `[cost]` (OpenAI or Jira) and `[long]` (runs until stopped). Parameters can be `NAME!` (required), `NAME=default`, `NAME=default:a|b|c` (choice) or `NAME?` (flag). `make help` and the terminal UI pick it up automatically, and `make api-test` fails if a target is undocumented.
- **Change the AWS deployment:** edit `iac/*.tf`, then `terraform -chdir=iac fmt` and `make iac-plan` (review the plan before `make iac-up`). Keep secrets out of `user_data` and Terraform variables: app settings travel only in the filtered `.env` upload. A new service must be added to both `compose.yaml` and `iac/compose.prod.yaml`; never publish a port that has no authentication (bind it to `127.0.0.1`).
- **Add a dependency:** `uv add <pkg>` for the runtime (it goes into the API image), or `uv add --group kb <pkg>` for KB generation and notebook-only packages.
- **Change the web UI:** code lives in `web/src/` by feature (`features/auth`, `chat`, `run`, `requests`, `status`). Shared pieces go in `components/`, `hooks/` and `lib/`. Every HTTP call goes through `src/api/` (`apiFetch`, `ApiError`, `openStream`), never a raw `fetch` in a component. Use the design tokens from `src/styles/index.css` (`bg-card`, `text-ink-2`, ...) instead of hard-coded colours, so dark mode keeps working. Run `make web-dev` (hot reload, proxies `/api` to `localhost:8080`).
- **Change the gateway:** edit `web/nginx/*.conf`. Keep `proxy_buffering off` for SSE, and keep everything self-hosted so the CSP in `security-headers.conf` can stay `'self'`.
- **Add a front-end dependency:** `npm --prefix web install --save-exact <pkg>`, and commit `web/package-lock.json`.
- **Containers:** test with Docker, and with Podman if you can (`make api-up ENGINE=podman`). Keep image names fully qualified and volumes named.

## Before Opening a PR

1. `make generate && make verify` must pass (KB changes), and `make api-test` must pass (API or agent changes). New API behaviour needs a unit test, with external services faked as in `api/tests/conftest.py`.
   For MCP server changes, `make mcp-test` must pass (`make api-test` runs both suites).
   For web changes, `make web-lint web-test web-build` must pass, and new behaviour needs a Vitest test (helpers in `web/src/test/utils.jsx`).
2. Keep all content fictional: no real vendor or product names.
3. Never commit `.env` or API keys.
4. Add an entry under a new version heading in [CHANGELOG.md](CHANGELOG.md).
5. Use small, focused commits with clear messages.

By contributing you agree that your work is licensed under the [MIT License](LICENSE) and that you will follow the [Code of Conduct](CODE_OF_CONDUCT.md).
