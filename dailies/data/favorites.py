from collections.abc import Callable, Sequence
from typing import ClassVar

from gi.repository import Gio, GLib, GObject

from dailies.core import favorites_file
from dailies.core.favorites_file import FavoritesFileError, ImportMode

_KEY = "favorites"


class Favorites(GObject.Object):
    """The favourite game ids, in display order (insertion order, newest last), kept in the `favorites` key.

    Emits `changed(id)` whenever a game becomes or stops being a favourite or moves, whether through this object or
    through an external change to the key, such as `gsettings set` from a terminal.
    """

    __gtype_name__ = "DailiesFavorites"
    __gsignals__: ClassVar = {"changed": (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self, settings: Gio.Settings) -> None:
        super().__init__()
        self._settings = settings
        self._order = _unique(settings.get_strv(_KEY))
        settings.connect(f"changed::{_KEY}", self._on_settings_changed)

    def is_favorite(self, game_id: str) -> bool:
        """Return whether `game_id` is a favourite."""
        return game_id in self._order

    def order(self) -> list[str]:
        """Return the favourite ids in display order."""
        return list(self._order)

    def toggle(self, game_id: str) -> bool:
        """Append `game_id` when it is not a favourite, remove it when it is.

        Returns:
            Whether `game_id` is a favourite now.
        """
        if game_id in self._order:
            self._order.remove(game_id)
        else:
            self._order.append(game_id)
        self._store(game_id)
        return game_id in self._order

    def add(self, game_id: str, index: int | None = None) -> None:
        """Make `game_id` a favourite at position `index` (appended when None); undo uses it to restore a removal."""
        if game_id in self._order:
            return
        self._order.insert(len(self._order) if index is None else index, game_id)
        self._store(game_id)

    def set_order(self, ids: Sequence[str]) -> None:
        """Make `ids` the favourites, in that order (duplicates dropped)."""
        # The list is updated first, so the changed::favorites this write triggers finds nothing new.
        self._update(_unique(list(ids)))
        self._settings.set_strv(_KEY, self._order)

    def import_ids(self, ids: Sequence[str], mode: ImportMode) -> None:
        """Merge `ids` into the favourites or replace them with `ids`, as `mode` says (see `favorites_file.combine`)."""
        self.set_order(favorites_file.combine(self._order, ids, mode))

    def _store(self, game_id: str) -> None:
        # The list is updated first, so the changed::favorites this write triggers finds nothing new.
        self._settings.set_strv(_KEY, self._order)
        self.emit("changed", game_id)

    def _on_settings_changed(self, settings: Gio.Settings, key: str) -> None:
        self._update(_unique(settings.get_strv(key)))

    def _update(self, new: list[str]) -> None:
        """Make `new` the list and emit `changed` for every id added, removed or moved."""
        old, self._order = self._order, new
        affected = [game_id for game_id in new if game_id not in old or old.index(game_id) != new.index(game_id)]
        affected += [game_id for game_id in old if game_id not in new]
        for game_id in affected:
            self.emit("changed", game_id)


def export(file: Gio.File, ids: Sequence[str], done: Callable[[GLib.Error | None], None]) -> None:
    """Write the export file for `ids` to `file` asynchronously, then call `done` with the error or None."""

    def on_replaced(file: Gio.File, result: Gio.AsyncResult) -> None:
        try:
            file.replace_contents_finish(result)
        except GLib.Error as e:
            done(e)
            return
        done(None)

    data = GLib.Bytes.new(favorites_file.dump(ids))
    file.replace_contents_bytes_async(data, None, False, Gio.FileCreateFlags.REPLACE_DESTINATION, None, on_replaced)


def read_export(
    file: Gio.File, done: Callable[[list[str] | None, GLib.Error | FavoritesFileError | None], None]
) -> None:
    """Read and check an export file asynchronously, then call `done(ids, None)`, or `done(None, error)`."""

    def on_loaded(file: Gio.File, result: Gio.AsyncResult) -> None:
        try:
            _ok, contents, _etag = file.load_contents_finish(result)
            ids = favorites_file.parse(contents)
        except (GLib.Error, FavoritesFileError) as e:
            done(None, e)
            return
        done(ids, None)

    file.load_contents_async(None, on_loaded)


def _unique(ids: list[str]) -> list[str]:
    return list(dict.fromkeys(ids))
