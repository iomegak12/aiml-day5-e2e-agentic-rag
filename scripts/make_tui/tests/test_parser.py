"""Makefile ## metadata parser and command builder (no Textual, no make needed)."""

from __future__ import annotations

import re

import pytest

from make_tui.parser import (
    MAKEFILE,
    MakefileError,
    Param,
    build_args,
    display_command,
    groups,
    load_targets,
    parse_makefile,
    parse_meta,
    parse_param,
    validate,
)

SAMPLE = """\
UV ?= uv
.PHONY: a b

##@ First group
plain:  ## Just a description
	@echo plain

deps: plain other  ## Has prerequisites [long]
	@echo deps

undocumented:
	@echo hidden

##@ Second group
ask:  ## Ask something [cost] {Q! U=bob:alice|bob|carol M=plan:plan|react}
	@echo $(Q)

reset:  ## Delete it all [danger] [cost] {FORCE? NAME=x}
	@echo reset
"""


@pytest.fixture
def targets():
    return {t.name: t for t in parse_makefile(SAMPLE)}


def test_documented_targets_only_in_file_order():
    assert [t.name for t in parse_makefile(SAMPLE)] == ["plain", "deps", "ask", "reset"]


def test_groups_descriptions_deps_and_tags(targets):
    assert targets["plain"].group == "First group" and targets["plain"].description == "Just a description"
    assert targets["deps"].deps == ("plain", "other") and targets["deps"].long_running
    assert targets["ask"].group == "Second group" and targets["ask"].costly and not targets["ask"].dangerous
    assert targets["reset"].tags == ("danger", "cost") and targets["reset"].needs_confirmation
    assert targets["reset"].description == "Delete it all"
    assert list(groups(list(targets.values()))) == ["First group", "Second group"]


def test_param_kinds(targets):
    q, u, m = targets["ask"].params
    assert q == Param("Q", "text", required=True)
    assert u == Param("U", "choice", default="bob", choices=("alice", "bob", "carol"))
    assert m.choices == ("plan", "react")
    force, name = targets["reset"].params
    assert force == Param("FORCE", "flag") and name == Param("NAME", "text", default="x")
    assert [p.spec for p in targets["ask"].params] == ['Q="..."', "[U=alice|bob|carol]", "[M=plan|react]"]


@pytest.mark.parametrize("meta,message", [
    ("Bad tag [boom]", "unknown tag"),
    ("[cost]", "missing description"),
    ("Choice default not listed {U=dave:alice|bob}", "is not one of"),
    ("Lower-case param {q!}", "bad parameter spec"),
])
def test_malformed_metadata_is_reported_with_line(meta, message):
    with pytest.raises(MakefileError, match=message):
        parse_meta(meta, line=7)


def test_duplicate_target_is_an_error():
    with pytest.raises(MakefileError, match="documented twice"):
        parse_makefile("a:  ## one\na:  ## two\n")


def test_variable_assignments_are_not_targets():
    assert parse_makefile("X := 1  ## not a target\nY ?= 2\n") == []


def test_build_args_and_preview(targets):
    ask = targets["ask"]
    args = build_args(ask, {"Q": "  How do I fix BFD flaps?  ", "U": "carol", "M": None}, engine="podman")
    assert args == ["make", "ask", "Q=How do I fix BFD flaps?", "U=carol", "M=plan", "ENGINE=podman"]
    assert display_command(args) == 'make ask Q="How do I fix BFD flaps?" U=carol M=plan ENGINE=podman'
    assert build_args(ask, {"Q": "x"}, engine="auto", dry_run=True)[:3] == ["make", "-n", "ask"]
    reset = targets["reset"]
    assert build_args(reset, {"FORCE": True, "NAME": ""}) == ["make", "reset", "FORCE=1"]
    assert build_args(reset, {"FORCE": False, "NAME": "y"}) == ["make", "reset", "NAME=y"]


def test_validate(targets):
    ask = targets["ask"]
    assert validate(ask, {"Q": "  "}) == ["Q is required"]
    assert "double quotes" in validate(ask, {"Q": 'say "hi"'})[0]
    assert validate(ask, {"Q": "ok", "U": "mallory"}) == ["U must be one of alice, bob, carol"]
    assert validate(ask, {"Q": "it's fine", "U": "bob"}) == []


# ---------------------------- the real Makefile ----------------------------


def test_every_real_target_is_documented():
    """Every rule in the Makefile (except special/pattern ones) carries a ## description and a group."""
    text = MAKEFILE.read_text(encoding="utf-8")
    rules = {m[1] for m in re.finditer(r"^([a-z][\w-]*)\s*:(?!=)", text, re.MULTILINE)}
    documented = {t.name: t for t in load_targets()}
    assert rules == set(documented), f"undocumented: {rules - set(documented)}"
    assert all(t.group != "Other" and t.description for t in documented.values())


def test_real_makefile_highlights():
    t = {x.name: x for x in load_targets()}
    assert t["agent-ask"].params[0].required and t["agent-ask"].params[1].choices == ("alice", "bob", "carol")
    assert t["chroma-reset"].dangerous and t["populate"].costly and t["api-run"].long_running
    assert [p.name for p in t["up-all"].params] == ["REPOPULATE"]
    assert set(t["up-all"].deps) >= {"chroma-up", "redis-up", "db-up"}


@pytest.mark.parametrize("token", ["=x", "U=bob:", "Q!!", "1A"])
def test_parse_param_rejects_garbage(token):
    with pytest.raises(MakefileError):
        parse_param(token, line=1)
