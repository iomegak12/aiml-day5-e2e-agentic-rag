# Phase 4 – Enterprise Agentic RAG agent (+ planning mode)

Your prompts (lightly cleaned), the MCQ clarifications with every option ([x] = your choice), and a one-line outcome.

## Prompt 1

> Can you analyze the following Mermaid content? I would like to design an enterprise-grade Agentic AI RAG agent that provides all the capabilities highlighted in this Enterprise RAG workflow.
>
> <details><summary>Enterprise RAG workflow (Mermaid)</summary>
>
> ```mermaid
> flowchart TD
>     U(["User request"])
>
>
>     subgraph AGENT["Agentic RAG Orchestrator: plans and executes each step"]
>         IG["Input Guardrails<br/>prompt injection · PII · toxicity · topic policy<br/><i>solves: unsafe or malicious input</i>"]
>         IGD{"Allowed?"}
>         SC["Semantic Cache Lookup<br/>Redis Semantic Cache<br/><i>solves: cost and latency of repeat questions</i>"]
>         SCD{"Cache hit?"}
>         CHK["Cache Hit Checks<br/>RBAC + output guardrails<br/><i>solves: leaking answers across access levels</i>"]
>         CHKD{"Pass?"}
>
>
>         ROUTER["LLM Router · Adaptive RAG<br/><i>solves: one-size-fits-all retrieval</i>"]
>         RD{"Route"}
>         WEB["Online Search<br/><i>solves: stale or missing internal data</i>"]
>         VEC["Vector DB Search<br/>with RBAC metadata filter<br/><i>solves: unauthorized document access</i>"]
>         FED["Federated Search<br/>web + vector DB in parallel"]
>         MERGE["Merge and de-duplicate results"]
>
>
>         RANK["Rerank · Score · Relevance Check<br/><i>solves: noisy or irrelevant retrieval</i>"]
>         RELD{"Above relevance<br/>threshold?"}
>         LOOPD{"Rewrite attempts<br/>less than 3?"}
>         RW["Query Rewriter · Corrective RAG<br/>decompose into sub-questions or rephrase<br/><i>solves: vague or multi-part questions</i>"]
>         WEBD{"Online search<br/>already tried?"}
>         NOINFO["No reliable information found message"]
>
>
>         CTX["Context Optimizer<br/>fit token limit · summarize · trim<br/><i>solves: context overflow and lost-in-the-middle</i>"]
>         PROMPT["Prompt Builder<br/>instructions + question + context + citations"]
>         GEN["LLM Response Generation"]
>
>
>         JUDGE["Judge LLM Evaluation<br/>input: question + context + response<br/>faithfulness · groundedness · context precision<br/><i>solves: hallucination</i>"]
>         JD{"Scores pass?"}
>         JFD{"Judge failure count"}
>         DISC["Add low-confidence disclaimer"]
>
>
>         OG["Output Guardrails<br/>PII · toxicity · policy · format<br/><i>solves: harmful or non-compliant output</i>"]
>         OGD{"Pass?"}
>         OGFD{"Regenerated already?"}
>         SAFE["Safe refusal message"]
>
>
>         CPD{"Judge passed?"}
>         CACHE["Write to Semantic Cache<br/>question + context + response<br/><i>solves: bad answers polluting the cache</i>"]
>     end
>
>
>     subgraph POLICY["Cross-cutting policies, applied to every step"]
>         RETRY["Retry with exponential backoff<br/>on LLM, search or DB failures<br/><i>solves: transient errors</i>"]
>         TO["Global timeout budget<br/><i>solves: unbounded latency</i>"]
>         TOFB["Graceful timeout response<br/>best partial answer or apology"]
>     end
>
>
>     RESP(["Response to user"])
>
>
>     U --> IG --> IGD
>     IGD -->|no| SAFE
>     IGD -->|yes| SC --> SCD
>     SCD -->|hit| CHK --> CHKD
>     CHKD -->|pass| RESP
>     CHKD -->|fail| ROUTER
>     SCD -->|miss| ROUTER
>
>
>     ROUTER --> RD
>     RD -->|public / current info| WEB
>     RD -->|internal knowledge| VEC
>     RD -->|both| FED
>     WEB & VEC & FED --> MERGE --> RANK --> RELD
>
>
>     RELD -->|yes| CTX
>     RELD -->|no| LOOPD
>     LOOPD -->|yes| RW --> ROUTER
>     LOOPD -->|no| WEBD
>     WEBD -->|no| WEB
>     WEBD -->|yes| NOINFO --> OG
>
>
>     CTX --> PROMPT --> GEN --> JUDGE --> JD
>     JD -->|yes| OG
>     JD -->|no| JFD
>     JFD -->|1st: regenerate| GEN
>     JFD -->|2nd: re-retrieve| RW
>     JFD -->|3rd: give up| DISC --> OG
>
>
>     OG --> OGD
>     OGD -->|pass| CPD
>     OGD -->|fail| OGFD
>     OGFD -->|no| GEN
>     OGFD -->|yes| SAFE
>     SAFE --> RESP
>
>
>     CPD -->|yes| CACHE --> RESP
>     CPD -->|no: disclaimer or no-info| RESP
>
>
>     TO -.->|time exceeded| TOFB -.-> RESP
>     RETRY -.-|wraps all steps| AGENT
>     TO -.-|wraps all steps| AGENT
> ```
> </details>
>
> NOTE:
> - Let me know what you have understood; I would like to review your understanding before we proceed to the implementation.
> - Do NOT generate any code, scripts, notebooks, commands or anything else.
> - Do NOT give a detailed response; just list what you have understood, with titles only.
> - As I said earlier, do NOT assume anything on your own. Always clarify with me.
>
> Do you understand what I am saying?

### Clarifications

#### Round 1

**Does my understanding of the Enterprise Agentic RAG workflow (24 items listed) match yours?** _(Understanding)_

- [x] **Yes, matches** – Proceed to MCQs on the 'points to clarify' list
- [ ] Partly, corrections needed – You'll point out what to correct or add
- [ ] No, re-analyze – Re-read the workflow with your hints

#### Round 2

**Which orchestration framework should drive the agent workflow?** _(Framework)_

- [ ] LangGraph StateGraph (Recommended) – Explicit nodes and conditional edges map 1:1 to the flowchart; loops, counters and checkpoints
- [x] **LangChain create_agent** – LangChain v1 agent with tools + middleware; LLM decides the steps
- [ ] Hybrid – LangGraph for the fixed pipeline, an agent node for routing/rewriting

**How should RBAC work for the vector search filter?** _(RBAC)_

- [x] **Role → access_level metadata** – Add access_level (e.g. public/internal/restricted) to chunks; user roles map to allowed levels
- [ ] Role → domain/product – Roles grant access per domain or product (e.g. network-engineer → networking only)
- [ ] Both – Domain-level and access-level checks combined

**How should the router choose between the networking and meetings databases?** _(DB routing)_

- [x] **LLM router picks** – Router decides networking | meetings | both, plus web, in one structured decision
- [ ] Caller specifies – Domain passed in with the request; router decides only vector vs web vs both
- [ ] Search both always – Query both DBs and let the reranker decide

**In what form should the agent be delivered?** _(Delivery, multi-select)_

- [x] **Python package/scripts** – Reusable modules under scripts/ (or a package)
- [x] **Notebook walkthrough** – Step-by-step teaching notebook, like naive-rag.ipynb
- [ ] REST API (FastAPI) – Service endpoint for the agent
- [ ] Chat UI – e.g. Streamlit/Chainlit front end

#### Round 3

**The flowchart has fixed rules (max 3 rewrites, judge failure counts, regenerate-once). With create_agent, how should those rules be enforced?** _(Enforcement)_

- [x] **Middleware + tools (Recommended)** – Guardrails, cache, judge, retry, timeout as middleware hooks (deterministic); search/rewrite/rerank as tools the agent calls; counters held in agent state
- [ ] Prompt instructions only – System prompt describes the workflow; the LLM decides (least reliable)
- [ ] Tools only + limits – Every step is a tool; ToolCallLimit/ModelCallLimit middleware caps the loops

**Which guardrails tooling should be used?** _(Guardrails)_

- [x] **LangChain built-ins + LLM checks** – PIIMiddleware for PII; LLM classifier (structured output) for injection/toxicity/topic; no extra vendor
- [ ] Guardrails AI – guardrails-ai validators (extra dependency/hub)
- [ ] NeMo Guardrails – NVIDIA rails config (heavier)
- [ ] OpenAI Moderation + LLM – Moderation API for toxicity, LLM for injection/topic, PIIMiddleware for PII

**Which online search provider should be used?** _(Web search)_

- [ ] Tavily – langchain-tavily; needs TAVILY_API_KEY (free tier)
- [ ] DuckDuckGo – No API key; less reliable/rate-limited
- [ ] OpenAI web search tool – Built-in tool via the Responses API; uses the existing OpenAI key
- [x] **Other:** We shall use the Serper API; I will provide `SERPER_API_KEY` in the `.env` file.

**How should the Redis semantic cache be set up?** _(Redis cache)_

- [x] **Redis Stack in docker compose** – Add a redis service next to Chroma; use langchain-redis / RedisVL SemanticCache with OpenAI embeddings
- [ ] Separate compose file – Own docker-compose for Redis

#### Round 4

**Which reranker should score retrieved results?** _(Reranker)_

- [ ] LLM reranker (structured) – OPENAI_MODEL scores each chunk 0-1; no new vendor; slower and costs tokens
- [ ] Local cross-encoder – e.g. a sentence-transformers cross-encoder (adds torch, a big dependency)
- [ ] FlashRank – Lightweight local ONNX reranker; small download
- [ ] Cohere Rerank – API-based; needs COHERE_API_KEY
- [x] **Other:** LLM reranker, but I would like to use a different OpenAI model rather than the same gpt-5.5 (I will provide a new `.env` setting, `RERANKER_OPENAI_MODEL`).

**How should the Judge LLM evaluation be implemented?** _(Judge)_

- [ ] Custom LLM judge – Structured output: faithfulness, groundedness, context precision (0-1) + reasons; no extra library
- [x] **RAGAS** – ragas metrics library
- [ ] DeepEval – deepeval metrics library

**Where do user identity and roles come from (for RBAC)?** _(Identity)_

- [x] **Demo users in config** – A small users/roles file (e.g. guest, employee, network-admin); a user_id is passed with each request
- [ ] Role passed directly – Caller passes the role with the request; no user registry

**How should access_level be assigned to the existing chunks?** _(Access level)_

- [ ] Per article in the seed catalog – Add access_level to the KB seeds/manifest and re-populate (re-run populate)
- [ ] Rule-based at populate time – e.g. FAQ/help = public, config/runbook = internal, policy = restricted
- [x] **Update metadata in place** – Patch Chroma metadata without re-embedding

#### Round 5

**Updating metadata in place: which rule should decide each chunk's access_level?** _(Level rule)_

- [x] **By article_type** – faq/help = public; config/runbook/reference = internal; policy = restricted
- [ ] Per KB ID mapping – An explicit kb_id → access_level table in config that you review
- [ ] By status + type – Superseded = restricted (archive); others by article_type

**Which demo roles should exist?** _(Roles)_

- [x] **guest / employee / admin** – guest → public; employee → public+internal; admin → all
- [ ] Domain-flavoured roles – e.g. customer, network-engineer, collab-admin, support-lead (levels mapped per role)

**Which model should RAGAS use as its judge?** _(Judge model)_

- [x] **New JUDGE_OPENAI_MODEL** – You add a separate setting in .env
- [ ] Same as OPENAI_MODEL – gpt-5.5
- [ ] Same as RERANKER_OPENAI_MODEL – Reuse the reranker model

**Should tracing/observability be included?** _(Tracing)_

- [ ] LangSmith (optional via .env) – Enabled only if LANGSMITH_API_KEY is set
- [x] **Structured console logs** – Step-by-step trace printed (node, decision, scores, timings)
- [ ] Both – Console trace always; LangSmith if configured

#### Round 6

**What threshold and limit defaults should be used? (All configurable in .env.)** _(Thresholds)_

- [x] **Balanced (Recommended)** – rerank relevance ≥ 0.6; RAGAS faithfulness ≥ 0.7, context precision ≥ 0.6; cache similarity ≥ 0.90; timeout 90 s; retries 3
- [ ] Strict – relevance ≥ 0.7; faithfulness ≥ 0.85; precision ≥ 0.7; cache ≥ 0.95; timeout 60 s
- [ ] Lenient (demo-friendly) – relevance ≥ 0.5; faithfulness ≥ 0.6; precision ≥ 0.5; cache ≥ 0.85; timeout 120 s

**On a cache hit, how should the RBAC check work?** _(Cache RBAC)_

- [x] **Store access levels with the entry** – Each cached answer records the max access_level of its sources; the hit is served only if the user may see that level
- [ ] Partition cache by role – Separate cache namespace per role (simpler, less sharing)

**What should the topic policy (input guardrail) allow?** _(Topic policy)_

- [x] **NetCore networking + collaboration** – SD-WAN, SLA, QoS, meetings, calling, plus general networking/collab questions; reject everything else
- [ ] Only NetCore products – Strictly NetCore SD-WAN / Meet / Calling

**How should the code be organised?** _(Code layout)_

- [x] **Package scripts/agentic_rag/** – Modules: config, guardrails, cache, retrieval, rerank, rewrite, judge, middleware, agent (reuses rag_search.py)
- [ ] Single file scripts/agentic_rag.py – One big module, like the earlier scripts

#### Round 7

**Which scenarios should the notebook demonstrate? (multi-select)** _(Scenarios, multi-select)_

- [x] **Guardrail blocks** – Prompt injection, PII in the input, off-topic question → safe refusal
- [x] **Cache hit/miss + RBAC** – Same question twice; a guest is denied an admin-cached answer
- [x] **Routing + corrective loop** – Vector vs web vs federated; vague question → rewrite → success or no-info
- [x] **Judge + output guardrails** – RAGAS scores shown, regenerate/disclaimer path, PII redaction in the output

**How should the Context Optimizer fit the context into the token limit?** _(Context opt)_

- [ ] Trim + reorder – Token-count with tiktoken, keep the top-ranked chunks, put the best at the edges (lost-in-the-middle); no extra LLM call
- [x] **Trim + LLM summarise** – Summarise overflow chunks with the reranker model

**Which Make targets should be added? (multi-select)** _(Make, multi-select)_

- [x] **redis-up / down** – Can also be folded into chroma-up as 'infra-up'
- [x] **assign-access-levels** – Patch access_level metadata in Chroma
- [x] **agent-ask Q=... U=...** – Ask the agent from the CLI as a demo user
- [ ] cache-clear – Flush the semantic cache

**After implementation, may I run the end-to-end tests (Chroma + Redis + OpenAI + Serper calls, a few dollars at most)?** _(Test run)_

- [x] **Yes, run them** – Execute the CLI scenarios and the notebook headless (saved clean)
- [ ] Dry checks only – Imports and unit-level checks without paid calls

#### Round 8

**RAGAS (latest, 0.4.3) cannot import with langchain-community 0.4.2: it needs a module removed in the 0.4 sunset. How should I proceed?** _(RAGAS compat)_

- [x] **Pin community to 0.3.31 (Recommended)** – Verified: RAGAS + all metrics, our loaders, BM25 and Serper import fine; langchain 1.4.9 / core 1.7.6 unchanged. Re-run make verify / populate checks afterwards
- [ ] Import shim – Keep community 0.4.2; inject a stub module before importing RAGAS (hacky, fragile)
- [ ] Custom LLM judge instead – Drop RAGAS; implement faithfulness/groundedness/precision with JUDGE_OPENAI_MODEL structured output

**Outcome:** Built the agent in `scripts/agentic_rag/` (LangChain `create_agent`, guardrails, Redis semantic cache with RBAC, routing, rerank + rewrite loop, judge escalation, retry/timeout) and the `notebooks/agentic-rag.ipynb` test scenarios; every path ran end to end.

---

## Prompt 2

> I get the following error when I execute cell 9, even though I got the results:
>
> ```text
> Task exception was never retrieved
> future: <Task finished name='Task-83' coro=<AsyncClient.aclose() done, ...> exception=RuntimeError('Event loop is closed')>
> Traceback (most recent call last):
>   ...
> RuntimeError: Event loop is closed
> ```
>
> Can you look into this?

**Outcome:** Fixed in `judge.py`: the judge's async OpenAI client is now closed inside its own event loop. Also flagged that RAGAS faithfulness scores swung between runs.

---

## Prompt 3

> I would like to enhance the agent we built to support Agentic RAG by adding a planning mode: show the plan, then execute it.

### Clarifications

#### Round 1

**Which planning approach should the agent use?** _(Approach)_

- [x] **Plan-and-Execute (Recommended)** – A planner LLM writes a structured step list up front (e.g. retrieve X from networking, search web for Y, compare, answer); the executor runs each step with the existing tools
- [ ] Built-in TodoListMiddleware – LangChain's write_todos tool: the agent keeps and updates its own to-do list while it works (less deterministic)
- [ ] Hybrid – Structured plan up front, executed through TodoListMiddleware-style status tracking

**After the plan is shown, how should execution start?** _(Approval)_

- [ ] Human approval (HITL) – Pause after showing the plan; user approves, edits or rejects (LangGraph interrupt + checkpointer)
- [x] **Auto-execute** – Show the plan, then execute immediately
- [ ] Configurable – approve_plan=True/False per request

**When should the agent create a plan?** _(Trigger)_

- [ ] Only complex questions – LLM decides: multi-part, comparison or cross-domain questions get a plan; simple ones keep the current direct flow
- [x] **Always** – Every request gets a plan (even single-step)
- [ ] User flag – plan=True passed with the request / CLI flag

**Should the plan adapt while executing?** _(Replanning)_

- [x] **Replan on failure** – Re-plan only when a step finds nothing relevant / fails (fits the corrective loop)
- [ ] Replan after every step – Re-evaluate the remaining steps after each step (more LLM calls)
- [ ] Static plan – Execute the plan as written

#### Round 2

**Who executes the plan steps?** _(Executor)_

- [x] **Deterministic executor (Recommended)** – Code runs each step's tool directly (search KB / web / federated per step), then one synthesis LLM call writes the answer; predictable, cheaper
- [ ] Agent follows the plan – Plan injected into the existing create_agent loop; the LLM calls tools step by step and marks them done (more agentic, less predictable)

**Which model should the planner (and re-planner) use?** _(Planner model)_

- [x] **OPENAI_MODEL** – gpt-5.5, same as the orchestrator
- [ ] RERANKER_OPENAI_MODEL – gpt-5.1, cheaper/faster
- [ ] New PLANNER_OPENAI_MODEL – You add a separate .env setting

**How should the plan be shown?** _(Display, multi-select)_

- [x] **Plan table before execution** – Step #, goal, tool, domain(s), query, depends-on
- [x] **Live step status** – pending -> running -> done / no results / replanned, in the console trace
- [x] **Final plan report in result** – Executed plan with per-step outcome, sources and timings in show_result

**How should the planning demo be delivered?** _(Delivery, multi-select)_

- [x] **New section in agentic-rag.ipynb** – Planning scenarios added to the existing test notebook
- [ ] New notebook agentic-rag-planning.ipynb – Separate test-scenarios-only notebook
- [ ] CLI flag / Make target – e.g. make agent-plan Q=... U=...

#### Round 3

**With 'always plan' + deterministic executor, what happens to the current agent-driven tool loop?** _(Mode)_

- [x] **Keep both, planning default** – ask(..., mode='plan') is the new default; mode='react' keeps the current behaviour so existing scenarios still work
- [ ] Replace it – Planning becomes the only flow; existing notebook scenarios get re-run on the new flow

**When a plan step finds nothing relevant, how should it interact with the existing corrective loop (MAX_REWRITES=3, then web fallback, then no-info)?** _(Step failure)_

- [x] **Replan = the rewrite** – A failed step triggers a re-plan (planner rewrites the remaining steps); each re-plan counts as one rewrite; after 3 -> web fallback -> no-info
- [ ] Rewrite step first, then replan – Retry the failed step with a rewritten query; re-plan only if still empty

**On the judge's 2nd failure ('re-retrieve'), what should happen in planning mode?** _(Judge 2nd)_

- [x] **Re-plan with judge feedback** – Planner creates a revised plan using the failed metrics as feedback, then executes it
- [ ] Rewrite query (as today) – Keep the current rewrite_query behaviour

**What is the maximum number of steps per plan?** _(Max steps)_

- [x] **4** – Keeps latency within the 90 s budget
- [ ] 6 – More room for complex questions (configurable in .env)
- [ ] 3 – Tightest

#### Round 4

**Approve this planning-mode design (deterministic Plan-and-Execute, auto-execute, re-plan on failure, existing notebook sections pinned to mode='react', new section 7)?** _(Approve)_

- [x] **Approve, implement & test** – Build it, run the CLI scenarios and execute the notebook headless (saved clean)
- [ ] Approve, implement only – No paid test runs
- [ ] Changes needed – Tell me what to change

**Outcome:** Added plan mode (planner → plan shown → executor, re-planning on empty steps and on judge feedback) and `notebooks/agentic-rag-plan.ipynb`.

---

## Prompt 4

> You don't have to execute all the cells. Just test the cell that has the planning demo.

**Outcome:** Ran only the setup and §7 planning cells (7a–7e) in a scratch copy: all passed, and the notebook was left clean.
