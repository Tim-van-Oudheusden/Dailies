"""data/ui/meson.build compiles every Blueprint file and declares each .ui it writes as an output.

The GResource bundles the compiled .ui files. Ninja rebuilds it in the same run as a changed .blp only when an edge
says the Blueprint step produces that .ui; a target whose output is a directory, or a .ui missing from `output:`, leaves
`dailies.gresource` holding the previous template after one `ninja`, so `meson test` and the app run from the build
directory load the old UI (#432). Clean builds, which CI and Flatpak use, never show it.
"""

import re
from pathlib import Path

from tests.tooling.test_meson_install import without_comments

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "data" / "ui"

_TARGET = re.compile(r"\bcustom_target\(\s*'blueprints',(?P<args>.*?)\n\)", re.DOTALL)
_INPUT = re.compile(r"\binput:\s*files\((?P<list>[^)]*)\)")
_OUTPUT = re.compile(r"\boutput:\s*(?P<list>\[[^\]]*\]|'[^']*')")
_QUOTED = re.compile(r"'([^']+)'")


def declared(meson: str) -> tuple[list[str], list[str]]:
    """The `blueprints` target's (inputs, outputs) as written in `meson`."""
    target = _TARGET.search(without_comments(meson))
    assert target, "no custom_target('blueprints', ...)"
    inputs = _INPUT.search(target.group("args"))
    outputs = _OUTPUT.search(target.group("args"))
    assert inputs, target.group("args")
    assert outputs, target.group("args")
    return _QUOTED.findall(inputs.group("list")), _QUOTED.findall(outputs.group("list"))


def undeclared_outputs(meson: str) -> set[str]:
    """Each .ui some input compiles to that `output:` does not name, plus any output that is not such a .ui."""
    inputs, outputs = declared(meson)
    compiled = {Path(name).with_suffix(".ui").name for name in inputs}
    return compiled ^ set(outputs)


def test_every_blueprint_file_is_compiled() -> None:
    inputs, _ = declared((UI / "meson.build").read_text(encoding="utf-8"))
    assert sorted(inputs) == sorted(path.name for path in UI.glob("*.blp"))


def test_every_compiled_ui_is_a_declared_output() -> None:
    assert undeclared_outputs((UI / "meson.build").read_text(encoding="utf-8")) == set()


def test_the_compiler_writes_where_the_outputs_are_declared() -> None:
    # batch-compile writes into the directory it is given; @OUTDIR@ is where Meson expects the declared outputs.
    assert "'@OUTDIR@'" in (UI / "meson.build").read_text(encoding="utf-8")


def test_a_directory_output_is_reported() -> None:
    # The shape #432 replaced: one '.' output that names no .ui at all.
    meson = "x = custom_target(\n  'blueprints',\n  input: files('ui/a.blp'),\n  output: '.',\n)\n"
    assert undeclared_outputs(meson) == {"a.ui", "."}


def test_a_blueprint_left_out_of_the_outputs_is_reported() -> None:
    meson = (
        "x = custom_target(\n  'blueprints',\n  input: files(\n    'a.blp',\n    'b.blp',\n  ),\n"
        "  output: [\n    'a.ui',\n    # 'b.ui',\n  ],\n)\n"
    )
    assert undeclared_outputs(meson) == {"b.ui"}
