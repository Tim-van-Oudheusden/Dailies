import logging
from collections.abc import Callable
from datetime import UTC, datetime

import gi

gi.require_version("Soup", "3.0")

from gi.repository import Gio, GLib, Soup

from dailies.core import cache
from dailies.core.cache import Backoff, CacheDir, Outcome, Refresh, Request, Response

log = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 30


class Fetcher:
    """Sends the requests a `dailies.core.cache.Refresh` asks for over libsoup, asynchronously, one at a time."""

    def __init__(self, cache_dir: CacheDir, urls: list[str], version: str) -> None:
        self._cache = cache_dir
        self._urls = urls
        self._backoff = Backoff()
        self._session = Soup.Session(
            user_agent=f"Dailies/{version} (+https://github.com/Tim-van-Oudheusden/Dailies)",
            timeout=_TIMEOUT_SECONDS,
        )

    def refresh_all(self, callback: Callable[[dict[str, Outcome]], None], *, force: bool = False) -> None:
        """Refresh the catalog, then the popularity file, and call `callback` with both outcomes.

        Args:
            callback: Called with each file's outcome from the main loop, never before this method returns.
            force: Ask the server even when a file is younger than its maximum age or the network is metered.
        """
        names = [cache.CATALOG, cache.POPULARITY]
        if not force and Gio.NetworkMonitor.get_default().get_network_metered():
            log.info("the network is metered, not refreshing")
            _call_soon(callback, dict.fromkeys(names, Outcome.SKIPPED))
            return
        outcomes: dict[str, Outcome] = {}

        def next_file(*_args: object) -> None:
            if len(outcomes) == len(names):
                _call_soon(callback, outcomes)
                return
            name = names[len(outcomes)]
            refresh = Refresh(name, self._cache, urls=self._urls, now=datetime.now(UTC), backoff=self._backoff)

            def finished() -> None:
                outcomes[name] = refresh.outcome
                next_file()

            self._run(refresh, refresh.first_request(force=force), finished)

        next_file()

    def _run(self, refresh: Refresh, request: Request | None, finished: Callable[[], None]) -> None:
        if request is None:
            finished()
            return
        message = Soup.Message.new("GET", request.url)
        for header, value in request.headers.items():
            message.get_request_headers().append(header, value)

        def on_response(session: Soup.Session, result: Gio.AsyncResult) -> None:
            try:
                body = session.send_and_read_finish(result).get_data() or b""
            except GLib.Error as e:
                log.info("%s: %s", request.url, e.message)
                response = Response(None)
            else:
                headers = message.get_response_headers()
                response = Response(
                    int(message.get_status()),
                    body,
                    etag=headers.get_one("ETag"),
                    retry_after=headers.get_one("Retry-After"),
                )
            self._run(refresh, refresh.handle(response), finished)

        self._session.send_and_read_async(message, GLib.PRIORITY_DEFAULT, None, on_response)


def _call_soon(callback: Callable[[dict[str, Outcome]], None], outcomes: dict[str, Outcome]) -> None:
    def call() -> bool:
        callback(outcomes)
        return GLib.SOURCE_REMOVE

    GLib.idle_add(call)
