from collections.abc import Callable
from datetime import UTC, datetime
from typing import ClassVar

from gi.repository import Gio, GLib, GObject

from dailies.core import done_today

_KEY = "done-today"


def _local_now() -> datetime:
    return datetime.now(UTC).astimezone()


class DoneToday(GObject.Object):
    """The games marked as done today (the local day), kept in the `done-today` key (see `dailies.core.done_today`).

    Marks from other days are pruned at startup, at local midnight and whenever `refresh()` runs. A GLib timeout runs
    on the monotonic clock, which stops while the computer sleeps, so midnight can pass unnoticed during a suspend:
    the window calls `refresh()` when it becomes active, which also catches a changed clock or time zone.

    Emits `changed(id)` whenever a game becomes or stops being done, whether through this object, the day changing or
    an external change to the key. `now` returns the local time, with its UTC offset; tests replace it.
    """

    __gtype_name__ = "DailiesDoneToday"
    __gsignals__: ClassVar = {"changed": (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self, settings: Gio.Settings, *, now: Callable[[], datetime] = _local_now) -> None:
        super().__init__()
        self._settings = settings
        self._now = now
        self._timeout = 0
        self._marks = done_today.prune(settings.get_value(_KEY).unpack(), now().date())
        settings.connect(f"changed::{_KEY}", self._on_settings_changed)
        self._write()
        self._schedule()

    def is_done(self, game_id: str) -> bool:
        """Return whether `game_id` was marked as done today."""
        return done_today.is_done(self._marks, game_id, self._now().date())

    def toggle(self, game_id: str) -> bool:
        """Mark `game_id` as done today when it was not, unmark it when it was.

        Returns:
            Whether `game_id` is done today now.
        """
        self._update(done_today.toggle(self._marks, game_id, self._now().date()))
        return self.is_done(game_id)

    def mark(self, game_id: str) -> None:
        """Mark `game_id` as done today; the automatic mode uses it, so it never unmarks."""
        self._update(done_today.mark(self._marks, game_id, self._now().date()))

    def refresh(self) -> None:
        """Drop the marks of earlier days, as at midnight, and set the midnight timer again."""
        self._update(done_today.prune(self._marks, self._now().date()))
        self._schedule()

    def close(self) -> None:
        """Stop the midnight timer."""
        if self._timeout:
            GLib.source_remove(self._timeout)
            self._timeout = 0

    def _update(self, marks: dict[str, str]) -> None:
        old, self._marks = self._marks, marks
        # The marks are set first, so the changed::done-today this write triggers finds nothing new.
        self._write()
        self._emit_changes(old, marks)

    def _write(self) -> None:
        if self._settings.get_value(_KEY).unpack() != self._marks:
            self._settings.set_value(_KEY, GLib.Variant("a{ss}", self._marks))

    def _emit_changes(self, old: dict[str, str], new: dict[str, str]) -> None:
        for game_id in sorted(old.keys() | new.keys()):
            if old.get(game_id) != new.get(game_id):
                self.emit("changed", game_id)

    def _schedule(self) -> None:
        self.close()
        self._timeout = GLib.timeout_add_seconds(done_today.seconds_until_midnight(self._now()), self._on_midnight)

    def _on_midnight(self) -> bool:
        self._timeout = 0
        # Early by a daylight saving change, the day may not have changed yet: refresh() then only sets the timer again.
        self.refresh()
        return GLib.SOURCE_REMOVE

    def _on_settings_changed(self, settings: Gio.Settings, key: str) -> None:
        new = done_today.prune(settings.get_value(key).unpack(), self._now().date())
        old, self._marks = self._marks, new
        self._emit_changes(old, new)
