import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from gi.repository import Gio, GObject

from dailies.core import cache, catalog, popularity
from dailies.core.cache import CacheDir, Outcome
from dailies.core.catalog import Catalog
from dailies.core.popularity import Popularity, Shelf
from dailies.data.done_today import DoneToday
from dailies.data.favorites import Favorites
from dailies.data.fetcher import Fetcher
from dailies.ui.game_object import GameObject

log = logging.getLogger(__name__)

_PARSERS: dict[str, Callable[[bytes], Catalog | Popularity]] = {
    cache.CATALOG: catalog.parse,
    cache.POPULARITY: popularity.parse,
}


class Store(GObject.Object):
    """Every catalog game as a `GameObject` in `model`, with this week's ranks, the favourite and the done-today state.

    The model holds broken and retired games too, so favourites still resolve; the section filter hides them. The
    properties tell the UI how old the data is: `popularity-week` and `popularity-stale` for the This Week shelves,
    `last-success` (when the server last confirmed the catalog, None before the first time) and `stale-banner`
    (whether to say that the game list is old). `catalog` and `popularity` notify on every reload. Without
    `done_today`, no game is ever done.
    """

    __gtype_name__ = "DailiesStore"

    catalog = GObject.Property(type=object)
    popularity = GObject.Property(type=object)
    popularity_week = GObject.Property(type=str, default="")
    popularity_stale = GObject.Property(type=bool, default=False)
    last_success = GObject.Property(type=object)
    stale_banner = GObject.Property(type=bool, default=False)

    def __init__(
        self,
        cache_dir: CacheDir,
        bundle_dir: Path,
        favorites: Favorites,
        fetcher: Fetcher | None = None,
        *,
        done_today: DoneToday | None = None,
    ) -> None:
        super().__init__()
        self.model = Gio.ListStore(item_type=GameObject)
        self._cache = cache_dir
        self._bundle = bundle_dir
        self._favorites = favorites
        self._fetcher = fetcher
        self._done_today = done_today
        self._objects: dict[str, GameObject] = {}
        self._network = Gio.NetworkMonitor.get_default()
        favorites.connect("changed", self._on_favorite_changed)
        if done_today is not None:
            done_today.connect("changed", self._on_done_changed)
        self._network.connect("network-changed", lambda *_args: self._update_freshness())

    def load_initial(self) -> None:
        """Fill the model from the cache, first replacing a missing, unreadable or older cached file by the bundle."""
        self.reload(self._load(cache.CATALOG), self._load(cache.POPULARITY))

    def reload(self, new_catalog: Catalog, new_popularity: Popularity) -> None:
        """Show `new_catalog` and `new_popularity`, changing only the objects and positions that differ."""
        new_popularity = new_popularity.restricted_to({game.id for game in new_catalog.games})
        ids = [game.id for game in new_catalog.games]
        wanted = set(ids)
        for position in reversed(range(self.model.get_n_items())):
            if self.model.get_item(position).props.game.id not in wanted:
                self.model.remove(position)
        self._objects = {item.props.game.id: item for item in self.model}
        for position, game in enumerate(new_catalog.games):
            item = self._objects.get(game.id)
            current = self.model.get_item(position)
            if item is None:
                item = self._objects[game.id] = GameObject(game)
                # Existing objects follow `changed`; a new one starts from the current marks.
                item.props.done = self._done_today is not None and self._done_today.is_done(game.id)
                self.model.insert(position, item)
            elif current is not item:
                self.model.remove(self.model.find(item)[1])
                self.model.insert(position, item)
            item.update(
                game=game,
                favorite=self._favorites.is_favorite(game.id),
                popular_rank=new_popularity.rank_of(game.id, Shelf.POPULAR) or 0,
                trending_rank=new_popularity.rank_of(game.id, Shelf.TRENDING) or 0,
            )
        log.debug("showing %d games, popularity week %s", len(ids), new_popularity.week)
        if self.props.popularity_week != new_popularity.week:
            self.props.popularity_week = new_popularity.week
        self.props.catalog = new_catalog
        self.props.popularity = new_popularity
        self._update_freshness()

    def get(self, game_id: str) -> GameObject | None:
        """Return the object of the game with id `game_id`, or None when the catalog has no such game."""
        return self._objects.get(game_id)

    def refresh_all(self, callback: Callable[[dict[str, Outcome]], None] | None = None, *, force: bool = False) -> None:
        """Revalidate the cached files with the server, reload when one changed, then call `callback` with outcomes.

        Args:
            callback: Called with each file's outcome once both refreshes have ended.
            force: Ask the server even when the cached files are younger than their maximum age, or the network is
                metered.
        """
        if self._fetcher is None:
            return

        def done(outcomes: dict[str, Outcome]) -> None:
            if Outcome.UPDATED in outcomes.values():
                self.load_initial()
            else:
                self._update_freshness()
            if callback:
                callback(outcomes)

        self._fetcher.refresh_all(done, force=force)

    def _load(self, name: str) -> Catalog | Popularity:
        parse = _PARSERS[name]
        bundled = parse(bundle_data := (self._bundle / f"{name}.json").read_bytes())
        data = self._cache.read(name)
        try:
            cached = parse(data) if data is not None else None
        except ValueError as e:
            log.warning("%s: the cached copy is unusable (%s), using the bundled one", name, e)
        else:
            if cached is None:
                log.info("%s: nothing cached yet, using the bundled copy", name)
            elif cached.generated_at >= bundled.generated_at:
                return cached
            else:
                log.info("%s: the bundled copy is newer than the cached one, using it", name)
        try:
            self._cache.seed(name, bundle_data)
        except OSError as e:
            log.warning("%s: could not write the cache: %s", name, e)
        return bundled

    def _update_freshness(self) -> None:
        now = datetime.now(UTC)
        last_success = self._cache.fetched_at(cache.CATALOG)
        if self.props.last_success != last_success:
            self.props.last_success = last_success
        stale = self.props.popularity is not None and self.props.popularity.is_stale(now)
        if self.props.popularity_stale != stale:
            self.props.popularity_stale = stale
        banner = cache.needs_stale_banner(last_success, now, online=self._network.get_network_available())
        if self.props.stale_banner != banner:
            self.props.stale_banner = banner

    def _on_favorite_changed(self, favorites: Favorites, game_id: str) -> None:
        if item := self._objects.get(game_id):
            item.props.favorite = favorites.is_favorite(game_id)

    def _on_done_changed(self, done_today: DoneToday, game_id: str) -> None:
        if item := self._objects.get(game_id):
            item.props.done = done_today.is_done(game_id)
