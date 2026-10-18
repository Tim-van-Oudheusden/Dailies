"""The cache of the published data files and the decisions of one refresh, without any networking.

`data/fetcher.py` performs the HTTP requests a `Refresh` asks for and hands back each `Response`; everything it decides
lives here, so it is tested with plain pytest: whether a file is fresh enough to skip, which conditional header to send,
which URL to try next on a server or network error, how long `Retry-After` defers a URL, and that a response is
validated before it replaces the last good copy.

The cache holds `<name>.json` (the body), `<name>.etag` (the validator the server sent with it) and `<name>.fetched`
(when the server last confirmed the body, ISO 8601 UTC) for each name in `MAX_AGE`. Every write is atomic.
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from enum import Enum
from http import HTTPStatus
from pathlib import Path

from dailies.core import catalog, popularity

log = logging.getLogger(__name__)

CATALOG = "games"
POPULARITY = "popularity"

#: How long a cached file is used without asking the server again. Upstream sends `max-age` of 5 to 10 minutes.
MAX_AGE = {CATALOG: timedelta(hours=6), POPULARITY: timedelta(hours=24)}

_VALIDATORS: Mapping[str, Callable[[bytes], object]] = {CATALOG: catalog.parse, POPULARITY: popularity.parse}

#: The most digits a `Retry-After` in seconds is converted with; a `timedelta` holds at most 14.
_MAX_SECONDS_DIGITS = 15

#: How long without a successful fetch before the app says, while online, that its game list is old.
STALE_BANNER_AFTER = timedelta(days=14)


class Outcome(Enum):
    """How a refresh of one file ended."""

    PENDING = "pending"
    #: Not asked: the network is metered, so only a refresh the user asks for goes out.
    SKIPPED = "skipped"
    FRESH = "fresh"
    NOT_MODIFIED = "not-modified"
    UPDATED = "updated"
    FAILED = "failed"


def summarize(outcomes: Mapping[str, Outcome]) -> Outcome:
    """Return the outcome of a whole refresh, as the user is told: failed, updated, skipped, or else not modified."""
    for outcome in (Outcome.FAILED, Outcome.UPDATED):
        if outcome in outcomes.values():
            return outcome
    if outcomes and all(outcome is Outcome.SKIPPED for outcome in outcomes.values()):
        return Outcome.SKIPPED
    return Outcome.NOT_MODIFIED


@dataclass(frozen=True)
class Request:
    """A GET the caller is to send."""

    url: str
    headers: Mapping[str, str]


@dataclass(frozen=True)
class Response:
    """What came back: `status` is None when no HTTP response arrived (DNS, TLS, connection or timeout error)."""

    status: int | None
    body: bytes = b""
    etag: str | None = None
    retry_after: str | None = None


class CacheDir:
    """The cache directory, `$XDG_CACHE_HOME/dailies/v1` in the app."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self, name: str) -> bytes | None:
        """Return the cached body of `name`, or None when there is none."""
        return self._read(f"{name}.json")

    def etag(self, name: str) -> str | None:
        """Return the ETag the cached body of `name` was served with, or None."""
        data = self._read(f"{name}.etag")
        return data.decode() if data else None

    def fetched_at(self, name: str) -> datetime | None:
        """Return when the server last confirmed the cached `name`, or None when it never did."""
        data = self._read(f"{name}.fetched")
        try:
            fetched = datetime.fromisoformat(data.decode().strip()) if data else None
        except ValueError:
            return None
        return fetched if fetched and fetched.tzinfo else None

    def store(self, name: str, body: bytes, etag: str | None, now: datetime) -> None:
        """Replace the cached `name` with a body the server just sent (and that has been validated)."""
        self._write(f"{name}.json", body)
        if etag:
            self._write(f"{name}.etag", etag.encode())
        else:
            self._remove(f"{name}.etag")
        self.touch(name, now)

    def touch(self, name: str, now: datetime) -> None:
        """Record that the server confirmed the cached `name` at `now`."""
        self._write(f"{name}.fetched", now.isoformat().encode())

    def seed(self, name: str, body: bytes) -> None:
        """Replace the cached `name` with a bundled copy, which no server has confirmed."""
        self._write(f"{name}.json", body)
        self._remove(f"{name}.etag")
        self._remove(f"{name}.fetched")

    def _read(self, filename: str) -> bytes | None:
        try:
            return (self.path / filename).read_bytes()
        except FileNotFoundError:
            return None

    def _write(self, filename: str, data: bytes) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        temporary = self.path / f".{filename}.tmp"
        temporary.write_bytes(data)
        temporary.replace(self.path / filename)

    def _remove(self, filename: str) -> None:
        (self.path / filename).unlink(missing_ok=True)


@dataclass
class Backoff:
    """The URLs a server asked, with `Retry-After`, not to be contacted again until a given time."""

    _not_before: dict[str, datetime] = field(default_factory=dict)

    def allows(self, url: str, now: datetime) -> bool:
        """Return whether `url` may be requested at `now`."""
        return now >= self._not_before.get(url, now)

    def defer(self, url: str, until: datetime) -> None:
        """Keep `url` from being requested before `until`."""
        self._not_before[url] = until


def parse_retry_after(value: str | None, now: datetime, *, longest: timedelta) -> datetime | None:
    """Return the time a `Retry-After` header (seconds or an HTTP date) points at, or None when it is absent or bad.

    Args:
        value: The header value.
        now: The current time, timezone-aware.
        longest: The furthest from `now` the returned time may be; a later one is cut back to `now + longest`.
    """
    if not value:
        return None
    # Seconds are ASCII digits: `isdigit` also takes "²", which `int` refuses. `int` refuses over 4300 digits too, so a
    # longer number than any `timedelta` holds is cut back to `longest` without converting it.
    if value.isascii() and value.isdigit():
        digits = value.lstrip("0") or "0"
        seconds = int(digits) if len(digits) <= _MAX_SECONDS_DIGITS else longest.total_seconds()
        return now + timedelta(seconds=min(seconds, longest.total_seconds()))
    try:
        until = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    # A zone of "-0000" makes the date naive; HTTP dates are always UTC.
    return min(until if until.tzinfo else until.replace(tzinfo=UTC), now + longest)


def needs_stale_banner(last_success: datetime | None, now: datetime, *, online: bool) -> bool:
    """Return whether to say the game list is old: online, and the last successful fetch is over 14 days ago.

    Before the first successful fetch there is no banner, so a fresh install that is kept offline stays quiet.
    """
    return online and last_success is not None and now - last_success > STALE_BANNER_AFTER


class Refresh:
    """One refresh of one cached file: asks for at most one request per URL and updates the cache from the answers.

    Call `first_request()`, send what it returns, pass the result to `handle()` and keep sending what that returns
    until it returns None; `outcome` then says how the refresh ended. A URL is never asked twice.
    """

    def __init__(
        self,
        name: str,
        cache: CacheDir,
        *,
        urls: list[str],
        now: datetime,
        backoff: Backoff,
    ) -> None:
        if name not in _VALIDATORS:
            msg = f"unknown data file {name!r}"
            raise ValueError(msg)
        self.name = name
        self.outcome = Outcome.PENDING
        self._cache = cache
        self._urls = [f"{base}{name}.json" for base in urls]
        self._now = now
        self._backoff = backoff
        etag = cache.etag(name) if cache.read(name) is not None else None
        self._headers = {"If-None-Match": etag} if etag else {}
        self._current: str | None = None

    def first_request(self, *, force: bool = False) -> Request | None:
        """Return the first request to send, or None when the cached file is fresh enough or every URL is deferred.

        Args:
            force: Ask the server even when the cached file is younger than its maximum age.
        """
        fetched = self._cache.fetched_at(self.name)
        if not force and fetched is not None and self._now - fetched < MAX_AGE[self.name]:
            log.debug("%s: fetched %s ago, no request", self.name, self._now - fetched)
            return self._finish(Outcome.FRESH)
        return self._next_request()

    def handle(self, response: Response) -> Request | None:
        """Act on the answer to the last request; return the next request to send, or None when the refresh is over."""
        if self._current is None:
            return None
        url, status = self._current, response.status
        if status == HTTPStatus.NOT_MODIFIED:
            log.info("%s: %s not modified", self.name, url)
            return self._write(Outcome.NOT_MODIFIED, lambda: self._cache.touch(self.name, self._now))
        if status == HTTPStatus.OK:
            return self._accept(url, response)
        if status is None or status == HTTPStatus.TOO_MANY_REQUESTS or status >= HTTPStatus.INTERNAL_SERVER_ERROR:
            log.warning("%s: %s failed (%s), trying the next URL", self.name, url, status or "network error")
            if until := parse_retry_after(response.retry_after, self._now, longest=MAX_AGE[self.name]):
                self._backoff.defer(url, until)
            return self._next_request()
        log.warning("%s: %s answered %s, keeping the saved copy", self.name, url, status)
        return self._finish(Outcome.FAILED)

    def _accept(self, url: str, response: Response) -> None:
        try:
            _VALIDATORS[self.name](response.body)
        except ValueError as e:
            log.warning("%s: %s sent an invalid file, keeping the saved copy: %s", self.name, url, e)
            return self._finish(Outcome.FAILED)
        log.info("%s: updated from %s", self.name, url)
        return self._write(
            Outcome.UPDATED, lambda: self._cache.store(self.name, response.body, response.etag, self._now)
        )

    def _write(self, outcome: Outcome, write: Callable[[], None]) -> None:
        try:
            write()
        except OSError as e:
            log.warning("%s: could not write the cache, keeping the saved copy: %s", self.name, e)
            return self._finish(Outcome.FAILED)
        return self._finish(outcome)

    def _next_request(self) -> Request | None:
        start = self._urls.index(self._current) + 1 if self._current else 0
        for url in self._urls[start:]:
            if self._backoff.allows(url, self._now):
                self._current = url
                log.info("%s: requesting %s", self.name, url)
                return Request(url, self._headers)
            log.info("%s: %s asked to wait, skipping it", self.name, url)
        log.warning("%s: no URL left to try, keeping the saved copy", self.name)
        return self._finish(Outcome.FAILED)

    def _finish(self, outcome: Outcome) -> None:
        self.outcome = outcome
        self._current = None
