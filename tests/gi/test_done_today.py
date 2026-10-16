"""DoneToday against the real schema; run by Meson with GSETTINGS_BACKEND=memory (see tests/meson.build)."""

import os
import time
import unittest
from datetime import datetime, timedelta, timezone

import gi

gi.require_version("Gio", "2.0")

from gi.repository import Gio, GLib

from dailies.data.done_today import DoneToday

SCHEMA_ID = os.environ["DAILIES_SCHEMA_ID"]
KEY = "done-today"
LOCAL = timezone(timedelta(hours=2))


class Clock:
    """A local wall clock the test sets."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class DoneTodayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Gio.Settings.new(SCHEMA_ID)
        self.settings.reset(KEY)
        self.clock = Clock(datetime(2026, 10, 16, 9, 30, tzinfo=LOCAL))
        self.emitted: list[str] = []

    def done_today(self) -> DoneToday:
        done = DoneToday(self.settings, now=self.clock)
        self.addCleanup(done.close)
        done.connect("changed", lambda _done, game_id: self.emitted.append(game_id))
        return done

    def stored(self) -> dict[str, str]:
        return self.settings.get_value(KEY).unpack()

    def store(self, marks: dict[str, str]) -> None:
        self.settings.set_value(KEY, GLib.Variant("a{ss}", marks))

    def test_nothing_is_done_by_default(self) -> None:
        assert not self.done_today().is_done("wordle")

    def test_marks_from_earlier_days_are_ignored_and_pruned_at_startup(self) -> None:
        self.store({"wordle": "2026-10-16", "globle": "2026-10-15", "heardle": "garbage"})
        done = self.done_today()
        assert done.is_done("wordle")
        assert not done.is_done("globle")
        assert self.stored() == {"wordle": "2026-10-16"}

    def test_toggle_marks_then_unmarks_and_says_so(self) -> None:
        done = self.done_today()
        assert done.toggle("wordle")
        assert done.is_done("wordle")
        assert self.stored() == {"wordle": "2026-10-16"}
        assert not done.toggle("wordle")
        assert not done.is_done("wordle")
        assert self.stored() == {}
        drain_main_context()
        assert self.emitted == ["wordle", "wordle"]

    def test_mark_never_unmarks_and_only_emits_on_a_change(self) -> None:
        done = self.done_today()
        done.mark("wordle")
        done.mark("wordle")
        drain_main_context()
        assert done.is_done("wordle")
        assert self.emitted == ["wordle"]

    def test_after_midnight_a_refresh_clears_the_marks(self) -> None:
        done = self.done_today()
        done.toggle("wordle")
        done.toggle("globle")
        self.emitted.clear()
        self.clock.now = datetime(2026, 10, 17, 0, 0, 1, tzinfo=LOCAL)

        done.refresh()

        assert not done.is_done("wordle")
        assert self.stored() == {}
        assert sorted(self.emitted) == ["globle", "wordle"]

    def test_a_refresh_on_the_same_day_changes_nothing(self) -> None:
        done = self.done_today()
        done.toggle("wordle")
        self.emitted.clear()
        done.refresh()
        assert done.is_done("wordle")
        assert self.emitted == []

    def test_the_marks_clear_on_their_own_at_local_midnight(self) -> None:
        self.clock.now = datetime(2026, 10, 16, 23, 59, 59, tzinfo=LOCAL)
        done = self.done_today()
        done.toggle("wordle")
        self.emitted.clear()
        self.clock.now = datetime(2026, 10, 17, 0, 0, 0, tzinfo=LOCAL)

        deadline = time.monotonic() + 5
        while not self.emitted and time.monotonic() < deadline:
            GLib.MainContext.default().iteration(may_block=False)
            time.sleep(0.02)

        assert self.emitted == ["wordle"]
        assert not done.is_done("wordle")

    def test_an_external_change_emits_for_each_affected_id(self) -> None:
        done = self.done_today()
        done.toggle("wordle")
        self.emitted.clear()

        Gio.Settings.new(SCHEMA_ID).set_value(KEY, GLib.Variant("a{ss}", {"globle": "2026-10-16"}))
        drain_main_context()

        assert done.is_done("globle")
        assert not done.is_done("wordle")
        assert sorted(self.emitted) == ["globle", "wordle"]


def drain_main_context() -> None:
    context = GLib.MainContext.default()
    while context.iteration(may_block=False):
        pass


if __name__ == "__main__":
    unittest.main()
