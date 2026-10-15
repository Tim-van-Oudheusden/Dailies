from typing import ClassVar

from gi.repository import Gio, GObject

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

    def _store(self, game_id: str) -> None:
        # The list is updated first, so the changed::favorites this write triggers finds nothing new.
        self._settings.set_strv(_KEY, self._order)
        self.emit("changed", game_id)

    def _on_settings_changed(self, settings: Gio.Settings, key: str) -> None:
        new = _unique(settings.get_strv(key))
        old, self._order = self._order, new
        affected = [game_id for game_id in new if game_id not in old or old.index(game_id) != new.index(game_id)]
        affected += [game_id for game_id in old if game_id not in new]
        for game_id in affected:
            self.emit("changed", game_id)


def _unique(ids: list[str]) -> list[str]:
    return list(dict.fromkeys(ids))
