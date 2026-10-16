"""Favorites against the real schema; run by Meson with GSETTINGS_BACKEND=memory (see tests/meson.build)."""

import os
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")

from gi.repository import Gio, GLib

from dailies.core.favorites_file import FavoritesFileError, ImportMode
from dailies.data import favorites
from dailies.data.favorites import Favorites

SCHEMA_ID = os.environ["DAILIES_SCHEMA_ID"]


class FavoritesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Gio.Settings.new(SCHEMA_ID)
        self.settings.reset("favorites")
        self.favorites = Favorites(self.settings)
        self.emitted: list[str] = []
        self.favorites.connect("changed", lambda _favorites, game_id: self.emitted.append(game_id))

    def test_a_game_is_not_a_favorite_by_default(self) -> None:
        assert not self.favorites.is_favorite("wordle")
        assert self.favorites.order() == []

    def test_toggle_adds_then_removes(self) -> None:
        assert self.favorites.toggle("wordle")
        assert self.favorites.is_favorite("wordle")
        assert self.settings.get_strv("favorites") == ["wordle"]

        assert not self.favorites.toggle("wordle")
        assert not self.favorites.is_favorite("wordle")
        assert self.settings.get_strv("favorites") == []

    def test_order_is_insertion_order_newest_last(self) -> None:
        for game_id in ("wordle", "globle", "framed"):
            self.favorites.toggle(game_id)
        self.favorites.toggle("globle")
        self.favorites.toggle("globle")

        assert self.favorites.order() == ["wordle", "framed", "globle"]

    def test_add_at_an_index_restores_the_original_position(self) -> None:
        for game_id in ("wordle", "globle", "framed"):
            self.favorites.toggle(game_id)
        index = self.favorites.order().index("globle")
        self.favorites.toggle("globle")

        self.favorites.add("globle", index)

        assert self.favorites.order() == ["wordle", "globle", "framed"]
        assert self.settings.get_strv("favorites") == ["wordle", "globle", "framed"]

    def test_add_without_an_index_appends(self) -> None:
        self.favorites.toggle("wordle")
        self.favorites.add("globle")
        assert self.favorites.order() == ["wordle", "globle"]

    def test_adding_a_favorite_again_changes_nothing(self) -> None:
        self.favorites.toggle("wordle")
        self.emitted.clear()

        self.favorites.add("wordle", 0)

        assert self.favorites.order() == ["wordle"]
        assert self.emitted == []

    def test_changed_is_emitted_once_per_toggle(self) -> None:
        self.favorites.toggle("wordle")
        self.favorites.toggle("globle")
        self.favorites.toggle("wordle")
        drain_main_context()

        assert self.emitted == ["wordle", "globle", "wordle"]

    def test_move_rewrites_the_key_once_and_emits_changed_once(self) -> None:
        for game_id in ("wordle", "globle", "framed"):
            self.favorites.toggle(game_id)
        self.emitted.clear()
        writes: list[list[str]] = []
        self.settings.connect("changed::favorites", lambda settings, key: writes.append(settings.get_strv(key)))

        assert self.favorites.move("framed", 0)
        drain_main_context()

        assert self.favorites.order() == ["framed", "wordle", "globle"]
        assert writes == [["framed", "wordle", "globle"]]
        assert self.emitted == ["framed"]

    def test_a_move_that_changes_nothing_writes_nothing(self) -> None:
        for game_id in ("wordle", "globle"):
            self.favorites.toggle(game_id)
        self.emitted.clear()

        assert not self.favorites.move("wordle", 0)
        assert not self.favorites.move("pokedle", 0)
        drain_main_context()

        assert self.settings.get_strv("favorites") == ["wordle", "globle"]
        assert self.emitted == []

    def test_an_external_change_updates_the_list_and_emits_for_each_affected_id(self) -> None:
        self.favorites.toggle("wordle")
        self.favorites.toggle("globle")
        self.emitted.clear()

        # As `gsettings set` from a terminal would, through another Gio.Settings on the same backend.
        Gio.Settings.new(SCHEMA_ID).set_strv("favorites", ["globle", "framed"])
        drain_main_context()

        assert self.favorites.order() == ["globle", "framed"]
        assert self.favorites.is_favorite("framed")
        assert not self.favorites.is_favorite("wordle")
        assert sorted(self.emitted) == ["framed", "globle", "wordle"]

    def test_duplicates_from_an_external_change_are_dropped(self) -> None:
        self.settings.set_strv("favorites", ["wordle", "globle", "wordle"])
        drain_main_context()
        assert self.favorites.order() == ["wordle", "globle"]

    def test_set_order_replaces_the_list_and_emits_for_each_affected_id(self) -> None:
        for game_id in ("wordle", "globle", "framed"):
            self.favorites.toggle(game_id)
        self.emitted.clear()

        self.favorites.set_order(["framed", "globle", "connections"])
        drain_main_context()

        assert self.favorites.order() == ["framed", "globle", "connections"]
        assert self.settings.get_strv("favorites") == ["framed", "globle", "connections"]
        assert sorted(self.emitted) == ["connections", "framed", "wordle"]

    def test_import_ids_merges_or_replaces(self) -> None:
        for game_id in ("wordle", "globle"):
            self.favorites.toggle(game_id)

        self.favorites.import_ids(["framed", "wordle"], ImportMode.MERGE)
        assert self.favorites.order() == ["wordle", "globle", "framed"]

        self.favorites.import_ids(["framed", "not-in-any-catalog"], ImportMode.REPLACE)
        assert self.favorites.order() == ["framed", "not-in-any-catalog"]


class ExportImportTest(unittest.TestCase):
    """Export to a file, then read it back, through Gio's asynchronous file I/O."""

    def setUp(self) -> None:
        self.settings = Gio.Settings.new(SCHEMA_ID)
        self.settings.reset("favorites")
        self.favorites = Favorites(self.settings)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "favorites.json"
        self.file = Gio.File.new_for_path(str(self.path))

    def test_export_then_reset_then_import_gives_the_same_order(self) -> None:
        for game_id in ("wordle", "globle", "framed", "connections"):
            self.favorites.toggle(game_id)
        exported = self.favorites.order()

        assert wait_for(lambda done: favorites.export(self.file, exported, done)) is None
        self.settings.reset("favorites")
        drain_main_context()
        assert self.favorites.order() == []
        ids, error = wait_for(lambda done: favorites.read_export(self.file, lambda *args: done(args)))
        assert error is None
        self.favorites.import_ids(ids, ImportMode.MERGE)

        assert self.favorites.order() == exported
        assert self.settings.get_strv("favorites") == exported

    def test_the_exported_file_is_two_space_json(self) -> None:
        assert wait_for(lambda done: favorites.export(self.file, ["wordle", "globle"], done)) is None
        assert self.path.read_text(encoding="utf-8") == (
            '{\n  "schema_version": 1,\n  "favorites": [\n    "wordle",\n    "globle"\n  ]\n}\n'
        )

    def test_a_malformed_file_is_reported_and_read_as_nothing(self) -> None:
        self.path.write_bytes(b'{"schema_version": 1, "favorites": [')

        ids, error = wait_for(lambda done: favorites.read_export(self.file, lambda *args: done(args)))

        assert ids is None
        assert isinstance(error, FavoritesFileError)

    def test_a_missing_file_is_reported(self) -> None:
        ids, error = wait_for(lambda done: favorites.read_export(self.file, lambda *args: done(args)))

        assert ids is None
        assert isinstance(error, GLib.Error)

    def test_an_export_that_cannot_be_written_is_reported(self) -> None:
        unwritable = Gio.File.new_for_path(str(self.path.parent / "missing-directory" / "favorites.json"))
        error = wait_for(lambda done: favorites.export(unwritable, ["wordle"], done))
        assert isinstance(error, GLib.Error)


def drain_main_context() -> None:
    context = GLib.MainContext.default()
    while context.iteration(may_block=False):
        pass


def wait_for(start: Callable[[Callable[[object], None]], None]) -> object:
    """Call `start(done)` and run the main context until `done(value)` is called; return the value."""
    results: list[object] = []
    start(results.append)
    context = GLib.MainContext.default()
    while not results:
        context.iteration(may_block=True)
    return results[0]


if __name__ == "__main__":
    unittest.main()
