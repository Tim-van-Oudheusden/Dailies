"""The library's sidebar sections, identified by id: the three fixed ones, then one per category id.

The id of the selected section is what the window saves and restores, never its position, because the categories
shown change with the catalog.
"""

import sys
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Self

from dailies.core import languages, reorder
from dailies.core.catalog import Catalog
from dailies.core.models import Category, Difficulty, Game, Status
from dailies.core.popularity import Popularity
from dailies.core.reorder import Move
from dailies.core.search import fold

FAVORITES = "favorites"
POPULAR = "popular"
TRENDING = "trending"

#: The sections always shown, in sidebar order; Favorites is the top and the default.
FIXED = (FAVORITES, POPULAR, TRENDING)


def visible_categories(
    catalog: Catalog, *, system_languages: Collection[str] = (), show_other: bool = True
) -> set[Category]:
    """Return the categories that have at least one active game shown; the sidebar hides the others.

    Unless `show_other` is set, only games in one of `system_languages` count (see `languages.matches_language`).
    """
    return {
        game.category for game in catalog.active() if languages.matches_language(game, system_languages, show_other)
    }


def restore(saved: str, visible: Collection[str]) -> str:
    """Return the section to select at startup: the saved one if it is shown, else Favorites."""
    return saved if saved in visible else FAVORITES


def week_as_of(popularity: Popularity, now: datetime) -> date | None:
    """Return the date the This Week shelves were computed on once they are stale, or None while they are current."""
    return popularity.generated_at.date() if popularity.is_stale(now) else None


class SortMode(Enum):
    """The order of a section's games, the `sort-mode` setting; `DEFAULT` is the section's own order.

    `NOT_DONE` keeps the section's own order but puts the games done today after the others.
    """

    DEFAULT = "default"
    NAME = "name"
    DIFFICULTY = "difficulty"
    NOT_DONE = "not-done"

    @classmethod
    def from_id(cls, value: str) -> Self:
        """Return the mode with id `value`, or `DEFAULT` when the id is unknown."""
        try:
            return cls(value)
        except ValueError:
            return cls.DEFAULT


class Page(Enum):
    """What the content area shows; each value is the name of a page of the window's stack."""

    GRID = "grid"
    EMPTY_FAVORITES = "empty-favorites"
    NO_RESULTS = "no-results"
    EMPTY_SECTION = "empty-section"


@dataclass(frozen=True, kw_only=True)
class Listing:
    """A game as the library lists it: the catalog entry, whether it is a favourite and its ranks this week.

    A rank of 0 means the game is not on that shelf. `done` says whether the game was marked as done today.
    """

    game: Game
    favorite: bool = False
    popular_rank: int = 0
    trending_rank: int = 0
    done: bool = False


def contains(section: str, listing: Listing) -> bool:
    """Return whether the game belongs in `section`.

    Favorites keep broken and retired favourites, so they can be shown as unavailable; a shelf holds the games ranked on
    it; a category holds its active games.
    """
    if section == FAVORITES:
        return listing.favorite
    if section == POPULAR:
        return listing.popular_rank > 0
    if section == TRENDING:
        return listing.trending_rank > 0
    return listing.game.category.value == section and listing.game.status is Status.ACTIVE


def sort_key(
    section: str, mode: SortMode, listing: Listing, favorite_position: int | None
) -> tuple[bool, int, str, str]:
    """Return the key that orders the game within `section`; the id breaks ties, so the order is stable.

    The default order is the shelf rank on Popular and Trending, the favourite order (`favorite_position`, oldest first)
    on Favorites and the name elsewhere. Sorting by name or by difficulty (then name) overrides it everywhere; "not done
    first" keeps it, after moving the games done today to the end. Names compare case- and accent-insensitively.
    """
    game = listing.game
    done_last = mode is SortMode.NOT_DONE and listing.done
    if mode is SortMode.DIFFICULTY:
        primary = game.difficulty.sort_key
    elif mode is SortMode.NAME:
        primary = 0
    elif section == FAVORITES:
        primary = sys.maxsize if favorite_position is None else favorite_position
    elif section == POPULAR:
        primary = listing.popular_rank or sys.maxsize
    elif section == TRENDING:
        primary = listing.trending_rank or sys.maxsize
    else:
        primary = 0
    return (done_last, primary, fold(game.name), game.id)


def favorite_moves(section: str, mode: SortMode, order: Sequence[str], game_id: str) -> set[Move]:
    """Return the moves `game_id` can make: none outside Favorites or while a sort mode overrides the favourite order.

    The tile menu disables the other moves; with none, the game cannot be dragged either.
    """
    if section != FAVORITES or mode is not SortMode.DEFAULT:
        return set()
    return reorder.possible_moves(order, game_id)


def page(section: str, *, empty: bool, searching: bool) -> Page:
    """Return the content page for `section`: the grid, or the empty state that explains why there is nothing in it."""
    if not empty:
        return Page.GRID
    if searching:
        return Page.NO_RESULTS
    return Page.EMPTY_FAVORITES if section == FAVORITES else Page.EMPTY_SECTION


def category_style(category: Category) -> str:
    """Return the CSS class that tints a tile's glyph in its category's colour."""
    return f"cat-{category.value}"


def difficulty_style(difficulty: Difficulty) -> str:
    """Return the CSS class that colours a difficulty pill."""
    return f"difficulty-{difficulty.value}"
