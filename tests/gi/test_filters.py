"""The library's list pipeline (section, search and language filters, sorter) over GameObjects; run by Meson."""

import gettext
import os
import unittest
from dataclasses import replace
from datetime import date

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GObject, Gtk

from dailies.core.models import Category, Difficulty, Game, Status
from dailies.data.favorites import Favorites
from dailies.ui.filters import LanguageFilter, SearchFilter, SearchSorter, SectionFilter, SectionSorter
from dailies.ui.game_object import GameObject

gettext.install("dailies")
SCHEMA_ID = os.environ["DAILIES_SCHEMA_ID"]


def game(
    game_id: str,
    name: str,
    category: Category = Category.WORDS,
    difficulty: Difficulty = Difficulty.MEDIUM,
    status: Status = Status.ACTIVE,
) -> Game:
    return Game(
        id=game_id,
        name=name,
        url=f"https://{game_id}.example/",
        category=category,
        difficulty=difficulty,
        description="A daily guessing game.",
        added=date(2026, 10, 1),
        status=status,
        domain=f"{game_id}.example",
    )


class PipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        settings = Gio.Settings.new(SCHEMA_ID)
        settings.reset("favorites")
        self.favorites = Favorites(settings)
        self.games = Gio.ListStore(item_type=GameObject)
        self.section = SectionFilter()
        self.search = SearchFilter()
        self.sorter = SectionSorter(self.favorites)
        self.search_sorter = SearchSorter()
        self.search.bind_property("text", self.search_sorter, "text", GObject.BindingFlags.SYNC_CREATE)
        sorters = Gtk.MultiSorter()
        sorters.append(self.search_sorter)
        sorters.append(self.sorter)
        every = Gtk.EveryFilter()
        every.append(self.section)
        every.append(self.search)
        self.view = Gtk.SortListModel(model=Gtk.FilterListModel(model=self.games, filter=every), sorter=sorters)
        for item, popular, trending in (
            (game("wordle", "Wordle", difficulty=Difficulty.EASY), 1, 0),
            (game("pokedle", "Pokédle", Category.VIDEO_GAMES, Difficulty.HARD), 3, 1),
            (game("worldle", "Worldle", Category.GEOGRAPHY, Difficulty.EASY), 2, 0),
            (game("globle", "Globle", Category.GEOGRAPHY, status=Status.BROKEN), 0, 2),
            (game("absurdle", "absurdle", difficulty=Difficulty.HARD), 0, 0),
        ):
            obj = GameObject(item)
            obj.update(game=item, favorite=False, popular_rank=popular, trending_rank=trending)
            self.games.append(obj)

    def shown(self) -> list[str]:
        return [item.props.game.id for item in self.view]

    def item(self, game_id: str) -> GameObject:
        return next(item for item in self.games if item.props.game.id == game_id)

    def star(self, game_id: str) -> None:
        self.favorites.toggle(game_id)
        self.item(game_id).props.favorite = self.favorites.is_favorite(game_id)
        self.section.changed(Gtk.FilterChange.DIFFERENT)

    def show(self, section: str) -> None:
        self.section.props.section = section
        self.sorter.props.section = section

    def test_the_shelves_list_their_games_in_rank_order(self) -> None:
        self.show("popular")
        assert self.shown() == ["wordle", "worldle", "pokedle"]
        self.show("trending")
        assert self.shown() == ["pokedle", "globle"]

    def test_a_category_lists_its_available_games_by_name(self) -> None:
        self.show("words")
        assert self.shown() == ["absurdle", "wordle"]
        self.show("geography")
        assert self.shown() == ["worldle"]

    def test_favorites_keep_their_order_and_unavailable_games(self) -> None:
        self.show("favorites")
        assert self.shown() == []
        for game_id in ("worldle", "globle", "absurdle"):
            self.star(game_id)
        assert self.shown() == ["worldle", "globle", "absurdle"]
        self.star("worldle")
        assert self.shown() == ["globle", "absurdle"]
        self.favorites.add("worldle", 0)
        self.item("worldle").props.favorite = True
        self.section.changed(Gtk.FilterChange.LESS_STRICT)
        assert self.shown() == ["worldle", "globle", "absurdle"]

    def test_the_sort_mode_overrides_the_section_order(self) -> None:
        self.show("popular")
        self.sorter.props.sort_mode = "name"
        assert self.shown() == ["pokedle", "wordle", "worldle"]
        self.sorter.props.sort_mode = "difficulty"
        assert self.shown() == ["wordle", "worldle", "pokedle"]
        self.sorter.props.sort_mode = "default"
        assert self.shown() == ["wordle", "worldle", "pokedle"]

    def test_not_done_first_moves_the_games_done_today_last(self) -> None:
        self.show("popular")
        self.sorter.props.sort_mode = "not-done"
        assert self.shown() == ["wordle", "worldle", "pokedle"]
        self.item("wordle").props.done = True
        self.sorter.changed(Gtk.SorterChange.DIFFERENT)
        assert self.shown() == ["worldle", "pokedle", "wordle"]

    def test_search_folds_accents_and_narrows_the_current_section(self) -> None:
        self.show("popular")
        self.search.props.text = "pokedle"
        assert self.shown() == ["pokedle"]
        self.search.props.text = "w"
        assert self.shown() == ["wordle", "worldle"]
        self.search.props.text = "wor"
        assert self.shown() == ["wordle", "worldle"]
        self.search.props.text = "world"
        assert self.shown() == ["worldle"]
        self.show("words")
        assert self.shown() == []
        self.search.props.text = ""
        assert self.shown() == ["absurdle", "wordle"]

    def test_search_matches_the_translated_category_label(self) -> None:
        self.show("trending")
        self.search.props.text = "video"
        assert self.shown() == ["pokedle"]

    def test_while_searching_the_best_match_comes_first_and_clearing_restores_the_section_order(self) -> None:
        self.show("popular")
        assert self.shown() == ["wordle", "worldle", "pokedle"]
        self.search.props.text = "worldle"
        assert self.shown() == ["worldle", "wordle"]  # Worldle starts with the query, Wordle is one typo away
        self.search.props.text = ""
        assert self.shown() == ["wordle", "worldle", "pokedle"]

    def test_a_longer_query_that_allows_a_typo_tests_the_hidden_games_again(self) -> None:
        self.show("popular")
        for end in range(1, len("wordl") + 1):
            self.search.props.text = "wordl"[:end]
        assert self.shown() == ["wordle"]
        self.search.props.text = "wordle"
        assert self.shown() == ["wordle", "worldle"]
        self.search.props.text = "wordl"
        assert self.shown() == ["wordle"]


class LanguageFilterTest(unittest.TestCase):
    def pipeline(self, system_languages: set[str]) -> None:
        self.section = SectionFilter()
        self.language = LanguageFilter(system_languages, show_other_languages=False)
        self.section.bind_property("section", self.language, "section", GObject.BindingFlags.SYNC_CREATE)
        every = Gtk.EveryFilter()
        every.append(self.section)
        every.append(self.language)
        games = Gio.ListStore(item_type=GameObject)
        for item, favorite in (
            (game("wordle", "Wordle"), False),
            (replace(game("woordle", "Woordle"), language="nl"), True),
            (replace(game("absurdle", "absurdle"), language=""), True),
        ):
            obj = GameObject(item)
            obj.update(game=item, favorite=favorite, popular_rank=0, trending_rank=0)
            games.append(obj)
        self.view = Gtk.FilterListModel(model=games, filter=every)

    def shown(self) -> list[str]:
        return sorted(item.props.game.id for item in self.view)

    def test_an_english_system_hides_a_dutch_game_except_in_favorites(self) -> None:
        self.pipeline({"en"})
        self.section.props.section = "words"
        assert self.shown() == ["absurdle", "wordle"]
        self.section.props.section = "favorites"
        assert self.shown() == ["absurdle", "woordle"]

    def test_a_dutch_system_hides_english_games(self) -> None:
        self.pipeline({"nl"})
        self.section.props.section = "words"
        assert self.shown() == ["woordle"]

    def test_toggling_the_setting_refilters_at_once(self) -> None:
        self.pipeline({"en"})
        self.section.props.section = "words"
        self.language.props.show_other_languages = True
        assert self.shown() == ["absurdle", "woordle", "wordle"]
        self.language.props.show_other_languages = False
        assert self.shown() == ["absurdle", "wordle"]


class GameObjectTest(unittest.TestCase):
    def test_the_derived_properties_follow_the_game(self) -> None:
        obj = GameObject(game("worldle", "Worldle", Category.GEOGRAPHY, Difficulty.EASY))
        assert obj.props.name == "Worldle"
        assert obj.props.category_label == "Geography"
        assert obj.props.difficulty_label == "Easy"
        assert obj.props.caption == "Geography · Easy"
        assert obj.props.available

        notified: list[str] = []
        obj.connect("notify", lambda _obj, pspec: notified.append(pspec.name))
        broken = game("worldle", "Worldle", Category.GEOGRAPHY, Difficulty.HARD, Status.BROKEN)
        obj.update(game=broken, favorite=False, popular_rank=0, trending_rank=0)
        assert not obj.props.available
        assert obj.props.caption == "Geography · Hard"
        assert sorted(notified) == ["available", "caption", "difficulty-label", "game"]


if __name__ == "__main__":
    unittest.main()
