"""po/POTFILES.in lists exactly the files xgettext must read, and po/LINGUAS only languages that have a catalog."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PO = ROOT / "po"

# The gettext functions the app calls in Python (application.py installs `_` and `ngettext` as builtins).
_PY_KEYWORDS = {"_", "ngettext", "C_", "pgettext", "npgettext"}
# Blueprint marks a translatable string as _("…") or C_("context", "…").
_BLP_MARKER = re.compile(r"\bC?_\(\s*\"")
# Merged by i18n.merge_file or read through the schema's gettext-domain: always translatable.
_DATA_TEMPLATES = ("*.desktop.in", "*.metainfo.xml.in", "*.gschema.xml.in")


def entries(path: Path) -> list[str]:
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def listed() -> list[str]:
    return entries(PO / "POTFILES.in")


def calls_gettext(path: Path) -> bool:
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _PY_KEYWORDS
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    )


def translatable_sources() -> set[str]:
    python = (path for path in (ROOT / "dailies").rglob("*.py") if calls_gettext(path))
    blueprints = (path for path in (ROOT / "data" / "ui").glob("*.blp") if _BLP_MARKER.search(path.read_text("utf-8")))
    templates = (path for pattern in _DATA_TEMPLATES for path in (ROOT / "data").glob(pattern))
    return {path.relative_to(ROOT).as_posix() for path in (*python, *blueprints, *templates)}


def test_every_file_with_translatable_strings_is_listed() -> None:
    assert sorted(translatable_sources() - set(listed())) == []


def test_every_listed_file_exists() -> None:
    assert [name for name in listed() if not (ROOT / name).is_file()] == []


def test_potfiles_lists_each_file_once_in_sorted_order() -> None:
    assert listed() == sorted(set(listed()))


def test_every_language_in_linguas_has_a_catalog() -> None:
    languages = [language for line in entries(PO / "LINGUAS") for language in line.split()]
    assert [language for language in languages if not (PO / f"{language}.po").is_file()] == []
