"""The grid's filters and sorter: thin `Gtk.Filter` and `Gtk.Sorter` shells over `dailies.core`."""

from gi.repository import GObject, Gtk

from dailies.core import search, sections
from dailies.data.favorites import Favorites
from dailies.ui.game_object import GameObject

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
    """Keeps the games that match `text` (see `search.matches`); an empty text keeps every game."""

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

    def _key(self, item: GameObject) -> tuple[int, str, str]:
        mode = sections.SortMode.from_id(self.props.sort_mode)
        listing = item.listing()
        return sections.sort_key(self.props.section, mode, listing, self._positions.get(listing.game.id))

    def _on_favorites_changed(self, favorites: Favorites, _game_id: str) -> None:
        self._positions = _positions(favorites)
        if self.props.section == sections.FAVORITES:
            self.changed(Gtk.SorterChange.DIFFERENT)


def _positions(favorites: Favorites) -> dict[str, int]:
    return {game_id: position for position, game_id in enumerate(favorites.order())}
