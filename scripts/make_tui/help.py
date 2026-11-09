"""`make help`: the target list, generated from the Makefile's ## comments (python -m make_tui.help)."""

from __future__ import annotations

import os
import sys

from make_tui.parser import groups, load_targets

TAG_LABELS = {"danger": "DESTRUCTIVE", "cost": "costs API calls", "long": "runs until stopped"}


def render(color: bool = False) -> str:
    def paint(text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if color else text

    targets = load_targets()
    width = max(len(t.name) for t in targets) + 2
    lines = ["Usage: make <target> [NAME=value ...]    Terminal UI: uv run tui.py  (or make tui)", ""]
    for group, members in groups(targets).items():
        lines.append(paint(group, "1;36"))
        for t in members:
            tags = "".join(f"  [{TAG_LABELS[tag]}]" for tag in t.tags)
            lines.append(f"  {paint(t.name.ljust(width), '1')}{t.description}{paint(tags, '33') if tags else ''}")
            if t.params:
                lines.append(f"  {' ' * width}{paint(' '.join(p.spec for p in t.params), '2')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(render(color))


if __name__ == "__main__":
    main()
