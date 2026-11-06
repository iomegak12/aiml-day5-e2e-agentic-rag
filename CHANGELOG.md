# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/).

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
