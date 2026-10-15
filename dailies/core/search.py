"""Library search: a case- and accent-insensitive substring match."""

import unicodedata

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
