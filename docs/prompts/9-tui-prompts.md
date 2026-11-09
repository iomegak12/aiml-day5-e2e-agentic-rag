# Phase 9 – Terminal UI for the make targets (Textual)

Your prompts (lightly cleaned), the MCQ clarifications with every option ([x] = your choice), and a one-line outcome.

## Prompt 1

> As an engineer, I have to remember many make target commands, which sometimes confuses me.
>
> Can you help me build a simple Python terminal UI that shows all the commands available as make targets, so I can run them through a console UI? The Python Textual UI library is preferred.
>
> Do you get my points? Let's have MCQ-based Q&As so we are both aligned.

### Clarifications

#### Round 1

**Where should the TUI get the list of targets from?** _(Target source)_

- [x] **Parse Makefile + '##' comments (Recommended)** – Add a short '## description' and '# group: X' to each target; the TUI reads them, so it stays in sync automatically. make help can use the same text.
- [ ] Parse existing make help output – No Makefile changes; but help lines are free text, so parsing is fragile.
- [ ] Hard-coded catalog in the TUI – A Python list of targets; it drifts when the Makefile changes.

**How should a selected target run?** _(Execution)_

- [x] **Inside the TUI, live log (Recommended)** – Streams output into a log panel; shows exit code and time; Stop button cancels. You stay in the UI.
- [ ] Suspend TUI, run in terminal – TUI hides, make runs with full terminal (colours, Ctrl+C), then returns on Enter.
- [ ] Both, chosen per run – Default in-TUI; a key (e.g. T) runs in the terminal instead.

**Targets need parameters (Q=, U=, M=, D=, TRACE=1, REPOPULATE=1, ENGINE=). How should the TUI handle them?** _(Parameters)_

- [x] **Form per target (Recommended)** – Known variables shown as inputs/selects (U: alice/bob/carol, M: plan/react, D: ...); Q required where needed.
- [ ] Free-text extra args – One input box: e.g. Q="..." U=bob. Simple, no validation.
- [ ] No parameters – Only parameter-less targets runnable.

**Safety for destructive / costly targets (chroma-reset, clean-data, regenerate, populate, stack-down)?** _(Safety)_

- [x] **Confirm dialog + tags (Recommended)** – Marked 'destructive' or 'costs OpenAI' in the list; a Yes/No modal before running.
- [ ] Tags only – Visible warning, no confirmation.
- [ ] Hide them – Not shown in the TUI at all.

#### Round 2

**Where are each target's parameters declared?** _(Param meta)_

- [x] **In the '##' comment (Recommended)** – e.g. agent-ask: ## Ask the agent [Q! U=bob:alice|bob|carol M=plan:plan|react]. One source of truth in the Makefile.
- [ ] Catalog in the TUI – Makefile has only descriptions; the TUI knows U/M/D/Q choices per target.

**Should 'make help' be generated from the same '##' comments?** _(make help)_

- [x] **Yes, generate it (Recommended)** – Replace the ~50 hand-written @echo lines with a small parser script; no duplication, never out of date.
- [ ] No, keep current help – Keep @echo lines; descriptions live in two places.

**Where does the TUI live and how is it launched?** _(Location)_

- [ ] tools/make_tui/ + make tui (Recommended) – Small package (parser, app, widgets, .tcss), run with `make tui` or `uv run python -m tools.make_tui`.
- [ ] scripts/make_tui.py – Single file next to the other scripts.
- [ ] Own folder at root: make_tui/ – Top-level package like netcore_mcp.
- [x] **Other:** "`uv run tui.py` should launch the terminal UI. Keep all implementation dependencies in the scripts folder, and keep tui.py lightweight."

**Which extras do you want?** _(Extras, multi-select)_

- [x] **Search / filter box** – Type to filter targets by name or description.
- [x] **Run history** – Last runs with exit code and duration; re-run with one key.
- [x] **Container status panel** – Shows netcore-\* containers and health (docker/podman ps), refreshed periodically.
- [x] **Command preview (make -n)** – Shows the exact command line and a dry-run before running.

#### Round 3

**Confirm the layout: tui.py at the workspace root (only imports and runs), with the implementation in scripts/make_tui/ (parser, app, widgets, styles)?** _(Layout)_

- [x] **Yes, exactly that (Recommended)** – uv run tui.py -> from make_tui import run; run(). Package under scripts/, like agentic_rag.
- [ ] Single scripts/make_tui.py – One module instead of a package.

**Where does the textual dependency go?** _(Dependency)_

- [x] **dev group (Recommended)** – Installed by uv sync locally; excluded from the API/MCP images (--no-default-groups).
- [ ] New 'tools' group – Also local-only, separately named.
- [ ] Main dependencies – Adds it to every image (not needed there).

**Can several targets run at the same time?** _(Concurrency)_

- [x] **One at a time (Recommended)** – Simple and safe (make targets share containers/DB); Run disabled while busy; Stop cancels.
- [ ] Several, one log tab each – e.g. mcp-run + api-run side by side; more complex.

**Run history storage?** _(History)_

- [x] **JSON file, git-ignored (Recommended)** – Last 50 runs in .make_tui_history.json; survives restarts.
- [ ] In memory only – Cleared when the TUI closes.

#### Round 4

**Tests for the TUI?** _(Tests)_

- [ ] Parser + Textual pilot tests (Recommended) – pytest: Makefile '##' parsing, param forms, confirm dialog, run flow with a fake runner. In scripts/make_tui/tests, added to testpaths.
- [x] **Parser tests only** – No UI tests.
- [ ] None – Manual check only.

**Docs and version?** _(Docs)_

- [x] **README + CHANGELOG + CONTRIBUTING, 0.9.1 (Recommended)** – README 'Terminal UI' section, CHANGELOG 0.9.1, CONTRIBUTING: how to document a new target with ##. No image tag changes.
- [ ] README + CHANGELOG, no version bump – Add under 0.9.0.
- [ ] README only – Minimal.

**Outcome:** Added `uv run tui.py` / `make tui` (`scripts/make_tui/`, Textual 8): grouped, searchable targets with `!`/`$`/`~` badges, parameter forms with a live command preview, live output with Stop and dry run, confirmation for `[danger]`/`[cost]`, run history, container panel and command palette. Every Makefile target now carries `## description [tags] {params}`, and `make help` is generated from it; 17 parser tests.
