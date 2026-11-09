# Phase 1 – KB article generator

Your prompts (lightly cleaned), the MCQ clarifications with every option ([x] = your choice), and a one-line outcome.

## Prompt 1

> My name is Ramkumar. I am the instructor teaching Enterprise RAG capabilities to my students, using Agentic AI concepts and building enterprise agents. My students are experienced, professional engineers with good knowledge of Python programming and Generative AI concepts, and they want to learn how Agentic AI and RAG really work for enterprise problems. They primarily work on networking products, including SD-WAN and SLA-breach policies, and some students focus on online meeting tools like WebEx (configuration, calling features, help articles and so on).
>
> As part of the workflow, I'm now preparing two vector databases populated with KB articles for two different capabilities.
>
> First, I want you to generate a script that generates practical, realistic KB articles (PDFs, HTML pages and Markdown files) for those domains.
>
> NOTE:
> - Do NOT assume anything on your own; always clarify with me.
> - Do NOT generate an exhaustive or detailed response initially. Keep it as brief as possible, and give details only when I ask.
> - Do NOT generate anything immediately, until I review and approve it.
> - I'll primarily use the LangChain ecosystem for the complete demonstration, so please use the latest version of LangChain and refer to the online documentation wherever applicable.
> - I prefer to be questioned in MCQ-style Q&As instead of prose.
>
> Do you understand my requirements? Let's go.

### Clarifications

#### Round 1

**How should the two Vector DBs split the domains?** _(DB split)_

- [x] **Networking vs Meetings** – DB1 = SD-WAN + SLA breach policies; DB2 = WebEx (config, calling, help articles)
- [ ] SD-WAN vs SLA Policies – Both DBs networking; WebEx handled separately later
- [ ] Three domains, two DBs – You'll tell me how SD-WAN, SLA, and WebEx map to the two DBs

**How should the script produce the KB article content?** _(Content gen)_

- [ ] LLM via LangChain – Script calls an LLM (with structured output) to write the articles, then renders them to PDF/HTML/MD
- [ ] Static templates – Hand-written content embedded in the script; deterministic, no API key needed
- [x] **Hybrid** – Seed topics/templates in the script, LLM fills in the body text

**Roughly how many KB articles per domain?** _(Volume)_

- [x] **~10 per domain** – Quick classroom demo
- [ ] ~25 per domain – Enough variety for retrieval-quality demos
- [ ] ~50 per domain – Closer to a realistic corpus
- [ ] Configurable (CLI arg) – Script takes a count parameter

**What branding should the articles use?** _(Branding)_

- [ ] Fictional vendor – Made-up company and product names, which avoids confusion with official docs
- [ ] Real product names – Use Cisco SD-WAN / Webex names as written in real docs (content is still synthetic)
- [ ] Generic / vendor-neutral – No company names at all
- [x] **Other:** NetCore Systems

#### Round 2

**Which LLM provider should the hybrid generator use, through its LangChain integration?** _(LLM)_

- [ ] OpenAI (langchain-openai) – e.g., gpt-4o / gpt-4.1 family
- [ ] Azure OpenAI – langchain-openai AzureChatOpenAI
- [ ] Anthropic (langchain-anthropic) – Claude models
- [ ] Local (Ollama) – langchain-ollama, no cloud key
- [x] **Other:** I have already provided the details in the `.env` file (OpenAI API key and model).

**Should 'NetCore Systems' brand both domains?** _(Brand scope)_

- [x] **Both domains** – NetCore Systems makes both the SD-WAN product and the meeting tool
- [ ] Separate brands – NetCore for networking; you'll name the meeting product

**How should the ~10 articles per domain be split across file formats?** _(Format mix)_

- [x] **Even mix** – ~3-4 each of PDF, HTML, and Markdown per domain
- [ ] By article type – e.g., PDF = config guides, HTML = help/FAQ, MD = troubleshooting runbooks
- [ ] All three for every article – Each article rendered in all 3 formats (30 files per domain)

**Which article types should be included? (multi-select)** _(Article types, multi-select)_

- [x] **Configuration guides** – Step-by-step setup, CLI/UI snippets
- [x] **Troubleshooting runbooks** – Symptoms → diagnosis → fix
- [x] **Policy / reference docs** – SLA thresholds, breach policies, feature matrices
- [x] **FAQs / help articles** – Short Q&A style end-user help

#### Round 3

**What output folder layout should the generated files use?** _(Output)_

- [ ] kb/<domain>/<format>/ – e.g., kb/networking/pdf/, kb/meetings/html/
- [ ] kb/<domain>/ (flat) – All formats mixed in one folder per domain
- [x] **data/raw/<domain>/** – Conventional RAG pipeline 'raw' staging folder

**How should article metadata (for LangChain filtering) be stored?** _(Metadata)_

- [ ] Embedded in each file – MD frontmatter, HTML <meta> tags, PDF document properties
- [ ] Sidecar manifest – One manifest.json per domain (id, title, type, product, version, tags)
- [x] **Both** – Embedded metadata plus a manifest.json

**Which realism features should the articles include? (multi-select)** _(Realism, multi-select)_

- [x] **Tables & CLI/config blocks** – Tests chunking of structured content
- [x] **Versioned / superseded articles** – e.g., v4.2 vs v5.0 guidance, which is useful for showing conflicts and metadata filters
- [x] **Cross-references & KB IDs** – e.g., 'See KB-NET-1042'
- [x] **Error codes / alarm IDs** – Exact-match terms that make a good hybrid-search demo

**Which PDF generation library should the script use?** _(PDF lib)_

- [x] **ReportLab (Recommended)** – Pure Python, no system deps on Windows, supports tables/headers
- [ ] fpdf2 – Lightweight, simpler API
- [ ] WeasyPrint (HTML→PDF) – Nicer styling, but needs GTK libs on Windows

#### Round 4

**How should the script be structured?** _(Structure)_

- [x] **Single script** – One generate_kb.py, easy for students to read top to bottom
- [ ] Small package – kbgen/ with topics.py, llm.py, renderers.py and a CLI entry point

**How should the topic catalog (10 article seeds per domain) be finalized?** _(Topics)_

- [x] **I propose, you approve** – I put a brief 10+10 topic list in the plan for your review
- [ ] You provide – You'll share the topic list

**If an article was generated in an earlier run, what should a rerun do?** _(Reruns)_

- [x] **Skip existing** – Only generate missing files; use --force to regenerate
- [ ] Always overwrite – Regenerate everything each run

**Outcome:** Built `generate_kb.py` (seed topics + LLM structured output) and generated 20 KB articles (10 networking, 10 meetings) as PDF/HTML/Markdown, with a `manifest.json` per domain.

---

## Prompt 2

> - Move `generate_kb.py` to the `scripts` folder.
> - Generate an MIT license.
> - Generate README, TROUBLESHOOTING, CHANGELOG, CODE_OF_CONDUCT, SECURITY and CONTRIBUTING markdown files.
> - A Makefile is preferred for target commands.
> - Create `.env.example` as a template from `.env`.

### Clarifications

#### Round 1

**Who should be the copyright holder in the MIT LICENSE?** _(License)_

- [x] **Ramkumar** – Copyright (c) 2026 Ramkumar
- [ ] iomegak12 – Your git username
- [ ] Ramkumar (iomegak12) – Both name and handle

**Which contact email should SECURITY.md and CODE_OF_CONDUCT.md use for reports?** _(Contact)_

- [x] **jd.ramkumar@gmail.com** – Your git email
- [ ] Placeholder – e.g. <security@example.com> for you to fill in later

**Which Makefile targets do you want? (multi-select)** _(Make targets, multi-select)_

- [x] **install / help** – uv sync; list the targets
- [x] **generate variants** – generate, generate-networking, generate-meetings, regenerate (--force)
- [x] **verify** – Loader smoke test (PDF/HTML/MD) using uv run --with
- [x] **clean / clean-data** – Remove caches, and separately remove data/raw

**How detailed should the docs be?** _(Doc depth)_

- [x] **Concise** – Short, scannable files; README ~1 page with a quick start, layout and article catalog
- [ ] Detailed – Full README with architecture, schema and customization guide

**Outcome:** Moved the script to `scripts/`, added `LICENSE`, the six docs, a Makefile (`generate`, `verify`, `clean`, …), `scripts/verify_kb.py` and `.env.example`.
