"""MakeTui: browse, configure and run the Makefile targets (Textual)."""

from __future__ import annotations

import time
from datetime import datetime
from functools import partial

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, RichLog, Select, Static, Tree

from make_tui.history import History, Run
from make_tui.parser import Target, build_args, display_command, load_targets, validate
from make_tui.runner import MakeRunner
from make_tui.screens import ConfirmScreen
from make_tui.status import containers, detect_engine
from make_tui.widgets import HistoryPanel, ParamForm, StatusPanel, TargetTree

HIDDEN = {"tui"}  # running the TUI inside itself makes no sense
TAG_TEXT = {"danger": ("destructive", "bold red"), "cost": ("costs API calls", "bold yellow"),
            "long": ("runs until stopped", "bold cyan")}
STATUS_REFRESH_SECONDS = 10


class MakeTui(App):
    CSS_PATH = "app.tcss"
    TITLE = "NetCore make"
    SUB_TITLE = "idle"

    BINDINGS = [
        Binding("slash", "focus_search", "Search"),
        Binding("f5", "run", "Run"),
        Binding("d", "dry_run", "Dry run"),
        Binding("s", "stop", "Stop"),
        Binding("r", "rerun", "Re-run last"),
        Binding("h", "focus_history", "History"),
        Binding("c", "clear_log", "Clear log"),
        Binding("q", "quit", "Quit"),
    ]

    running: reactive[bool] = reactive(False)

    def __init__(self):
        super().__init__()
        self.targets = [t for t in load_targets() if t.name not in HIDDEN]
        self.by_name = {t.name: t for t in self.targets}
        self.history = History()
        self.runner = MakeRunner()
        self.selected: Target | None = None
        self.engine = "auto"

    # ---------------------------- layout ----------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Input(placeholder="/  search targets", id="search")
                yield TargetTree(self.targets, id="targets")
            with Vertical(id="center"):
                with Vertical(id="details"):
                    yield Static(id="target-title")
                    yield Static(id="target-desc")
                    yield ParamForm(id="params")
                    yield Static(id="preview", markup=False)
                    yield Static(id="problems")
                    with Horizontal(id="actions"):
                        yield Button("Run (F5)", variant="success", id="run")
                        yield Button("Dry run (d)", id="dry-run")
                        yield Button("Stop (s)", variant="error", id="stop", disabled=True)
                        yield Select([("engine: auto", "auto"), ("engine: docker", "docker"),
                                      ("engine: podman", "podman")], value="auto", allow_blank=False, id="engine")
                yield RichLog(id="log", highlight=False, markup=False, wrap=True, max_lines=5000)
                yield Static("ready", id="run-status")
            with Vertical(id="right"):
                yield StatusPanel(id="status")
                yield HistoryPanel(id="history")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(HistoryPanel).show(self.history.runs)
        tree = self.query_one(TargetTree)
        tree.focus()
        if leaf := tree.first_leaf():
            tree.focus_leaf(leaf)
            self.show_target(leaf.data)
        self.refresh_status()
        self.set_interval(STATUS_REFRESH_SECONDS, self.refresh_status)

    def get_system_commands(self, screen: Screen):
        """Command palette (Ctrl+P): every make target, plus Textual's own commands."""
        yield from super().get_system_commands(screen)
        for t in self.targets:
            yield SystemCommand(f"make {t.name}", t.description, partial(self.select_target, t.name))

    # ---------------------------- selection + form ----------------------------

    def show_target(self, target: Target | None) -> None:
        if target is None or target is self.selected:
            return
        self.selected = target
        title = Text(target.name, style="bold") + Text(f"   {target.group}", style="dim")
        for tag in target.tags:
            label, style = TAG_TEXT[tag]
            title.append(f"   {label}", style=style)
        self.query_one("#target-title", Static).update(title)
        desc = target.description
        if target.long_running:
            desc += "\nRuns until you press Stop (s)."
        if target.deps:
            desc += f"\nRuns first: {', '.join(target.deps)}"
        self.query_one("#target-desc", Static).update(desc)
        self.query_one(ParamForm).show(target)
        self.update_preview()

    def select_target(self, name: str) -> None:
        """Move the tree cursor to a target (clearing the search if it hides it)."""
        search = self.query_one("#search", Input)
        tree = self.query_one(TargetTree)
        if name not in self.by_name:
            return
        self.show_target(self.by_name[name])  # before clearing the search: _search keeps a visible selection
        if search.value:
            search.value = ""
            tree.filter("")
        if leaf := tree.leaf_for(name):
            tree.focus_leaf(leaf)
        tree.focus()

    def current_args(self, dry_run: bool = False) -> tuple[list[str], list[str]]:
        if self.selected is None:
            return [], ["select a target"]
        values = self.query_one(ParamForm).values()
        return build_args(self.selected, values, self.engine, dry_run=dry_run), validate(self.selected, values)

    def update_preview(self) -> None:
        args, errors = self.current_args()
        self.query_one("#preview", Static).update(f"$ {display_command(args)}" if args else "")
        self.query_one("#problems", Static).update(Text("  ".join(errors), style="red") if errors else "")
        self.query_one("#run", Button).disabled = bool(errors) or self.running
        self.query_one("#dry-run", Button).disabled = bool(errors) or self.running

    @on(Tree.NodeHighlighted, "#targets")
    def _highlighted(self, event: Tree.NodeHighlighted) -> None:
        self.show_target(event.node.data)

    @on(Tree.NodeSelected, "#targets")
    def _selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data is None:
            return
        self.show_target(event.node.data)
        field = self.query_one(ParamForm).first_input()
        (field or self.query_one("#run", Button)).focus()

    @on(Input.Changed, "#search")
    def _search(self, event: Input.Changed) -> None:
        tree = self.query_one(TargetTree)
        shown = tree.filter(event.value)
        # keep the current target if it is still listed, else jump to the first match
        leaf = (tree.leaf_for(self.selected.name) if self.selected else None) or tree.first_leaf()
        if leaf:
            tree.focus_leaf(leaf)
            self.show_target(leaf.data)
        self.sub_title = f"{shown} target(s)" if event.value else ("running" if self.running else "idle")

    @on(Input.Submitted, "#search")
    def _search_done(self) -> None:
        self.query_one(TargetTree).focus()

    @on(ParamForm.Changed)
    def _params_changed(self) -> None:
        self.update_preview()

    @on(Input.Submitted, "#params Input")
    def _param_submitted(self) -> None:
        self.action_run()

    @on(Select.Changed, "#engine")
    def _engine_changed(self, event: Select.Changed) -> None:
        self.engine = str(event.value)
        self.update_preview()
        self.refresh_status()

    @on(Button.Pressed, "#run")
    def _run_pressed(self) -> None:
        self.action_run()

    @on(Button.Pressed, "#dry-run")
    def _dry_pressed(self) -> None:
        self.action_dry_run()

    @on(Button.Pressed, "#stop")
    def _stop_pressed(self) -> None:
        self.action_stop()

    @on(HistoryPanel.Rerun)
    def _history_rerun(self, event: HistoryPanel.Rerun) -> None:
        self.confirm_and_run(event.run.target, list(event.run.args))

    # ---------------------------- actions ----------------------------

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_focus_history(self) -> None:
        self.query_one("#history-table").focus()

    def action_clear_log(self) -> None:
        self.query_one(RichLog).clear()

    def action_run(self) -> None:
        if self.running:
            self.notify("A target is already running - stop it first (s).", severity="warning")
            return
        args, errors = self.current_args()
        if errors or self.selected is None:
            self.notify("; ".join(errors) or "Select a target first.", severity="error")
            return
        self.confirm_and_run(self.selected.name, args)

    def action_dry_run(self) -> None:
        if self.running:
            self.notify("A target is already running.", severity="warning")
            return
        args, errors = self.current_args(dry_run=True)
        if errors or self.selected is None:
            self.notify("; ".join(errors) or "Select a target first.", severity="error")
            return
        self.execute(self.selected.name, args, dry_run=True)

    def action_rerun(self) -> None:
        if not self.history.runs:
            self.notify("No run yet.", severity="information")
            return
        last = self.history.runs[0]
        self.confirm_and_run(last.target, list(last.args))

    def action_stop(self) -> None:
        if self.running:
            self.stop_run()

    async def action_quit(self) -> None:
        if self.runner.running:
            await self.runner.stop()
        self.exit()

    def confirm_and_run(self, name: str, args: list[str]) -> None:
        if self.running:
            self.notify("A target is already running - stop it first (s).", severity="warning")
            return
        target = self.by_name.get(name)
        if target is None or not target.needs_confirmation:
            self.execute(name, args)
            return
        if target.dangerous:
            title, message = "Destructive target", "This deletes or overwrites data and cannot be undone."
        else:
            title, message = "This target costs money", "It calls OpenAI (and may create Jira issues)."

        def done(confirmed: bool | None) -> None:
            if confirmed:
                self.execute(name, args)

        self.push_screen(ConfirmScreen(f"{title}: make {name}", message, display_command(args), target.dangerous),
                         done)

    # ---------------------------- running ----------------------------

    def watch_running(self, running: bool) -> None:
        self.query_one("#stop", Button).disabled = not running
        self.sub_title = "running" if running else "idle"
        self.update_preview()

    @work(exclusive=True, group="make")
    async def execute(self, name: str, args: list[str], dry_run: bool = False) -> None:
        log = self.query_one(RichLog)
        status = self.query_one("#run-status", Static)
        command = display_command(args)
        log.write(Text(f"\n$ {command}", style="bold cyan"))
        self.running = True
        self.sub_title = f"running: {name}"
        status.update(Text(f"running {name} ...", style="yellow"))
        started = time.monotonic()
        code: int | None
        try:
            code = await self.runner.run(args, lambda line: log.write(Text.from_ansi(line)))
        except FileNotFoundError as exc:
            log.write(Text(str(exc), style="bold red"))
            code = 127
        finally:
            self.running = False
        seconds = time.monotonic() - started
        if self.runner.stopped:
            code = None
            status.update(Text(f"stopped {name} after {seconds:.1f} s", style="yellow"))
        elif code == 0:
            status.update(Text(f"✓ {name} finished · exit 0 · {seconds:.1f} s", style="green"))
        else:
            status.update(Text(f"✗ {name} failed · exit {code} · {seconds:.1f} s", style="bold red"))
        log.write(Text(f"[{'stopped' if code is None else f'exit {code}'} · {seconds:.1f} s]", style="dim"))
        if not dry_run:
            self.history.add(Run(name, args, code, round(seconds, 1), datetime.now().isoformat(timespec="seconds")))
            self.query_one(HistoryPanel).show(self.history.runs)
            self.refresh_status()  # containers may have changed

    @work(group="stop")
    async def stop_run(self) -> None:
        await self.runner.stop()

    @work(exclusive=True, group="status")
    async def refresh_status(self) -> None:
        engine = detect_engine(self.engine)
        rows = None
        if engine:
            try:
                rows = await containers(engine)
            except Exception:  # noqa: BLE001 - daemon down, timeout: show "not reachable"
                rows = None
        self.query_one(StatusPanel).show(rows, engine)
