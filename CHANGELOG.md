# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/).

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
