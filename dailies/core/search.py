"""Library search: a case- and accent-insensitive substring match."""

import unicodedata
from enum import Enum

from dailies.core.models import Game


def fold(text: str) -> str:
    """Return `text` case-folded, in compatibility form and without combining marks, so "Pokédle" folds to "pokedle"."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def matches(game: Game, query: str, category_label: str) -> bool:
    """Return whether `query` occurs in the game's name, description, tags or category label.

    Args:
        game: The game to test.
        query: What the user typed; an empty or all-whitespace query matches every game.
        category_label: The category's display name as shown, so a translated label is searchable.
    """
    needle = fold(query.strip())
    if not needle:
        return True
    return any(needle in fold(text) for text in (game.name, game.description, *game.tags, category_label))


class Change(Enum):
    """How a new query relates to the previous one, so a list filter knows which games it has to test again."""

    SAME = "same"
    MORE_STRICT = "more-strict"
    LESS_STRICT = "less-strict"
    DIFFERENT = "different"


def change(old: str, new: str) -> Change:
    """Return how replacing the query `old` by `new` changes the matches.

    A query that contains the old one can only drop matches; one contained in the old one can only add matches.
    """
    old, new = fold(old.strip()), fold(new.strip())
    if old == new:
        return Change.SAME
    if old in new:
        return Change.MORE_STRICT
    if new in old:
        return Change.LESS_STRICT
    return Change.DIFFERENT
