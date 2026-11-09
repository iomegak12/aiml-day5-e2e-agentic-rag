"""Modal confirmation before [danger] / [cost] targets."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ConfirmScreen(ModalScreen[bool]):
    """Yes / No dialog; dismisses with True only on 'Run it'."""

    BINDINGS = [("escape", "dismiss(False)", "Cancel"), ("n", "dismiss(False)", "No"), ("y", "dismiss(True)", "Yes")]

    def __init__(self, title: str, message: str, command: str, danger: bool):
        super().__init__()
        self._title, self._message, self._command, self._danger = title, message, command, danger

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box", classes="danger" if self._danger else "cost"):
            yield Label(self._title, id="confirm-title")
            yield Static(self._message, id="confirm-message")
            yield Static(f"$ {self._command}", id="confirm-command", markup=False)
            with Horizontal(id="confirm-buttons"):
                yield Button("Run it (y)", variant="error" if self._danger else "warning", id="confirm-yes")
                yield Button("Cancel (n)", variant="default", id="confirm-no")

    def on_mount(self) -> None:
        self.query_one("#confirm-no", Button).focus()  # the safe choice has the focus

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")
