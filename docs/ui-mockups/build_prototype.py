"""Build the clickable prototype (docs/ui-mockups/prototype/) from the Google Stitch export.

    uv run docs/ui-mockups/build_prototype.py [--screenshots]

The Stitch screens are copied, never edited in place. On each copy this script:
  - wires navigation   (data-href / data-toast hooks handled by prototype/assets/prototype.js)
  - fixes the shell     (inline SVG logo, initials avatar, API-backed top nav, demo-user hooks)
  - aligns the copy     (real API fields and values, no real vendor/product names, RBAC-consistent data)
  - adds hooks          (ids / data-* attributes for the light behaviours in prototype.js)
and writes index.html, a gallery of all screens. Re-run it after re-exporting from Stitch.
Every anchor is checked: if Stitch output changes, the build stops and names the missing anchor.
"""

from __future__ import annotations

import copy
import html
import re
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

HERE = Path(__file__).resolve().parent
SRC = HERE / "stitch_netcore_assist_web_app"
OUT = HERE / "prototype"
LOGO = (OUT / "assets" / "logo.svg").read_text(encoding="utf-8")

SCREENS = [
    # file, stitch folder, data-screen, title, purpose, endpoints, things to try
    ("01-sign-in.html", "sign_in_netcore_assist", "signin", "Sign in",
     "Authenticate with an API key or pick a demo user; the role decides which KB articles the agent may use.",
     ["X-API-Key header (all agent endpoints)", "401 problem on a bad key"],
     ["Pick Alice / Bob / Carol", "Clear the key and press Continue (401 message)"]),
    ("02-new-chat.html", "new_chat_netcore_assist", "newchat", "New chat",
     "Empty state: compose a question, choose Plan or ReAct, set the request options.",
     ["POST /api/v1/agent/ask/stream", "body: question, mode, timeout_seconds, include_trace, bypass_cache"],
     ["Open the mode pill and the options (sliders) popover", "Click an example, then send (Enter)"]),
    ("03-live-run.html", "agent_working_netcore_assist", "liverun", "Live run (streaming)",
     "Progress while the agent works: plan, steps, tool calls and judge arrive as SSE events.",
     ["POST /api/v1/agent/ask/stream (SSE)", "events: accepted, plan, step, tool_call, trace, judge, result, done"],
     ["Watch step 2 finish and the answer become ready", "Press 'Stop watching' to simulate a disconnect"]),
    ("04-answer-insights.html", "answer_insights_netcore_assist", "answer", "Answer + insights",
     "The answer with citations and every detail of the run in the Insights panel.",
     ["AskResponse: plan, executed_plan, sources, judge, tool_calls, trace, cache, timings"],
     ["Switch the Insights tabs", "Click a citation chip to jump to its source"]),
    ("05-request-history.html", "request_history_netcore_assist", "history", "Request history",
     "All earlier requests with status filters; owners see their own, the admin sees everyone's.",
     ["GET /api/v1/agent/requests?status=&limit=&cursor="],
     ["Filter by status / mode / text", "Switch user in the review bar: Bob sees only his rows"]),
    ("06-request-detail.html", "request_detail_reconnect_netcore_assist", "detail", "Request detail / resume",
     "Reconnect after a dropped stream: missed events are replayed, then the stored result is shown.",
     ["GET /api/v1/agent/requests/{id}", "GET /api/v1/agent/requests/{id}/events + Last-Event-ID"],
     ["Watch the replay catch up", "Export JSON (sample payload)"]),
    ("07-error-states.html", "error_limit_states_netcore_assist", "errors", "Error & limit states",
     "How RFC 9457 problems are presented: 429, 504, 401 and 503.",
     ["application/problem+json: type, title, status, detail, instance, request_id"],
     ["Wait for the 429 countdown to re-enable send", "Expand the problem details"]),
    ("08-system-status.html", "system_status_telemetry_netcore_assist", "status", "System status (admin)",
     "Dependency readiness and key metrics for admins.",
     ["GET /health", "GET /ready", "GET /metrics (Prometheus)"],
     ["Refresh", "Switch to Bob: admin-only notice"]),
]
FILE_OF = {s[2]: s[0] for s in SCREENS}

FIXES = [
    "Logo: the broken remote image is replaced by an inline SVG logo; avatars are initials (nothing loads from "
    "googleusercontent).",
    "Top navigation: 'Diagnostic Stream / Topology & Telemetry / Audit Logs' (no backing API) became Chat | Requests.",
    "RBAC: KB-MTG-2006 is an internal article, so Bob (Employee) sees it as Internal, not Restricted; history is "
    "owner-scoped for non-admins; System status and the user filter are admin-only.",
    "Popovers that Stitch rendered open (mode, options) are closed by default and interactive.",
    "Real vendor and product names (Cisco, IOS-XE, PagerDuty, Langfuse, S3, OpsGenie) were removed; NetCore stays "
    "fictional.",
    "Invented telemetry and tools were replaced by what the API returns: SSE events instead of 'websocket', real "
    "tools (search_knowledge_base, search_web, federated_search, rewrite_query), judge thresholds 0.70 / 0.70 / "
    "0.60, cache similarity 0.90 and TTL 24 h, problem type URIs, request ids.",
    "Inconsistencies fixed: 2 tool calls for a 2-step plan, 'plan v1 (2 steps)', 4 replayed events, follow-up "
    "composer without attachment/scope chips.",
]


# ---------------------------------------------------------------- helpers


class AnchorError(RuntimeError):
    pass


def after_comment(soup: BeautifulSoup, text: str) -> Tag:
    """The element that follows the Stitch comment containing `text`."""
    for c in soup.find_all(string=lambda s: isinstance(s, Comment) and text in s):
        node = c.next_sibling
        while node is not None and not isinstance(node, Tag):
            node = node.next_sibling
        if node is not None:
            return node
    raise AnchorError(f"comment not found: {text!r}")


def by_text(root, text: str, name: str | None = None, exact: bool = True) -> Tag:
    """Innermost tag whose text equals (or contains) `text`."""
    matches = []
    for tag in root.find_all(name or True):
        value = " ".join(tag.get_text(" ", strip=True).split())
        if (value == text) if exact else (text in value):
            matches.append(tag)
    if not matches:
        raise AnchorError(f"text not found: {text!r}")
    return min(matches, key=lambda t: len(t.get_text()))


def sub(root, old: str, new: str, count: int | None = None) -> int:
    """Replace text inside text nodes (whitespace-normalised match)."""
    hits = 0
    for node in list(root.find_all(string=True)):
        if isinstance(node, Comment) or node.parent.name in ("script", "style"):
            continue
        text = " ".join(str(node).split())
        if old in text:
            node.replace_with(NavigableString(text.replace(old, new)))
            hits += 1
    if not hits:
        raise AnchorError(f"copy not found: {old!r}")
    if count is not None and hits != count:
        raise AnchorError(f"expected {count} matches for {old!r}, got {hits}")
    return hits


def wrap_text(root, text: str, element_id: str) -> Tag:
    """Wrap the text node containing `text` in <span id=...> (so JS can update it without touching icons)."""
    for node in root.find_all(string=True):
        if not isinstance(node, Comment) and text in " ".join(str(node).split()):
            span = BeautifulSoup("", "html.parser").new_tag("span", id=element_id)
            span.string = " ".join(str(node).split())
            node.replace_with(span)
            return span
    raise AnchorError(f"copy not found: {text!r}")


def frag(markup: str) -> Tag:
    return BeautifulSoup(markup, "html.parser")


def clickable(tag: Tag) -> Tag:
    """The link/button that contains `tag` (or the tag itself)."""
    return tag if tag.name in ("a", "button") else (tag.find_parent(["a", "button"]) or tag)


def set_href(tag: Tag, target: str) -> None:
    tag["data-href"] = target
    if tag.name == "a":
        tag["href"] = target
    tag.attrs.pop("onclick", None)


def toast(tag: Tag, message: str) -> None:
    tag["data-toast"] = message
    if tag.name == "a":
        tag["href"] = "#"


# ---------------------------------------------------------------- shared transforms


def common(soup: BeautifulSoup, key: str, title: str) -> None:
    if soup.title:
        soup.title.string = f"NetCore Assist · {title}"
    else:
        t = soup.new_tag("title")
        t.string = f"NetCore Assist · {title}"
        soup.head.insert(0, t)
    if "JetBrains+Mono" not in str(soup.head):  # Stitch's sign-in omits it -> mono labels fell back to serif
        soup.head.append(frag('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:'
                              'wght@400;500&amp;display=swap"/>'))
    soup.head.append(frag('<link rel="stylesheet" href="assets/prototype.css"/>'))
    soup.head.append(frag('<script defer src="assets/prototype.js"></script>'))
    soup.body["data-screen"] = key

    # images: logo -> inline SVG, people -> initials avatar
    for img in soup.find_all("img"):
        classes = " ".join(img.get("class", []))
        if "logo" in (img.get("alt") or "").lower():
            img.replace_with(frag(f'<span class="nc-logo" aria-label="NetCore Assist">{LOGO}</span>'))
        else:
            size = "w-8 h-8" if "w-8" in classes or not classes else " ".join(
                c for c in img.get("class", []) if re.match(r"(w|h)-", c))
            img.replace_with(frag(f'<span class="nc-avatar {size}" data-user-initial>B</span>'))

    aside = soup.find("aside")
    header = soup.find("header")
    if aside is None or header is None:
        return  # sign-in has no app shell

    # sidebar: new chat, search, history, system status, profile
    set_href(by_text(aside, "add New chat ⌘K", "button"), FILE_OF["newchat"])
    toast(aside.find("button", attrs={"aria-label": "Search queries"}),
          "Search filters your history (client-side over <code>GET /api/v1/agent/requests</code>).")
    targets = {"chat-session-active": "answer", "bgp-route-incident": "liverun", "qos-policy-review": "answer",
               "bfd-diagnostics": "answer", "core-switch-provisioning": "errors", "acl-rule-verification": "detail"}
    for a in aside.find_all("a", attrs={"data-path": True}):
        path = a["data-path"]
        if path == "system-status":
            set_href(a, FILE_OF["status"])
            a["data-admin-only"] = ""
        elif path in targets:
            set_href(a, FILE_OF[targets[path]])
    profile = aside.find("span", string=lambda s: s and s.strip() in ("Bob", "Carol"))
    if profile:
        profile["data-user-name"] = ""
        title_span = profile.find_next_sibling("span")
        if title_span:
            title_span["data-user-title"] = ""
        card = profile.find_parent("div", class_=lambda c: c and "rounded-xl" in c)
        if card:
            set_href(card, FILE_OF["signin"])
            card["title"] = "Sign out (back to sign-in)"
            badge = card.find("span", string=lambda s: s and s.strip() in ("Employee", "Admin"))
            if badge:
                badge["data-user-role"] = ""

    # header: API-backed top navigation
    nav = header.find("nav")
    active_class = "transition-colors text-on-surface font-semibold font-label-md text-label-md"
    idle_class = "font-label-md text-label-md text-on-surface-variant hover:text-on-surface transition-colors"
    chat_active = key in ("newchat", "liverun", "answer", "errors")
    req_active = key in ("history", "detail")
    nav.clear()
    nav.append(frag(f'<a class="{active_class if chat_active else idle_class}" href="{FILE_OF["newchat"]}" '
                    f'data-href="{FILE_OF["newchat"]}">Chat</a>'))
    nav.append(frag(f'<a class="{active_class if req_active else idle_class}" href="{FILE_OF["history"]}" '
                    f'data-href="{FILE_OF["history"]}">Requests</a>'))
    help_btn = header.find("button", attrs={"aria-label": re.compile("Help")})
    if help_btn:
        set_href(help_btn, "index.html")
        help_btn["title"] = "Prototype index"


# ---------------------------------------------------------------- per-screen transforms


def signin(soup: BeautifulSoup) -> None:
    error = after_comment(soup, "Inline Error Feedback State")
    error["id"] = "nc-key-error"
    error["class"] = error.get("class", []) + ["nc-hidden"]
    for user in ("alice", "bob", "carol"):
        card = soup.find("button", attrs={"onclick": re.compile(f"selectUser\\('{user}'")})
        card["data-user-card"] = user
        card["class"] = card.get("class", []) + ["user-card"]
    bob = soup.find("button", attrs={"data-user-card": "bob"}).find(attrs={"data-user-initial": True})
    alice = by_text(soup.find("button", attrs={"data-user-card": "alice"}), "A", "div")
    if bob:  # the Stitch photo became an initials avatar: Bob's, styled like Alice's
        bob.replace_with(frag(f'<div class="{" ".join(alice.get("class", []))}">B</div>'))
    sub(soup, "Zero Trust SD-WAN", "RBAC: guest · employee · admin")
    sub(soup, "v2.4.12-rc", "API v0.7.0")
    for a in soup.select("footer a"):
        toast(a, f"{a.get_text(strip=True)}: placeholder page (not part of the prototype).")


def newchat(soup: BeautifulSoup) -> None:
    for pid in ("mode-popover", "options-popover"):
        pop = soup.find(id=pid)
        pop["class"] = pop.get("class", []) + ["nc-hidden"]
        pop["data-popover"] = ""
    for bid in ("mode-pill-btn", "options-trigger-btn"):
        soup.find(id=bid)["aria-expanded"] = "false"
    soup.find(id="mode-pill-btn").find("span")["id"] = "nc-mode-label"
    plan = after_comment(soup, "Option 1: Plan")
    plan["data-mode"] = "plan"
    plan.find("span", class_="material-symbols-outlined")["data-check"] = ""
    react = after_comment(soup, "Option 2: ReAct")
    react["data-mode"] = "react"
    placeholder = react.find("span")
    placeholder.replace_with(frag('<span class="material-symbols-outlined text-[18px] text-primary shrink-0 mt-0.5" '
                                  'data-check style="visibility:hidden">check</span>'))
    sub(soup, "Execution Strategy", "Mode (request field: mode)")
    sub(soup, "The agent routes itself with tools and reasoning cycles", "The agent routes itself with tools")
    # time budget slider -> real range input
    slider = after_comment(soup, "Time Budget Slider")
    value = by_text(slider, "120 s", "span")
    value["id"] = "nc-budget-label"
    track = value.find_parent("div").find_next_sibling("div")
    track.replace_with(frag('<input id="nc-budget" type="range" min="10" max="300" step="5" value="120" '
                            'class="w-full accent-black" aria-label="Time budget (timeout_seconds)"/>'))
    sub(soup, "Tier 3 NetOps", "request options")
    sub(soup, "Streams live CLI query telemetry", "include_trace: trace[] and tool_calls[]")
    sub(soup, "Forces full LLM reasoning path", "bypass_cache: skip the semantic-cache lookup")
    sub(soup, "Time budget", "Time budget (timeout_seconds)")
    send = soup.find("button", attrs={"aria-label": "Send diagnostic request"})
    send["id"] = "nc-send"
    for chip in soup.find_all("button", class_=lambda c: c and "rounded-full" in c and "justify-between" in c):
        text = chip.find("span").get_text(strip=True)
        if text and "?" in text:
            chip["data-example"] = text
    sub(soup, "Diagnose SD-WAN fabric, analyze route telemetry, or orchestrate policy changes.",
        "Answers from the NetCore knowledge base (SD-WAN, Meet and Calling) with a visible plan, sources and a "
        "quality judge.")
    env = by_text(soup, "Environment: Production Backbone East-01", "span")
    env.replace_with(frag('<span>Signed in as <b data-user-name>Bob</b> · sees <span data-user-levels>public + '
                          'internal</span> articles</span>'))
    sub(soup, "v4.19-orchestrator", "API v0.7.0")
    sub(soup, "BGP Mesh: 142/142 Up", "GET /ready: Chroma ✓ · Redis ✓ · Postgres ✓")
    sub(soup, "SLA Index: 99.98%", "rate limit 100 req/min per IP")
    sub(soup, "Session token: nc-sess-4102-rt", "X-API-Key: ••••••••")


def liverun(soup: BeautifulSoup) -> None:
    sub(soup, "INCIDENT #NC-89410", "POST /api/v1/agent/ask/stream")
    sub(soup, "SD-WAN Voice Tier", "mode: plan")
    sub(soup, "Edge: NCX-BOS-04", "text/event-stream")
    bubble = by_text(soup, "Our NetCore Meet calls show MTG-MED-4102 packet loss at branch sites. Which SD-WAN QoS "
                           "settings and SLA class should we apply, and what does the Meet troubleshooting guide "
                           "recommend?", "p")
    bubble["id"] = "nc-question"
    sub(soup, "09:41 AM · Tier-3 NetOps", "09:41 · you")
    after_comment(soup, "Running Badge")["id"] = "nc-run-badge"
    stop = by_text(soup, "Stop watching", "button")
    stop["id"] = "nc-stop"
    copy_btn = soup.find("button", attrs={"aria-label": "Copy Request ID"})
    toast(copy_btn, "Request id copied: <code>2f13a1af-1efb-4c29-9d33-728b94091a11</code>")
    sub(soup, "DAG: 2 nodes", "2 steps")
    sub(soup, "Execution Plan v1", "Plan v1")
    after_comment(soup, "Section: Plan v1")["id"] = "nc-plan-section"
    step2 = after_comment(soup, "Step 2 (Active/Running)")
    step2["id"] = "nc-step2"
    icon = step2.find("span", string=lambda s: s and s.strip() == "sync")
    icon["data-step-icon"] = ""
    domain = by_text(step2, "domain: meetings", "span")
    tool = copy.copy(by_text(soup.find(string=lambda s: isinstance(s, Comment) and "Step 1" in s).find_next("div"),
                             "search_knowledge_base", "span"))
    domain.insert_before(tool)
    status = by_text(step2, "running…", "span", exact=False).find_parent("div")
    status["data-step-status"] = ""
    sub(step2, "evaluating fallback policies", "reranking candidates")
    log_box = after_comment(soup, "Collapsible Live Activity Log")
    sub(log_box, "Telemetry & Agent Stream", "Live activity (event: trace)")
    sub(log_box, "3 active trace spans", "streaming")
    sub(log_box, "plan v1 · 2 steps compiled", "plan v1 · 2 steps")
    sub(log_box, "3/6 pass (threshold 0.60) · Cisco Catalyst vBond", "3/6 pass (threshold 0.60)")
    sub(log_box, "evaluating SLA fallback convergence…", "waiting for step 2…")
    lines = log_box.find_all("div", recursive=False)
    lines[-1]["id"] = "nc-log"
    skeleton = after_comment(soup, "Answer Streaming Skeleton Placeholder")
    skeleton["id"] = "nc-skeleton"
    sub(skeleton, "Synthesizing Answer Stream", "Writing the answer (after the judge and output guardrails)")
    # right panel: invented site telemetry -> the SSE event feed the API actually sends
    panel = after_comment(soup, "Right-Hand Contextual Inspector")
    events = [("1794241086028-0", "accepted", "request_id 2f13a1af… · user bob · mode plan"),
              ("1794241087573-0", "trace", "Input guardrails · allowed"),
              ("1794241087579-0", "trace", "Semantic cache · miss"),
              ("1794241090340-0", "plan", "v1 · 2 steps · networking + meetings"),
              ("1794241090378-0", "step", "step 1 running"),
              ("1794241094793-0", "step", "step 1 done · 3 relevant · best 0.92"),
              ("1794241094794-0", "tool_call", "search_knowledge_base · planner · done · 4.1 s"),
              ("1794241094796-0", "step", "step 2 running")]
    rows = "".join(
        f'<div class="flex items-start gap-2 py-1.5 border-b border-[#ECECEC] last:border-0">'
        f'<span class="font-code-sm text-code-sm text-outline whitespace-nowrap shrink-0">{eid}</span>'
        f'<span class="px-1.5 rounded bg-surface-container-high font-code-sm text-code-sm shrink-0">{etype}</span>'
        f'<span class="font-body-sm text-body-sm text-on-surface-variant">{html.escape(text)}</span></div>'
        for eid, etype, text in events)
    panel.clear()
    panel.append(frag(
        '<div class="h-14 px-space-lg flex items-center justify-between border-b border-[#ECECEC]">'
        '<div class="flex items-center gap-2"><span class="material-symbols-outlined text-[18px]">stream</span>'
        '<span class="font-label-md text-label-md font-semibold">Live events (SSE)</span></div>'
        '<span class="px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 font-label-sm text-label-sm">streaming</span>'
        '</div><div class="p-space-lg space-y-3">'
        '<p class="font-body-sm text-body-sm text-secondary">Each event has an <code>id</code>. If the connection '
        'drops, resume with <code>GET /requests/{id}/events</code> and <code>Last-Event-ID</code>.</p>'
        f'<div id="nc-events" class="max-h-[60vh] overflow-y-auto">{rows}</div></div>'))
    hint = by_text(soup, "Answer in progress… you can safely leave; resume anytime", "span")
    hint["id"] = "nc-composer-hint"
    soup.find("input", attrs={"placeholder": "Agent is synthesizing remediation script..."})["placeholder"] = \
        "Waiting for the answer…"
    sub(soup, "AI-generated, for reference only · NetCore Assist OS v4.2", "AI-generated, for reference only")


def answer(soup: BeautifulSoup) -> None:
    sub(soup, "Verified Resolution Pattern", "Answer")
    by_text(soup, "BO", "div")["data-user-initial"] = ""
    sub(soup, "Tier 3 SD-WAN", "answered")
    answer_box = by_text(soup, "Answer", "span").find_parent("div").find_parent("div").find_parent("div")
    answer_box["id"] = "nc-answer"
    for a in soup.find_all("a", href=re.compile("^#kb-")):
        a["data-cite"] = a["href"][1:]
    for chip_text, cite in (("KB-NET-1010 · p.3", "kb-1010"), ("KB-MTG-2006 · chunk 2", "kb-2006")):
        chip = by_text(soup, chip_text, "span").find_parent("span")
        chip["data-cite"] = cite
        chip["title"] = "Show this source"
    soup.find("button", attrs={"aria-label": "Copy Answer"})["id"] = "nc-copy-answer"
    for label in ("Helpful response", "Unhelpful response"):
        toast(soup.find("button", attrs={"aria-label": label}),
              "Feedback captured in the UI only: the API has no feedback endpoint yet.")
    set_href(by_text(soup, "View request arrow_outward", "button"), FILE_OF["detail"])

    # Insights tabs -> panels
    for button in by_text(soup, "Plan Sources Judge Tool calls Trace Timing", "div").find_all("button"):
        button["data-tab"] = {"Plan": "plan", "Sources": "sources", "Judge": "judge", "Tool calls": "tools",
                              "Trace": "trace", "Timing": "timing"}[button.get_text(strip=True)]
    judge = after_comment(soup, "Active Tab Content: Judge")
    judge["data-panel"] = "judge"
    sources = after_comment(soup, "Preview Stack: Sources Card")
    sources["data-panel"] = "sources"
    tools = after_comment(soup, "Preview Stack: Tool Calls Card")
    tools["data-panel"] = "tools"
    timing = after_comment(soup, "Preview Stack: Timing Breakdown Card")
    timing["data-panel"] = "timing"
    sub(judge, "Synthesized Judge Evaluation", "Judge LLM")

    # RBAC: KB-MTG-2006 is internal (employee-visible), not restricted
    restricted = by_text(sources, "Restricted", "span")
    internal = by_text(sources, "Internal", "span")
    restricted.string = "Internal"
    restricted["class"] = internal.get("class", [])
    by_text(sources, "KB-NET-1010", "span").find_parent("div").find_parent("div")["id"] = "kb-1010"
    by_text(sources, "KB-MTG-2006", "span").find_parent("div").find_parent("div")["id"] = "kb-2006"

    # 2-step plan -> 2 tool calls
    sub(tools, "1 call", "2 calls")
    row = by_text(tools, "search_knowledge_base", "div")
    while "4.1 s" not in row.get_text():
        row = row.find_parent("div")
    second = copy.copy(row)
    sub(second, "4.1 s", "3.6 s")
    by_text(second, "planner · done", "div").string = "planner · done · meetings"
    by_text(row, "planner · done", "div").string = "planner · done · networking"
    row.insert_after(second)
    sub(timing, "Agent Generation", "Agent (agent_s)")
    sub(timing, "Queued / Network Ingress", "Queued (queued_s)")

    # new panels the API provides: plan and trace
    step = ('<div class="flex items-start gap-3 p-3 rounded-lg bg-surface-container-low">'
            '<span class="material-symbols-outlined text-[18px] text-emerald-600">check_circle</span>'
            '<div class="min-w-0"><div class="font-label-md text-label-md">{n}. {goal}</div>'
            '<div class="font-code-sm text-code-sm text-secondary">search_knowledge_base · {dom} · “{q}”</div>'
            '<div class="font-body-sm text-body-sm text-outline">done · {rel} relevant · best {best} · {s} s</div>'
            '</div></div>')
    plan_panel = frag(
        '<div data-panel="plan" class="p-space-lg space-y-3">'
        '<div class="flex items-center justify-between"><span class="font-label-md text-label-md font-semibold">'
        'Plan v1</span><span class="font-code-sm text-code-sm text-outline">0 re-plans</span></div>'
        '<p class="font-body-sm text-body-sm text-secondary">Split into networking QoS/SLA and Meet '
        'troubleshooting</p>'
        + step.format(n=1, goal="SD-WAN QoS and SLA class for voice", dom="networking",
                      q="SD-WAN QoS SLA class voice packet loss", rel=3, best="0.92", s="4.1")
        + step.format(n=2, goal="Meet troubleshooting for MTG-MED-4102", dom="meetings",
                      q="MTG-MED-4102 troubleshooting", rel=2, best="0.88", s="3.6")
        + '<p class="font-body-sm text-body-sm text-outline">Routes: vector, vector · cache: miss</p></div>')
    trace_rows = [("0.10", "Request", "bob · role=employee · mode=plan"), ("1.52", "Input guardrails", "allowed"),
                  ("1.56", "Semantic cache", "miss"), ("4.31", "Planner", "plan v1 · 2 steps"),
                  ("8.40", "Plan executor", "step 1 done · 3 relevant, best 0.92"),
                  ("12.0", "Plan executor", "step 2 done · 2 relevant, best 0.88"),
                  ("14.2", "Context optimizer", "5 chunks · 2 980 tokens"),
                  ("52.9", "Judge LLM", "pass {faithfulness 1.0, groundedness 1.0, precision 1.0}"),
                  ("53.4", "Output guardrails", "pass"), ("53.5", "Cache write", "stored · scope=internal"),
                  ("63.1", "Response", "answered")]
    trace_panel = frag(
        '<div data-panel="trace" class="p-space-lg"><div class="rounded-xl bg-[#1E1E1E] text-neutral-200 p-4 '
        'font-code-sm text-code-sm space-y-1 overflow-x-auto">'
        + "".join(f'<div class="flex gap-3"><span class="text-neutral-500 w-12 text-right shrink-0">{t}s</span>'
                  f'<span class="text-sky-300 w-32 shrink-0">{html.escape(s)}</span>'
                  f'<span>{html.escape(d)}</span></div>' for t, s, d in trace_rows)
        + "</div></div>")
    judge.insert_before(plan_panel)
    timing.insert_after(trace_panel)

    # follow-up composer: no attachment / invented scope chips (not API fields)
    composer = after_comment(soup, "Bottom Floating Execution Composer")
    scope = by_text(composer, "tune Scope: Site-B12", "button")
    scope.replace_with(frag('<button type="button" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full '
                            'bg-surface-container-high font-label-md text-label-md" data-href="02-new-chat.html">'
                            'Plan <span class="material-symbols-outlined text-[16px]">expand_more</span></button>'))
    by_text(composer, "router Target: NCX-1002", "button").decompose()
    by_text(composer, "attach_file", "button").decompose()
    composer.find("textarea")["placeholder"] = "Ask a follow-up question…"
    set_href(composer.find("button", attrs={"aria-label": "Send Query"}), FILE_OF["liverun"])


def history(soup: BeautifulSoup) -> None:
    sub(soup, "8 active sessions", "GET /api/v1/agent/requests")
    sub(soup, "Active Mode", "Scope")
    wrap_text(soup, "Dual Agent", "nc-scope").string = "Admin: all users"
    search = soup.find("input", attrs={"type": re.compile("text|search")})
    search["id"] = "nc-search"
    search["placeholder"] = "Search questions…"
    after_comment(soup, "Admin User Selector Dropdown")["data-admin-only"] = ""
    rows = {
        1: ("running", "bob", "plan", "liverun"), 2: ("completed", "alice", "plan", "answer"),
        3: ("client_disconnected", "carol", "react", "detail"), 4: ("completed", "bob", "plan", "answer"),
        5: ("completed", "carol", "plan", "answer"), 6: ("timeout", "bob", "react", "errors"),
        7: ("completed", "alice", "plan", "answer"), 8: ("completed", "carol", "plan", "answer"),
    }
    for n, (status, owner, mode, target) in rows.items():
        tr = after_comment(soup, f"Row {n}:")
        tr["data-status"], tr["data-owner"], tr["data-mode"] = status, owner, mode
        set_href(tr, FILE_OF[target])
    set_href(clickable(by_text(soup, "Resume", exact=False)), FILE_OF["detail"])
    sub(soup, "Client session terminated at step 3/7 during route-map dampening analysis.",
        "Client left after 3 tool calls; the run continued on the server and its result is stored.")
    sub(soup, "Partial", "Answered")
    sub(soup, "Execution deadline exceeded while waiting for multi-chassis LACP bundle telemetry reply.",
        "No result within the time budget (504 agent-timeout); the run may still finish.")
    sub(soup, "triggering PagerDuty Sev1", "escalates to Sev1")
    sub(soup, "Recommends DSCP 46 (EF) mapping for RTP media streams and CS3/AF31 for SIP payload signaling.",
        "Recommends DSCP 46 (EF) for voice media [KB-NET-1010].")
    tbody = soup.find("tbody")
    cols = len(soup.find("thead").find_all("th")) if soup.find("thead") else 7
    tbody.append(frag(f'<tr id="nc-empty" class="nc-hidden"><td colspan="{cols}" class="py-10 text-center '
                      'font-body-md text-body-md text-secondary">No requests match these filters.</td></tr>'))
    toast(by_text(soup, "Load more expand_more", "button"),
          "Next page: <code>GET /api/v1/agent/requests?cursor=&lt;next_cursor&gt;</code>")
    footer = after_comment(soup, "Administrative Quick Access & Telemetry Footprint")
    sub(footer, "Edge Node Sync", "Owner-scoped")
    sub(footer, "Connected to 14 Cisco SD-WAN controllers", "Non-admins see only their own requests (others: 404)")
    sub(footer, "Admin Audit Active", "Stored results")
    sub(footer, "Logging all ReAct CLI generation calls", "agent_runs in Postgres, PII-redacted")
    sub(footer, "SLA Engine: V2", "Replay buffer")
    sub(footer, "Real-time telemetry sampling at 1000ms", "Live events kept 1 h (Redis Streams)")


def detail(soup: BeautifulSoup) -> None:
    for text, target in (("arrow_back", "history"), ("Requests", "history")):
        el = by_text(after_comment(soup, "Top Breadcrumb Navigation"), text, exact=False)
        set_href(clickable(el), FILE_OF[target])
    set_href(by_text(soup, "refresh Re-run Pipeline", "button"), FILE_OF["newchat"])
    sub(soup, "Re-run Pipeline", "Ask again")
    by_text(soup, "download Export JSON", "button")["id"] = "nc-export"
    banner = after_comment(soup, "Amber Reconnect Banner")
    sub(banner, "Replaying 6 missed events", "Replaying 4 missed events")
    wrap_text(banner, "Replaying 4 missed events", "nc-replay-count")
    sub(banner, ", but the agent kept working in headless background isolation. Stream reconstructed successfully.",
        ", but the run continued on the server (it is decoupled from the HTTP connection). Missed events are "
        "replayed from the Redis Stream after your Last-Event-ID.")
    buffer = after_comment(soup, "Replay Buffer Bar")
    wrap_text(buffer, "100% (6/6)", "nc-buffer-pct")
    bar = buffer.find("div", style=re.compile("width")) or buffer.find_all("div")[-1]
    bar["id"] = "nc-buffer-bar"
    live = after_comment(soup, "Live Status Pill")
    live["id"] = "nc-live-pill"
    live["class"] = live.get("class", []) + ["nc-hidden"]
    sub(soup, "Under 90s SLA", "budget 240 s")
    sub(soup, "Bearer token verified for tenant", "X-API-Key verified · user bob (employee)")
    sub(soup, "prod-us-east-1", "")
    sub(soup, "plan v1 (1 step)", "plan v1 (2 steps)")
    sub(soup, "Plan decomposed into 2 sub-goals: Policy audit and DSCP QoS jitter verification.",
        "Networking QoS/SLA (step 1) and Meet troubleshooting (step 2).")
    sub(soup, "Client websocket dropped at 00:18.9 · Background headless processing engaged",
        "SSE connection dropped at 00:18.9 · the run continues on the server")
    sub(soup, "passed confidence threshold (>0.85). Verification accepted.",
        " ≥ 0.70; groundedness 1.00 ≥ 0.70; context precision 1.00 ≥ 0.60 → accept")
    sub(soup, "Synthesizing markdown answer with remediation script blocks.",
        "AskResponse: agent_status answered, judge passed, 2 sources.")
    sub(soup, "Stream closed gracefully. Final state preserved in Redis cluster",
        "Stream closed. Result stored in Postgres (agent_runs); events kept 1 h in Redis Streams")
    sub(soup, "cache-node-02", "")
    for n in (4, 5, 6, 7):
        event = after_comment(soup, f"Event {n}:")
        event["class"] = event.get("class", []) + ["nc-replay", "nc-pending"]
    card = after_comment(soup, "Final Verified Answer Output Card")
    set_href(clickable(by_text(card, "Open full insights", exact=False)), FILE_OF["answer"])
    sub(card, "Integrity Verified", "Judge passed")
    sub(card, "NCX-1002 (GigabitEthernet0/0/1)", "branch NCX edges")
    sub(card, "REMEDIATION CONFIG · CISCO-IOS-XE", "sdwan-cli · edge-template")
    code = after_comment(soup, "Inline Code Container")
    pre = code.find("pre") or code
    pre.clear()
    pre.append("policy qos VOICE-POLICY\n  class CLASS-VOICE-EF\n    set dscp ef\n    priority percent 30\n"
               "  sla-profile SLA-GOLD-VOICE\n    latency 150\n    jitter 10\n    loss 0.5")
    expired = after_comment(soup, "Empty-State / Edge-Case Variant Card")
    sub(expired, "Real-time token streaming steps are archived into cold telemetry storage.",
        "Resume then replays only result + done from Postgres.")
    link = by_text(expired, "View raw audit dump in Cold Tier open_in_new", exact=False)
    sub(expired, "View raw audit dump in Cold Tier", "GET /api/v1/agent/requests/{id}")
    toast(clickable(link),
          "Returns status + the stored AskResponse (owner or admin only).")


def errors(soup: BeautifulSoup) -> None:
    for script in soup.find_all("script"):
        if "countdown" in script.get_text():
            script.decompose()  # prototype.js runs the countdown and re-enables send
    sub(soup, "Live telemetry simulation of client-facing network edge exceptions across the conversational agent "
              "runtime.", "How the UI presents RFC 9457 problem details returned by the API.")
    sub(soup, "cluster: edge-us-east-04", "application/problem+json")
    toast(by_text(soup, "refresh Re-poll endpoints", "button"), "Re-polled <code>GET /ready</code>.")
    sub(soup, "Re-poll endpoints", "Re-check")
    # 429
    disabled = after_comment(soup, "Disabled circular action button")
    disabled["id"] = "nc-429-send"
    tip = after_comment(soup, "Prominent Tooltip Overlay")
    tip["id"] = "nc-429-tip"
    tip.find(string=re.compile("Rate limit active")).parent["data-retry-seconds"] = ""
    sub(soup, "Ask NetCore Assist a question or run traceroute analysis...", "Ask NetCore Assist a question…")
    sub(soup, "Scope: SD-WAN | BGP-v4", "Plan") if _has(soup, "Scope: SD-WAN | BGP-v4") else None
    for old in ("Scope: SD-WAN", "BGP-v4"):
        if _has(soup, old):
            if old == "BGP-v4":
                clickable(by_text(soup, "BGP-v4")).decompose()
            else:
                sub(soup, old, "Plan")
    sub(soup, "https://api.netcore.internal/errors/rate-limited", "https://netcore.example/problems/rate-limited")
    sub(soup, "Exceeded 100 req/min quota for NetOps tier.",
        "Rate limit of 100 requests/minute exceeded; this IP is blocked for 30 s.")
    # 504
    sub(soup, "The agent exceeded its allocated 120s time budget while querying the topology vector store. The "
              "answer may still finish in the background.",
        "No result within the 120 s budget + 15 s grace. The run may still finish in the background: its "
        "result_url stays valid.")
    telemetry = after_comment(soup, "Vector store progress telemetry visual")
    telemetry.clear()
    telemetry.append(frag(
        '<div class="rounded-lg bg-surface-container-low p-3 font-code-sm text-code-sm space-y-1">'
        '<div><span class="text-outline">status</span> running</div>'
        '<div><span class="text-outline">request_id</span> 7c1e09d2-55aa-4b8e-9f10-2a4c6d8e0b31</div>'
        '<div><span class="text-outline">result_url</span> /api/v1/agent/requests/7c1e09d2…</div></div>'))
    set_href(by_text(soup, "hourglass_bottom Check result later", "button"), FILE_OF["detail"])
    set_href(clickable(by_text(soup, "Try again with a longer time budget", exact=False)), FILE_OF["newchat"])
    # 401
    sub(soup, "AUTH_EXPIRED", "unauthorized")
    sub(soup, "API secret key expired or lacks authorization for SD-WAN cluster policy telemetry.",
        "Missing or invalid API key. Send a valid key in the X-API-Key header.")
    sub(soup, "Tokens automatically invalidate after 12h of inactive Tier 3 diagnostic duty.",
        "Keys are configured by your admin (API_KEYS); ask them to issue or rotate yours.")
    set_href(clickable(by_text(soup, "Sign in again", exact=False)), FILE_OF["signin"])
    # 503
    sub(soup, "failover: eu-west-01 pending", "GET /ready → 503 not-ready")
    toast(by_text(soup, "refresh Retry", "button"), "Retrying <code>GET /ready</code>… Chroma still unreachable.")
    # footer note: invented policy, vault, incident tools
    note = after_comment(soup, "Bottom contextual guidance note")
    note.clear()
    note.append(frag('<div class="flex items-center gap-2 font-body-sm text-body-sm text-secondary">'
                     '<span class="material-symbols-outlined text-[18px]">shield</span>Every error is RFC 9457 '
                     '<code>application/problem+json</code> with a <code>request_id</code>; quote it to support.'
                     '</div>'))


def _has(soup: BeautifulSoup, text: str) -> bool:
    return any(text in " ".join(str(s).split()) for s in soup.find_all(string=True))


def status(soup: BeautifulSoup) -> None:
    for script in soup.find_all("script"):
        if "switcher to Carol" in script.get_text():
            script.decompose()  # the demo user comes from the review bar
    wrap_text(soup, "checked 5 s ago", "nc-checked")
    sub(soup, "Cluster: us-east-prod-04", "GET /ready · GET /metrics")
    for card, value in (("Card 1: Chroma Vector DB", "24"), ("Card 2: Redis Semantic Cache", "2.1"),
                        ("Card 3: Postgres Audit DB", "8.4")):
        span = wrap_text(after_comment(soup, card), value, f"nc-lat-{value.replace('.', '-')}")
        span["data-latency"] = value
    sub(soup, "2.4M embeddings", "2 databases · 194 chunks")
    sub(soup, "HNSW cos_dist", "chromadb 1.5.9")
    sub(soup, "99.98% hit reliability", "semantic cache · similarity ≥ 0.90")
    sub(soup, "TTL 48h active", "TTL 24 h")
    sub(soup, "WAL replication sync", "api_requests · agent_runs")
    sub(soup, "Lag: 0 B", "Alembic 0001")
    sub(soup, "threshold ≥85%", "thresholds 0.70 / 0.70 / 0.60")
    sub(soup, "Semantic cosine ≥0.92", "similarity ≥ 0.90")
    sub(soup, "Response durations tracked through Langfuse proxy", "agent_run_duration_seconds (Prometheus)")
    for old, new in (("query_telemetry_influx", "search_web"), ("bfd_diagnostic_check", "rewrite_query"),
                     ("sdwan_policy_evaluator", "federated_search")):
        sub(soup, old, new)
    sub(soup, "Target pool: 12 nodes", "single API instance")


TRANSFORMS = {"signin": signin, "newchat": newchat, "liverun": liverun, "answer": answer, "history": history,
              "detail": detail, "errors": errors, "status": status}


# ---------------------------------------------------------------- index.html


def thumb(file: str, folder: str) -> str:
    """Prototype screenshot when available (--screenshots), else the Stitch original."""
    shot = OUT / "assets" / "shots" / file.replace(".html", ".png")
    return f"assets/shots/{shot.name}" if shot.exists() else f"../stitch_netcore_assist_web_app/{folder}/screen.png"


def screenshots() -> None:
    """Capture each prototype page with headless Edge/Chrome (optional; used as index thumbnails)."""
    import subprocess
    candidates = [Path(p) for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                                    "/usr/bin/google-chrome", "/usr/bin/chromium",
                                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    browser = next((p for p in candidates if p.exists()), None)
    if browser is None:
        print("  screenshots skipped: no Edge/Chrome found")
        return
    shots = OUT / "assets" / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    profile = shots / ".profile"
    for file, *_ in SCREENS:
        subprocess.run([str(browser), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=1440,900", "--virtual-time-budget=9000", f"--user-data-dir={profile}",
                        f"--screenshot={shots / file.replace('.html', '.png')}", (OUT / file).as_uri()],
                       capture_output=True, timeout=120)
        print(f"  screenshot {file}")
    import shutil
    shutil.rmtree(profile, ignore_errors=True)


def index_html() -> str:
    cards = []
    for n, (file, folder, _key, title, purpose, endpoints, tries) in enumerate(SCREENS, start=1):
        cards.append(f"""
      <article class="card">
        <a class="thumb" href="{file}"><img src="{thumb(file, folder)}"
           alt="{html.escape(title)} screenshot" loading="lazy"/></a>
        <div class="body">
          <div class="num">{n:02d}</div>
          <h2><a href="{file}">{html.escape(title)}</a></h2>
          <p>{html.escape(purpose)}</p>
          <h3>API</h3><ul class="chips">{"".join(f"<li><code>{html.escape(e)}</code></li>" for e in endpoints)}</ul>
          <h3>Try</h3><ul>{"".join(f"<li>{html.escape(t)}</li>" for t in tries)}</ul>
          <a class="open" href="{file}">Open screen →</a>
        </div>
      </article>""")
    fixes = "".join(f"<li>{html.escape(f)}</li>" for f in FIXES)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>NetCore Assist Prototype</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
  :root {{ --ink:#111; --text:#333; --muted:#6b6b6b; --line:#ECECEC; --card:#fff; --bg:#f9f9f9; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font:400 15px/1.55 Inter, system-ui, sans-serif; color:var(--text); background:var(--bg); }}
  .glow {{ position:fixed; inset:0; z-index:-1; pointer-events:none;
    background:radial-gradient(ellipse 70% 50% at 50% 0%, #FFFBEB 0%, #FDF2F8 45%, #F5F3FF 75%, transparent 100%); }}
  header, main, footer {{ max-width:1180px; margin:0 auto; padding:0 16px; }}
  header {{ padding-top:40px; }}
  .brand {{ display:flex; align-items:center; gap:10px; font-weight:600; color:var(--ink); }}
  .brand svg {{ width:32px; height:32px; }}
  h1 {{ font-size:32px; line-height:1.2; letter-spacing:-.025em; color:var(--ink); margin:18px 0 8px; }}
  .lead {{ max-width:760px; color:var(--muted); margin:0 0 18px; }}
  .start {{ display:inline-block; padding:10px 18px; border-radius:999px; background:var(--ink); color:#fff;
    text-decoration:none; font-weight:500; }}
  .how {{ display:flex; flex-wrap:wrap; gap:8px; margin:18px 0 0; padding:0; list-style:none; }}
  .how li {{ padding:6px 12px; border:1px solid var(--line); border-radius:999px; background:#fff; font-size:13px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(340px, 1fr)); gap:18px; margin:32px 0; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:16px; overflow:hidden; display:flex;
    flex-direction:column; box-shadow:0 4px 24px -6px rgba(17,17,17,.06); }}
  .thumb {{ display:block; aspect-ratio:16/10; overflow:hidden; background:#f3f3f4; border-bottom:1px solid var(--line); }}
  .thumb img {{ width:100%; height:100%; object-fit:cover; object-position:top left; transition:transform .3s; }}
  .card:hover .thumb img {{ transform:scale(1.02); }}
  .body {{ padding:16px 18px 18px; display:flex; flex-direction:column; flex:1; }}
  .num {{ font:500 12px "JetBrains Mono", monospace; color:var(--muted); }}
  h2 {{ font-size:18px; margin:2px 0 6px; letter-spacing:-.015em; }}
  h2 a {{ color:var(--ink); text-decoration:none; }}
  h3 {{ font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin:12px 0 4px; }}
  p {{ margin:0; }}
  ul {{ margin:0; padding-left:18px; font-size:14px; }}
  .chips {{ list-style:none; padding:0; display:flex; flex-wrap:wrap; gap:6px; }}
  code {{ font:400 12px "JetBrains Mono", monospace; background:#f3f3f4; padding:2px 6px; border-radius:6px;
    overflow-wrap:anywhere; }}
  .open {{ margin-top:auto; padding-top:14px; color:var(--ink); font-weight:500; text-decoration:none; }}
  .fixes {{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:18px 22px; margin-bottom:40px; }}
  .fixes h2 {{ margin-top:0; }}
  .fixes li {{ margin:6px 0; }}
  footer {{ color:var(--muted); font-size:13px; padding-bottom:40px; }}
  @media (max-width:420px) {{ .grid {{ grid-template-columns:1fr; }} h1 {{ font-size:26px; }} }}
</style>
</head>
<body>
<div class="glow"></div>
<header>
  <div class="brand">{LOGO}<span>NetCore Assist</span></div>
  <h1>UI prototype: 8 screens</h1>
  <p class="lead">Clickable prototype built from the Google Stitch mockups for the Agentic RAG REST API. Screens are
    linked, the main behaviours are simulated (no API calls), and the data matches what the API returns.</p>
  <a class="start" href="01-sign-in.html">Start the walkthrough →</a>
  <ul class="how">
    <li>Review bar (top): Index · Prev / Next · demo user</li>
    <li>Alice = guest · Bob = employee · Carol = admin</li>
    <li>Main journey: 01 → 02 → 03 → 04</li>
    <li>Disconnect journey: 03 “Stop watching” → 06</li>
  </ul>
</header>
<main>
  <section class="grid">{"".join(cards)}
  </section>
  <section class="fixes">
    <h2>Fixes applied to the Stitch output</h2>
    <ul>{fixes}</ul>
  </section>
</main>
<footer>Generated by <code>docs/ui-mockups/build_prototype.py</code> from
  <code>docs/ui-mockups/stitch_netcore_assist_web_app/</code> (originals untouched).</footer>
</body>
</html>
"""


# ---------------------------------------------------------------- main


def main() -> None:
    for file, folder, key, title, *_ in SCREENS:
        soup = BeautifulSoup((SRC / folder / "code.html").read_text(encoding="utf-8"), "html.parser")
        try:
            common(soup, key, title)
            TRANSFORMS[key](soup)
        except AnchorError as exc:
            raise SystemExit(f"{folder}: {exc} (did the Stitch export change?)") from None
        (OUT / file).write_text(str(soup), encoding="utf-8")
        print(f"  {file:<28} <- {folder}")
    (OUT / "index.html").write_text(index_html(), encoding="utf-8")
    print(f"  index.html\nwrote {len(SCREENS) + 1} pages to {OUT}")


if __name__ == "__main__":
    import sys
    main()
    if "--screenshots" in sys.argv:
        screenshots()
        (OUT / "index.html").write_text(index_html(), encoding="utf-8")  # now with prototype thumbnails
