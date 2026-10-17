"""Fetcher against a local HTTP server with ETag support; run by Meson (see tests/meson.build)."""

import gettext
import tempfile
import threading
import unittest
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import gi

gi.require_version("Soup", "3.0")

from gi.repository import GLib

gettext.install("dailies")

from dailies.core import catalog
from dailies.core.cache import CacheDir, Outcome
from dailies.data.fetcher import Fetcher
from dailies.ui.game_object import GameObject

BUNDLE = Path(__file__).resolve().parents[2] / "data" / "v1"
GAMES = (BUNDLE / "games.json").read_bytes()
POPULARITY = (BUNDLE / "popularity.json").read_bytes()


class Server(ThreadingHTTPServer):
    """Serves `files` (path -> body) with a fixed ETag per body, or `status` for every request when set."""

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), Handler)
        self.files: dict[str, bytes] = {"/v1/games.json": GAMES, "/v1/popularity.json": POPULARITY}
        self.status: int | None = None
        self.requests: list[dict[str, str]] = []
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}/v1/"


class Handler(BaseHTTPRequestHandler):
    server: Server

    def do_GET(self) -> None:
        self.server.requests.append({"path": self.path, **dict(self.headers.items())})
        if self.server.status is not None:
            self.send_response(self.server.status)
            self.send_header("Retry-After", "600")
            self.end_headers()
            return
        body = self.server.files[self.path]
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


def snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir()) if path.is_file()}


class FetcherTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cache = CacheDir(Path(directory.name) / "v1")
        self.cache.seed("games", GAMES)
        self.cache.seed("popularity", POPULARITY)
        self.server = Server()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def refresh_all(self, urls: list[str], *, force: bool = False) -> dict[str, Outcome]:
        loop = GLib.MainLoop()
        results: dict[str, Outcome] = {}

        def done(outcomes: dict[str, Outcome]) -> None:
            results.update(outcomes)
            loop.quit()

        Fetcher(self.cache, urls, "1.2.3").refresh_all(done, force=force)
        GLib.timeout_add_seconds(10, loop.quit)
        loop.run()
        return results

    def test_a_never_fetched_cache_is_updated_unconditionally(self) -> None:
        assert self.refresh_all([self.server.url]) == {"games": Outcome.UPDATED, "popularity": Outcome.UPDATED}

        assert [request["path"] for request in self.server.requests] == ["/v1/games.json", "/v1/popularity.json"]
        assert "If-None-Match" not in self.server.requests[0]
        assert self.cache.etag("games")
        assert self.cache.fetched_at("games") is not None

    def test_the_user_agent_names_the_app_and_nothing_else(self) -> None:
        self.refresh_all([self.server.url])
        assert self.server.requests[0]["User-Agent"] == "Dailies/1.2.3 (+https://github.com/Tim-van-Oudheusden/Dailies)"

    def test_a_fresh_cache_makes_no_request(self) -> None:
        self.refresh_all([self.server.url])
        self.server.requests.clear()

        assert self.refresh_all([self.server.url]) == {"games": Outcome.FRESH, "popularity": Outcome.FRESH}
        assert self.server.requests == []

    def test_a_valid_etag_gets_304_and_only_the_fetched_time_changes(self) -> None:
        self.refresh_all([self.server.url])
        before = snapshot(self.cache.path)

        assert self.refresh_all([self.server.url], force=True)["games"] is Outcome.NOT_MODIFIED

        assert self.server.requests[-2]["If-None-Match"] == self.cache.etag("games")
        after = snapshot(self.cache.path)
        assert {name for name in after if after[name] != before[name]} == {"games.fetched", "popularity.fetched"}

    def test_a_truncated_response_leaves_the_cache_untouched(self) -> None:
        self.server.files["/v1/games.json"] = GAMES[: len(GAMES) // 2]
        before = snapshot(self.cache.path)

        assert self.refresh_all([self.server.url])["games"] is Outcome.FAILED

        assert {name: body for name, body in snapshot(self.cache.path).items() if name.startswith("games")} == {
            name: body for name, body in before.items() if name.startswith("games")
        }

    def test_a_server_error_falls_through_to_the_next_url(self) -> None:
        failing = Server()
        self.addCleanup(failing.server_close)
        self.addCleanup(failing.shutdown)
        failing.status = HTTPStatus.SERVICE_UNAVAILABLE

        outcomes = self.refresh_all([failing.url, self.server.url])

        assert outcomes["games"] is Outcome.UPDATED
        assert [request["path"] for request in failing.requests] == ["/v1/games.json", "/v1/popularity.json"]

    def test_a_network_error_falls_through_to_the_next_url(self) -> None:
        closed = Server()
        url = closed.url
        closed.shutdown()
        closed.server_close()

        assert self.refresh_all([url, self.server.url])["games"] is Outcome.UPDATED

    def test_when_every_url_fails_the_saved_copy_is_kept(self) -> None:
        self.server.status = HTTPStatus.INTERNAL_SERVER_ERROR
        before = snapshot(self.cache.path)

        assert self.refresh_all([self.server.url]) == {"games": Outcome.FAILED, "popularity": Outcome.FAILED}
        assert snapshot(self.cache.path) == before

    def test_timestamps_are_recent(self) -> None:
        self.refresh_all([self.server.url])
        assert datetime.now(UTC) - self.cache.fetched_at("games") < timedelta(minutes=1)

    def test_a_cache_write_error_still_ends_the_refresh(self) -> None:
        # A directory where the temporary file goes makes the write fail, even for root.
        for name in ("games", "popularity"):
            (self.cache.path / f".{name}.json.tmp").mkdir()
        before = snapshot(self.cache.path)

        assert self.refresh_all([self.server.url]) == {"games": Outcome.FAILED, "popularity": Outcome.FAILED}
        assert snapshot(self.cache.path) == before

    def test_the_icons_come_from_the_same_urls_into_the_cache(self) -> None:
        self.server.files["/v1/icons/worldle.png"] = (BUNDLE / "icons" / "worldle.png").read_bytes()
        game = catalog.parse(GAMES).get("worldle")
        fetcher = Fetcher(self.cache, [self.server.url], "1.2.3")

        fetcher.icons.load(GameObject(game))
        context = GLib.MainContext.default()
        deadline = GLib.get_monotonic_time() + 10_000_000
        while not self.server.requests and GLib.get_monotonic_time() < deadline:
            context.iteration(False)

        assert [request["path"] for request in self.server.requests] == ["/v1/icons/worldle.png"]
        assert self.server.requests[0]["User-Agent"] == "Dailies/1.2.3 (+https://github.com/Tim-van-Oudheusden/Dailies)"


if __name__ == "__main__":
    unittest.main()
