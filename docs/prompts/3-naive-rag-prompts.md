# Phase 3 – Naive RAG

Your prompts (lightly cleaned), the MCQ clarifications with every option ([x] = your choice), and a one-line outcome.

## Prompt 1

> Great. Now I would like to try how Naive RAG really works with the vector databases prepared above.
>
> Please follow these guidelines:
> - Create a Jupyter notebook at `notebooks\naive-rag.ipynb`.
> - Referring to the LangChain documentation, create reusable functions for similarity search, keyword search and a hybrid search that combines both, and keep them in the `scripts\` folder.
> - Import those functions in the notebook.
> - Demonstrate a variety of RAG searches (refer to `scripts\test_query_vector_dbs.py` for samples).
> - Using the `.env` settings, prepare the context and prompt with appropriate system instructions to show that RAG really works with the LLM.
>
> Do you get my points? Ask me questions so we're both clear on what we want to develop.

### Clarifications

#### Round 1

**What should the reusable search module return?** _(Module API)_

- [x] **Functions + Retrievers** – similarity_search / keyword_search / hybrid_search return (Document, score) lists, plus get_retriever(mode) returning a LangChain Retriever for LCEL chains
- [ ] Functions only – Plain functions returning ranked Documents with scores in metadata
- [ ] Retrievers only – LangChain BaseRetriever objects (invoke(query) -> docs)

**Which keyword search method should the reusable function use?** _(Keyword)_

- [x] **BM25 (Recommended)** – Ranked, so it can be fused into hybrid search; same as the test script
- [ ] BM25 + $contains option – method='bm25' | 'contains' parameter

**How should a query be routed to a domain database?** _(Routing)_

- [x] **Caller picks domain** – domain='networking' | 'meetings' argument (true Naive RAG)
- [ ] Search both & merge – Query both DBs and merge by score
- [ ] Both – domain argument, with 'all' searching both

**How should the notebook environment be set up?** _(Jupyter)_

- [x] **ipykernel (dev dep)** – Run inside VS Code's notebook UI with the project .venv
- [ ] jupyterlab + ipykernel – Also adds a `make notebook` target that launches JupyterLab

#### Round 2

**How should the RAG flow be shown in the notebook?** _(RAG style)_

- [x] **Step-by-step, then LCEL** – First show retrieve -> context -> prompt -> LLM explicitly (printing context and prompt), then the same as an LCEL chain
- [ ] Step-by-step only – Most transparent
- [ ] LCEL chain only – Most idiomatic

**Which demos should the notebook include? (multi-select)** _(Demos, multi-select)_

- [x] **LLM without vs with RAG** – LLM alone can't know the fictional NetCore facts; RAG grounds it
- [x] **Similarity vs keyword vs hybrid** – Same question answered with each retrieval mode, with the retrieved context compared
- [x] **Metadata filter (status=current)** – Superseded 4.2 vs 5.0 conflict, with and without the filter
- [x] **Out-of-scope question** – System prompt makes it say 'not in the KB' instead of hallucinating

**What should the system instructions and answers include?** _(Answer rules, multi-select)_

- [x] **Cite KB IDs + page/section** – e.g. [KB-NET-1003, Table 1]
- [x] **Answer only from context** – Say 'I don't know' when the context is insufficient
- [x] **Flag superseded sources** – Warn if an answer relies on a superseded article
- [x] **Streaming output** – Stream the answer token by token in the notebook

**How should the notebook import the functions from scripts/?** _(Imports)_

- [x] **sys.path in first cell** – Add <project>/scripts to sys.path; no packaging changes
- [ ] Make scripts a package – Add scripts/__init__.py and `from scripts.rag_search import ...`

#### Round 3

**What should the reusable search module be called?** _(Module name)_

- [x] **scripts/rag_search.py** – Search functions + retriever factory
- [ ] scripts/retrievers.py – Same content, retriever-centric name

**Should scripts/test_query_vector_dbs.py be refactored to use the new module (removing its duplicate search code)?** _(Refactor)_

- [ ] Yes, reuse it – One source of truth for the search logic; re-run make test-query to confirm
- [x] **No, leave it** – Keep the test script standalone

**What defaults should the search functions use?** _(Defaults)_

- [x] **k=4, hybrid 0.5/0.5** – Slightly more context for the LLM; equal BM25/vector weights
- [ ] k=3, hybrid 0.5/0.5 – Same as the test script
- [ ] k=5, hybrid 0.4/0.6 – More context, favouring vector search

**After creating the notebook, should I execute it so the outputs are saved in the .ipynb?** _(Execute)_

- [ ] Yes, execute & save outputs – Students see results without running it (about 15-20 LLM calls)
- [x] **No, leave it clean** – Execute only to validate, then clear the outputs

**Outcome:** Added `scripts/rag_search.py` (similarity/keyword/hybrid search + retriever factory) and `notebooks/naive-rag.ipynb` (step-by-step RAG and an LCEL chain).
