"""The game icons' cache and the decisions of one icon fetch, without any networking or image decoding.

A game's icon is the PNG its catalog entry names in `icon` (`icons/<name>.png`), published next to the catalog under
each data URL (docs/data-format.md, "Icons"). `data/icons.py` sends the requests an `IconFetch` asks for and decodes
the cached PNG with glycin; what it decides lives here, so it is tested with plain pytest: an icon is asked for again
at most once a week, with its ETag, never on a metered network, and a body only replaces the cached icon when it looks
like one. `IconCache.prune` deletes the icons the catalog no longer names, so a takedown reaches every installation.

The cache holds `<name>.png`, `<name>.etag` (the validator the server sent with it) and `<name>.fetched` (when the
server last confirmed it, ISO 8601 UTC) for each icon. Every write is atomic.
"""

import logging
from collections.abc import Callable, Collection
from datetime import datetime, timedelta
from http import HTTPStatus
from pathlib import Path, PurePosixPath

from dailies.core.cache import Outcome, Request, Response
from dailies.core.catalog import ICON_PATH

log = logging.getLogger(__name__)

#: How long a cached icon is shown without asking the server again.
MAX_AGE = timedelta(days=7)
#: The largest body taken for an icon; the published ones are 64x64 PNGs of a few kilobytes.
MAX_BYTES = 256 * 1024
#: The largest width or height of a decoded icon.
MAX_SIDE = 256

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_SUFFIXES = (".png", ".etag", ".fetched")


def is_icon(body: bytes) -> bool:
    """Return whether `body` may replace a cached icon: a PNG of at most `MAX_BYTES`. Only glycin decodes it."""
    return body.startswith(_PNG_SIGNATURE) and len(body) <= MAX_BYTES


def fits(width: int, height: int) -> bool:
    """Return whether a decoded icon of `width` by `height` pixels may be shown on a tile."""
    return 0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE


class IconCache:
    """The icon cache directory, `$XDG_CACHE_HOME/dailies/v1/icons` in the app, keyed by the catalog's `icon` path."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self, icon: str) -> bytes | None:
        """Return the cached PNG of `icon`, or None when there is none."""
        return self._read(_name(icon), ".png")

    def etag(self, icon: str) -> str | None:
        """Return the ETag the cached PNG of `icon` was served with, or None."""
        data = self._read(_name(icon), ".etag")
        return data.decode() if data else None

    def fetched_at(self, icon: str) -> datetime | None:
        """Return when the server last confirmed the cached `icon`, or None when it never did."""
        data = self._read(_name(icon), ".fetched")
        try:
            fetched = datetime.fromisoformat(data.decode().strip()) if data else None
        except ValueError:
            return None
        return fetched if fetched and fetched.tzinfo else None

    def store(self, icon: str, body: bytes, etag: str | None, now: datetime) -> None:
        """Replace the cached `icon` with a body the server just sent."""
        name = _name(icon)
        self._write(f"{name}.png", body)
        if etag:
            self._write(f"{name}.etag", etag.encode())
        else:
            (self.path / f"{name}.etag").unlink(missing_ok=True)
        self.touch(icon, now)

    def touch(self, icon: str, now: datetime) -> None:
        """Record that the server confirmed the cached `icon` at `now`."""
        self._write(f"{_name(icon)}.fetched", now.isoformat().encode())

    def remove(self, icon: str) -> None:
        """Delete every file of the cached `icon`; used when the cached PNG does not decode."""
        name = _name(icon)
        for suffix in _SUFFIXES:
            (self.path / f"{name}{suffix}").unlink(missing_ok=True)

    def prune(self, keep: Collection[str]) -> list[str]:
        """Delete every file that does not belong to an icon in `keep`; return the deleted icons, sorted.

        Args:
            keep: The `icon` paths the current catalog names.
        """
        names = {_name(icon) for icon in keep}
        removed: set[str] = set()
        try:
            files = list(self.path.iterdir())
        except OSError:
            return []
        for path in files:
            if path.is_file() and path.stem not in names:
                path.unlink(missing_ok=True)
                if path.suffix in _SUFFIXES:
                    removed.add(f"icons/{path.stem}.png")
        return sorted(removed)

    def _read(self, name: str, suffix: str) -> bytes | None:
        # An icon is never worth an error: an unreadable cache is an empty one.
        try:
            return (self.path / f"{name}{suffix}").read_bytes()
        except OSError:
            return None

    def _write(self, filename: str, data: bytes) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        temporary = self.path / f".{filename}.tmp"
        temporary.write_bytes(data)
        temporary.replace(self.path / filename)


class IconFetch:
    """One fetch of one icon: asks for at most one request per data URL and updates the cache from the answers.

    Call `first_request()`, send what it returns, pass the result to `handle()` and keep sending what that returns
    until it returns None; `outcome` then says how the fetch ended. The cached icon is kept unless a server sends a
    new one.
    """

    def __init__(self, icon: str, cache: IconCache, *, urls: list[str], now: datetime) -> None:
        _name(icon)
        self.icon = icon
        self.outcome = Outcome.PENDING
        self._cache = cache
        self._urls = [f"{base}{icon}" for base in urls]
        self._now = now
        etag = cache.etag(icon) if cache.read(icon) is not None else None
        self._headers = {"If-None-Match": etag} if etag else {}
        self._current: str | None = None

    def first_request(self, *, metered: bool) -> Request | None:
        """Return the first request to send, or None when the cached icon is fresh enough or the network is metered."""
        if metered:
            return self._finish(Outcome.SKIPPED)
        fetched = self._cache.fetched_at(self.icon)
        if fetched is not None and self._now - fetched < MAX_AGE:
            return self._finish(Outcome.FRESH)
        return self._next_request()

    def handle(self, response: Response) -> Request | None:
        """Act on the answer to the last request; return the next request to send, or None when the fetch is over."""
        if self._current is None:
            return None
        url, status = self._current, response.status
        if status == HTTPStatus.NOT_MODIFIED:
            return self._write(Outcome.NOT_MODIFIED, lambda: self._cache.touch(self.icon, self._now))
        if status == HTTPStatus.OK:
            if not is_icon(response.body):
                log.warning("%s: %s sent something that is not an icon, keeping the saved one", self.icon, url)
                return self._finish(Outcome.FAILED)
            return self._write(
                Outcome.UPDATED, lambda: self._cache.store(self.icon, response.body, response.etag, self._now)
            )
        if status is None or status == HTTPStatus.TOO_MANY_REQUESTS or status >= HTTPStatus.INTERNAL_SERVER_ERROR:
            log.info("%s: %s failed (%s), trying the next URL", self.icon, url, status or "network error")
            return self._next_request()
        log.info("%s: %s answered %s", self.icon, url, status)
        return self._finish(Outcome.FAILED)

    def _write(self, outcome: Outcome, write: Callable[[], None]) -> None:
        try:
            write()
        except OSError as e:
            log.warning("%s: could not write the icon cache: %s", self.icon, e)
            return self._finish(Outcome.FAILED)
        return self._finish(outcome)

    def _next_request(self) -> Request | None:
        start = self._urls.index(self._current) + 1 if self._current else 0
        if start < len(self._urls):
            self._current = self._urls[start]
            return Request(self._current, self._headers)
        return self._finish(Outcome.FAILED)

    def _finish(self, outcome: Outcome) -> None:
        self.outcome = outcome
        self._current = None


def _name(icon: str) -> str:
    if not ICON_PATH.fullmatch(icon):
        msg = f"{icon!r} is not an icon path"
        raise ValueError(msg)
    return PurePosixPath(icon).stem
