"""Favorites against the real schema; run by Meson with GSETTINGS_BACKEND=memory (see tests/meson.build)."""

import os
import unittest

import gi

gi.require_version("Gio", "2.0")

from gi.repository import Gio, GLib

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


def drain_main_context() -> None:
    context = GLib.MainContext.default()
    while context.iteration(may_block=False):
        pass


if __name__ == "__main__":
    unittest.main()
