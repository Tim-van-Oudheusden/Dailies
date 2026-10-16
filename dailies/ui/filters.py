"""The grid's filters and sorters: thin `Gtk.Filter` and `Gtk.Sorter` shells over `dailies.core`."""

from collections.abc import Collection
from typing import TYPE_CHECKING

from gi.repository import GObject, Gtk

from dailies.core import languages, search, sections
from dailies.data.favorites import Favorites
from dailies.ui.game_object import GameObject

if TYPE_CHECKING:
    from dailies.core.models import Game

_FILTER_CHANGES = {
    search.Change.MORE_STRICT: Gtk.FilterChange.MORE_STRICT,
    search.Change.LESS_STRICT: Gtk.FilterChange.LESS_STRICT,
    search.Change.DIFFERENT: Gtk.FilterChange.DIFFERENT,
}


class SectionFilter(Gtk.Filter):
    """Keeps the games of `section`: a fixed section id or a category id (see `sections.contains`).

    It re-filters when `section` changes; whoever changes the games' favourite state or ranks calls `changed()`.
    """

    __gtype_name__ = "DailiesSectionFilter"

    section = GObject.Property(type=str, default=sections.FAVORITES)

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.connect("notify::section", lambda *_args: self.changed(Gtk.FilterChange.DIFFERENT))

    def do_match(self, item: GameObject) -> bool:
        """Return whether `item` belongs in the section."""
        return sections.contains(self.props.section, item.listing())

    def do_get_strictness(self) -> Gtk.FilterMatch:
        """Return that some games match."""
        return Gtk.FilterMatch.SOME


class SearchFilter(Gtk.Filter):
    """Keeps the games that match `text` (see `search.rank`); an empty text keeps every game.

    A new text tells the list which games to test again (see `search.change`): a query that may match with a typo
    tests them all.
    """

    __gtype_name__ = "DailiesSearchFilter"

    def __init__(self, **kwargs: object) -> None:
        self._text = ""
        super().__init__(**kwargs)

    @GObject.Property(type=str, default="")
    def text(self) -> str:
        """The query, as typed."""
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        old, self._text = self._text, value
        if (change := search.change(old, value)) is not search.Change.SAME:
            self.changed(_FILTER_CHANGES[change])

    def do_match(self, item: GameObject) -> bool:
        """Return whether `item` matches the query."""
        return search.matches(item.props.game, self._text, item.props.category_label)

    def do_get_strictness(self) -> Gtk.FilterMatch:
        """Return that every game matches an empty query, some games any other."""
        return Gtk.FilterMatch.ALL if not self._text.strip() else Gtk.FilterMatch.SOME


class LanguageFilter(Gtk.Filter):
    """Keeps the games in one of `system_languages` unless `show-other-languages` is set (see `matches_language`).

    Favorites are exempt: a favourite shows there whatever its language. It re-filters when `section` or
    `show-other-languages` changes.
    """

    __gtype_name__ = "DailiesLanguageFilter"

    section = GObject.Property(type=str, default=sections.FAVORITES)

    def __init__(self, system_languages: Collection[str], **kwargs: object) -> None:
        self._system_languages = system_languages
        self._show_other = True
        super().__init__(**kwargs)
        self.connect("notify::section", lambda *_args: self.changed(Gtk.FilterChange.DIFFERENT))

    @GObject.Property(type=bool, default=True)
    def show_other_languages(self) -> bool:
        """Whether games in languages other than the system's are kept: the `show-other-languages` setting."""
        return self._show_other

    @show_other_languages.setter
    def show_other_languages(self, value: bool) -> None:
        if value != self._show_other:
            self._show_other = value
            self.changed(Gtk.FilterChange.LESS_STRICT if value else Gtk.FilterChange.MORE_STRICT)

    def do_match(self, item: GameObject) -> bool:
        """Return whether `item` is shown in the section."""
        if self.props.section == sections.FAVORITES:
            return True
        return languages.matches_language(item.props.game, self._system_languages, self._show_other)

    def do_get_strictness(self) -> Gtk.FilterMatch:
        """Return that every game matches on Favorites or while other languages are shown, some games otherwise."""
        exempt = self._show_other or self.props.section == sections.FAVORITES
        return Gtk.FilterMatch.ALL if exempt else Gtk.FilterMatch.SOME


class SearchSorter(Gtk.Sorter):
    """Orders the games by how well they match `text` (see `search.rank`), best first, while a query is active.

    Put it first in a `Gtk.MultiSorter`, before the section's sorter: games of the same rank, and every game while the
    query is empty, keep the section's order.
    """

    __gtype_name__ = "DailiesSearchSorter"

    def __init__(self, **kwargs: object) -> None:
        self._text = ""
        self._ranks: dict[tuple[Game, str], int] = {}
        super().__init__(**kwargs)

    @GObject.Property(type=str, default="")
    def text(self) -> str:
        """The query, as typed."""
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        old, self._text = self._text, value
        if search.change(old, value) is not search.Change.SAME:
            self._ranks.clear()
            self.changed(Gtk.SorterChange.DIFFERENT)

    def do_compare(self, first: GameObject, second: GameObject) -> Gtk.Ordering:
        """Return the better match of `first` and `second` as the smaller."""
        a, b = self._rank(first), self._rank(second)
        return Gtk.Ordering.SMALLER if a > b else Gtk.Ordering.LARGER if a < b else Gtk.Ordering.EQUAL

    def do_get_order(self) -> Gtk.SorterOrder:
        """Return that every game compares equal without a query, and games of the same rank do with one."""
        return Gtk.SorterOrder.PARTIAL if self._text.strip() else Gtk.SorterOrder.NONE

    def _rank(self, item: GameObject) -> int:
        # Sorting compares each game many times; rank it once per query. A reload brings new `Game`s, so new keys.
        game, label = item.props.game, item.props.category_label
        if (rank := self._ranks.get((game, label))) is None:
            tier = search.rank(game, self._text, label)
            rank = self._ranks[game, label] = 0 if tier is None else int(tier)
        return rank


class SectionSorter(Gtk.Sorter):
    """Orders the games of `section` by `sort-mode` (the nick of the `sort-mode` setting; see `sections.sort_key`).

    It re-sorts when `section` or `sort-mode` changes, and when the favourite order changes.
    """

    __gtype_name__ = "DailiesSectionSorter"

    section = GObject.Property(type=str, default=sections.FAVORITES)
    sort_mode = GObject.Property(type=str, default=sections.SortMode.DEFAULT.value)

    def __init__(self, favorites: Favorites, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._favorites = favorites
        self._positions = _positions(favorites)
        favorites.connect("changed", self._on_favorites_changed)
        for prop in ("section", "sort-mode"):
            self.connect(f"notify::{prop}", lambda *_args: self.changed(Gtk.SorterChange.DIFFERENT))

    def do_compare(self, first: GameObject, second: GameObject) -> Gtk.Ordering:
        """Return how `first` and `second` are ordered in the section."""
        a, b = self._key(first), self._key(second)
        return Gtk.Ordering.SMALLER if a < b else Gtk.Ordering.LARGER if a > b else Gtk.Ordering.EQUAL

    def do_get_order(self) -> Gtk.SorterOrder:
        """Return that the order is total: no two games compare equal."""
        return Gtk.SorterOrder.TOTAL

    def _key(self, item: GameObject) -> tuple[bool, int, str, str]:
        mode = sections.SortMode.from_id(self.props.sort_mode)
        listing = item.listing()
        return sections.sort_key(self.props.section, mode, listing, self._positions.get(listing.game.id))

    def _on_favorites_changed(self, favorites: Favorites, _game_id: str) -> None:
        self._positions = _positions(favorites)
        if self.props.section == sections.FAVORITES:
            self.changed(Gtk.SorterChange.DIFFERENT)


def _positions(favorites: Favorites) -> dict[str, int]:
    return {game_id: position for position, game_id in enumerate(favorites.order())}
