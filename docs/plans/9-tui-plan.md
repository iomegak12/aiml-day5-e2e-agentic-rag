# Plan: Make-target Terminal UI (Textual), v0.9.1

## Context
The Makefile now has about 55 targets, many of which take parameters (`Q=`, `U=`, `M=`, `D=`, `TRACE=1`, `REPOPULATE=1`, `ENGINE=`). They are hard to remember.

The goal is a lightweight **Textual** terminal UI, started with `uv run tui.py`, that:
- lists every target, grouped and searchable, each with its description;
- collects its parameters in a form;
- previews the command;
- runs it with live output.

The Makefile itself becomes the single source of truth, and `make help` is generated from the same metadata.

## Decisions (MCQ)
| Topic | Decision |
|---|---|
| Source | Parse the Makefile's `##` comments: description, group, tags and parameters |
| `make help` | Generated from the same comments (the roughly 50 `@echo` lines go away) |
| Run | Inside the TUI, with live output, exit code and duration. **Stop** cancels. One run at a time. |
| Params | A form per target, built from the parameter spec in the `##` comment |
| Safety | `[danger]` / `[cost]` tags are shown in the list, plus a Yes/No modal before running |
| Extras | Search/filter, run history, container status panel, command preview (`make -n`) |
| Layout | `tui.py` at the root is a few lines only; the implementation lives in `scripts/make_tui/` |
| Dependency | `textual>=8.2.8` in the **dev** group (not in any image) |
| History | `.make_tui_history.json` (last 50 runs), git-ignored |
| Tests | Parser tests only |
| Docs/version | README, CHANGELOG 0.9.1, CONTRIBUTING; no image tag changes |

## 1. Makefile annotations (one source of truth)
```make
##@ Vector DB                                   <- group header
chroma-up:  ## Start the Chroma server
chroma-reset:  ## Stop the server and DELETE its volume [danger]
populate:  ## Read, chunk, describe, embed and store both domains [cost]
agent-ask:  ## Ask the agent as a demo user {Q! U=bob:alice|bob|carol M=plan:plan|react}
query:  ## Ad-hoc similarity + BM25 + hybrid query {Q! D=all:all|networking|meetings}
up-all: chroma-up redis-up ...  ## Whole stack in dependency order {REPOPULATE?}
api-run:  ## Run the API locally with auto-reload [long]
```

**Tags**

| Tag | Meaning |
|---|---|
| `[danger]` | Deletes data or overwrites it |
| `[cost]` | Calls OpenAI or creates Jira issues |
| `[long]` | Runs until stopped (servers, `*-logs`) |

**Parameters**

| Form | Meaning |
|---|---|
| `NAME!` | Required free text |
| `NAME=default` | Optional, with a default |
| `NAME=default:a\|b\|c` | Choice from a list |
| `NAME?` | Flag (checkbox), passed as `NAME=1` |

`ENGINE` is global, chosen in the TUI header (auto, docker or podman).

**Changes**
- Every target gets a `##` comment.
- The groups mirror today's help sections: KB generation, Vector DB, Agentic RAG, REST API, Web UI, IT ticket MCP server, Stack.
- `help:` becomes `@$(UV) run --no-sync python -m make_tui.help` (PYTHONPATH already includes `scripts`).
- New alias `tui:` runs `$(UV) run tui.py`.

## 2. Files
```
tui.py                          from make_tui import main; main()   (adds scripts/ to sys.path)
scripts/make_tui/
  __init__.py                   main() -> MakeTui(...).run()
  parser.py                     Makefile -> [Target(name, group, description, tags, params)]; Param(name, kind,
                                default, choices, required); build_command(target, values, engine) -> argv.
                                Pure Python, no Textual import (shared with help.py)
  help.py                       `make help` output: groups, aligned names, params, tags
  runner.py                     async subprocess `make ...` (stdout+stderr merged, ANSI -> Rich Text), stop =
                                kill the process tree (Windows: taskkill /T /F; POSIX: new session + killpg)
  history.py                    load/append/trim .make_tui_history.json (target, args, exit, seconds, when)
  status.py                     container status: `<engine> ps -a --filter name=netcore- --format ...`
  app.py                        MakeTui(App): layout, bindings, workers
  widgets.py                    TargetTree (grouped, filterable), ParamForm (Input / Select / Checkbox),
                                DetailsPanel, StatusPanel (DataTable), HistoryPanel
  screens.py                    ConfirmScreen (ModalScreen) for [danger] / [cost]
  app.tcss                      styles
  tests/test_parser.py          parser and command-builder tests against fixtures + the real Makefile
```

## 3. UI
```
┌ NetCore make ── engine: [auto▾] ─────────────────────────────── containers ─┐
│ / search…            │ agent-ask   [cost]                     │ netcore-api  ● healthy
│ ▾ Agentic RAG        │ Ask the agent as a demo user           │ netcore-mcp  ● healthy
│   redis-up           │ Q  [___________________________] *     │ netcore-web  ● healthy
│ ▸ agent-ask          │ U  [bob ▾]   M  [plan ▾]               │ …
│ ▾ REST API …         │ $ make agent-ask Q="…" U=bob M=plan    │
│                      │ [Run ⏎] [Dry run d] [Stop s]           │ History (h)
├──────────────────────┴─────────────────────────────────────────┤ ✓ up-all 0 62s
│ output (live, ANSI colours) … exit 0 · 14.3 s                  │ ✗ query  2 1s
└──────────────────────────────────────────────────────────────────────────────┘
```

**Keys**

| Key | Action |
|---|---|
| `/` | Search |
| `Enter` | Run |
| `d` | Dry run (`make -n`), output into the log |
| `s` | Stop |
| `r` | Re-run the last command |
| `h` | Focus history (Enter there re-runs a past entry) |
| `c` | Clear the log |
| `q` | Quit |
| `Ctrl+P` | Textual command palette; make targets are added as commands |

**Behaviour**
- **Preview:** the command line updates live as the form changes. **Run** stays disabled until required fields are filled and no run is in progress.
- **`[long]` targets:** shown with a note that they run until **Stop**.
- **Container panel:** refreshes every 10 s; if docker or podman is missing, it shows "engine not found".

## 4. Other changes
- `pyproject.toml`: dev group gets `textual>=8.2.8`; `testpaths` adds `scripts/make_tui/tests`.
- `.gitignore`: `.make_tui_history.json`.
- **Docs**
  - README: a "Terminal UI" section (screenshot-style layout, keys, the annotation syntax) and a `make tui` row.
  - CHANGELOG: `[0.9.1]`.
  - CONTRIBUTING: "every new target needs a `## description` (+ group, tags, params)".

## 5. Verification
1. `uv run pytest scripts/make_tui/tests`:
   - every real Makefile target has a description and a group;
   - parameter parsing covers required, default, choices and flag;
   - command quoting works for `Q` with spaces and quotes;
   - tag parsing.
2. `make help` prints the generated grouped list, with the same targets as before.
3. Manual run with `uv run tui.py` in Windows Terminal:
   - search "mcp" filters the list;
   - `agent-ask` without Q keeps Run disabled; fill Q, then the preview shows the exact command;
   - dry run `up-all` shows `make -n` output;
   - run `db-stats` streams output, and the exit code lands in history;
   - `chroma-reset` asks for confirmation (answer No);
   - run `mcp-logs`, then Stop terminates it;
   - the container panel lists the netcore-* containers;
   - history survives a restart.
4. All suites still pass: `uv run pytest` and `make web-test`.
5. No commit unless asked.
