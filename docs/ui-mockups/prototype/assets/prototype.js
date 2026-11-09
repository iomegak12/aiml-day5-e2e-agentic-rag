/* NetCore Assist clickable prototype: navigation, demo-user switching, review bar and light per-screen behaviours.
   Pages are the Google Stitch screens transformed by docs/ui-mockups/build_prototype.py, which adds the
   data-href / data-toast / data-panel / id hooks used below. Nothing here calls the real API. */
(() => {
  "use strict";

  const SCREENS = [
    ["01-sign-in.html", "Sign in"],
    ["02-new-chat.html", "New chat"],
    ["03-live-run.html", "Live run (streaming)"],
    ["04-answer-insights.html", "Answer + insights"],
    ["05-request-history.html", "Request history"],
    ["06-request-detail.html", "Request detail / resume"],
    ["07-error-states.html", "Error & limit states"],
    ["08-system-status.html", "System status (admin)"],
  ];
  const USERS = {
    alice: { name: "Alice", role: "Guest", title: "Field technician", levels: "public", initial: "A" },
    bob: { name: "Bob", role: "Employee", title: "NetOps Tier 3", levels: "public + internal", initial: "B" },
    carol: { name: "Carol", role: "Admin", title: "Platform admin", levels: "public + internal + restricted",
             initial: "C" },
  };

  // storage can be unavailable (private mode, file previews): never let it break the page
  const store = {
    get(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch { /* ignore */ } },
    sget(key) { try { return sessionStorage.getItem(key); } catch { return null; } },
    sset(key, value) { try { sessionStorage.setItem(key, value); } catch { /* ignore */ } },
  };
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const screen = document.body.dataset.screen || "";
  const userId = () => (USERS[store.get("nc-user", "bob")] ? store.get("nc-user", "bob") : "bob");
  const isAdmin = () => userId() === "carol";

  // ------------------------------------------------------------------ toast
  let toastTimer;
  function toast(html) {
    let el = $(".nc-toast");
    if (!el) {
      el = document.createElement("div");
      el.className = "nc-toast";
      el.setAttribute("role", "status");
      document.body.appendChild(el);
    }
    el.innerHTML = html;
    el.classList.add("nc-show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("nc-show"), 3200);
  }
  window.ncToast = toast;

  // ------------------------------------------------------------------ navigation (data-href / data-toast)
  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-href],[data-toast]");
    if (!target) return;
    event.preventDefault();
    if (target.dataset.toast) {
      toast(target.dataset.toast);
    } else {
      location.href = target.dataset.href;
    }
  });

  // ------------------------------------------------------------------ demo user (RBAC role)
  function applyUser() {
    const u = USERS[userId()];
    $$("[data-user-name]").forEach((el) => { el.textContent = u.name; });
    $$("[data-user-title]").forEach((el) => { el.textContent = u.title; });
    $$("[data-user-initial]").forEach((el) => { el.textContent = u.initial; });
    $$("[data-user-levels]").forEach((el) => { el.textContent = u.levels; });
    $$("[data-user-role]").forEach((el) => {
      el.textContent = u.role;
      el.style.background = isAdmin() ? "#111" : "";
      el.style.color = isAdmin() ? "#fff" : "";
    });
    $$("[data-admin-only]").forEach((el) => el.classList.toggle("nc-hidden", !isAdmin()));
    if (screen === "history") filterHistory();
    if (screen === "status") adminGate();
  }

  // ------------------------------------------------------------------ review bar
  function reviewBar() {
    const file = location.pathname.split("/").pop() || "index.html";
    const index = SCREENS.findIndex(([f]) => f === file);
    if (index < 0) return;
    const bar = document.createElement("nav");
    bar.className = "nc-review";
    bar.setAttribute("aria-label", "Prototype review bar");
    const prev = SCREENS[index - 1];
    const next = SCREENS[index + 1];
    bar.innerHTML = `
      <button class="nc-toggle" type="button" title="Collapse / expand">◐</button>
      <a href="index.html" title="All screens">← Index</a>
      <span class="nc-sep"></span>
      ${prev ? `<a href="${prev[0]}" title="${prev[1]}">‹ Prev</a>` : ""}
      <span class="nc-title">${String(index + 1).padStart(2, "0")} / 08 · ${SCREENS[index][1]}</span>
      ${next ? `<a href="${next[0]}" title="${next[1]}">Next ›</a>` : ""}
      <span class="nc-sep"></span>
      <label title="Demo user (role decides RBAC)"><select aria-label="Demo user">
        ${Object.entries(USERS).map(([id, u]) =>
          `<option value="${id}" ${id === userId() ? "selected" : ""}>${u.name} · ${u.role}</option>`).join("")}
      </select></label>`;
    bar.querySelector("select").addEventListener("change", (e) => {
      store.set("nc-user", e.target.value);
      applyUser();
      toast(`Signed in as <b>${USERS[e.target.value].name}</b> (${USERS[e.target.value].role}): sees ` +
            `${USERS[e.target.value].levels} articles`);
    });
    bar.querySelector(".nc-toggle").addEventListener("click", () => bar.classList.toggle("nc-collapsed"));
    document.body.appendChild(bar);
  }

  // ------------------------------------------------------------------ helpers
  function popover(trigger, panel) {
    if (!trigger || !panel) return;
    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = panel.classList.contains("nc-hidden");
      $$("[data-popover]").forEach((p) => p.classList.add("nc-hidden"));
      panel.classList.toggle("nc-hidden", !open);
      trigger.setAttribute("aria-expanded", String(open));
    });
    panel.addEventListener("click", (e) => e.stopPropagation());
  }
  document.addEventListener("click", () => $$("[data-popover]").forEach((p) => p.classList.add("nc-hidden")));

  function copy(text, label = "Copied") {
    try { navigator.clipboard?.writeText(text); } catch { /* ignore */ }
    toast(label);
  }

  // ------------------------------------------------------------------ 01 sign in
  function initSignIn() {
    const field = $("#apiKeyField");
    const error = $("#nc-key-error");
    const original = window.selectUser;
    window.selectUser = (id, el) => {
      if (original) original(id, el);
      store.set("nc-user", id);
    };
    const current = $(`[data-user-card="${userId()}"]`);
    if (current && original) original(userId(), current);
    $("form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      const key = (field?.value || "").trim();
      if (key.length < 8) {
        error?.classList.remove("nc-hidden");
        field?.focus();
        return;
      }
      const id = key.includes("_guest_") ? "alice" : key.includes("_adm_") ? "carol" : "bob";
      store.set("nc-user", id);
      location.href = "02-new-chat.html";
    });
    field?.addEventListener("input", () => error?.classList.add("nc-hidden"));
  }

  // ------------------------------------------------------------------ 02 new chat
  function initNewChat() {
    popover($("#mode-pill-btn"), $("#mode-popover"));
    popover($("#options-trigger-btn"), $("#options-popover"));
    $$("[data-mode]").forEach((option) => option.addEventListener("click", () => {
      const mode = option.dataset.mode;
      $("#nc-mode-label").textContent = mode === "plan" ? "Plan" : "ReAct";
      $$("[data-mode]").forEach((o) => {
        const selected = o === option;
        o.classList.toggle("bg-surface-container-low", selected);
        const icon = o.querySelector("[data-check]");
        if (icon) icon.style.visibility = selected ? "visible" : "hidden";
      });
      store.sset("nc-mode", mode);
      $("#mode-popover").classList.add("nc-hidden");
    }));
    $$("#options-popover button[aria-pressed]").forEach((btn) => btn.addEventListener("click", () => {
      const on = btn.getAttribute("aria-pressed") !== "true";
      btn.setAttribute("aria-pressed", String(on));
      btn.classList.toggle("bg-primary", on);
      btn.classList.toggle("bg-surface-container-high", !on);
      const knob = btn.querySelector("span");
      knob?.classList.toggle("translate-x-4", on);
      knob?.classList.toggle("translate-x-0", !on);
    }));
    const range = $("#nc-budget");
    range?.addEventListener("input", () => { $("#nc-budget-label").textContent = `${range.value} s`; });
    const input = $("#diagnostic-composer-input");
    $$("[data-example]").forEach((chip) => chip.addEventListener("click", () => {
      input.value = chip.dataset.example;
      input.focus();
    }));
    const send = () => {
      if (!input.value.trim()) {
        toast("Type a question or pick an example first.");
        input.focus();
        return;
      }
      store.sset("nc-question", input.value.trim());
      location.href = "03-live-run.html";
    };
    $("#nc-send")?.addEventListener("click", send);
    input?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
    });
  }

  // ------------------------------------------------------------------ 03 live run (simulated SSE)
  function initLiveRun() {
    const question = store.sget("nc-question");
    if (question && $("#nc-question")) $("#nc-question").textContent = question;
    const feed = $("#nc-events");
    const log = $("#nc-log");
    let seq = 8;
    const addEvent = (type, text) => {
      if (!feed) return;
      seq += 1;
      const row = document.createElement("div");
      row.className = "flex items-start gap-2 py-1.5 border-b border-[#ECECEC] last:border-0 nc-pending";
      row.innerHTML = `<span class="font-code-sm text-code-sm text-outline whitespace-nowrap shrink-0">17942411${String(seq).padStart(5, "0")}-0</span>
        <span class="px-1.5 rounded bg-surface-container-high font-code-sm text-code-sm shrink-0">${type}</span>
        <span class="font-body-sm text-body-sm text-on-surface-variant">${text}</span>`;
      feed.appendChild(row);
      requestAnimationFrame(() => { row.classList.remove("nc-pending"); row.classList.add("nc-revealed"); });
      feed.scrollTop = feed.scrollHeight;
    };
    const addLog = (t, step, text) => {
      if (!log) return;
      const line = document.createElement("div");
      line.className = "flex gap-3";
      line.innerHTML = `<span class="text-neutral-500">[${t}]</span><span class="text-sky-300 w-24 shrink-0">${step}</span><span class="text-neutral-200">${text}</span>`;
      log.appendChild(line);
    };
    const timeline = [
      [1500, () => {
        const step = $("#nc-step2");
        if (step) {
          const icon = step.querySelector("[data-step-icon]");
          if (icon) { icon.textContent = "check"; icon.classList.remove("animate-spin"); }
          const status = step.querySelector("[data-step-status]");
          if (status) status.innerHTML = "done · 2 relevant items · best: 0.88 · 3.6 s";
        }
        addEvent("step", "step 2 done · 2 relevant · best 0.88");
        addEvent("tool_call", "search_knowledge_base · planner · done · 3.6 s");
        addLog("46.0s", "Plan executor", "step 2 done · 2 relevant, best 0.88");
      }],
      [3000, () => {
        addEvent("trace", "Context optimizer · 5 chunks · 2 980 tokens");
        addLog("47.2s", "Judge LLM", "evaluating faithfulness · groundedness · context precision…");
      }],
      [4600, () => {
        addEvent("judge", "attempt 1 · accept · faithfulness 1.00 · groundedness 1.00 · precision 1.00");
        addLog("57.1s", "Judge LLM", "pass {faithfulness: 1.0, groundedness: 1.0, context_precision: 1.0}");
        addLog("57.4s", "Output guard", "pass");
      }],
      [6000, () => {
        addEvent("result", "AskResponse · status completed · agent_status answered");
        addEvent("done", "{request_id: 2f13a1af…, status: completed}");
        const badge = $("#nc-run-badge");
        if (badge) {
          badge.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500"></span><span>Completed</span>';
          badge.className = "flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 font-label-sm text-label-sm";
        }
        const ready = `<div class="flex items-center justify-between gap-3 p-4 rounded-xl bg-emerald-50 border border-emerald-200">
            <div class="flex items-center gap-2 text-emerald-800"><span class="material-symbols-outlined">task_alt</span>
              <span class="font-label-md text-label-md">Answer ready · answered · judge passed · 63.1 s</span></div>
            <a href="04-answer-insights.html" class="px-4 py-2 rounded-full bg-primary text-on-primary font-label-md text-label-md">View answer →</a></div>`;
        const skeleton = $("#nc-skeleton");
        if (skeleton) skeleton.innerHTML = ready;
        const plan = $("#nc-plan-section");  // also at the top of the card, above the fixed composer
        if (plan) {
          plan.insertAdjacentHTML("beforebegin", `<div class="mb-4">${ready}</div>`);
          plan.previousElementSibling.scrollIntoView({ block: "center", behavior: "smooth" });
        }
        $("#nc-composer-hint") && ($("#nc-composer-hint").textContent = "Done. Open the answer, or ask a follow-up.");
      }],
    ];
    timeline.forEach(([delay, fn]) => setTimeout(fn, delay));
    $("#nc-stop")?.addEventListener("click", () => {
      store.sset("nc-disconnected", "1");
      location.href = "06-request-detail.html";
    });
  }

  // ------------------------------------------------------------------ 04 answer + insights
  function initAnswer() {
    const tabs = $$("[data-tab]");
    const activeClass = tabs.find((t) => t.dataset.tab === "judge")?.className || "";
    const inactiveClass = tabs.find((t) => t.dataset.tab !== "judge")?.className || "";
    const activate = (name) => {
      tabs.forEach((t) => { t.className = t.dataset.tab === name ? activeClass : inactiveClass; });
      $$("[data-panel]").forEach((p) => p.classList.toggle("nc-hidden", p.dataset.panel !== name));
    };
    tabs.forEach((t) => t.addEventListener("click", () => activate(t.dataset.tab)));
    activate("judge");
    $$("[data-cite]").forEach((chip) => chip.addEventListener("click", (e) => {
      e.preventDefault();
      activate("sources");
      const row = document.getElementById(chip.dataset.cite);
      if (row) {
        row.scrollIntoView({ block: "center", behavior: "smooth" });
        row.classList.remove("nc-flash");
        void row.offsetWidth;
        row.classList.add("nc-flash");
      }
    }));
    $("#nc-copy-answer")?.addEventListener("click", () => copy($("#nc-answer")?.innerText || "", "Answer copied"));
  }

  // ------------------------------------------------------------------ 05 history (owner-scoped, filters)
  const historyFilter = { status: "all", user: "all", mode: "all", text: "" };
  function filterHistory() {
    const me = userId();
    let shown = 0;
    $$("tr[data-status]").forEach((row) => {
      const visible =
        (isAdmin() || row.dataset.owner === me) &&
        (historyFilter.status === "all" || row.dataset.status === historyFilter.status) &&
        (historyFilter.user === "all" || row.dataset.owner === historyFilter.user) &&
        (historyFilter.mode === "all" || row.dataset.mode === historyFilter.mode) &&
        (!historyFilter.text || row.innerText.toLowerCase().includes(historyFilter.text));
      row.classList.toggle("nc-hidden", !visible);
      if (visible) shown += 1;
    });
    const scope = $("#nc-scope");
    if (scope) scope.textContent = isAdmin() ? "Admin: all users" : "Own requests only";
    const empty = $("#nc-empty");
    if (empty) empty.classList.toggle("nc-hidden", shown > 0);
  }
  function initHistory() {
    const wrap = (name, handler) => {
      const original = window[name];
      window[name] = (...args) => { if (original) original(...args); handler(...args); filterHistory(); };
    };
    wrap("filterStatus", (_el, status) => {
      historyFilter.status = status === "disconnected" ? "client_disconnected" : status;
    });
    wrap("selectUser", (name) => {
      const n = String(name).toLowerCase();
      historyFilter.user = n.includes("carol") ? "carol" : n.includes("bob") ? "bob" : n.includes("alice") ? "alice" : "all";
    });
    wrap("selectMode", (name) => {
      const n = String(name).toLowerCase();
      historyFilter.mode = n.includes("react") ? "react" : n.includes("plan") ? "plan" : "all";
    });
    $("#nc-search")?.addEventListener("input", (e) => { historyFilter.text = e.target.value.trim().toLowerCase(); filterHistory(); });
    filterHistory();
  }

  // ------------------------------------------------------------------ 06 request detail (replay after reconnect)
  function initDetail() {
    const pending = $$(".nc-replay");
    const counter = $("#nc-replay-count");
    const bar = $("#nc-buffer-bar");
    const pct = $("#nc-buffer-pct");
    const live = $("#nc-live-pill");
    if (bar) bar.style.width = "0%";
    pending.forEach((el, i) => setTimeout(() => {
      el.classList.remove("nc-pending");
      el.classList.add("nc-revealed");
      const done = i + 1;
      if (counter) counter.textContent = `Replayed ${done} of ${pending.length} missed events`;
      if (bar) bar.style.width = `${Math.round((done / pending.length) * 100)}%`;
      if (pct) pct.textContent = `${Math.round((done / pending.length) * 100)}% (${done}/${pending.length})`;
      if (done === pending.length && live) live.classList.remove("nc-hidden");
    }, 700 * (i + 1)));
    $("#nc-export")?.addEventListener("click", () => {
      const blob = new Blob([JSON.stringify(SAMPLE_RESPONSE, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "2f13a1af-1efb-4c29-9d33-728b94091a11.json";
      a.click();
      URL.revokeObjectURL(a.href);
      toast("Downloaded a sample <code>GET /api/v1/agent/requests/{id}</code> payload");
    });
  }

  // ------------------------------------------------------------------ 07 errors (429 countdown)
  function initErrors() {
    const el = $("#countdown-timer");
    let seconds = 27;
    const tick = setInterval(() => {
      seconds -= 1;
      if (seconds > 0) {
        if (el) el.textContent = `Retry in ${seconds} s`;
        $$("[data-retry-seconds]").forEach((t) => { t.textContent = `Rate limit active: retry in ${seconds}s`; });
        return;
      }
      clearInterval(tick);
      if (el) el.textContent = "Ready: you can send again";
      $("#nc-429-tip")?.classList.add("nc-hidden");
      const send = $("#nc-429-send");
      if (send) {
        send.disabled = false;
        send.classList.remove("opacity-40", "cursor-not-allowed");
        send.dataset.href = "02-new-chat.html";
      }
    }, 1000);
  }

  // ------------------------------------------------------------------ 08 system status (admin only)
  function adminGate() {
    let overlay = $(".nc-overlay");
    if (isAdmin()) { overlay?.remove(); return; }
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.className = "nc-overlay";
    overlay.innerHTML = `<div><h2>Admins only</h2><p>System status is shown to admins (Carol). The API's
      <code>/health</code>, <code>/ready</code> and <code>/metrics</code> are probes; the UI hides this page from other roles.</p>
      <button type="button" data-href="02-new-chat.html">Back to chat</button></div>`;
    document.body.appendChild(overlay);
  }
  function initStatus() {
    let checked = 5;
    const label = $("#nc-checked");
    setInterval(() => { checked += 1; if (label) label.textContent = `checked ${checked} s ago`; }, 1000);
    $("#refreshBtn")?.addEventListener("click", () => {
      const icon = $("#refreshBtn .material-symbols-outlined");
      icon?.classList.add("nc-spin");
      setTimeout(() => icon?.classList.remove("nc-spin"), 700);
      checked = 0;
      if (label) label.textContent = "checked just now";
      $$("[data-latency]").forEach((el) => {
        const base = Number(el.dataset.latency);
        el.textContent = (base * (0.8 + Math.random() * 0.4)).toFixed(base < 10 ? 1 : 0);
      });
      toast("Re-polled <code>GET /ready</code> and <code>GET /metrics</code>");
    });
    adminGate();
  }

  // sample payload (same shape as AskResponse in api/app/schemas/agent.py)
  const SAMPLE_RESPONSE = {
    request_id: "2f13a1af-1efb-4c29-9d33-728b94091a11", status: "client_disconnected", agent_status: "answered",
    mode: "plan", endpoint: "stream", user_id: "bob", elapsed_s: 60.09, client_disconnected: true,
    result: {
      question: "Our NetCore Meet calls show MTG-MED-4102 packet loss at branch sites. Which SD-WAN QoS settings and SLA class should we apply, and what does the Meet troubleshooting guide recommend?",
      user: { id: "bob", name: "Bob", role: "employee", allowed_levels: ["public", "internal"] },
      plan: { replans: 0, versions: [{ version: 1, rationale: "Split into networking QoS/SLA and Meet troubleshooting",
        steps: [
          { id: 1, version: 1, goal: "SD-WAN QoS and SLA class for voice", tool: "search_knowledge_base", domains: ["networking"], query: "SD-WAN QoS SLA class voice packet loss", depends_on: [] },
          { id: 2, version: 1, goal: "Meet troubleshooting for MTG-MED-4102", tool: "search_knowledge_base", domains: ["meetings"], query: "MTG-MED-4102 troubleshooting", depends_on: [] }] }] },
      executed_plan: [
        { id: 1, version: 1, tool: "search_knowledge_base", status: "done", relevant: 3, best: 0.92, seconds: 4.1 },
        { id: 2, version: 1, tool: "search_knowledge_base", status: "done", relevant: 2, best: 0.88, seconds: 3.6 }],
      sources: [
        { kb_id: "KB-NET-1010", score: 0.94, location: "p. 3", access_level: "internal", status: "current" },
        { kb_id: "KB-MTG-2006", score: 0.91, location: "chunk 2", access_level: "internal", status: "current" }],
      judge: { model: "gpt-6.1-sol", passed: true,
        scores: { faithfulness: 1.0, groundedness: 1.0, context_precision: 1.0 },
        thresholds: { faithfulness: 0.7, groundedness: 0.7, context_precision: 0.6 },
        attempts: [{ attempt: 1, action: "accept", passed: true, seconds: 9.9 }] },
      cache: { hit: false, similarity: null, cached_question: null },
      routes: ["vector", "vector"], rewrites: 0,
      timings: { total_s: 60.1, agent_s: 59.9, queued_s: 0.0 },
    },
    error: null, events_url: "/api/v1/agent/requests/2f13a1af-1efb-4c29-9d33-728b94091a11/events",
  };

  // ------------------------------------------------------------------ boot
  const INIT = { signin: initSignIn, newchat: initNewChat, liverun: initLiveRun, answer: initAnswer,
                 history: initHistory, detail: initDetail, errors: initErrors, status: initStatus };
  document.addEventListener("DOMContentLoaded", () => {
    reviewBar();
    INIT[screen]?.();
    applyUser();
  });
})();
