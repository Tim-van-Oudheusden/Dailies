"""The favourites export file: `{"schema_version": 1, "favorites": ["worldle", …]}`, UTF-8, 2-space JSON.

`parse` checks the whole file before anything changes, so a bad file leaves the favourites as they were.
"""

import json
from collections.abc import Sequence
from enum import StrEnum

from dailies.core._fields import SCHEMA_VERSION, Fields


class FavoritesFileError(ValueError):
    """The file is not a favourites export this app understands; the favourites must not change."""


class ImportMode(StrEnum):
    """How imported favourites join the current ones."""

    MERGE = "merge"
    """Keep the current favourites in their order and append the imported ids not among them, in file order."""
    REPLACE = "replace"
    """Take the file's favourites and order instead."""


def dump(ids: Sequence[str]) -> bytes:
    """Return the export file for the favourite ids `ids`, in display order."""
    document = {"schema_version": SCHEMA_VERSION, "favorites": list(ids)}
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def parse(data: bytes) -> list[str]:
    """Return the favourite ids in an export file, in its order.

    Raises:
        FavoritesFileError: The data is not JSON, has another `schema_version`, or `favorites` is not a list of
            distinct, non-empty strings.
    """
    document = Fields.load(data, FavoritesFileError)
    ids = document.required("favorites", list)
    seen: set[str] = set()
    for i, game_id in enumerate(ids):
        if not isinstance(game_id, str) or not game_id.strip():
            document.fail(f"favorites[{i}]", f"{game_id!r} is not a game id")
        if game_id in seen:
            document.fail(f"favorites[{i}]", f"{game_id!r} is listed twice")
        seen.add(game_id)
    return ids


def combine(current: Sequence[str], imported: Sequence[str], mode: ImportMode) -> list[str]:
    """Return the favourites after importing `imported` into `current` the way `mode` says.

    Ids the catalog does not know are kept either way: they resolve once the catalog has them.
    """
    if mode is ImportMode.REPLACE:
        return list(imported)
    return list(dict.fromkeys([*current, *imported]))
