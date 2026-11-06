# NetCore KB Generator

Generates a realistic, **synthetic** knowledge base for an Enterprise RAG / Agentic AI course. It covers two domains, and each domain feeds its own vector database:

| Domain | Product (fictional) | Topics |
|---|---|---|
| `networking` | NetCore SD-WAN | SLA classes, SLA breach policies, BFD, ZTP, QoS, alarm codes |
| `meetings` | NetCore Meet / NetCore Calling | SSO, dial plans, calling features, recording policy, help articles, error codes |

The generator writes 10 articles per domain, spread evenly across **PDF, HTML and Markdown**, and adds a `manifest.json` per domain.

> "NetCore Systems" and all of its products, codes and values are fictional.

## Quick Start

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), GNU make, Docker, an OpenAI API key.

```bash
cp .env.example .env      # then set OPENAI_API_KEY (and review the other settings)
make install              # uv sync
make generate             # 1. write missing KB articles to data/raw/
make verify               #    load every article with LangChain loaders
make chroma-up            # 2. start the Chroma server (docker compose)
make populate             #    Pre-RAG pipeline -> one Chroma database per domain
make db-stats             #    check what was stored
```

## Make Targets

| Target | What it does |
|---|---|
| `make help` | List targets (default) |
| `make install` | Sync dependencies |
| `make generate` | Generate missing articles for both domains (skips existing files) |
| `make generate-networking` / `make generate-meetings` | Generate one domain only |
| `make regenerate` | Overwrite all 20 articles (20 LLM calls) |
| `make verify` | Smoke-test loading, KB IDs and vendor-name leaks |
| `make clean` / `make clean-data` | Remove caches / delete `data/raw` |
| `make chroma-up` / `chroma-down` / `chroma-logs` | Start / stop / follow the Chroma server |
| `make chroma-reset` | Stop the server and delete `./chroma-data` |
| `make populate` | Run the Pre-RAG pipeline for both domains (upserts, safe to re-run) |
| `make populate-networking` / `populate-meetings` | Populate one database |
| `make db-stats` | Chunk counts by type/format/status, plus sample metadata |
| `make test-query` | DB info, then similarity, keyword, metadata-filter, hybrid and cross-domain demos |
| `make query Q="..." [D=meetings]` | Ad-hoc query: similarity, BM25 and hybrid results |
| `make redis-up` / `redis-down` | Start / stop the Redis Stack semantic cache |
| `make assign-access-levels` | Patch RBAC `access_level` into the Chroma metadata (no re-embedding) |
| `make agent-ask Q="..." U=bob [M=react]` | Ask the agentic RAG agent as a demo user, with a live trace (default `M=plan`) |

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
| Judge | RAGAS faithfulness, groundedness and context precision (`JUDGE_OPENAI_MODEL`). Failures escalate: regenerate, then re-retrieve, then a disclaimer |
| Output guardrails | PII, citations, LLM toxicity/policy check, plus built-in `PIIMiddleware` redaction. A failing answer is regenerated once, then refused |
| Cross-cutting | `ModelRetryMiddleware` / `ToolRetryMiddleware` (exponential backoff), `ModelCallLimitMiddleware`, `TimeoutMiddleware` (`AGENT_TIMEOUT_SECONDS`) |

**Two modes** (`ask(..., mode=...)`, `make agent-ask M=...`):

| Mode | How it retrieves |
|---|---|
| `plan` (default) | **Plan-and-Execute**: the planner (`OPENAI_MODEL`) writes up to `MAX_PLAN_STEPS` retrieval steps, and the plan is **shown** before it runs. A deterministic executor then runs each step (KB / web / federated → rerank). A step that finds nothing triggers a **re-plan** (counts as a rewrite, max 3), then a web fallback, then "no info". The model only writes the final answer. A 2nd judge failure triggers a re-plan with the judge's feedback |
| `react` | The agent routes with tools (`search_*`, `rewrite_query`) under `CorrectiveRAGMiddleware` |

RBAC: `access_level` is derived from `article_type` (faq/help = public; config/runbook/reference = internal; policy = restricted). guest sees public; employee sees public + internal; admin sees everything.

Test scenarios: [notebooks/agentic-rag.ipynb](notebooks/agentic-rag.ipynb) (scenarios only; all code lives in the package).

The reusable retrieval functions live in [scripts/rag_search.py](scripts/rag_search.py): `similarity_search`, `keyword_search`, `hybrid_search`, `search`, `get_retriever` (a LangChain `BaseRetriever`), `format_docs` and `show_results`. Smoke test: `uv run scripts/rag_search.py`.

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
chroma-data/                    Chroma server data (git-ignored)
docs/plans/                     planning notes
scripts/generate_kb.py          KB generator
scripts/verify_kb.py            loader smoke test
scripts/populate_vector_dbs.py  Pre-RAG pipeline -> Chroma
scripts/test_query_vector_dbs.py  query demos (similarity, keyword, filters, hybrid)
scripts/rag_search.py           reusable retrieval functions + LangChain retriever
notebooks/naive-rag.ipynb       Naive RAG walkthrough
scripts/agentic_rag/            Enterprise Agentic RAG agent (package)
scripts/assign_access_levels.py RBAC access_level metadata patch
notebooks/agentic-rag.ipynb     Agentic RAG test scenarios
redis-data/                     Redis cache data (git-ignored)
docker-compose.yml              Chroma server
Makefile                        command entry points
```

## Documentation

[TROUBLESHOOTING](TROUBLESHOOTING.md) · [CHANGELOG](CHANGELOG.md) · [CONTRIBUTING](CONTRIBUTING.md) · [CODE OF CONDUCT](CODE_OF_CONDUCT.md) · [SECURITY](SECURITY.md)

## License

[MIT](LICENSE) © 2026 Ramkumar
