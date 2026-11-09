"""Terminal UI for the project's make targets (Textual). Start it with `uv run tui.py` or `make tui`.

The target list, groups, tags and parameter forms come from the Makefile's ## comments (see parser.py).
Textual is imported lazily, so `make help` (help.py) works without it.
"""


def main() -> None:
    from make_tui.app import MakeTui

    MakeTui().run()
