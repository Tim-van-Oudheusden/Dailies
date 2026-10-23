"""Icons against a local HTTP server, decoded with glycin; run by Meson (see tests/meson.build)."""

import functools
import gettext
import tempfile
import threading
import unittest
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gly", "2")

from gi.repository import Gdk, GLib, Gly

gettext.install("dailies")

from dailies.core.icons import IconCache
from dailies.core.models import Category, Difficulty, Game, Status
from dailies.data.fetcher import new_session
from dailies.data.icons import Icons, decode
from dailies.ui.game_object import GameObject

ICONS = Path(__file__).resolve().parents[2] / "data" / "v1" / "icons"
WORLDLE = (ICONS / "worldle.png").read_bytes()
WORDLE = (ICONS / "wordle.png").read_bytes()
# Passes the PNG signature check, but glycin cannot decode it.
GARBLED = WORLDLE[:16] + bytes(64)
# The build sandbox cannot start glycin's own sandbox; the app always uses it.
UNSANDBOXED = functools.partial(decode, sandbox=Gly.SandboxSelector.NOT_SANDBOXED)


class Server(ThreadingHTTPServer):
    """Serves `files` (path -> body) with a fixed ETag per body; every other path is 404.

    Each response waits until `gate` is set; it is set unless a test holds the responses back.
    """

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), Handler)
        self.files: dict[str, bytes] = {"/v1/icons/worldle.png": WORLDLE}
        self.requests: list[dict[str, str]] = []
        self.gate = threading.Event()
        self.gate.set()
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}/v1/"


class Handler(BaseHTTPRequestHandler):
    server: Server

    def do_GET(self) -> None:
        self.server.requests.append({"path": self.path, **dict(self.headers.items())})
        # Bounded, so a failing test cannot leave server_close waiting on this thread.
        self.server.gate.wait(10)
        body = self.server.files.get(self.path)
        if body is None:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
            return
        etag = f'"{hash(body) & 0xFFFF:x}"'
        if self.headers.get("If-None-Match") == etag:
            self.send_response(HTTPStatus.NOT_MODIFIED)
            self.end_headers()
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("ETag", etag)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        pass


def worldle(**changes: object) -> Game:
    fields = {
        "id": "worldle",
        "name": "Worldle",
        "url": "https://worldle.teuteuf.fr/",
        "category": Category.GEOGRAPHY,
        "difficulty": Difficulty.EASY,
        "description": "Identify a country from its silhouette.",
        "added": date(2026, 10, 1),
        "status": Status.ACTIVE,
        "domain": "teuteuf.fr",
        "icon": "icons/worldle.png",
    }
    return Game(**{**fields, **changes})


def run_until(condition: Callable[[], bool], seconds: float = 10) -> None:
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + int(seconds * 1_000_000)
    while not condition() and GLib.get_monotonic_time() < deadline:
        context.iteration(False)


def settle() -> None:
    # Long enough for a request and a decode that should not happen to have happened.
    run_until(lambda: False, 0.5)


class IconsTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cache = IconCache(Path(directory.name) / "v1" / "icons")
        self.server = Server()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.metered = False
        self.icons = self.new_icons()

    def new_icons(self) -> Icons:
        return Icons(
            self.cache, [self.server.url], new_session("1.2.3"), decode=UNSANDBOXED, metered=lambda: self.metered
        )

    def paths(self) -> list[str]:
        return [request["path"] for request in self.server.requests]

    def test_an_icon_is_fetched_cached_and_shown(self) -> None:
        item = GameObject(worldle())

        self.icons.load(item)
        run_until(lambda: item.props.icon is not None)

        assert isinstance(item.props.icon, Gdk.Texture)
        assert (item.props.icon.get_width(), item.props.icon.get_height()) == (64, 64)
        assert self.cache.read("icons/worldle.png") == WORLDLE
        assert self.paths() == ["/v1/icons/worldle.png"]
        assert self.server.requests[0]["User-Agent"] == "Dailies/1.2.3 (+https://github.com/Tim-van-Oudheusden/Dailies)"

    def test_a_fresh_cached_icon_is_shown_without_a_request(self) -> None:
        self.cache.store("icons/worldle.png", WORLDLE, '"abc"', datetime.now(UTC))
        item = GameObject(worldle())

        self.icons.load(item)
        run_until(lambda: item.props.icon is not None)
        settle()

        assert item.props.icon is not None
        assert self.server.requests == []

    def test_a_week_old_icon_is_shown_then_replaced_by_the_new_one(self) -> None:
        self.cache.store("icons/worldle.png", WORDLE, '"old"', datetime.now(UTC) - timedelta(days=8))
        item = GameObject(worldle())
        shown: list[Gdk.Texture] = []
        item.connect("notify::icon", lambda *_args: shown.append(item.props.icon))
        # Hold the new icon back until the cached one is shown: a newer decode supersedes an unfinished older one.
        self.server.gate.clear()

        self.icons.load(item)
        run_until(lambda: len(shown) == 1)
        self.server.gate.set()
        run_until(lambda: self.cache.read("icons/worldle.png") == WORLDLE and len(shown) == 2)

        assert self.server.requests[0]["If-None-Match"] == '"old"'
        assert len(shown) == 2
        assert all(isinstance(texture, Gdk.Texture) for texture in shown)

    def test_on_a_metered_network_the_cached_icon_is_shown_but_never_fetched(self) -> None:
        self.metered = True
        self.cache.store("icons/worldle.png", WORLDLE, '"abc"', datetime.now(UTC) - timedelta(days=30))
        item = GameObject(worldle())

        self.icons.load(item)
        run_until(lambda: item.props.icon is not None)
        settle()

        assert item.props.icon is not None
        assert self.server.requests == []

    def test_each_icon_is_asked_for_once_per_run(self) -> None:
        first, second = GameObject(worldle()), GameObject(worldle())

        self.icons.load(first)
        self.icons.load(second)
        self.icons.load(first)
        run_until(lambda: first.props.icon is not None and second.props.icon is not None)
        self.icons.load(GameObject(worldle()))
        settle()

        assert first.props.icon is second.props.icon
        assert self.paths() == ["/v1/icons/worldle.png"]

    def test_a_game_without_an_icon_shows_none_and_asks_for_nothing(self) -> None:
        item = GameObject(worldle(icon=None))

        self.icons.load(item)
        settle()

        assert item.props.icon is None
        assert self.server.requests == []

    def test_a_missing_icon_leaves_the_glyph(self) -> None:
        item = GameObject(worldle(id="wordle", icon="icons/wordle.png"))

        self.icons.load(item)
        settle()

        assert item.props.icon is None
        assert self.paths() == ["/v1/icons/wordle.png"]
        assert self.cache.read("icons/wordle.png") is None

    def test_an_icon_that_does_not_decode_is_not_shown_and_leaves_the_cache(self) -> None:
        self.server.files["/v1/icons/worldle.png"] = GARBLED
        item = GameObject(worldle())

        self.icons.load(item)
        run_until(lambda: self.cache.read("icons/worldle.png") is not None)
        run_until(lambda: self.cache.read("icons/worldle.png") is None)
        settle()

        assert item.props.icon is None
        assert self.cache.read("icons/worldle.png") is None

    def test_a_takedown_clears_the_icon_and_deletes_it_from_the_cache(self) -> None:
        item = GameObject(worldle())
        self.icons.load(item)
        run_until(lambda: item.props.icon is not None)

        item.update(game=worldle(icon=None), favorite=False, popular_rank=0, trending_rank=0)
        self.icons.forget(set())

        assert item.props.icon is None
        assert self.cache.read("icons/worldle.png") is None

    def test_forget_keeps_the_icons_the_catalog_still_names(self) -> None:
        item = GameObject(worldle())
        self.icons.load(item)
        run_until(lambda: item.props.icon is not None)

        self.icons.forget({"icons/worldle.png"})

        assert item.props.icon is not None
        assert self.cache.read("icons/worldle.png") == WORLDLE

    def test_a_forgotten_icon_is_fetched_again_once_the_catalog_names_it(self) -> None:
        item = GameObject(worldle())
        self.icons.load(item)
        run_until(lambda: item.props.icon is not None)
        self.icons.forget(set())

        self.icons.load(item)
        run_until(lambda: item.props.icon is not None)

        assert self.paths() == ["/v1/icons/worldle.png", "/v1/icons/worldle.png"]

    def test_without_a_decoder_no_icon_is_fetched_or_shown_and_the_cache_stays(self) -> None:
        # The Windows build: MSYS2's glycin has no typelibs and no loaders.
        self.cache.store("icons/worldle.png", WORLDLE, '"abc"', datetime.now(UTC) - timedelta(days=30))
        icons = Icons(self.cache, [self.server.url], new_session("1.2.3"), decode=None, metered=lambda: False)
        item = GameObject(worldle())

        icons.load(item)
        settle()

        assert item.props.icon is None
        assert self.server.requests == []
        assert self.cache.read("icons/worldle.png") == WORLDLE


class DecodeTest(unittest.TestCase):
    def decode(self, data: bytes) -> list[Gdk.Texture | None]:
        results: list[Gdk.Texture | None] = []
        UNSANDBOXED(data, results.append)
        run_until(lambda: bool(results))
        return results

    def test_a_png_decodes_to_a_texture(self) -> None:
        (texture,) = self.decode(WORLDLE)
        assert (texture.get_width(), texture.get_height()) == (64, 64)

    def test_garbage_decodes_to_none(self) -> None:
        assert self.decode(b"not an image at all") == [None]


if __name__ == "__main__":
    unittest.main()
