"""Store against the bundled snapshot in a temporary cache; run by Meson (see tests/meson.build)."""

import gettext
import json
import os
import tempfile
import unittest
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")

from gi.repository import Gio

from dailies.core import catalog, popularity
from dailies.core.cache import CacheDir
from dailies.data.done_today import DoneToday
from dailies.data.favorites import Favorites
from dailies.data.store import Store

gettext.install("dailies")
BUNDLE = Path(__file__).resolve().parents[2] / "data" / "v1"
SCHEMA_ID = os.environ["DAILIES_SCHEMA_ID"]


def edited(name: str, edit: Callable[[dict], object]) -> bytes:
    document = json.loads((BUNDLE / f"{name}.json").read_bytes())
    edit(document)
    return json.dumps(document).encode()


class RecordingIcons:
    """Stands in for `dailies.data.icons.Icons`: records which games asked for an icon and what was kept."""

    def __init__(self) -> None:
        self.loaded: list[str] = []
        self.kept: list[set[str]] = []

    def load(self, item: object) -> None:
        self.loaded.append(item.props.game.id)

    def forget(self, keep: set[str]) -> None:
        self.kept.append(set(keep))


class RecordingFetcher:
    """Stands in for `dailies.data.fetcher.Fetcher`, for its icons only."""

    def __init__(self) -> None:
        self.icons = RecordingIcons()


class StoreTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cache = CacheDir(Path(directory.name) / "v1")
        settings = Gio.Settings.new(SCHEMA_ID)
        settings.reset("favorites")
        self.favorites = Favorites(settings)
        self.store = Store(self.cache, BUNDLE, self.favorites)

    def ids(self) -> list[str]:
        return [item.props.game.id for item in self.store.model]

    def item(self, game_id: str) -> object:
        return next(item for item in self.store.model if item.props.game.id == game_id)

    def test_a_cold_start_shows_the_whole_bundled_catalog_and_seeds_the_cache(self) -> None:
        self.store.load_initial()

        bundled = catalog.parse((BUNDLE / "games.json").read_bytes())
        assert self.ids() == [game.id for game in bundled.games]
        assert self.cache.read("games") == (BUNDLE / "games.json").read_bytes()
        assert self.cache.read("popularity") == (BUNDLE / "popularity.json").read_bytes()
        assert self.store.props.last_success is None

    def test_a_corrupt_cache_is_replaced_by_the_bundle(self) -> None:
        self.cache.store("games", b'{"schema_version": 1, "games": [', '"x"', datetime.now(UTC))

        self.store.load_initial()

        assert len(self.store.model) == len(catalog.parse((BUNDLE / "games.json").read_bytes()).games)
        assert self.cache.etag("games") is None

    def test_a_valid_cache_is_used_as_is(self) -> None:
        fetched = datetime.now(UTC) - timedelta(hours=1)
        body = edited("games", lambda document: document["games"].pop())
        self.cache.store("games", body, '"x"', fetched)

        self.store.load_initial()

        assert len(self.store.model) == len(catalog.parse(body).games)
        assert self.store.props.last_success == fetched

    def test_a_bundle_newer_than_the_cache_wins(self) -> None:
        old = edited("games", lambda document: document.update(generated_at="2020-01-01T00:00:00Z"))
        self.cache.store("games", old, '"x"', datetime.now(UTC))

        self.store.load_initial()

        assert self.cache.read("games") == (BUNDLE / "games.json").read_bytes()

    def test_popularity_ranks_and_favorites_are_applied(self) -> None:
        # Shelves of its own, generated after the bundle so the bundle does not replace them: the published file
        # changes every week (#118).
        shelves = edited(
            "popularity",
            lambda document: document.update(
                generated_at="2099-01-01T00:00:00Z",
                valid_until="2099-01-11T00:00:00Z",
                popular=[
                    {"id": "wordle", "rank": 1, "reason": "score", "score": 1.0},
                    {"id": "globle", "rank": 2, "reason": "score", "score": 0.5},
                ],
                trending=[{"id": "nyt-pips", "rank": 1, "reason": "new", "score": 0.0, "delta": None}],
            ),
        )
        self.cache.store("popularity", shelves, None, datetime.now(UTC))
        self.favorites.toggle("globle")
        self.store.load_initial()

        assert self.item("wordle").props.popular_rank == 1
        assert self.item("globle").props.popular_rank == 2
        assert self.item("wordle").props.trending_rank == 0
        assert self.item("nyt-pips").props.trending_rank == 1
        assert self.item("nyt-pips").props.popular_rank == 0
        assert self.item("globle").props.favorite
        assert not self.item("wordle").props.favorite

    def test_a_favorite_toggle_updates_its_object(self) -> None:
        self.store.load_initial()
        self.favorites.toggle("wordle")
        assert self.item("wordle").props.favorite

    def test_a_game_object_is_found_by_id(self) -> None:
        self.store.load_initial()
        assert self.store.get("wordle") is self.item("wordle")
        assert self.store.get("no-such-game") is None

    def test_the_done_today_marks_are_applied_and_followed(self) -> None:
        settings = Gio.Settings.new(SCHEMA_ID)
        settings.reset("done-today")
        done = DoneToday(settings)
        self.addCleanup(done.close)
        done.toggle("globle")
        store = Store(self.cache, BUNDLE, self.favorites, done_today=done)
        store.load_initial()
        assert store.get("globle").props.done
        assert not store.get("wordle").props.done

        done.toggle("wordle")
        done.toggle("globle")
        assert store.get("wordle").props.done
        assert not store.get("globle").props.done

    def test_the_popularity_week_and_staleness_are_exposed(self) -> None:
        self.store.load_initial()
        bundled = popularity.parse((BUNDLE / "popularity.json").read_bytes())
        assert self.store.props.popularity_week == bundled.week
        assert self.store.props.popularity_stale == bundled.is_stale(datetime.now(UTC))

    def test_stale_popularity_is_flagged(self) -> None:
        # Generated after the bundle, so the bundle does not replace it, but valid only until long ago.
        stale = edited(
            "popularity",
            lambda document: document.update(generated_at="2099-01-01T00:00:00Z", valid_until="2020-01-01T00:00:00Z"),
        )
        self.cache.store("popularity", stale, None, datetime.now(UTC))

        self.store.load_initial()

        assert self.store.props.popularity_stale

    def test_reload_diffs_by_id(self) -> None:
        self.store.load_initial()
        kept = self.item("wordle")
        changes: list[tuple[int, int, int]] = []
        self.store.model.connect("items-changed", lambda _model, *change: changes.append(change))

        def edit(document: dict) -> None:
            document["games"] = [game for game in document["games"] if game["id"] != "globle"]
            wordle = next(game for game in document["games"] if game["id"] == "wordle")
            wordle["name"] = "Wordle!"
            document["games"].append({**wordle, "id": "zzz-new", "name": "New"})

        self.store.reload(catalog.parse(edited("games", edit)), self.store.popularity)

        assert self.item("wordle") is kept
        assert kept.props.game.name == "Wordle!"
        assert "globle" not in self.ids()
        assert self.ids()[-1] == "zzz-new"
        assert len(changes) == 2

    def test_reload_with_the_same_data_changes_nothing(self) -> None:
        self.store.load_initial()
        changes = []
        self.store.model.connect("items-changed", lambda *change: changes.append(change))

        self.store.reload(self.store.catalog, self.store.popularity)

        assert changes == []

    def test_a_game_asks_the_icons_for_its_icon(self) -> None:
        fetcher = RecordingFetcher()
        icons = fetcher.icons
        store = Store(self.cache, BUNDLE, self.favorites, fetcher)
        store.load_initial()

        store.get("worldle").request_icon()

        assert icons.loaded == ["worldle"]

    def test_without_a_fetcher_asking_for_an_icon_does_nothing(self) -> None:
        self.store.load_initial()
        self.store.get("worldle").request_icon()
        assert self.store.get("worldle").props.icon is None

    def test_each_reload_keeps_only_the_icons_the_catalog_names(self) -> None:
        fetcher = RecordingFetcher()
        icons = fetcher.icons
        store = Store(self.cache, BUNDLE, self.favorites, fetcher)
        store.load_initial()
        named = {game.icon for game in store.catalog.games if game.icon}
        assert "icons/worldle.png" in named

        def take_down(document: dict) -> None:
            next(game for game in document["games"] if game["id"] == "worldle").pop("icon")

        store.reload(catalog.parse(edited("games", take_down)), store.popularity)

        assert icons.kept == [named, named - {"icons/worldle.png"}]


if __name__ == "__main__":
    unittest.main()
