# Plan: Pre-RAG Pipeline: `scripts/populate_vector_dbs.py` → Chroma Server

## Context
The KB corpus (20 articles, PDF/HTML/MD) exists in `data/raw/<domain>/`, along with a `manifest.json` per domain. The next step is the Pre-RAG pipeline from the instructor's diagram: read, chunk, add metadata, embed, and store in a **Chroma server**, with one database per domain. `.env` already has `OPENAI_API_KEY`, `OPENAI_MODEL` and `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`. Docker 29.8 and Compose v5.5 are available.

## Decisions (from the MCQs)
| Topic | Decision |
|---|---|
| Chroma layout | 2 **databases** (`networking_kb`, `meetings_kb`), 1 collection each (`kb_articles`) |
| Readers | `PyPDFLoader`, `UnstructuredHTMLLoader`, `UnstructuredMarkdownLoader` (langchain-community) |
| Chunking | `RecursiveCharacterTextSplitter` with 3000 chars / 200 overlap (configurable in `.env`) |
| Tables/code | Detected per format; **LLM-generated** description stored as **separate chunks** (`content_type=table\|code`) with document/page/table references. Tables and code are also kept inside the text chunks |
| PDF tables/code | `pdfplumber`: tables via `extract_tables()`, code via Courier-font lines |
| Metadata | Parsed from each file (MD frontmatter / HTML `<meta>` / PDF keywords), falling back to `manifest.json`. Adds `product_family`: Networking / Collaboration |
| Re-runs | Upsert with deterministic IDs (stale chunks of a KB ID are removed first) |
| Server | docker compose, bind mount `./chroma-data`, no auth |
| KB folder | `KB_DATA_DIR=data/raw` with domain subfolders |

## Files
- **New** `scripts/populate_vector_dbs.py` (single file):
  1. `load_config()`: reads `.env`.
  2. `read_documents(domain)`: runs the loader for each format and merges metadata (file first, then manifest). Strips MD frontmatter from the text.
  3. `extract_tables_and_code(path)`:
     - MD: regex for pipe tables and code fences
     - HTML: BeautifulSoup on `<table>` and `<pre>`
     - PDF: pdfplumber per page
     - Each item records kb_id, page, table/code index and caption.
  4. `describe_items()`: `ChatPromptTemplate | ChatOpenAI` run with `.batch()` (concurrency). Each chunk's content is `[ref header] + description + raw table/code`.
  5. `chunk_text()`: `RecursiveCharacterTextSplitter(add_start_index=True)`.
  6. `ensure_database()`: `chromadb.AdminClient` → `create_database` if missing.
  7. Store: `chromadb.HttpClient(tenant, database)` → `langchain_chroma.Chroma(client, collection_name, OpenAIEmbeddings)`.
  8. Write: delete the KB ID's old chunks, then `add_documents(ids=...)`.
  9. CLI: `--domain {networking,meetings,all}`, `--stats`.
  - Chunk metadata is scalar only, with lists comma-joined: kb_id, title, domain, product, product_family, article_type, version, status, superseded_by, last_updated, error_codes, related, tags, source_file, file_format, content_type, chunk_index, page, item_index, caption.
- **New** `docker-compose.yml`: `chromadb/chroma:<version matching the installed chromadb client>`, port `${CHROMA_PORT}`, `./chroma-data` bind mount, telemetry off, healthcheck.
- **New** `.dockerignore`: `.env`, `.venv`, `data/`, `chroma-data/`, caches, `.git`.
- **Edit** `.env` and `.env.example`: append `KB_DATA_DIR`, `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_TENANT`, `CHROMA_DB_NETWORKING`, `CHROMA_DB_MEETINGS`, `CHROMA_COLLECTION`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `DESCRIBE_CONCURRENCY`. Existing keys stay untouched.
- **Edit** `Makefile`: `chroma-up`, `chroma-down`, `chroma-logs`, `chroma-reset`, `populate`, `populate-networking`, `populate-meetings`, `db-stats`, and update `help`.
- **Edit** `.gitignore` (add `chroma-data/`), `pyproject.toml` (deps via `uv add`), README, TROUBLESHOOTING and CHANGELOG (short additions).

Dependencies (latest, via `uv add`): `langchain-community langchain-chroma langchain-text-splitters chromadb pypdf pdfplumber "unstructured[md]" beautifulsoup4 lxml`. During implementation I'll check the installed APIs with `inspect` (AdminClient, Chroma ctor, upsert behaviour) and the Chroma image's data path.

## Risks / Notes
- `unstructured` is heavy and may download NLTK data on first run. I'll document this in TROUBLESHOOTING.
- `langchain-community` prints a sunset deprecation warning. It is kept, as requested.

## Verification
1. `make chroma-up`, then check the healthcheck / heartbeat.
2. `make populate`: both domains, about 65 description LLM calls plus embeddings.
3. `make db-stats`: chunk counts per DB split by content_type, plus sample metadata.
4. Run `make populate` again: the counts must stay the same (no duplicates).
5. Run a sample similarity search per DB (e.g. "NCS-SLA-2001 escalation", "MTG-JOIN-1007"). It should return relevant chunks with page/table references.
