"""The enums in the GSettings schema spell their nicks as the code does, and every id the code styles has a CSS rule.

`from_id` falls back on an unknown value, and GSettings refuses a nick its schema lacks, so a drift between the two
would only show in the running app: a setting that silently resets, or a write that fails.
"""

import re
from enum import Enum
from pathlib import Path

import pytest

from dailies.core.models import Category, Difficulty
from dailies.core.opening import OpenMode
from dailies.core.sections import SortMode, category_style, difficulty_style
from dailies.core.web import SessionIsolation

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "data" / "io.github.tim_van_oudheusden.Dailies.gschema.xml.in"
STYLE = ROOT / "data" / "ui" / "style.css"


def nicks(enum_id: str) -> set[str]:
    enum = re.search(rf'<enum id="@APP_ID@\.{enum_id}">(.*?)</enum>', SCHEMA.read_text(encoding="utf-8"), re.DOTALL)
    assert enum, enum_id
    return set(re.findall(r'<value nick="([^"]+)"', enum[1]))


@pytest.mark.parametrize("enum", [OpenMode, SortMode, SessionIsolation])
def test_a_settings_enum_has_the_nicks_of_its_schema_enum(enum: type[Enum]) -> None:
    assert {member.value for member in enum} == nicks(enum.__name__)


def test_every_category_and_difficulty_style_has_a_css_rule() -> None:
    classes = set(re.findall(r"^\.([a-z0-9-]+)\s*\{", STYLE.read_text(encoding="utf-8"), re.MULTILINE))

    assert {category_style(category) for category in Category} <= classes
    assert {difficulty_style(difficulty) for difficulty in Difficulty} <= classes
