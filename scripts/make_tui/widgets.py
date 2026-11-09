"""Widgets: grouped target tree, parameter form, container status and run history panels."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Checkbox, DataTable, Input, Label, Select, Tree

from make_tui.history import Run
from make_tui.parser import Param, Target, groups
from make_tui.status import Container

TAG_STYLE = {"danger": ("!", "bold red"), "cost": ("$", "bold yellow"), "long": ("~", "bold cyan")}
HEALTH_STYLE = {"healthy": "green", "running": "green", "starting": "yellow", "unhealthy": "red", "stopped": "dim"}


def tag_badges(target: Target) -> Text:
    text = Text()
    for tag in target.tags:
        symbol, style = TAG_STYLE[tag]
        text.append(f" {symbol}", style=style)
    return text


def matches(target: Target, query: str) -> bool:
    words = query.lower().split()
    haystack = f"{target.name} {target.group} {target.description} {' '.join(target.tags)}".lower()
    return all(w in haystack for w in words)


class TargetTree(Tree[Target]):
    """Targets grouped as in the Makefile; filter() rebuilds it for a search query."""

    def __init__(self, targets: list[Target], **kwargs):
        super().__init__("make", **kwargs)
        self.targets = targets
        self.show_root = False
        self.guide_depth = 2

    def on_mount(self) -> None:
        self.filter("")

    def filter(self, query: str) -> int:
        """Show only matching targets (all groups expanded while searching). Returns the number shown."""
        self.clear()
        shown = 0
        for group, members in groups(self.targets).items():
            hits = [t for t in members if matches(t, query)]
            if not hits:
                continue
            node = self.root.add(Text(group, style="bold"), expand=True)
            for t in hits:
                node.add_leaf(Text(t.name) + tag_badges(t), data=t)
            shown += len(hits)
        return shown

    def first_leaf(self):
        for group in self.root.children:
            if group.children:
                return group.children[0]
        return None

    def leaf_for(self, name: str):
        for group in self.root.children:
            for leaf in group.children:
                if leaf.data and leaf.data.name == name:
                    return leaf
        return None

    def focus_leaf(self, leaf) -> None:
        """Put the cursor on a leaf once the rebuilt tree has laid out its lines."""
        def move() -> None:
            self.move_cursor(leaf)
            self.scroll_to_node(leaf)

        self.call_after_refresh(move)


class ParamForm(Vertical):
    """One input per Makefile parameter: Input (text), Select (choice) or Checkbox (flag)."""

    class Changed(Message):
        """Any parameter value changed."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.target: Target | None = None

    def show(self, target: Target, values: dict[str, object] | None = None) -> None:
        self.target = target
        self.remove_children()
        values = values or {}
        rows = [self._row(p, values.get(p.name)) for p in target.params]
        if rows:
            self.mount_all(rows)
        self.display = bool(rows)

    def _row(self, p: Param, value: object) -> Horizontal:
        label = Label(f"{p.name}{' *' if p.required else ''}", classes="param-label")
        wid = f"param-{p.name}"
        if p.kind == "choice":
            widget = Select([(c, c) for c in p.choices], value=value or p.default, allow_blank=False, id=wid)
        elif p.kind == "flag":
            widget = Checkbox(f"{p.name}=1", value=bool(value), id=wid)
        else:
            widget = Input(value=str(value or p.default or ""), id=wid,
                           placeholder="required" if p.required else (p.default or "optional"))
        return Horizontal(label, widget, classes="param-row")

    def values(self) -> dict[str, object]:
        out: dict[str, object] = {}
        if self.target is None:
            return out
        for p in self.target.params:
            widgets = self.query(f"#param-{p.name}")
            if not widgets:
                continue
            widget = widgets.first()
            value = widget.value
            out[p.name] = None if value is Select.BLANK else value
        return out

    def first_input(self):
        return next(iter(self.query("Input, Select, Checkbox")), None)

    def on_input_changed(self, _event: Input.Changed) -> None:
        self.post_message(self.Changed())

    def on_select_changed(self, _event: Select.Changed) -> None:
        self.post_message(self.Changed())

    def on_checkbox_changed(self, _event: Checkbox.Changed) -> None:
        self.post_message(self.Changed())


class StatusPanel(Vertical):
    """netcore-* containers with their health."""

    def compose(self) -> ComposeResult:
        yield Label("Containers", classes="panel-title")
        table = DataTable(id="status-table", cursor_type="none", zebra_stripes=False)
        table.add_columns("container", "health")
        yield table
        yield Label("", id="status-note")

    def show(self, rows: list[Container] | None, engine: str | None) -> None:
        table = self.query_one(DataTable)
        note = self.query_one("#status-note", Label)
        table.clear()
        if engine is None:
            note.update("engine not found (docker / podman)")
            return
        if rows is None:
            note.update(f"{engine}: not reachable")
            return
        for c in rows:
            style = HEALTH_STYLE.get(c.health, "")
            table.add_row(c.name.removeprefix("netcore-"), Text(f"● {c.health}", style=style))
        note.update(f"{engine} · {len(rows)} container(s)" if rows else f"{engine}: no netcore-* containers")


class HistoryPanel(Vertical):
    """Recent runs, newest first. Enter on a row re-runs it."""

    class Rerun(Message):
        def __init__(self, run: Run):
            super().__init__()
            self.run = run

    def compose(self) -> ComposeResult:
        yield Label("History  (Enter re-runs)", classes="panel-title")
        table = DataTable(id="history-table", cursor_type="row", zebra_stripes=True)
        table.add_columns("", "target", "exit", "time")
        yield table

    def show(self, runs: list[Run]) -> None:
        self.runs = list(runs)
        table = self.query_one(DataTable)
        table.clear()
        for r in self.runs:
            mark = Text("■", style="yellow") if r.exit_code is None else (
                Text("✓", style="green") if r.ok else Text("✗", style="red"))
            exit_text = "stop" if r.exit_code is None else str(r.exit_code)
            table.add_row(mark, r.target, exit_text, f"{r.seconds:.0f}s")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "history-table" and 0 <= event.cursor_row < len(self.runs):
            self.post_message(self.Rerun(self.runs[event.cursor_row]))
