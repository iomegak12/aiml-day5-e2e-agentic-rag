# Plan: KB Article Generator for Enterprise RAG Demo

## Context
The students need two realistic KB corpora to load into two vector DBs: **Networking** (SD-WAN and SLA breach policies) and **Meetings** (a WebEx-style tool covering configuration, calling and help articles). The project is an empty `uv` project on Python 3.12+. `.env` already contains `OPENAI_API_KEY` and `OPENAI_MODEL`.

## Decisions (from the MCQs)
- Fictional brand **NetCore Systems** for both domains (products: *NetCore SD-WAN* and *NetCore Meet/Calling*)
- Hybrid generation: the topic seeds live in the script, and an LLM (`langchain-openai`, structured output) writes the article bodies
- About 10 articles per domain, with an even mix of PDF, HTML and MD
- Article types: config guides, troubleshooting runbooks, policy/reference docs, FAQs/help articles
- Realism features: tables, CLI/config blocks, versioned and superseded articles (v4.2 → v5.0), KB-ID cross-references, error/alarm codes
- Metadata is embedded in each file (MD frontmatter, HTML `<meta>` tags, PDF properties) and also written to a `manifest.json` per domain
- Output goes to `data/raw/<domain>/`
- One single script, `generate_kb.py`; ReportLab for PDFs; reruns skip existing files unless `--force` is passed

## Design: `generate_kb.py` (single file)
1. **Seed catalog** (a list of dataclasses): `kb_id, domain, title, type, format, product, version, status (current/superseded), superseded_by, error_codes, related_kb_ids, brief`.
2. **LLM step**: `ChatOpenAI(model=OPENAI_MODEL).with_structured_output(Article)`. `Article` is a Pydantic model with fields `summary`, `applies_to`, and `sections[]`; each section has a heading, paragraphs, an optional table and an optional code block. The model also produces `faq[]` where it fits. The prompt is built from the seed: brand, type, version, error codes and cross-refs to include.
3. **Renderers**: `render_md` (YAML frontmatter), `render_html` (meta tags plus basic CSS, stdlib only), `render_pdf` (ReportLab Platypus: headings, tables, monospace code, document properties).
4. **Manifest**: writes `data/raw/<domain>/manifest.json`.
5. **CLI**: `--domain {networking,meetings,all}` and `--force`.

Dependencies: `uv add langchain-openai langchain-core pydantic python-dotenv reportlab`. I'll pin the latest versions at implementation time and check the current LangChain docs for the `with_structured_output` usage.

## Proposed Topic Catalog (please review)

**Networking** (`KB-NET-*`)
| ID | Title | Type | Fmt |
|---|---|---|---|
| 1001 | Configuring App-Aware Routing SLA Classes | Config | PDF |
| 1002 | SLA Class Thresholds Reference (latency/jitter/loss) | Reference | PDF |
| 1003 | SLA Breach Policy: Escalation & Auto-Failover (v5.0) | Policy | HTML |
| 1004 | SLA Breach Policy (v4.2, superseded by 1003) | Policy | HTML |
| 1005 | Troubleshooting Alarm NCS-SLA-2001 "SLA Violation Detected" | Runbook | MD |
| 1006 | Troubleshooting BFD Tunnel Flaps (NCS-BFD-3004) | Runbook | MD |
| 1007 | Zero-Touch Provisioning of a Branch Edge | Config | PDF |
| 1008 | NCS Alarm & Error Code Reference | Reference | HTML |
| 1009 | SD-WAN FAQ: Transports, Failover & SLA Reports | FAQ | MD |
| 1010 | QoS & Traffic Steering for Voice/Video | Config | MD |

**Meetings** (`KB-MTG-*`)
| ID | Title | Type | Fmt |
|---|---|---|---|
| 2001 | Configuring SAML SSO for NetCore Meet Sites | Config | PDF |
| 2002 | NetCore Calling: Number Provisioning & Dial Plans | Config | PDF |
| 2003 | Meeting Policy Reference: Recording, Lobby & Retention (v5.0) | Policy | PDF |
| 2004 | Recording Retention Policy (v4.2, superseded by 2003) | Policy | HTML |
| 2005 | Call Forwarding, Hunt Groups & Voicemail Setup | Config | HTML |
| 2006 | Troubleshooting Audio/Video Quality (MTG-MED-4102) | Runbook | MD |
| 2007 | Troubleshooting Join Failures (MTG-JOIN-1003/1007) | Runbook | MD |
| 2008 | NetCore Meet & Calling Error Code Reference | Reference | HTML |
| 2009 | Help: Scheduling & Joining Meetings from Calendar | Help/FAQ | MD |
| 2010 | FAQ: Licensing, Limits & Network Requirements | FAQ | MD |

## Verification
- `uv run generate_kb.py --domain all` should produce 20 files and 2 manifests under `data/raw/`
- Run it again without `--force` and confirm that every file is skipped
- Smoke-test loading with LangChain loaders (`PyPDFLoader`, `BSHTMLLoader`, `TextLoader`), check that text and metadata come through, and spot-check one article per format
