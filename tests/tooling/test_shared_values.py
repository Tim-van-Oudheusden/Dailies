"""Every copy of a value that two or more files write out is the same.

Some values have to be restated: one copy lives where the other cannot import it (a JSON Schema, a workflow, a shell
script, a Meson file), or nothing wires the import up. A test that pins each copy to its own literal list stays green
while the copies drift apart, because nothing compares them with each other. The catalog taxonomy is the case that
prompted this file (#543): `catalog.schema.json` and `dailies.core.models` each list the category, difficulty and status
ids, and `from_id` maps an id the app lacks to a fallback, so a schema-only addition files every game that uses it under
the fallback (Trivia, Medium, Broken) and fails nothing else.

A new shared value is a row in `SHARED_VALUES`: its name and one extractor per file that holds a copy. An extractor
reads its copy or fails naming the place it no longer finds, so a copy that moves fails here instead of dropping out of
the check. Add an extractor kind (a regex for a file Python cannot parse, say) when a row needs one; it must fail unless
its pattern matches exactly once.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pytest

from dailies.core.models import Category, Difficulty, Status

ROOT = Path(__file__).resolve().parents[2]
CATALOG_SCHEMA = ROOT / "data" / "v1" / "schema" / "catalog.schema.json"


@dataclass(frozen=True)
class Copy:
    """One file's copy of a shared value: where it is, for the failure message, and how to read it."""

    where: str
    read: Callable[[], tuple[str, ...]]


def enum_values(enum: type[Enum]) -> Copy:
    """The values of a Python enum's members, in definition order."""
    return Copy(f"{enum.__module__}.{enum.__qualname__}", lambda: tuple(member.value for member in enum))


def json_list(path: Path, *keys: str) -> Copy:
    """The list at `keys` in the JSON file `path`."""
    where = f"{path.relative_to(ROOT)} {'/'.join(keys)}"

    def read() -> tuple[str, ...]:
        node = json.loads(path.read_text(encoding="utf-8"))
        for depth, key in enumerate(keys):
            if not isinstance(node, dict) or key not in node:
                pytest.fail(f"{path.relative_to(ROOT)} no longer has {'/'.join(keys[: depth + 1])}")
            node = node[key]
        if not isinstance(node, list):
            pytest.fail(f"{where} is no longer a list")
        return tuple(node)

    return Copy(where, read)


def catalog_enum(field: str) -> Copy:
    """The `enum` of a game field in the catalog schema."""
    return json_list(CATALOG_SCHEMA, "$defs", "game", "properties", field, "enum")


SHARED_VALUES: dict[str, tuple[Copy, ...]] = {
    "catalog category ids, in sidebar order": (enum_values(Category), catalog_enum("category")),
    "catalog difficulty ids, easiest first": (enum_values(Difficulty), catalog_enum("difficulty")),
    "catalog status ids": (enum_values(Status), catalog_enum("status")),
}


@pytest.mark.parametrize("copies", SHARED_VALUES.values(), ids=SHARED_VALUES.keys())
def test_every_copy_of_a_shared_value_is_the_same(copies: tuple[Copy, ...]) -> None:
    assert len(copies) >= 2, "a shared value needs at least two copies to compare"
    first, *others = copies
    expected = first.read()
    for other in others:
        assert other.read() == expected, f"{other.where} differs from {first.where}"
