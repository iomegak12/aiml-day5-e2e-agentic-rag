# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `KeyError: 'OPENAI_MODEL'` | `.env` is missing or incomplete | `cp .env.example .env`, then set both variables |
| `AuthenticationError` / 401 | Invalid or expired API key | Update `OPENAI_API_KEY` in `.env` |
| `[fail] KB-…` in the output | Rate limit, timeout or schema error for that article | Re-run `make generate`. Only missing articles are regenerated |
| `make generate` does nothing | Every file already exists (skip-existing behaviour) | `make regenerate`, or delete specific files and re-run |
| `make: command not found` | GNU make isn't installed | Windows: `choco install make`. macOS: `xcode-select --install` |
| `BSHTMLLoader … uses the 'lxml' package` | `lxml` isn't installed | Use `make verify`, which supplies it. In your own code: `uv add lxml` |
| Garbled characters (`›`) in loaded HTML | Windows default encoding (cp1252) | Pass `open_encoding="utf-8"` to `BSHTMLLoader` |
| `DeprecationWarning: langchain-community is being sunset` | Upstream LangChain change | Harmless for now. See [langchain-community #674](https://github.com/langchain-ai/langchain-community/issues/674) |
| PDF page text starts with "NetCore Systems \| KB-… \| Page n" | The page footer is extracted as text | Expected. Strip it during chunk cleaning if you want |
| Frontmatter / `<meta>` missing from `Document.metadata` | `TextLoader` / `BSHTMLLoader` don't parse them | Join on `manifest.json` by file name, or parse them yourself |
| Articles differ between runs | LLM output is non-deterministic | Expected. The seeds and domain facts keep key values consistent |
| `Chroma server not reachable at localhost:8000` | The server isn't running, or the port differs | `make chroma-up`, and check `CHROMA_HOST` / `CHROMA_PORT` in `.env` |
| `port is already allocated` on `make chroma-up` | Another service is using the port | Change `CHROMA_PORT` in `.env` (compose reads it), then `make chroma-up` |
| `KeyError: 'OPENAI_EMBEDDING_MODEL'` | Variable missing from `.env` | Add `OPENAI_EMBEDDING_MODEL=text-embedding-3-small` |
| `KB folder not found` | `KB_DATA_DIR` is wrong, or there are no articles yet | Fix the path, or run `make generate` |
| Client/server version errors from Chroma | The `chromadb-client` version and the image tag differ | Keep the `compose.yaml` image tag equal to the `chromadb-client` version in `uv.lock` |
| First `make populate` is slow or downloads data | `unstructured` initialises (and may fetch NLTK data) on first use | Wait for it once. Later runs are faster |
| A table split into two table chunks | The PDF table continues onto the next page | Expected. Each part carries its own page reference |
| `[warn] description failed …` | LLM error for one table/code item | A template description is used instead. Re-run `make populate` (it upserts) |
| Start from an empty vector DB | — | `make chroma-reset && make chroma-up && make populate` |
| `Cannot open the Chroma databases` in `make test-query` | The server is down, or the DBs aren't populated yet | `make chroma-up && make populate` |
| `$contains` returns 0 for a known code | `$contains` is case-sensitive | Use the exact case (`MTG-JOIN-1007`), or BM25 |
| `$contains` matches many chunks | Codes are cross-referenced across articles | Expected. It filters but doesn't rank; compare with BM25 |
| "Server API version 1.0.0" while the image is 1.5.9 | `/api/v2/version` reports the API version | Expected |
| `make query` prints a usage error | `Q` wasn't given | `make query Q="your question" D=meetings` |
| Notebook: `ModuleNotFoundError: rag_search` / `langchain_*` | Wrong kernel, or the notebook was started outside the project | Select the project's `.venv` kernel (run `uv sync` first). Open the notebook from `notebooks/` or the project root |
| Notebook: connection refused | The Chroma server isn't running | `make chroma-up`, then re-run the setup cell |
| Answers vary between runs | LLM output is non-deterministic | Expected. Citations and grounded values should stay the same |
| The LLM-only demo happens to answer correctly | Generic values can be guessed by luck | Ask about product-specific facts (codes, timers), as demo 6a does |
| Judge: `Unsupported parameter: 'reasoning_effort'` | `JUDGE_OPENAI_MODEL` is not a reasoning model | Set `JUDGE_REASONING_EFFORT=` (empty) in `.env` |
| Judge scores differ between runs | LLM-as-a-judge is non-deterministic | Expected. Compare pass/fail against the thresholds, not exact scores |
| Agent: Redis `ConnectionError` | Redis isn't running | `make redis-up` |
| Guest gets "no information" for internal topics | RBAC: guests only see `public` chunks | Expected. Ask as `U=bob` or `U=carol` |
| `access_level` missing (no results with an RBAC filter) | Metadata wasn't patched | `make assign-access-levels` (new `make populate` runs include it) |
| Status `timeout` | The request exceeded `AGENT_TIMEOUT_SECONDS` | Raise the budget in `.env`. The judge takes ~20–40 s per round |
| `GraphRecursionError` | Too many graph steps | The agent uses `recursion_limit=300`; real loops are capped by `ModelCallLimitMiddleware` and `MAX_REWRITES` |
| Answers differ between runs | LLM routing, rewriting and judging are non-deterministic | Expected. The path (trace) is what to compare |
| `Task exception was never retrieved ... Event loop is closed` (older versions) | The former RAGAS judge closed its async client after the event loop | Gone since 0.7.0 (the judge is synchronous). Restart the kernel after updating |
| Plan mode takes longer than `AGENT_TIMEOUT_SECONDS` | The budget is only checked between steps; a running LLM call (synthesis, judge) isn't interrupted | Expected for multi-step plans. Raise `AGENT_TIMEOUT_SECONDS` or use `override_settings(timeout_seconds=...)` |
| Plan has more steps than expected | The planner decomposes multi-part questions | Cap it with `MAX_PLAN_STEPS` in `.env` |
| Plan step `no_results` but the answer is still given | Other steps found evidence ("partial evidence") | Expected: the answer says which goal found nothing |
| API: `401 unauthorized` | Missing or wrong `X-API-Key` | Use a key from `API_KEYS` in `.env` (format `key:user,...`) |
| API: `429` with `Retry-After: 30` | The IP sent more than `RATE_LIMIT_PER_MINUTE` requests in a minute and is blocked | Wait `Retry-After` seconds. Tune the `RATE_LIMIT_*` settings. Behind a proxy, set `TRUST_PROXY_HEADERS=true` |
| API: `422` for `timeout_seconds` | Outside `API_TIMEOUT_MIN`..`API_TIMEOUT_MAX` | Use a value in range, or change the bounds in `.env` |
| API: `504 agent-timeout` | No result within budget + `API_TIMEOUT_GRACE` | The run may still finish: `GET /api/v1/agent/requests/{id}`. Raise `timeout_seconds` |
| API: `503 not-ready` on `/ready` | Chroma, Redis or Postgres is down | The `checks` field names it. `make stack-up` or start that service |
| API: `ConnectionRefusedError` / Postgres errors on start | Postgres not running or not migrated | `make db-up db-migrate` |
| SSE stream stops after a network drop | Client disconnected; the run continues on the server | Resume: `GET /api/v1/agent/requests/{id}/events` with `Last-Event-ID: <last id>` |
| Resume returns only `result` + `done` | The 1 h event buffer expired | Expected: the stored result is replayed from Postgres |
| `404` for a request id you know | It belongs to another user (only the owner and the admin can see it) | Use the owner's key, or the admin key |
| `/metrics` counts look low with several workers | Prometheus client is per process | Run one worker (default), or configure `prometheus_client` multiprocess mode |
| API logs not in the file | `LOG_FILE` empty or the directory isn't writable | Set `LOG_FILE` (default `logs/api.log`; in the container `/app/logs/api.log`, volume `api-logs`) |
| API: `GET /api/v1/me` returns 404 | The API container is older than 0.8.0 | `make api-up` (or `make stack-up`) rebuilds the 0.8.0 image |
| Agent runs fail fast with `agent_status: error`, and the trace shows `429 ... You have no credits remaining` | The OpenAI account is out of credits (not an API or UI bug) | Add credits or raise the quota in the OpenAI dashboard, then retry |
| Web: `make web-up` / `stack-up` fails with `cannot expose privileged port 80` or `bind: permission denied` (rootless Podman) | Unprivileged processes cannot bind ports below 1024 | Set `WEB_PORT=3000` in `.env`, or allow it: `podman machine ssh "sudo sysctl -w net.ipv4.ip_unprivileged_port_start=80"` (persist it in `/etc/sysctl.d/`) |
| Web: `port is already allocated` / `address already in use` on 80 | Another server (IIS, another container) owns port 80 | Stop it, or set `WEB_PORT=3000` and open http://localhost:3000 |
| Web: the live run shows nothing, then everything at the end | A proxy between the browser and the API buffers or compresses SSE | The bundled Nginx sets `proxy_buffering off` and does not gzip `text/event-stream`; do the same in any extra proxy (or honour `X-Accel-Buffering: no`) |
| Web: blank page or missing icons/fonts, and the console says `Refused to load ... Content Security Policy` | Something is loaded from another origin or inlined as `data:` | Keep assets self-hosted (`@fontsource`) and `assetsInlineLimit: 0` in `web/vite.config.js`; widen `web/nginx/security-headers.conf` only if really needed |
| Web: sent back to sign-in ("Your session key is no longer valid") | A call returned 401: `API_KEYS` changed or the key was rotated | Sign in with a current key from `API_KEYS` |
| Web: a new tab asks to sign in again | The key is in `sessionStorage`, which is per tab | Expected (a security choice); sign in once per tab |
| Web: `502 Bad Gateway` | Nginx cannot reach `api:8080` (the API is restarting or unhealthy) | `make api-logs`, then `make stack-up` |
| Web: Nginx exits with `host not found in upstream "api:8080"` | The web container started without the `api` service on the compose network | Start it through compose: `make web-up` or `make stack-up` |
| Web: every browser user hits the 429 limit together | The API counts the gateway's IP | Keep `TRUST_PROXY_HEADERS=true` on the `api` service (set in `compose.yaml`) |
| Web: System status shows "Admins only" | Only the `admin` role (carol) can open it | Sign in with the admin key |
| `make web-dev`: `http proxy error ... ECONNREFUSED` | No API on `localhost:8080` | `make api-run` or `make api-up`, or point Vite elsewhere with `API_TARGET=http://host:port` |
| `npm ci` warns `EBADENGINE`, or Vite says Node.js 22.12+ is required | Old Node.js | Install Node.js 22 LTS (the image build uses `node:22.22-alpine`) |
| MCP: ticket answers say "ticket service unavailable" | The agent cannot reach `MCP_SERVER_URL` (server stopped, wrong URL) | `make mcp-up` (or `make mcp-run`); in compose the api uses `http://mcp:9090/mcp`. The agent retries loading the tools after `MCP_RETRY_SECONDS` |
| MCP: `make mcp-up` fails with `port is already allocated` on 9090 | Another process uses the port | Stop it, or set `MCP_PORT` in `.env` (and `MCP_SERVER_URL` for local runs) |
| MCP: tool error `Missing X-User-Id header` / `Unknown user` | A client called the server without the demo user header | Send `X-User-Id` = `alice`, `bob` or `carol` (the agent does this automatically) |
| MCP: `Permission denied: only administrators can ...` | search, resolve and sync are admin-only | Ask as carol (`U=carol`), or sign in with the admin key in the web UI |
| Tickets stay `jira_sync=pending`, `jira_error` mentions `HTTP 401` or `403` | Wrong Jira e-mail/token pair, or the token lacks access to the project | Set `ATLASSIAN_EMAIL` to the token owner's e-mail and check the token; then `sync_pending_tickets` (or wait for the background loop) |
| `jira_error`: `Jira is not configured` | `ATLASSIAN_SITE_URL`, `ATLASSIAN_EMAIL` or `ATLASSIAN_API_TOKEN` is empty | Fill them in `.env` and restart the MCP server |
| `jira_error`: `No 'Resolved' transition for KAN-n (available: ...)` | The project workflow names the transition differently | Set `JIRA_RESOLVE_TRANSITION` to one of the listed names |
| `jira_error`: `HTTP 400 ... priority` or `issuetype` | The project's screen lacks that field or issue type | Use an issue type the project has (`JIRA_ISSUE_TYPE`), or add Priority to its create screen |
| `relation "itsm.tickets" does not exist` | The itsm migrations have not run | `make mcp-migrate` (the MCP container also runs them on start) |
| `uv add fastmcp` fails: `fastmcp==4.x ... and langchain-mcp-adapters ... are incompatible` | fastmcp 4 needs mcp 2.x; `langchain-mcp-adapters` 0.3 needs mcp 1.x | Stay on `fastmcp` 3.x (pinned 3.4.11) until the adapters support mcp 2 |
| `make publish`: `unauthorized: incorrect username or password` | `DOCKERHUB_TOKEN` is wrong or expired, or `DOCKERHUB_USERNAME` doesn't own it | Create a new access token on hub.docker.com (Account settings > Personal access tokens) and update `.env` |
| `make publish`: `requested access to the resource is denied` | Pushing to a namespace the token can't write | Use your own user: `make publish HUB_USER=<you>` (and `-var hub_user=` is passed to Terraform by make) |
| `make iac-*`: `No valid credential sources found` / `InvalidClientTokenId` | The AWS variables are missing or misnamed in `.env` | Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (standard name) and `AWS_REGION` |
| `make iac-up`: `Volume netcore-rag_chroma-data not found` | The local knowledge base has never been populated | `make up-all` locally first (or `make populate`) |
| `make iac-up` hangs at `terraform_data.deploy: Still creating` for several minutes | First boot: cloud-init is still installing Docker CE (about 1-2 min), then the images are pulled | Wait; up to 10 minutes is normal on a slow pull. Details: `make iac-ssh CMD="sudo tail -50 /var/log/cloud-init-output.log"` |
| `make iac-up`: `timeout - last error: dial tcp ...:22: i/o timeout` | Your public IP changed since the security group was created | `make iac-up` again (it re-detects the IP), or set `ssh_cidr` |
| `make iac-ssh`: `UNPROTECTED PRIVATE KEY FILE` / `bad permissions` | The key file is readable by other users | `iac/ssh.py` fixes it with `icacls` (Windows) or `chmod 600`; for a manual `ssh -i`, run it yourself |
| `make iac-ssh` does nothing inside the TUI | Interactive SSH needs a real terminal | Use `CMD=...` in the TUI form, or run `make iac-ssh` in a terminal |
| Web on EC2 shows 502 / containers restart (`docker ps`: `Restarting`, `dmesg`: `Out of memory`) | Memory pressure on the 2 GiB instance | Check `free -m`; raise `mem_limit` in `iac/compose.prod.yaml` or use `-var instance_type=t3.medium` |
| Agent answers on EC2 say "no reliable information" | The remote Chroma volume is empty or older than your local one | `make iac-prepare CHROMA_REFRESH=1`, delete the remote volume (`CMD="cd /opt/netcore && docker compose down && docker volume rm netcore-rag_chroma-data"`), then `make iac-up` |
| `deploy.sh: $'\r': command not found` on the instance | The script was checked out with CRLF line endings | `.gitattributes` keeps `*.sh` LF; the provisioner also strips `\r` before running it |
| `make` uses the wrong engine | Both Docker and Podman installed | `make <target> ENGINE=podman` (or `ENGINE=docker`) |
| `podman-compose: command not found` | Not installed | `uv tool install podman-compose` (>= 1.3) |
| Podman: `Cannot connect to Podman` (Windows/macOS) | The Podman machine isn't running | `podman machine init` (once), then `podman machine start` |
| Podman asks which registry to use | Short image names | `compose.yaml` and `Containerfile` use fully-qualified `docker.io/...` names; keep it that way |
| Podman image has no health status | OCI image format drops `HEALTHCHECK` | `make api-build` passes `--format docker`; `compose.yaml` also defines the healthcheck |
| `container name "netcore-chroma" is already in use` | Containers from the archived `docker-compose.yml` are still there | `docker rm -f netcore-chroma netcore-redis` (or `podman rm -f ...`), then `make bootstrap` |
| Vector DB empty after switching to `compose.yaml` | Named volumes replaced the `./chroma-data` bind mount | `make populate assign-access-levels` (or `make bootstrap`). The old `./chroma-data` folder can be deleted |
| API image size (~650 MB, ~140 MB compressed) | Runtime dependencies (LangChain, OpenAI, numpy, SQLAlchemy, ...) | Already slimmed: thin Chroma client, no RAGAS, no KB-only packages, stripped test suites and debug symbols |
| `ImportError` for an embedded-Chroma feature | The project uses `chromadb-client` (HTTP only), not the full `chromadb` package | Expected: always talk to the Chroma server (`make chroma-up`) |
