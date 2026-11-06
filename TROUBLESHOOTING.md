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
| Client/server version errors from Chroma | The `chromadb` client and the image tag differ | Keep the `docker-compose.yml` image tag equal to the `chromadb` version in `uv.lock` |
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
| `ModuleNotFoundError: langchain_community.chat_models.vertexai` (RAGAS) | RAGAS still imports a module removed in langchain-community 0.4 | The project pins `langchain-community==0.3.31`. Don't upgrade it until RAGAS drops that import |
| RAGAS: `'max_tokens' is not supported ... use 'max_completion_tokens'` | RAGAS doesn't recognise model names like `gpt-6.1-sol` as reasoning models | Handled in `agentic_rag/judge.py` (parameters set explicitly) |
| RAGAS: `IncompleteOutputException ... max_tokens length limit` | The reasoning tokens used up the output limit | `judge.py` uses `max_completion_tokens=16000` with `reasoning_effort="low"` |
| Agent: Redis `ConnectionError` | Redis isn't running | `make redis-up` |
| Guest gets "no information" for internal topics | RBAC: guests only see `public` chunks | Expected. Ask as `U=bob` or `U=carol` |
| `access_level` missing (no results with an RBAC filter) | Metadata wasn't patched | `make assign-access-levels` (new `make populate` runs include it) |
| Status `timeout` | The request exceeded `AGENT_TIMEOUT_SECONDS` | Raise the budget in `.env`. The judge takes ~20–40 s per round |
| `GraphRecursionError` | Too many graph steps | The agent uses `recursion_limit=300`; real loops are capped by `ModelCallLimitMiddleware` and `MAX_REWRITES` |
| Answers differ between runs | LLM routing, rewriting and judging are non-deterministic | Expected. The path (trace) is what to compare |
| `Task exception was never retrieved ... Event loop is closed` | The judge's async OpenAI client was closed after its event loop | Fixed in `judge.py` (the client is closed inside the loop). Restart the notebook kernel to load the fix |
| Plan mode takes longer than `AGENT_TIMEOUT_SECONDS` | The budget is only checked between steps; a running LLM call (synthesis, judge) isn't interrupted | Expected for multi-step plans. Raise `AGENT_TIMEOUT_SECONDS` or use `override_settings(timeout_seconds=...)` |
| Plan has more steps than expected | The planner decomposes multi-part questions | Cap it with `MAX_PLAN_STEPS` in `.env` |
| Plan step `no_results` but the answer is still given | Other steps found evidence ("partial evidence") | Expected: the answer says which goal found nothing |
