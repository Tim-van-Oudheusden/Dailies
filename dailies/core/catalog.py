"""Parse the published catalog, `data/v1/games.json`.

`parse` checks structure only: `schema_version` is 1, required keys are present and every field the app reads has the
right JSON type. Anything else raises `CatalogError`, so the caller keeps its last good copy. Enum values are
tolerant instead (see `dailies.core.models`): an unknown category is shown as trivia, an unknown status hides the game
as broken and an unknown difficulty is treated as medium, so a catalog written for a newer app still loads.
"""

from dataclasses import dataclass
from datetime import datetime
from functools import cached_property

from dailies.core._fields import Fields
from dailies.core.models import Category, Difficulty, Game, Status


class CatalogError(ValueError):
    """The catalog file is structurally wrong and must not replace the last good copy."""


@dataclass(frozen=True)
class Catalog:
    """Every game in a catalog file, including broken and retired ones, so favourites still resolve."""

    generated_at: datetime
    games: tuple[Game, ...]

    def get(self, game_id: str) -> Game | None:
        """Return the game with id `game_id`, whatever its status, or None when the catalog has no such game."""
        return self._by_id.get(game_id)

    def active(self) -> tuple[Game, ...]:
        """Return the games to display: those whose status is active, in catalog order."""
        return tuple(game for game in self.games if game.status is Status.ACTIVE)

    @cached_property
    def _by_id(self) -> dict[str, Game]:
        return {game.id: game for game in self.games}


def parse(data: bytes) -> Catalog:
    """Parse a catalog file.

    Args:
        data: The raw bytes of a `games.json` file.

    Returns:
        The parsed catalog, with every entry in file order.

    Raises:
        CatalogError: The data is not JSON, has another `schema_version`, or misses or mistypes a required field.
    """
    document = Fields.load(data, CatalogError)
    return Catalog(
        generated_at=document.timestamp("generated_at"),
        games=tuple(_parse_game(record) for record in document.objects("games")),
    )


def is_newer(a: Catalog, b: Catalog) -> bool:
    """Return whether catalog `a` was generated after catalog `b`."""
    return a.generated_at > b.generated_at


def _parse_game(record: Fields) -> Game:
    return Game(
        id=record.required("id", str),
        name=record.required("name", str),
        url=record.required("url", str),
        category=Category.from_id(record.required("category", str)),
        difficulty=Difficulty.from_id(record.required("difficulty", str)),
        description=record.required("description", str),
        tags=record.strings("tags"),
        language=record.optional("language", str, "en"),
        added=record.day("added"),
        status=Status.from_id(record.required("status", str)),
        domain=record.required("domain", str),
        free_no_account=record.optional("free_no_account", bool, None),
        wikipedia=record.optional("wikipedia", str, None),
        source_issue=record.optional("source_issue", int, None),
    )
