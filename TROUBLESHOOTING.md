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
| `make` uses the wrong engine | Both Docker and Podman installed | `make <target> ENGINE=podman` (or `ENGINE=docker`) |
| `podman-compose: command not found` | Not installed | `uv tool install podman-compose` (>= 1.3) |
| Podman: `Cannot connect to Podman` (Windows/macOS) | The Podman machine isn't running | `podman machine init` (once), then `podman machine start` |
| Podman asks which registry to use | Short image names | `compose.yaml` and `Containerfile` use fully-qualified `docker.io/...` names; keep it that way |
| Podman image has no health status | OCI image format drops `HEALTHCHECK` | `make api-build` passes `--format docker`; `compose.yaml` also defines the healthcheck |
| `container name "netcore-chroma" is already in use` | Containers from the archived `docker-compose.yml` are still there | `docker rm -f netcore-chroma netcore-redis` (or `podman rm -f ...`), then `make bootstrap` |
| Vector DB empty after switching to `compose.yaml` | Named volumes replaced the `./chroma-data` bind mount | `make populate assign-access-levels` (or `make bootstrap`). The old `./chroma-data` folder can be deleted |
| API image size (~650 MB, ~140 MB compressed) | Runtime dependencies (LangChain, OpenAI, numpy, SQLAlchemy, ...) | Already slimmed: thin Chroma client, no RAGAS, no KB-only packages, stripped test suites and debug symbols |
| `ImportError` for an embedded-Chroma feature | The project uses `chromadb-client` (HTTP only), not the full `chromadb` package | Expected: always talk to the Chroma server (`make chroma-up`) |
