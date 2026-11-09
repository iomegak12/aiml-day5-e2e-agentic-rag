# Phase 2 – Pre-RAG pipeline: populate and query the vector DBs

Your prompts (lightly cleaned), the MCQ clarifications with every option ([x] = your choice), and a one-line outcome.

## Prompt 1

> Can you refer to the attached image to understand how to prepare the Pre-RAG data-engineering pipeline? Let me know what you have understood at a high level (bullet points with item titles only).
>
> *(Attached: the Pre-RAG pipeline diagram.)*

**Outcome:** Summarised the diagram as 10 titled steps (connector → readers → chunking → metadata → embeddings → Chroma collections), plus the open questions to settle.

---

## Prompt 2

> Based on that understanding, I would like to design a script named `scripts\populate_vector_dbs.py` with the following capabilities:
>
> - The KB articles folder should be configurable through `.env`, so the articles can be loaded.
> - Use LangChain and LangChain Community features: PDF, HTML and Markdown readers.
> - Generate document-specific metadata, including product title and family information.
> - Use a Chroma DB server, with a separate database for each of the two domains.
> - Make it configurable in the `.env` file.
> - A `.dockerignore`.
> - Docker Compose to start the Chroma DB server.
> - `.env` should have the port and host settings.
> - Size-based chunking (3000 characters, 200-character overlap).
> - If tables or code are present in a document, generate an appropriate text description with document, page and table references.
> - I have already provided the `.env` setting for the embedding model (text-embedding-3-small).
> - Update the Make targets.
>
> Do you understand all my requirements? Let's have an MCQ-style Q&A for our debate, so we are both aligned.

### Clarifications

#### Round 1

**A Chroma server is organised as tenant → database → collection. How should the two domains be separated?** _(Chroma layout)_

- [x] **2 databases, 1 collection each** – e.g. DB 'networking_kb' → collection 'kb_articles'; DB 'meetings_kb' → collection 'kb_articles'
- [ ] 1 database, 2 collections – Matches the diagram: one Chroma DB holding the 'WebEx KB' and 'Product Family KB' collections
- [ ] 2 databases, named collections – Separate DBs, plus collection names you choose

**How should the table/code text descriptions be generated?** _(Table/Code)_

- [x] **LLM-generated** – OPENAI_MODEL writes a short natural-language description of each table/code block (~60-100 LLM calls)
- [ ] Rule-based template – No LLM: 'Table 2 on page 3 of KB-NET-1002 (caption) has columns A, B, C with N rows...'
- [ ] Hybrid – Template for references plus an LLM summary of the content

**Where should the table/code descriptions go?** _(Placement)_

- [x] **Separate chunks** – Description + raw table/code stored as its own Document (content_type=table|code), with doc/page/table refs in metadata
- [ ] Inline in text – Description inserted next to the table/code inside the normal text before chunking
- [ ] Both – Inline, plus a separate dedicated chunk

**PyPDFLoader cannot detect tables or code. How should tables and code be detected in PDFs?** _(PDF tables)_

- [x] **pdfplumber (Recommended)** – Detects tables and Courier-font code blocks per page; adds one dependency. PyPDFLoader is still used for the page text
- [ ] PyMuPDF – Fast and capable, but AGPL-licensed
- [ ] Text heuristics only – No extra dependency; less accurate

#### Round 2

**"Product family" metadata: which values should each domain carry?** _(Family)_

- [x] **Networking / Collaboration** – networking → family 'Networking' (product NetCore SD-WAN); meetings → family 'Collaboration' (NetCore Meet / Calling)
- [ ] SD-WAN / Meetings & Calling – Family names closer to the product lines
- [ ] I'll define them – You'll give me exact family names and per-product values

**Which size-based splitter should be used (3000 chars, 200 overlap)?** _(Splitter)_

- [x] **RecursiveCharacterTextSplitter** – Size-based, but prefers paragraph/line breaks before cutting (LangChain default)
- [ ] CharacterTextSplitter – Strict size-based split on a single separator

**What should happen when the populate script is re-run?** _(Re-runs)_

- [x] **Upsert (deterministic IDs)** – Same chunk → same ID, so no duplicates; changed chunks are updated
- [ ] Drop & recreate – Delete the collection and rebuild from scratch every run
- [ ] Upsert + --reset flag – Upsert by default; --reset rebuilds from scratch

**How should the Chroma server's data be persisted in docker compose?** _(Persistence)_

- [x] **Bind mount ./chroma-data** – Visible in the project folder (git-ignored); easy for students to inspect or delete
- [ ] Named docker volume – Managed by Docker; survives 'compose down'

#### Round 3

**How should the KB source folders be configured in .env?** _(KB folders)_

- [x] **One root + domain subfolders** – KB_DATA_DIR=data/raw → reads data/raw/networking and data/raw/meetings
- [ ] One variable per domain – NETWORKING_KB_DIR=..., MEETINGS_KB_DIR=...

**Where should document metadata (kb_id, version, status, error codes...) come from?** _(Meta source)_

- [ ] Parse each file – MD frontmatter, HTML <meta> tags, PDF keywords; no dependency on the manifest
- [ ] manifest.json join – Look up by file name; simplest
- [x] **File first, manifest fallback** – Most robust

**Should the Chroma server require authentication?** _(Chroma auth)_

- [x] **No auth** – Localhost classroom demo; simplest
- [ ] Token auth – CHROMA_AUTH_TOKEN in .env; more 'enterprise-like'

**Which new Make targets do you want? (multi-select)** _(Make targets, multi-select)_

- [x] **chroma-up / down / logs** – docker compose lifecycle for the Chroma server
- [x] **populate variants** – populate (both), populate-networking, populate-meetings
- [x] **db-stats** – Print chunk counts and sample metadata per DB
- [x] **chroma-reset** – Stop the server and delete ./chroma-data

#### Round 4

**Tables/code get their own description chunks. What should happen to the same tables/code inside the normal text chunks?** _(Duplication)_

- [x] **Keep in text chunks** – Text chunks stay faithful to the source; tables/code also appear in their own chunks
- [ ] Replace with a placeholder – e.g. '[Table 2: see table chunk]'; less duplication, but needs custom parsing per format

**Which Markdown reader should be used (langchain-community)?** _(MD reader)_

- [ ] TextLoader (Recommended) – Lightweight; frontmatter parsed by our own code
- [x] **UnstructuredMarkdownLoader** – Element-aware, but pulls in the heavy 'unstructured' dependency

**Which HTML reader should be used (langchain-community)?** _(HTML reader)_

- [ ] BSHTMLLoader (Recommended) – BeautifulSoup-based; also lets us read <meta>, <table>, <pre>
- [x] **UnstructuredHTMLLoader** – Heavy 'unstructured' dependency

**After implementing, may I run the full populate as a test (about 65 LLM calls plus embeddings, a few cents)?** _(Test run)_

- [x] **Yes, run it** – Start Chroma, populate both DBs, run db-stats
- [ ] No, only dry checks – I'll run it myself

**Outcome:** Built `scripts/populate_vector_dbs.py` and the Chroma server compose file; populated `networking_kb` (96 chunks) and `meetings_kb` (97 chunks) with table/code descriptions; re-runs don't duplicate.

---

## Prompt 3

> Can you generate a script named `scripts\test_query_vector_dbs.py` that first displays information about the Chroma DB connection, databases and other details, and also:
> - executes sample queries that return results with ranks and scores
> - demonstrates keyword search
> - demonstrates similarity search
> - demonstrates metadata filtering
>
> Do you get my test-specific requirements? You can ask me questions if you want.

### Clarifications

#### Round 1

**How should keyword search be demonstrated?** _(Keyword)_

- [x] **Both (Recommended)** – Chroma's native where_document $contains (exact match, unranked) plus BM25Retriever (ranked lexical, adds rank-bm25). Shows the contrast
- [ ] Chroma $contains only – Native server-side full-text filter; no extra dependency; no scores
- [ ] BM25 only – LangChain BM25Retriever over the chunks pulled from Chroma; ranked with BM25 scores

**Which similarity scores should be shown? (The collections use Chroma's default L2 distance.)** _(Scores)_

- [x] **Both distance & relevance** – Raw distance (lower = better) and LangChain's normalised relevance score 0-1 (higher = better)
- [ ] Relevance only – similarity_search_with_relevance_scores
- [ ] Distance only – similarity_search_with_score

**Where should the sample queries come from?** _(Queries)_

- [x] **Built-in + CLI override** – Curated samples per domain; --query "..." --domain to try your own
- [ ] Built-in only – Fixed, repeatable demo
- [ ] Interactive prompt – Ask for queries at runtime (REPL)

**How should the output be formatted?** _(Output)_

- [x] **rich tables (Recommended)** – Coloured tables and panels via the 'rich' library; good on a projector
- [ ] Plain print – No extra dependency

#### Round 2

**Which metadata-filtering scenarios should be shown? (multi-select)** _(Filters, multi-select)_

- [x] **status=current** – Exclude superseded 4.2 articles (the SLA conflict: same query with and without the filter)
- [x] **content_type=table|code** – Search only table/code description chunks
- [ ] Combined $and / $in – e.g. article_type=runbook AND file_format in [md, pdf]
- [x] **kb_id / version** – Scope to one article or a release

**Should the script also demonstrate extra retrieval techniques? (multi-select; pick none to skip)** _(Extras, multi-select)_

- [x] **Hybrid (BM25 + vector)** – EnsembleRetriever-style fusion (RRF) of keyword and vector results
- [ ] MMR – Max-marginal-relevance search for diverse results
- [x] **Cross-domain query** – Same query against both DBs to show the domain separation

**How many results (k) should each query return?** _(Top-k)_

- [x] **k=3** – Compact on screen
- [ ] k=5 – More context for ranking discussion
- [ ] Configurable --k (default 3) – CLI flag

**Which Make targets should be added? (multi-select)** _(Make, multi-select)_

- [x] **test-query** – Run all demos
- [ ] per-section targets – test-info, test-similarity, test-keyword, test-filter (via --section)
- [x] **query Q="..."** – Ad-hoc query: make query Q="MTG-JOIN-1007" D=meetings

#### Round 3

**How should the hybrid (BM25 + vector) search be implemented?** _(Hybrid impl)_

- [x] **EnsembleRetriever** – LangChain's built-in (langchain-classic) weighted RRF; idiomatic, less visible maths
- [ ] Manual RRF (~15 lines) – Explicit Reciprocal Rank Fusion; students see per-source ranks and the fused score

**Design: scripts/test_query_vector_dbs.py with sections 1) Connection & DB info (heartbeat, version, tenant, databases, collection, count, metadata keys), 2) Similarity (rank, distance, relevance), 3) Keyword ($contains vs BM25), 4) Metadata filters (status=current, content_type, kb_id/version), 5) Hybrid, 6) Cross-domain. k=3, rich output, --query/--domain override, Make targets test-query and query Q=... D=... Approve?** _(Approve)_

- [x] **Approve, generate & run** – Generate it, add the deps (rich, rank-bm25), and run it against the live Chroma
- [ ] Approve, generate only – Don't run it
- [ ] Changes needed – Tell me what to change

**Outcome:** Added `scripts/test_query_vector_dbs.py` (connection info, similarity, keyword/BM25, metadata filters, hybrid, cross-domain) plus `make test-query` and `make query`.
