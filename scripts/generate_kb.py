"""
generate_kb.py - Synthetic Knowledge Base generator for the Enterprise RAG demo.

Generates realistic KB articles for the fictional vendor "NetCore Systems" in two domains:
  - networking : NetCore SD-WAN, SLA classes and SLA breach policies
  - meetings   : NetCore Meet / NetCore Calling (configuration, calling features, help articles)

Approach (hybrid):
  1. A seed catalog (below) fixes each article's ID, title, type, format, version and key facts.
  2. An OpenAI model (via LangChain structured output) writes the article body as a Pydantic object.
  3. Renderers turn that object into Markdown, HTML or PDF, embedding the metadata in each file.
  4. A manifest.json per domain lists every article and its metadata.

Usage (from the project root; or use the Makefile targets):
  uv run scripts/generate_kb.py                      # both domains, skip files that already exist
  uv run scripts/generate_kb.py --domain networking  # one domain only
  uv run scripts/generate_kb.py --force              # regenerate everything

Requires OPENAI_API_KEY and OPENAI_MODEL in .env
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND = "NetCore Systems"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = PROJECT_ROOT / "data" / "raw"

# =============================================================================
# 1. Shared domain facts - keep all articles in a domain consistent with each other
# =============================================================================

DOMAIN_FACTS = {
    "networking": """
Product: NetCore SD-WAN (current release 5.0; previous release 4.2). Management plane: NetCore Orchestrator.
Edge devices: NCX-1000 (branch), NCX-4000 (regional hub), NCX-9000 (data center). CLI prompt style: "ncx-edge#".
Transports: MPLS, Internet broadband, LTE/5G. Tunnels monitored with BFD probes.
SLA classes (release 5.0):
  - Voice:             latency <= 150 ms, jitter <= 30 ms, loss <= 1%
  - Video:             latency <= 200 ms, jitter <= 40 ms, loss <= 2%
  - Business-Critical: latency <= 250 ms, jitter <= 50 ms, loss <= 3%
  - Best-Effort:       latency <= 400 ms, jitter n/a,     loss <= 5%
SLA breach policy (release 5.0): app-route poll interval 120 s, multiplier 3 -> breach declared after 3 consecutive
  intervals (~6 min). Automatic failover to the best compliant transport. Severity: Sev3 on breach,
  auto-escalate to Sev2 if breach persists > 15 min, Sev1 if > 30 min or >= 5 sites affected. Ticket auto-created in ITSM.
SLA breach policy (release 4.2, superseded): poll interval 600 s, multiplier 5 -> breach after ~50 min.
  Manual failover only. E-mail notification only, no automatic severity escalation.
Alarm / error codes:
  NCS-SLA-2001 SLA Violation Detected; NCS-SLA-2002 SLA Restored; NCS-BFD-3004 BFD Session Flap;
  NCS-BFD-3005 BFD Session Down; NCS-ZTP-4001 ZTP Redirect Failed; NCS-ZTP-4003 Device Certificate Validation Failed;
  NCS-QOS-5002 Queue Drop Threshold Exceeded; NCS-ORC-6001 Orchestrator Control Connection Lost.
Useful CLI: show sdwan app-route statistics | show sdwan bfd sessions | show sdwan sla-class |
  show sdwan control connections | show policy qos-queue counters | request sdwan ztp restart
""",
    "meetings": """
Products: NetCore Meet (video meetings), NetCore Calling (cloud PBX). Admin portal: NetCore Control Hub.
Current release 5.0; previous release 4.2. Clients: NetCore Meet desktop app (Windows/macOS), mobile app, web client.
Licences: Meet Starter (100 participants), Meet Business (300 participants), Meet Enterprise (1000 participants,
  webinar add-on up to 10,000 view-only attendees).
Network requirements: TCP 443 (signalling), UDP 9000 (media, preferred), TCP 5004 fallback for media.
  Recommended: latency < 300 ms, jitter < 40 ms, packet loss < 3%. Bandwidth per HD video stream ~2.5 Mbps.
Recording & retention policy (release 5.0): cloud recordings retained 365 days by default, configurable 30-1825 days,
  legal hold supported, auto-transcripts enabled; external participants wait in the lobby by default.
Recording & retention policy (release 4.2, superseded): fixed 180-day retention, no legal hold, no transcripts.
NetCore Calling: E.164 number provisioning, location-based dial plans, outbound prefix "9" optional,
  hunt groups (circular / top-down / simultaneous), call forwarding (always / busy / no-answer after 20 s), voicemail.
Error codes:
  MTG-JOIN-1003 Meeting Locked or Host Lobby Active; MTG-JOIN-1007 Media Ports Blocked by Firewall;
  MTG-MED-4102 Media Path Degraded (high packet loss); MTG-MED-4105 No Audio Device Detected;
  MTG-SSO-6001 SAML Assertion Invalid or Expired; MTG-SSO-6004 IdP Certificate Mismatch;
  MTG-CALL-7002 Number Not Provisioned; MTG-CALL-7010 Emergency Address Missing.
""",
}

# =============================================================================
# 2. Seed catalog - the "hand-written" half of the hybrid approach
# =============================================================================


@dataclass
class Seed:
    kb_id: str
    domain: str
    title: str
    article_type: str  # config | runbook | policy | reference | faq | help
    fmt: str  # pdf | html | md
    product: str
    version: str
    last_updated: str
    brief: str
    status: str = "current"  # current | superseded
    superseded_by: str | None = None
    error_codes: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


SEEDS: list[Seed] = [
    # ---------------------------- Networking ----------------------------
    Seed("KB-NET-1001", "networking", "Configuring App-Aware Routing SLA Classes", "config", "pdf",
         "NetCore SD-WAN", "5.0", "2026-08-12",
         "Define SLA classes in NetCore Orchestrator and on the CLI, bind applications to them via an "
         "app-route policy, verify with show commands.",
         error_codes=["NCS-SLA-2001"], related=["KB-NET-1002", "KB-NET-1003"],
         tags=["sla", "app-aware-routing", "policy"]),
    Seed("KB-NET-1002", "networking", "SLA Class Thresholds Reference (Latency, Jitter, Loss)", "reference", "pdf",
         "NetCore SD-WAN", "5.0", "2026-07-30",
         "Authoritative reference table of SLA class thresholds, default app-to-class mappings, measurement "
         "method (BFD probes, poll interval, multiplier) and how averages are computed.",
         related=["KB-NET-1001", "KB-NET-1003"], tags=["sla", "thresholds", "reference"]),
    Seed("KB-NET-1003", "networking", "SLA Breach Policy: Escalation and Auto-Failover", "policy", "html",
         "NetCore SD-WAN", "5.0", "2026-09-04",
         "The current SLA breach policy: breach detection timing, automatic failover behaviour, severity "
         "escalation matrix, ITSM ticketing, notification channels, exceptions and change history.",
         error_codes=["NCS-SLA-2001", "NCS-SLA-2002"], related=["KB-NET-1002", "KB-NET-1005", "KB-NET-1004"],
         tags=["sla", "breach", "escalation", "failover"]),
    Seed("KB-NET-1004", "networking", "SLA Breach Policy (Release 4.2)", "policy", "html",
         "NetCore SD-WAN", "4.2", "2024-11-18",
         "The OLD release 4.2 SLA breach policy: slow detection (~50 min), manual failover, e-mail-only "
         "notification. Write it as it was originally published for 4.2, using only the 4.2 values.",
         status="superseded", superseded_by="KB-NET-1003",
         error_codes=["NCS-SLA-2001"], related=["KB-NET-1002"], tags=["sla", "breach", "legacy"]),
    Seed("KB-NET-1005", "networking", 'Troubleshooting Alarm NCS-SLA-2001 "SLA Violation Detected"', "runbook", "md",
         "NetCore SD-WAN", "5.0", "2026-09-21",
         "Runbook for NOC engineers: symptoms, triage, CLI diagnostics with sample output, common root causes "
         "(ISP congestion, QoS mis-marking, LTE fallback), remediation and when to escalate.",
         error_codes=["NCS-SLA-2001", "NCS-SLA-2002", "NCS-QOS-5002"],
         related=["KB-NET-1003", "KB-NET-1006", "KB-NET-1010"], tags=["troubleshooting", "sla", "noc"]),
    Seed("KB-NET-1006", "networking", "Troubleshooting BFD Tunnel Flaps (NCS-BFD-3004)", "runbook", "md",
         "NetCore SD-WAN", "5.0", "2026-06-15",
         "Runbook for flapping BFD sessions: symptoms, diagnostics (bfd sessions, interface errors, NAT/MTU), "
         "root causes, fixes (hello interval tuning, MTU, ISP ticket) and impact on SLA measurement.",
         error_codes=["NCS-BFD-3004", "NCS-BFD-3005"], related=["KB-NET-1005", "KB-NET-1008"],
         tags=["troubleshooting", "bfd", "tunnels"]),
    Seed("KB-NET-1007", "networking", "Zero-Touch Provisioning of a Branch Edge (NCX-1000)", "config", "pdf",
         "NetCore SD-WAN", "5.0", "2026-05-02",
         "End-to-end ZTP onboarding of an NCX-1000: prerequisites, device template, serial allow-list, "
         "bootstrap, verification, and common ZTP failures.",
         error_codes=["NCS-ZTP-4001", "NCS-ZTP-4003", "NCS-ORC-6001"], related=["KB-NET-1008"],
         tags=["ztp", "onboarding", "branch"]),
    Seed("KB-NET-1008", "networking", "NCS Alarm and Error Code Reference", "reference", "html",
         "NetCore SD-WAN", "5.0", "2026-09-30",
         "Complete table of all NCS alarm codes: code, name, severity, description, likely cause, recommended "
         "action, related KB article.",
         error_codes=["NCS-SLA-2001", "NCS-SLA-2002", "NCS-BFD-3004", "NCS-BFD-3005", "NCS-ZTP-4001",
                      "NCS-ZTP-4003", "NCS-QOS-5002", "NCS-ORC-6001"],
         related=["KB-NET-1005", "KB-NET-1006", "KB-NET-1007"], tags=["alarms", "error-codes", "reference"]),
    Seed("KB-NET-1009", "networking", "SD-WAN FAQ: Transports, Failover and SLA Reports", "faq", "md",
         "NetCore SD-WAN", "5.0", "2026-08-25",
         "Frequently asked questions from network admins on transports, failover timing, SLA reporting in "
         "Orchestrator, report export and differences between release 4.2 and 5.0.",
         related=["KB-NET-1002", "KB-NET-1003"], tags=["faq", "sla", "reporting"]),
    Seed("KB-NET-1010", "networking", "QoS and Traffic Steering for Voice and Video", "config", "md",
         "NetCore SD-WAN", "5.0", "2026-07-08",
         "Configure DSCP marking, QoS queues and app-route steering so voice/video (including NetCore Meet "
         "traffic on UDP 9000) stays within its SLA class; verification and queue-drop monitoring.",
         error_codes=["NCS-QOS-5002"], related=["KB-NET-1001", "KB-NET-1005"],
         tags=["qos", "voice", "video", "dscp"]),
    # ---------------------------- Meetings ----------------------------
    Seed("KB-MTG-2001", "meetings", "Configuring SAML SSO for NetCore Meet Sites", "config", "pdf",
         "NetCore Meet", "5.0", "2026-06-20",
         "Configure SAML 2.0 SSO between NetCore Control Hub and a corporate IdP: metadata exchange, attribute "
         "mapping, testing, enforcement and certificate rollover.",
         error_codes=["MTG-SSO-6001", "MTG-SSO-6004"], related=["KB-MTG-2008"],
         tags=["sso", "saml", "identity"]),
    Seed("KB-MTG-2002", "meetings", "NetCore Calling: Number Provisioning and Dial Plans", "config", "pdf",
         "NetCore Calling", "5.0", "2026-07-14",
         "Provision E.164 numbers, assign to users/locations, configure location-based dial plans, outbound "
         "prefix, emergency addresses, and verify.",
         error_codes=["MTG-CALL-7002", "MTG-CALL-7010"], related=["KB-MTG-2005", "KB-MTG-2008"],
         tags=["calling", "numbers", "dial-plan"]),
    Seed("KB-MTG-2003", "meetings", "Meeting Policy Reference: Recording, Lobby and Retention", "policy", "pdf",
         "NetCore Meet", "5.0", "2026-09-10",
         "The current meeting policy: recording permissions, cloud recording retention, legal hold, transcripts, "
         "lobby rules for internal/external users, and policy precedence (org vs. group vs. user).",
         related=["KB-MTG-2004", "KB-MTG-2007"], tags=["policy", "recording", "retention", "lobby"]),
    Seed("KB-MTG-2004", "meetings", "Recording Retention Policy (Release 4.2)", "policy", "html",
         "NetCore Meet", "4.2", "2024-10-03",
         "The OLD release 4.2 recording retention policy: fixed 180-day retention, no legal hold, no transcripts. "
         "Write it as originally published for 4.2, using only the 4.2 values.",
         status="superseded", superseded_by="KB-MTG-2003", tags=["policy", "recording", "legacy"]),
    Seed("KB-MTG-2005", "meetings", "Call Forwarding, Hunt Groups and Voicemail Setup", "config", "html",
         "NetCore Calling", "5.0", "2026-08-01",
         "Admin guide to configure call forwarding rules, hunt groups (circular/top-down/simultaneous) and "
         "voicemail (greeting, PIN, e-mail delivery) in Control Hub; user self-service options.",
         error_codes=["MTG-CALL-7002"], related=["KB-MTG-2002"], tags=["calling", "hunt-group", "voicemail"]),
    Seed("KB-MTG-2006", "meetings", "Troubleshooting Audio and Video Quality (MTG-MED-4102)", "runbook", "md",
         "NetCore Meet", "5.0", "2026-09-18",
         "Runbook for poor audio/video: symptoms, in-meeting statistics, client logs, network checks against "
         "requirements, QoS/DSCP recommendations, resolution and escalation.",
         error_codes=["MTG-MED-4102", "MTG-MED-4105"], related=["KB-MTG-2007", "KB-MTG-2010"],
         tags=["troubleshooting", "media", "quality"]),
    Seed("KB-MTG-2007", "meetings", "Troubleshooting Meeting Join Failures (MTG-JOIN-1003 / MTG-JOIN-1007)",
         "runbook", "md", "NetCore Meet", "5.0", "2026-08-27",
         "Runbook for users unable to join: locked meeting/lobby, firewall blocking UDP 9000, proxy issues, "
         "SSO problems; diagnostics, fixes and escalation.",
         error_codes=["MTG-JOIN-1003", "MTG-JOIN-1007", "MTG-SSO-6001"],
         related=["KB-MTG-2003", "KB-MTG-2006", "KB-MTG-2010"], tags=["troubleshooting", "join", "firewall"]),
    Seed("KB-MTG-2008", "meetings", "NetCore Meet and Calling Error Code Reference", "reference", "html",
         "NetCore Meet", "5.0", "2026-09-30",
         "Complete table of all MTG error codes: code, message, component, description, likely cause, "
         "user action, admin action, related KB article.",
         error_codes=["MTG-JOIN-1003", "MTG-JOIN-1007", "MTG-MED-4102", "MTG-MED-4105", "MTG-SSO-6001",
                      "MTG-SSO-6004", "MTG-CALL-7002", "MTG-CALL-7010"],
         related=["KB-MTG-2006", "KB-MTG-2007", "KB-MTG-2001"], tags=["error-codes", "reference"]),
    Seed("KB-MTG-2009", "meetings", "Help: Scheduling and Joining Meetings from Your Calendar", "help", "md",
         "NetCore Meet", "5.0", "2026-05-22",
         "End-user help article: install the calendar add-in (Outlook / Google Calendar), schedule a meeting, "
         "set meeting options, join from the calendar or by dial-in, tips.",
         related=["KB-MTG-2007", "KB-MTG-2010"], tags=["help", "calendar", "end-user"]),
    Seed("KB-MTG-2010", "meetings", "FAQ: Licensing, Limits and Network Requirements", "faq", "md",
         "NetCore Meet", "5.0", "2026-08-11",
         "FAQ covering licence tiers and participant limits, webinar add-on, bandwidth per stream, required "
         "ports, latency/jitter/loss recommendations and differences between release 4.2 and 5.0.",
         related=["KB-MTG-2006", "KB-MTG-2007"], tags=["faq", "licensing", "network"]),
]

TYPE_GUIDANCE = {
    "config": "Sections: Overview, Prerequisites, Step-by-step Procedure (numbered steps with CLI or config "
              "blocks), Verification (commands with sample output), Rollback, Known Limitations.",
    "runbook": "Sections: Symptoms, Impact, Probable Causes, Diagnostic Steps (commands with realistic sample "
               "output), Resolution, Escalation Criteria. Include a cause-to-action table.",
    "policy": "Sections: Purpose, Scope, Definitions, Policy Statements (with a threshold/escalation table), "
              "Enforcement, Exceptions, Change History (table).",
    "reference": "Mostly tables. Sections: Overview, the main reference table(s) covering every listed item, "
                 "Notes on interpretation.",
    "faq": "A short Overview section, then 8-12 FAQs with concise, specific answers.",
    "help": "Friendly end-user tone. Sections: Before You Begin, numbered how-to steps per task, Tips, "
            "and 4-6 FAQs. No CLI.",
}

# =============================================================================
# 3. Structured output schema - what the LLM must return
#    (all fields required; "optional" ones are nullable, as OpenAI strict JSON schema expects)
# =============================================================================


class KBTable(BaseModel):
    caption: str
    headers: list[str]
    rows: list[list[str]]


class CodeBlock(BaseModel):
    language: str = Field(description="e.g. 'text', 'bash', 'json', 'xml'")
    content: str = Field(description="CLI commands, config snippet or sample output")


class Section(BaseModel):
    heading: str
    paragraphs: list[str]
    bullets: list[str] = Field(description="Bullet or numbered-step items; empty list if none")
    table: KBTable | None
    code: CodeBlock | None


class FAQItem(BaseModel):
    question: str
    answer: str


class Article(BaseModel):
    summary: str = Field(description="2-3 sentence abstract of the article")
    applies_to: list[str] = Field(description="Products, releases, device models or licence tiers")
    sections: list[Section]
    faqs: list[FAQItem] = Field(description="Empty list unless the article type calls for FAQs")


SYSTEM_PROMPT = """You are a senior technical writer at {brand}, writing internal knowledge-base articles \
for enterprise network engineers and collaboration administrators.

Rules:
- {brand} and all its products are fictional. Never mention real vendors or real products.
- Stay strictly consistent with the DOMAIN FACTS below. Never contradict them or invent different thresholds.
- Be concrete: real-looking CLI commands, config snippets, sample outputs, timestamps, interface names, values.
- Mention every listed error/alarm code verbatim, and refer to related articles by their KB ID (e.g. "see KB-NET-1003").
- Do not include the title, KB ID or metadata header; those are added separately.

DOMAIN FACTS:
{facts}"""

HUMAN_PROMPT = """Write the KB article.

KB ID: {kb_id}
Title: {title}
Article type: {article_type}
Product / release: {product} {version}
Status: {status}
Brief: {brief}
Error / alarm codes to cover: {error_codes}
Related articles to cross-reference: {related}

Structure guidance: {guidance}"""


def build_chain():
    """prompt | model.with_structured_output(Article)  -> returns an Article object."""
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", HUMAN_PROMPT)])
    llm = ChatOpenAI(model=os.environ["OPENAI_MODEL"], max_retries=3)
    return prompt | llm.with_structured_output(Article)


def seed_to_inputs(seed: Seed) -> dict:
    titles = {s.kb_id: s.title for s in SEEDS}
    return {
        "brand": BRAND,
        "facts": DOMAIN_FACTS[seed.domain],
        "kb_id": seed.kb_id,
        "title": seed.title,
        "article_type": seed.article_type,
        "product": seed.product,
        "version": seed.version,
        "status": seed.status,
        "brief": seed.brief,
        "error_codes": ", ".join(seed.error_codes) or "none",
        "related": ", ".join(f"{r} ({titles.get(r, '')})" for r in seed.related) or "none",
        "guidance": TYPE_GUIDANCE[seed.article_type],
    }


# =============================================================================
# 4. Renderers
# =============================================================================


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def output_path(seed: Seed) -> Path:
    return OUTPUT_ROOT / seed.domain / f"{seed.kb_id}_{slugify(seed.title)}.{seed.fmt}"


def metadata(seed: Seed) -> dict:
    """Flat metadata dict - embedded in every file and written to the manifest."""
    return {
        "kb_id": seed.kb_id,
        "title": seed.title,
        "domain": seed.domain,
        "article_type": seed.article_type,
        "product": seed.product,
        "version": seed.version,
        "status": seed.status,
        "superseded_by": seed.superseded_by or "",
        "last_updated": seed.last_updated,
        "error_codes": seed.error_codes,
        "related": seed.related,
        "tags": seed.tags,
        "author": f"{BRAND} Technical Support",
        "format": seed.fmt,
    }


def superseded_notice(seed: Seed) -> str | None:
    if seed.status != "superseded":
        return None
    return (f"NOTICE: This article applies to release {seed.version} and has been superseded by "
            f"{seed.superseded_by}. It is retained for customers still running release {seed.version}.")


# ---------------------------- Markdown ----------------------------


def _md_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_md(seed: Seed, art: Article) -> str:
    meta = metadata(seed)
    front = ["---"] + [f"{k}: {json.dumps(v)}" for k, v in meta.items()] + ["---", ""]
    out = front + [f"# {seed.title}", "",
                   f"**{seed.kb_id}** | {seed.product} {seed.version} | Last updated: {seed.last_updated} "
                   f"| Status: {seed.status}", ""]
    if notice := superseded_notice(seed):
        out += [f"> **{notice}**", ""]
    out += ["## Summary", "", art.summary, "", "**Applies to:** " + ", ".join(art.applies_to), ""]
    for sec in art.sections:
        out += [f"## {sec.heading}", ""]
        for p in sec.paragraphs:
            out += [p, ""]
        if sec.bullets:
            out += [f"- {b}" for b in sec.bullets] + [""]
        if sec.table:
            t = sec.table
            out += [f"*{t.caption}*", "",
                    "| " + " | ".join(_md_cell(h) for h in t.headers) + " |",
                    "|" + "---|" * len(t.headers)]
            out += ["| " + " | ".join(_md_cell(c) for c in row) + " |" for row in t.rows] + [""]
        if sec.code:
            out += [f"```{sec.code.language}", sec.code.content.rstrip(), "```", ""]
    if art.faqs:
        out += ["## Frequently Asked Questions", ""]
        for f in art.faqs:
            out += [f"**Q: {f.question}**", "", f"A: {f.answer}", ""]
    if seed.related:
        titles = {s.kb_id: s.title for s in SEEDS}
        out += ["## Related Articles", ""] + [f"- {r}: {titles.get(r, '')}" for r in seed.related] + [""]
    return "\n".join(out)


# ---------------------------- HTML ----------------------------

HTML_CSS = """
body{font-family:Segoe UI,Arial,sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem;color:#1d2733;line-height:1.55}
header{border-bottom:3px solid #0a5cad;margin-bottom:1rem} .brand{color:#0a5cad;font-weight:600}
.meta{color:#5b6773;font-size:.9rem} .notice{background:#fff4e5;border-left:4px solid #e08a00;padding:.75rem 1rem}
table{border-collapse:collapse;width:100%;margin:.5rem 0 1rem} th,td{border:1px solid #c9d2dc;padding:.4rem .6rem;text-align:left;vertical-align:top}
th{background:#eef3f8} caption{text-align:left;font-style:italic;padding:.25rem 0}
pre{background:#0f1720;color:#e6edf3;padding:.8rem;overflow-x:auto;border-radius:4px}
nav.breadcrumb{font-size:.85rem;color:#5b6773} footer{margin-top:2rem;border-top:1px solid #c9d2dc;font-size:.8rem;color:#5b6773}
"""


def render_html(seed: Seed, art: Article) -> str:
    e = html.escape
    meta = metadata(seed)
    meta_tags = "\n".join(
        f'  <meta name="{k}" content="{e(", ".join(v) if isinstance(v, list) else str(v))}">'
        for k, v in meta.items())
    body = [f'<nav class="breadcrumb">{BRAND} Support &rsaquo; Knowledge Base &rsaquo; {e(seed.product)}</nav>',
            "<header>", f'<div class="brand">{BRAND} Knowledge Base</div>', f"<h1>{e(seed.title)}</h1>",
            f'<p class="meta">{seed.kb_id} | {e(seed.product)} {seed.version} | Last updated: '
            f"{seed.last_updated} | Status: {seed.status}</p>", "</header>", "<article>"]
    if notice := superseded_notice(seed):
        body.append(f'<p class="notice"><strong>{e(notice)}</strong></p>')
    body += ["<h2>Summary</h2>", f"<p>{e(art.summary)}</p>",
             f"<p><strong>Applies to:</strong> {e(', '.join(art.applies_to))}</p>"]
    for sec in art.sections:
        body.append(f"<section><h2>{e(sec.heading)}</h2>")
        body += [f"<p>{e(p)}</p>" for p in sec.paragraphs]
        if sec.bullets:
            body.append("<ul>" + "".join(f"<li>{e(b)}</li>" for b in sec.bullets) + "</ul>")
        if sec.table:
            t = sec.table
            body.append(f"<table><caption>{e(t.caption)}</caption><thead><tr>"
                        + "".join(f"<th>{e(h)}</th>" for h in t.headers) + "</tr></thead><tbody>"
                        + "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in row) + "</tr>" for row in t.rows)
                        + "</tbody></table>")
        if sec.code:
            body.append(f'<pre><code class="language-{e(sec.code.language)}">{e(sec.code.content.rstrip())}'
                        "</code></pre>")
        body.append("</section>")
    if art.faqs:
        body.append("<section><h2>Frequently Asked Questions</h2>")
        body += [f"<h3>{e(f.question)}</h3><p>{e(f.answer)}</p>" for f in art.faqs]
        body.append("</section>")
    if seed.related:
        titles = {s.kb_id: s.title for s in SEEDS}
        body.append("<section><h2>Related Articles</h2><ul>"
                    + "".join(f"<li>{r}: {e(titles.get(r, ''))}</li>" for r in seed.related) + "</ul></section>")
    body += ["</article>", f"<footer>&copy; 2026 {BRAND}. Internal use only.</footer>"]
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n  <meta charset=\"utf-8\">\n"
            f"  <title>{seed.kb_id}: {e(seed.title)}</title>\n{meta_tags}\n"
            f"  <style>{HTML_CSS}</style>\n</head>\n<body>\n" + "\n".join(body) + "\n</body>\n</html>\n")


# ---------------------------- PDF ----------------------------


def render_pdf(seed: Seed, art: Article, path: Path) -> None:
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8, leading=10, alignment=TA_LEFT)
    cell_head = ParagraphStyle("cellhead", parent=cell, fontName="Helvetica-Bold")
    code_style = ParagraphStyle("code", parent=styles["Code"], fontSize=7.5, leading=9.5,
                                backColor=colors.HexColor("#f2f4f7"), borderPadding=4)
    meta_style = ParagraphStyle("meta", parent=styles["BodyText"], textColor=colors.HexColor("#5b6773"), fontSize=9)
    notice_style = ParagraphStyle("notice", parent=styles["BodyText"], backColor=colors.HexColor("#fff4e5"),
                                  borderPadding=6, textColor=colors.HexColor("#8a4b00"))
    x = xml_escape

    meta = metadata(seed)
    doc = SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
        title=f"{seed.kb_id}: {seed.title}", author=meta["author"],
        subject=f"{seed.product} {seed.version} | {seed.article_type} | status={seed.status}",
        # "key=value; key=value" - list values joined with "|" so the string stays parseable
        keywords="; ".join(f"{k}={'|'.join(v) if isinstance(v, list) else v}" for k, v in meta.items()
                           if k not in ("title", "author")),
        creator=f"{BRAND} KB Publisher",
    )
    width = doc.width

    story = [Paragraph(f"{BRAND} Knowledge Base", meta_style),
             Paragraph(x(seed.title), styles["Title"]),
             Paragraph(f"{seed.kb_id} | {x(seed.product)} {seed.version} | Last updated: {seed.last_updated} | "
                       f"Status: {seed.status}", meta_style), Spacer(1, 8)]
    if notice := superseded_notice(seed):
        story += [Paragraph(f"<b>{x(notice)}</b>", notice_style), Spacer(1, 8)]
    story += [Paragraph("Summary", styles["Heading2"]), Paragraph(x(art.summary), styles["BodyText"]),
              Paragraph(f"<b>Applies to:</b> {x(', '.join(art.applies_to))}", styles["BodyText"])]

    for sec in art.sections:
        story.append(Paragraph(x(sec.heading), styles["Heading2"]))
        story += [Paragraph(x(p), styles["BodyText"]) for p in sec.paragraphs]
        if sec.bullets:
            story.append(ListFlowable([ListItem(Paragraph(x(b), styles["BodyText"])) for b in sec.bullets],
                                      bulletType="bullet", leftIndent=12))
        if sec.table and sec.table.headers:
            t = sec.table
            ncols = len(t.headers)
            rows = [[Paragraph(x(h), cell_head) for h in t.headers]]
            rows += [[Paragraph(x(str(c)), cell) for c in (r + [""] * ncols)[:ncols]] for r in t.rows]
            tbl = Table(rows, colWidths=[width / ncols] * ncols, repeatRows=1)
            tbl.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d2dc")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story += [Spacer(1, 4), Paragraph(f"<i>{x(t.caption)}</i>", meta_style), tbl, Spacer(1, 6)]
        if sec.code:
            story += [Spacer(1, 4), Preformatted(sec.code.content.rstrip(), code_style, maxLineLength=110),
                      Spacer(1, 6)]

    if art.faqs:
        story.append(Paragraph("Frequently Asked Questions", styles["Heading2"]))
        for f in art.faqs:
            story += [Paragraph(f"<b>Q: {x(f.question)}</b>", styles["BodyText"]),
                      Paragraph(f"A: {x(f.answer)}", styles["BodyText"]), Spacer(1, 4)]
    if seed.related:
        titles = {s.kb_id: s.title for s in SEEDS}
        story.append(Paragraph("Related Articles", styles["Heading2"]))
        story += [Paragraph(f"{r}: {x(titles.get(r, ''))}", styles["BodyText"]) for r in seed.related]

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#5b6773"))
        canvas.drawString(18 * mm, 10 * mm, f"{BRAND} | {seed.kb_id} | Internal use only")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def write_article(seed: Seed, art: Article) -> Path:
    path = output_path(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    if seed.fmt == "md":
        path.write_text(render_md(seed, art), encoding="utf-8")
    elif seed.fmt == "html":
        path.write_text(render_html(seed, art), encoding="utf-8")
    else:
        render_pdf(seed, art, path)
    return path


def write_manifest(domain: str) -> Path:
    entries = []
    for seed in (s for s in SEEDS if s.domain == domain):
        path = output_path(seed)
        if path.exists():
            entries.append({**metadata(seed), "file": path.name})
    manifest = {"brand": BRAND, "domain": domain,
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "article_count": len(entries), "articles": entries}
    out = OUTPUT_ROOT / domain / "manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out


# =============================================================================
# 5. Main
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Generate synthetic {BRAND} KB articles.")
    parser.add_argument("--domain", choices=["networking", "meetings", "all"], default="all")
    parser.add_argument("--force", action="store_true", help="Regenerate articles that already exist")
    parser.add_argument("--concurrency", type=int, default=4, help="Parallel LLM calls")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    domains = ["networking", "meetings"] if args.domain == "all" else [args.domain]
    seeds = [s for s in SEEDS if s.domain in domains]

    todo = []
    for s in seeds:
        if output_path(s).exists() and not args.force:
            print(f"[skip]  {s.kb_id}  (exists: {output_path(s).relative_to(PROJECT_ROOT)})")
        else:
            todo.append(s)

    if todo:
        print(f"Generating {len(todo)} article(s) with model '{os.environ['OPENAI_MODEL']}'...")
        chain = build_chain()
        results = chain.batch([seed_to_inputs(s) for s in todo],
                              config={"max_concurrency": args.concurrency}, return_exceptions=True)
        for seed, result in zip(todo, results):
            if isinstance(result, Exception):
                print(f"[fail]  {seed.kb_id}  {type(result).__name__}: {result}")
                continue
            print(f"[ok]    {seed.kb_id}  -> {write_article(seed, result).relative_to(PROJECT_ROOT)}")

    for d in domains:
        print(f"[manifest] {write_manifest(d).relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
