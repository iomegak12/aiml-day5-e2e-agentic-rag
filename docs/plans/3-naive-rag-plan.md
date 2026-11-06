# Plan: Naive RAG Notebook + Reusable Search Module

## Context
The two Chroma databases (`networking_kb`, `meetings_kb`) are populated and the search techniques work (see `scripts/test_query_vector_dbs.py`). The next step is to show **Naive RAG** end to end: retrieve, build context, prompt with system instructions, generate with the LLM. This follows the "2-step RAG" pattern in the LangChain docs: retrieval always runs first, then a single LLM call.

## Decisions (from the MCQs)
| Topic | Decision |
|---|---|
| Module | `scripts/rag_search.py`: functions **plus** a retriever factory |
| Keyword search | BM25 (ranked, can be fused) |
| Routing | The caller picks `domain` (networking / meetings) |
| Defaults | `k=4`, hybrid weights 0.5/0.5 (RRF) |
| Notebook env | `ipykernel` as a dev dependency (VS Code notebook UI) |
| Imports | First cell adds `<project>/scripts` to `sys.path` |
| RAG style | Step-by-step first (show the context and prompt), then the same flow as an LCEL chain |
| Answer rules | Answer only from context, otherwise "not in the KB"; cite `[KB-ID, page/section/table]`; flag superseded sources; stream the answer |
| Demos | LLM alone vs with RAG; similarity vs keyword vs hybrid; `status=current` filter; out-of-scope question |
| test_query script | Left unchanged |
| Notebook outputs | Executed once to validate, then saved **without** outputs |

## `scripts/rag_search.py` (new)
Reuses `load_config` and `http_client` from [scripts/populate_vector_dbs.py](scripts/populate_vector_dbs.py) and the patterns from [scripts/test_query_vector_dbs.py](scripts/test_query_vector_dbs.py) (tokenizer, BM25, EnsembleRetriever).
- `get_vector_store(domain)`: cached `Chroma` built on `HttpClient` with `OpenAIEmbeddings`.
- `similarity_search(query, domain, k=4, filter=None)` returns `[(Document, relevance)]`. The distance is also stored in metadata.
- `keyword_search(query, domain, k=4, filter=None)` returns `[(Document, bm25_score)]`. The BM25 corpus is cached per domain and filter, and comes from `collection.get(where=filter)`.
- `hybrid_search(query, domain, k=4, weights=(0.5, 0.5), filter=None)` returns `[(Document, rrf_score)]` using `EnsembleRetriever`, and records `bm25_rank` and `vector_rank` in metadata.
- `KBRetriever(BaseRetriever)` takes `mode` (similarity / keyword / hybrid), `domain`, `k` and `filter`. Its `invoke(q)` returns docs with `score` and `search_type` in metadata. `get_retriever(...)` is a convenience factory.
- `format_docs(docs) -> str` produces numbered source blocks: `[Source n] KB-ID | title | product version | status | page/section/table`, followed by the content.
- `show_results(results)` prints a rich table (rank, score, KB ID, type, status, location, snippet).

## `notebooks/naive-rag.ipynb` (new)
1. **Intro** (markdown): the Naive RAG flow, with a diagram in text.
2. **Setup**: `sys.path`, `.env`, imports, and a printout of the configuration (chat model, embedding model, Chroma endpoint, databases).
3. **Retrieval building blocks**: one query each through similarity, keyword and hybrid (`show_results`).
4. **Context**: `format_docs` output.
5. **Prompt**: system instructions (the answer rules above) as a `ChatPromptTemplate`, and the rendered messages printed.
6. **Step-by-step RAG**: retrieve, then context, then prompt, then `ChatOpenAI(OPENAI_MODEL).invoke`, then print the answer.
7. **LCEL chain**: `build_rag_chain(retriever)` defined in the notebook, i.e. `{"context": retriever | format_docs, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser()`, run with `.stream()`.
8. **Demos**:
   - a. LLM alone vs RAG: "When does an SLA breach escalate to Sev1?"
   - b. Similarity vs keyword vs hybrid: "What should I do for MTG-JOIN-1007?" with the retrieved KB IDs and the answers compared
   - c. Filter: "How long are cloud recordings retained?", with no filter vs `status=current` (4.2 vs 5.0 conflict)
   - d. Out of scope: e.g. "How do I configure BGP route reflectors?", which should get "not in the KB"
9. **Takeaways** (markdown): the limitations of Naive RAG, as a lead-in to Advanced RAG.

## Other changes
- `uv add --dev ipykernel`
- Makefile: no new targets (none were requested)
- README (a notebook section), CHANGELOG 0.4.0, TROUBLESHOOTING (kernel selection, Chroma must be running)

## Verification
1. Unit-style smoke test of `rag_search` from the CLI: each search mode for both domains returns k results with scores.
2. Execute the notebook headless (`uv run --with nbconvert jupyter nbconvert --execute`, temporary output) and check that every cell succeeds, the answers cite KB IDs, the filter demo changes the sources, and the out-of-scope demo says "not in the KB".
3. Keep `notebooks/naive-rag.ipynb` saved without outputs.
