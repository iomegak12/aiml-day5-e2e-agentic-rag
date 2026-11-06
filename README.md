# NetCore KB Generator

Generates a realistic, **synthetic** knowledge base for an Enterprise RAG / Agentic AI course. It covers two domains, and each domain feeds its own vector database:

| Domain | Product (fictional) | Topics |
|---|---|---|
| `networking` | NetCore SD-WAN | SLA classes, SLA breach policies, BFD, ZTP, QoS, alarm codes |
| `meetings` | NetCore Meet / NetCore Calling | SSO, dial plans, calling features, recording policy, help articles, error codes |

The generator writes 10 articles per domain, spread evenly across **PDF, HTML and Markdown**, and adds a `manifest.json` per domain.

> "NetCore Systems" and all of its products, codes and values are fictional.

## Quick Start

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), GNU make, an OpenAI API key.

```bash
cp .env.example .env      # then set OPENAI_API_KEY and OPENAI_MODEL
make install              # uv sync
make generate             # write missing articles to data/raw/
make verify               # load every article with LangChain loaders
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
data/raw/<domain>/      generated articles + manifest.json
docs/plans/             planning notes
scripts/generate_kb.py  generator
scripts/verify_kb.py    loader smoke test
Makefile                command entry points
```

## Documentation

[TROUBLESHOOTING](TROUBLESHOOTING.md) · [CHANGELOG](CHANGELOG.md) · [CONTRIBUTING](CONTRIBUTING.md) · [CODE OF CONDUCT](CODE_OF_CONDUCT.md) · [SECURITY](SECURITY.md)

## License

[MIT](LICENSE) © 2026 Ramkumar
