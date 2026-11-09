"""Parse the Makefile's "##" metadata into targets (pure Python; shared by `make help` and the terminal UI).

    ##@ Group name
    target: deps  ## Description [tags] {params}

tags   : [danger] deletes/overwrites data, [cost] calls OpenAI or creates Jira issues, [long] runs until stopped
params : NAME! required text | NAME=default | NAME=default:a|b|c (choice) | NAME? (flag, passed as NAME=1)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = PROJECT_ROOT / "Makefile"

TAGS = ("danger", "cost", "long")
GROUP_RE = re.compile(r"^##@\s*(?P<group>.+?)\s*$")
TARGET_RE = re.compile(r"^(?P<name>[A-Za-z0-9][\w.-]*)\s*:(?!=)(?P<deps>[^#]*)##\s*(?P<meta>.+?)\s*$")
TAG_RE = re.compile(r"\[(?P<tag>[a-z]+)\]")
PARAMS_RE = re.compile(r"\{(?P<params>[^}]*)\}\s*$")
PARAM_RE = re.compile(r"^(?P<name>[A-Z][A-Z0-9_]*)(?:(?P<required>!)|(?P<flag>\?)|=(?P<default>[^:\s]*)"
                      r"(?::(?P<choices>[^\s]+))?)?$")


class MakefileError(ValueError):
    """Malformed ## metadata (reported with the Makefile line number)."""


@dataclass(frozen=True)
class Param:
    name: str
    kind: str  # text | choice | flag
    default: str = ""
    choices: tuple[str, ...] = ()
    required: bool = False

    @property
    def spec(self) -> str:
        """Short usage text, e.g. Q="..." or U=alice|bob|carol."""
        if self.kind == "flag":
            return f"[{self.name}=1]"
        if self.kind == "choice":
            text = f"{self.name}={'|'.join(self.choices)}"
        else:
            text = f'{self.name}="..."' if self.required else f"{self.name}={self.default or '...'}"
        return text if self.required else f"[{text}]"


@dataclass(frozen=True)
class Target:
    name: str
    group: str
    description: str
    tags: tuple[str, ...] = ()
    params: tuple[Param, ...] = ()
    deps: tuple[str, ...] = ()
    line: int = 0

    @property
    def dangerous(self) -> bool:
        return "danger" in self.tags

    @property
    def costly(self) -> bool:
        return "cost" in self.tags

    @property
    def long_running(self) -> bool:
        return "long" in self.tags

    @property
    def needs_confirmation(self) -> bool:
        return self.dangerous or self.costly


def parse_param(token: str, line: int = 0) -> Param:
    match = PARAM_RE.match(token)
    if not match:
        raise MakefileError(f"line {line}: bad parameter spec '{token}' "
                            "(use NAME!, NAME=default, NAME=default:a|b|c or NAME?)")
    name = match["name"]
    if match["required"]:
        return Param(name, "text", required=True)
    if match["flag"]:
        return Param(name, "flag")
    default = match["default"] or ""
    if match["choices"]:
        choices = tuple(c for c in match["choices"].split("|") if c)
        if default not in choices:
            raise MakefileError(f"line {line}: default '{default}' of {name} is not one of {choices}")
        return Param(name, "choice", default=default, choices=choices)
    return Param(name, "text", default=default)


def parse_meta(meta: str, line: int = 0) -> tuple[str, tuple[str, ...], tuple[Param, ...]]:
    """'Description [cost] {Q! U=bob:alice|bob}' -> (description, tags, params)."""
    params: tuple[Param, ...] = ()
    if match := PARAMS_RE.search(meta):
        params = tuple(parse_param(tok, line) for tok in match["params"].split())
        meta = meta[: match.start()]
    tags = tuple(m["tag"] for m in TAG_RE.finditer(meta))
    unknown = [t for t in tags if t not in TAGS]
    if unknown:
        raise MakefileError(f"line {line}: unknown tag(s) {unknown} (known: {', '.join(TAGS)})")
    description = " ".join(TAG_RE.sub("", meta).split())
    if not description:
        raise MakefileError(f"line {line}: missing description")
    return description, tags, params


def parse_makefile(text: str) -> list[Target]:
    """All documented targets, in file order. Undocumented targets (no ##) are ignored."""
    targets, group, seen = [], "Other", set()
    for number, raw in enumerate(text.splitlines(), start=1):
        if group_match := GROUP_RE.match(raw):
            group = group_match["group"]
            continue
        if not (match := TARGET_RE.match(raw)):
            continue
        name = match["name"]
        if name in seen:
            raise MakefileError(f"line {number}: target '{name}' is documented twice")
        seen.add(name)
        description, tags, params = parse_meta(match["meta"], number)
        targets.append(Target(name, group, description, tags, params, tuple(match["deps"].split()), number))
    return targets


def load_targets(path: Path = MAKEFILE) -> list[Target]:
    return parse_makefile(path.read_text(encoding="utf-8"))


def groups(targets: list[Target]) -> dict[str, list[Target]]:
    """Targets by group, keeping the Makefile order."""
    out: dict[str, list[Target]] = {}
    for t in targets:
        out.setdefault(t.group, []).append(t)
    return out


# ---------------------------- commands ----------------------------


def validate(target: Target, values: dict[str, object]) -> list[str]:
    """Problems that block a run: missing required values, values the Makefile recipes cannot carry."""
    errors = []
    for p in target.params:
        value = values.get(p.name)
        if p.kind == "flag":
            continue
        text = "" if value is None else str(value).strip()
        if p.required and not text:
            errors.append(f"{p.name} is required")
        if '"' in text:
            errors.append(f'{p.name}: double quotes (") are not supported by the recipe - use single quotes')
        if p.kind == "choice" and text and text not in p.choices:
            errors.append(f"{p.name} must be one of {', '.join(p.choices)}")
    return errors


def build_args(target: Target, values: dict[str, object], engine: str | None = None,
               dry_run: bool = False) -> list[str]:
    """argv for subprocess (no shell): make [-n] target NAME=value ... [ENGINE=...]"""
    args = ["make"] + (["-n"] if dry_run else []) + [target.name]
    for p in target.params:
        value = values.get(p.name)
        if p.kind == "flag":
            if value:
                args.append(f"{p.name}=1")
            continue
        text = "" if value is None else str(value).strip()
        if p.kind == "choice":
            text = text or p.default
        if text:
            args.append(f"{p.name}={text}")
    if engine and engine != "auto":
        args.append(f"ENGINE={engine}")
    return args


def display_command(args: list[str]) -> str:
    """Copy-pasteable command line: values with spaces or shell characters are double-quoted."""
    out = []
    for arg in args:
        name, sep, value = arg.partition("=")
        if sep and (not value or re.search(r"[\s'&|<>()$;`]", value)):
            out.append(f'{name}="{value}"')
        else:
            out.append(arg)
    return " ".join(out)
