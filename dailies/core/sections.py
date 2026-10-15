"""The library's sidebar sections, identified by id: the three fixed ones, then one per category id.

The id of the selected section is what the window saves and restores, never its position, because the categories
shown change with the catalog.
"""

from collections.abc import Collection
from datetime import date, datetime

from dailies.core.catalog import Catalog
from dailies.core.models import Category
from dailies.core.popularity import Popularity

FAVORITES = "favorites"
POPULAR = "popular"
TRENDING = "trending"

#: The sections always shown, in sidebar order; Favorites is the top and the default.
FIXED = (FAVORITES, POPULAR, TRENDING)


def visible_categories(catalog: Catalog) -> set[Category]:
    """Return the categories that have at least one active game; the sidebar hides the others."""
    return {game.category for game in catalog.active()}


def restore(saved: str, visible: Collection[str]) -> str:
    """Return the section to select at startup: the saved one if it is shown, else Favorites."""
    return saved if saved in visible else FAVORITES


def week_as_of(popularity: Popularity, now: datetime) -> date | None:
    """Return the date the This Week shelves were computed on once they are stale, or None while they are current."""
    return popularity.generated_at.date() if popularity.is_stale(now) else None
