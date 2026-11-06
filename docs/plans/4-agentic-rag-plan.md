# Plan: Enterprise Agentic RAG Agent (`scripts/agentic_rag/`)

## Context
Naive RAG works (`notebooks/naive-rag.ipynb`, `scripts/rag_search.py`). The instructor's Enterprise RAG flowchart adds input/output guardrails, a Redis semantic cache with RBAC, LLM routing (vector / web / federated), reranking with a corrective rewrite loop, context optimisation, a RAGAS judge with escalation, and cross-cutting retry and timeout policies. Goal: an agent built on **LangChain `create_agent`** that implements the whole flowchart, plus a teaching notebook.

## Decisions (from the MCQs)
| Topic | Decision |
|---|---|
| Orchestration | `create_agent`: **deterministic rules in middleware**, search/rewrite as **tools**, counters in agent state |
| Guardrails | LangChain built-in `PIIMiddleware`, plus an LLM classifier (structured) for injection, toxicity and topic |
| Topic policy | NetCore and general networking + collaboration topics; everything else refused |
| Web search | **Serper** (`SERPER_API_KEY`, `GoogleSerperAPIWrapper`) |
| Semantic cache | **Redis Stack** in the existing `docker-compose.yml`, RedisVL `SemanticCache`; each entry stores the **max access_level** of its sources |
| Routing | The LLM router picks vector / web / both, and networking / meetings / both |
| Reranker | LLM reranker on **`RERANKER_OPENAI_MODEL`**, scoring 0–1 |
| Judge | **RAGAS** (faithfulness, groundedness, context precision) on **`JUDGE_OPENAI_MODEL`** (new `.env` key, you add it) |
| RBAC | Demo users in config: guest → public; employee → public + internal; admin → all |
| access_level | **Patched in place** in Chroma by `article_type`: faq/help = public; config/runbook/reference = internal; policy = restricted |
| Context optimiser | tiktoken budget: trim, then LLM-summarise the overflow (reranker model) |
| Thresholds (.env) | relevance ≥ 0.6, faithfulness ≥ 0.7, groundedness ≥ 0.7, context precision ≥ 0.6, cache similarity ≥ 0.90, timeout 90 s, retries 3, rewrites 3 |
| Tracing | Structured console logs (step, decision, scores, timings) |
| Delivery | Package `scripts/agentic_rag/` + `notebooks/agentic-rag.ipynb` (saved clean) |

## Package `scripts/agentic_rag/`
| Module | Responsibility (flowchart node) |
|---|---|
| `config.py` | `.env` settings, thresholds, demo users and roles → allowed access levels |
| `guardrails.py` | Input checks (PII, injection, toxicity, topic), output checks (PII redaction, toxicity, policy, format), safe-refusal text |
| `cache.py` | Redis semantic cache: lookup, RBAC check on hit, write only for judge-passed answers |
| `retrieval.py` | Tools: `search_knowledge_base` (hybrid via `rag_search`, RBAC `where` filter on access_level), `search_web` (Serper), `federated_search` (parallel), merge + de-duplicate |
| `rerank.py` | LLM rerank, relevance threshold |
| `rewrite.py` | Tool: query rewriter (decompose or rephrase), Corrective RAG |
| `context.py` | Context optimiser (trim + summarise) and prompt builder (instructions, question, context, citations) |
| `judge.py` | RAGAS evaluation (question + context + response) |
| `middleware.py` | Input guardrails, cache lookup/write, retrieval-loop policy (rewrites < 3, web fallback once, then no-info), judge escalation (regenerate → re-retrieve → disclaimer), output guardrails (regenerate once → safe refusal), global timeout budget, console trace; plus built-in `ModelRetryMiddleware` / `ToolRetryMiddleware` with exponential backoff |
| `agent.py` | `build_agent()` = `create_agent(model, tools, middleware, state_schema, context_schema=user)` and `ask(question, user_id)` → answer, sources, scores, trace |
| `display.py` | Rich rendering of an agent result (answer, sources, scores, trace) for the CLI and the notebook |
| `__main__.py` | CLI: `--question`, `--user` |

Reused: `scripts/rag_search.py` (hybrid search, `format_docs`, `location`), `scripts/populate_vector_dbs.py` (`load_config`, `http_client`), and the system-prompt rules from `notebooks/naive-rag.ipynb`.

## Other files
- `scripts/assign_access_levels.py`: patch `access_level` into Chroma metadata (no re-embedding). The same rule is added to `populate_vector_dbs.py` so a re-populate keeps the levels.
- `docker-compose.yml`: add a `redis` service (redis-stack-server, port from `.env`).
- `.env` / `.env.example`: add `REDIS_*`, the thresholds, the limits and `CONTEXT_TOKEN_BUDGET`. Your keys `SERPER_API_KEY`, `RERANKER_OPENAI_MODEL` and `JUDGE_OPENAI_MODEL` stay untouched.
- Makefile: `redis-up`, `redis-down`, `assign-access-levels`, `agent-ask Q="..." U=...`.
- Dependencies: `langchain` (v1, for `create_agent` and middleware), `ragas`, `redisvl`, `tiktoken`. I'll check the installed APIs (middleware hooks, `jump_to`, RAGAS metrics) during implementation.
- README, TROUBLESHOOTING, CHANGELOG 0.5.0.

## `notebooks/agentic-rag.ipynb`: test scenarios only
**No implementation code in the notebook.** Cells only import from `agentic_rag`, call `ask(question, user_id)` or the cache/admin helpers, and display the answer, sources, scores and trace. All logic, including the display helpers, lives in the package.

1. Setup (import and config printout), demo users.
2. Guardrail blocks: prompt injection, PII, off-topic → safe refusal.
3. Cache: the same question twice (miss, then hit); a guest is denied an answer cached for an admin.
4. Routing and the corrective loop: vector vs web vs federated; a vague question gets rewritten, ending in success or no-info.
5. Judge and output guardrails: RAGAS scores, the regenerate/disclaimer path, PII redaction in the output.
6. Trace walkthrough and takeaways.

## Prerequisites (you)
- Add `JUDGE_OPENAI_MODEL` to `.env`.

## Verification
1. `make redis-up`, then `make assign-access-levels` (counts per level, checked with `db-stats`).
2. Run `make agent-ask` for each scenario and user. The trace must show the expected path (block / hit / miss / route / rewrite / judge / disclaimer / refusal).
3. Run RBAC checks: a guest never receives internal or restricted chunks, and the cache denies cross-level hits.
4. Execute the notebook headless, with no errors, then save it clean.
