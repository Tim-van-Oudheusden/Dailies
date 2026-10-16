#!/usr/bin/env python3
"""Collect this week's popularity signals: Tranco ranks always, Wikipedia, Hacker News and Cloudflare Radar on request.

Asks the Tranco API (https://tranco-list.eu/api/ranks/domain/{domain}, no key, about 30 daily ranks per domain) once
for each distinct `domain` of an active game, at most one request per second, retrying once on a 5xx answer and up to
three times, 2 s apart, on a 429. The catalog's `domain` field is the registrable domain of the game's URL, as the
submission validator computes it.

The optional sources are off by default (docs/research/data-pipeline.md section 4.1, issue #78), at most two requests
a second each, with the same retries:

- --wikipedia: English Wikipedia user pageviews of the seven full UTC days before today, from the Wikimedia
  Analytics API (no key, CC0), for each active game with a `wikipedia` article title.
- --hn: the number of Hacker News stories of the last 28 days with the game's name in their title, from HN Search by
  Algolia (no key), for each active game.
- --radar: each domain's Cloudflare Radar POPULAR ranking bucket (CC BY-NC 4.0) from
  /radar/ranking/domain/{domain}?rankingType=POPULAR&format=JSON, with the API token in CLOUDFLARE_RADAR_TOKEN. Without
  the token nothing is asked and radar.json carries an `error`, so compute.py reports the source as down.

Usage:
    python -I scripts/popularity/collect.py --catalog data/v1/games.json --out "$RUNNER_TEMP/raw/" [--wikipedia]
        [--hn] [--radar]

Writes OUT/tranco.json: {source, fetched_at, health: {ok, failed, count}, domains: {domain: {ok, fetched_at, status,
ranks: [{date, rank}], error?}}}. A domain Tranco does not rank is ok with no ranks. Each flag adds a file of the same
shape: OUT/wikipedia.json with articles: {game id: {..., article, views_7d}}, OUT/hn.json with games: {game id:
{..., stories_28d}}, OUT/radar.json with domains: {domain: {..., bucket, rank}} and a top-level error when the token is
missing. The collector never decides whether the week is usable: compute.py fails closed when too many Tranco domains
failed and leaves out an optional source that failed. Exits 0 once the files are written, 2 on a usage or I/O error.
"""

import argparse
import json
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urlencode

import requests

API = "https://tranco-list.eu/api/ranks/domain/"
WIKIPEDIA_API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
HN_API = "https://hn.algolia.com/api/v1/search_by_date"
RADAR_API = "https://api.cloudflare.com/client/v4/radar/ranking/domain/"
RADAR_ENV = "CLOUDFLARE_RADAR_TOKEN"
# Wikimedia's User-Agent policy asks automated clients to say they are a bot and how to reach their operator.
USER_AGENT = "DailiesPopularityBot/1.0 (+https://github.com/Tim-van-Oudheusden/Dailies)"
TIMEOUT = 10
# Tranco allows one request per second, counted where it receives them; retries count too. Spacing each request a
# second after the previous answer arrived keeps network jitter from bunching two into one second.
INTERVAL = 1.0
SERVER_ERROR_RETRIES = 1
# A 429 still happens now and then: wait, then try again (docs/research/data-pipeline.md section 5.2).
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_PAUSE = 2.0
# Wikimedia allows 200 requests a minute to a compliant bot, HN Algolia 10,000 an hour, Radar 1,200 per 5 minutes.
OPTIONAL_INTERVAL = 0.5
WIKIPEDIA_DAYS = 7
HN_DAYS = 28


class Response(Protocol):
    """The part of ``requests.Response`` the collector reads."""

    status_code: int

    def json(self) -> object:
        """Decode the body."""


class Session(Protocol):
    """The part of ``requests.Session`` the collector uses."""

    def get(self, url: str, **kwargs: Any) -> Response:
        """Send one GET request."""


def timestamp(moment: datetime) -> str:
    """UTC time in whole seconds, e.g. 2026-10-19T04:18:00Z."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def active_domains(catalog: dict[str, Any]) -> list[str]:
    """The distinct registrable domains of active games, sorted."""
    return sorted({game["domain"] for game in catalog["games"] if game.get("status") == "active"})


def parse_ranks(body: object) -> list[dict[str, Any]]:
    """The daily ranks of a Tranco answer; TypeError or ValueError when the body is not what the API documents."""
    ranks = body.get("ranks") if isinstance(body, dict) else None
    if not isinstance(ranks, list):
        msg = "no ranks array"
        raise TypeError(msg)
    parsed = []
    for item in ranks:
        date, rank = (item.get("date"), item.get("rank")) if isinstance(item, dict) else (None, None)
        if not isinstance(date, str) or type(rank) is not int or rank < 1:
            msg = f"bad rank entry {item!r}"
            raise ValueError(msg)
        parsed.append({"date": date, "rank": rank})
    return parsed


def _count(body: object, key: str) -> int:
    value = body.get(key) if isinstance(body, dict) else None
    if type(value) is not int or value < 0:
        msg = f"bad {key} {value!r}"
        raise ValueError(msg)
    return value


def parse_views(body: object) -> dict[str, int]:
    """The summed daily views of a Wikimedia pageviews answer."""
    items = body.get("items") if isinstance(body, dict) else None
    if not isinstance(items, list):
        msg = "no items array"
        raise TypeError(msg)
    return {"views_7d": sum(_count(item, "views") for item in items)}


def parse_stories(body: object) -> dict[str, int]:
    """The number of matching stories of an HN Algolia answer."""
    return {"stories_28d": _count(body, "nbHits")}


def parse_radar(body: object) -> dict[str, int | None]:
    """The POPULAR bucket and rank of a Radar domain answer; both None when the domain is not ranked."""
    result = body.get("result") if isinstance(body, dict) and body.get("success") is True else None
    details = result.get("details_0") if isinstance(result, dict) else None
    if not isinstance(details, dict):
        msg = "no result.details_0 object"
        raise TypeError(msg)
    bucket, rank = details.get("bucket"), details.get("rank")
    if bucket is not None and not (isinstance(bucket, str) and bucket.isdigit()):
        msg = f"bad bucket {bucket!r}"
        raise ValueError(msg)
    if rank is not None and (isinstance(rank, bool) or not isinstance(rank, int | float) or rank < 1):
        msg = f"bad rank {rank!r}"
        raise ValueError(msg)
    return {"bucket": None if bucket is None else int(bucket), "rank": None if rank is None else round(rank)}


class Throttle:
    """Keeps ``interval`` seconds between the end of one call and the start of the next."""

    def __init__(self, interval: float, monotonic: Callable[[], float], sleep: Callable[[float], None]) -> None:
        self._interval = interval
        self._monotonic = monotonic
        self.sleep = sleep
        self._last: float | None = None

    def wait(self) -> None:
        """Block until the next call is allowed."""
        if self._last is not None:
            remaining = self._last + self._interval - self._monotonic()
            if remaining > 0:
                self.sleep(remaining)

    def done(self) -> None:
        """Record that a call just finished."""
        self._last = self._monotonic()


@dataclass(frozen=True)
class Clock:
    """The time sources of a collector: UTC now for the stamps, a monotonic clock and sleep for the rate limit."""

    now: Callable[[], datetime] = lambda: datetime.now(UTC)
    monotonic: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep


class Fetcher:
    """Sends one source's GET requests, ``interval`` seconds apart, with the given extra headers."""

    def __init__(self, session: Session, interval: float, clock: Clock, headers: dict[str, str] | None = None) -> None:
        self._session = session
        self._throttle = Throttle(interval, clock.monotonic, clock.sleep)
        self._options: dict[str, Any] = {"timeout": TIMEOUT} | ({"headers": headers} if headers else {})
        self.clock = clock

    def get(self, url: str) -> tuple[dict[str, Any], object]:
        """GET a JSON document, retrying once on a server error and up to three times when rate-limited.

        Returns:
            The entry {ok: False, fetched_at, status, error?}, with an error when the request failed, and the decoded
            body (None on an error).
        """
        entry: dict[str, Any] = {"ok": False, "fetched_at": timestamp(self.clock.now()), "status": None}
        server_retries, rate_retries = SERVER_ERROR_RETRIES, RATE_LIMIT_RETRIES
        while True:
            self._throttle.wait()
            try:
                response = self._session.get(url, **self._options)
            except requests.RequestException as error:
                return {**entry, "error": f"request failed: {error}"}, None
            finally:
                self._throttle.done()
            entry["status"] = response.status_code
            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS and rate_retries:
                rate_retries -= 1
                self._throttle.sleep(RATE_LIMIT_PAUSE)
            elif response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR and server_retries:
                server_retries -= 1
            else:
                break
        if entry["status"] != HTTPStatus.OK:
            return {**entry, "error": f"HTTP {entry['status']}"}, None
        try:
            return entry, response.json()
        except ValueError as error:
            return {**entry, "error": f"malformed response: {error}"}, None

    def item(self, url: str, parse: Callable[[object], dict[str, Any]], **fields: Any) -> dict[str, Any]:
        """One item of a source: its entry with `fields`, plus the parsed values when it is ok."""
        entry, body = self.get(url)
        entry = {**entry, **fields}
        if "error" in entry:
            return entry
        try:
            values = parse(body)
        except (TypeError, ValueError) as error:
            return {**entry, "error": f"malformed response: {error}"}
        return {**entry, **values, "ok": True}


def health(items: dict[str, dict[str, Any]]) -> dict[str, int]:
    """How many items resolved and failed."""
    failed = sum(1 for entry in items.values() if not entry["ok"])
    return {"ok": len(items) - failed, "failed": failed, "count": len(items)}


def _collect_items(
    source: str,
    key: str,
    wanted: dict[str, tuple[str, dict[str, Any]]],
    parse: Callable[[object], dict[str, Any]],
    fetcher: Fetcher,
) -> dict[str, Any]:
    """Fetch each wanted item (id -> (url, extra entry fields)) in id order and summarise the source's health."""
    started = timestamp(fetcher.clock.now())
    items = {item: fetcher.item(url, parse, **fields) for item, (url, fields) in sorted(wanted.items())}
    return {"source": source, "fetched_at": started, "health": health(items), key: items}


def collect(
    catalog: dict[str, Any],
    session: Session,
    *,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Fetch the ranks of every active domain and summarise the source's health.

    Args:
        catalog: The parsed games.json.
        session: Sends the HTTP requests.
        now: The current UTC time, for the ``fetched_at`` stamps.
        monotonic: A monotonic clock in seconds, for the rate limit.
        sleep: Sleeps for the given number of seconds.

    Returns:
        The raw/tranco.json document.
    """
    wanted = {domain: (API + quote(domain, safe=""), {"ranks": []}) for domain in active_domains(catalog)}
    fetcher = Fetcher(session, INTERVAL, Clock(now, monotonic, sleep))
    return _collect_items("tranco", "domains", wanted, lambda body: {"ranks": parse_ranks(body)}, fetcher)


def collect_wikipedia(catalog: dict[str, Any], session: Session, *, clock: Clock | None = None) -> dict[str, Any]:
    """The English Wikipedia pageviews of the last seven full UTC days of every active game with an article."""
    clock = clock or Clock()
    end = clock.now().astimezone(UTC).date() - timedelta(days=1)
    days = f"/daily/{end - timedelta(days=WIKIPEDIA_DAYS - 1):%Y%m%d}/{end:%Y%m%d}"
    wanted = {
        game["id"]: (WIKIPEDIA_API + quote(title.replace(" ", "_"), safe="") + days, {"article": title})
        for game in catalog["games"]
        if game.get("status") == "active" and (title := game.get("wikipedia"))
    }
    return _collect_items("wikipedia", "articles", wanted, parse_views, Fetcher(session, OPTIONAL_INTERVAL, clock))


def collect_hn(catalog: dict[str, Any], session: Session, *, clock: Clock | None = None) -> dict[str, Any]:
    """The number of Hacker News stories of the last 28 days with each active game's name in their title."""
    clock = clock or Clock()
    until = int(clock.now().timestamp())
    since = until - HN_DAYS * 86400

    def url(name: str) -> str:
        query = {
            "query": name,
            "tags": "story",
            "restrictSearchableAttributes": "title",
            "typoTolerance": "false",
            "hitsPerPage": 0,
            "numericFilters": f"created_at_i>{since},created_at_i<{until}",
        }
        return f"{HN_API}?{urlencode(query)}"

    wanted = {game["id"]: (url(game["name"]), {}) for game in catalog["games"] if game.get("status") == "active"}
    return _collect_items("hn", "games", wanted, parse_stories, Fetcher(session, OPTIONAL_INTERVAL, clock))


def collect_radar(
    catalog: dict[str, Any], session: Session, token: str | None, *, clock: Clock | None = None
) -> dict[str, Any]:
    """Each active domain's Cloudflare Radar POPULAR bucket; without a token, nothing is asked and `error` says why."""
    clock = clock or Clock()
    domains = active_domains(catalog)
    if not token:
        return {
            "source": "radar",
            "fetched_at": timestamp(clock.now()),
            "error": f"{RADAR_ENV} is not set",
            "health": {"ok": 0, "failed": len(domains), "count": len(domains)},
            "domains": {},
        }
    query = urlencode({"rankingType": "POPULAR", "format": "JSON"})
    wanted = {domain: (f"{RADAR_API}{quote(domain, safe='')}?{query}", {}) for domain in domains}
    fetcher = Fetcher(session, OPTIONAL_INTERVAL, clock, {"Authorization": f"Bearer {token}"})
    return _collect_items("radar", "domains", wanted, parse_radar, fetcher)


def popularity_session() -> requests.Session:
    """A session that names Dailies in its User-Agent."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def _write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None, *, session: Session | None = None) -> int:
    """Collect the signals for the catalog named on the command line and write them to OUT.

    Args:
        argv: The command-line arguments; sys.argv by default.
        session: Sends the HTTP requests; a new ``requests.Session`` by default.

    Returns:
        0 when the files were written, 2 on a usage or I/O error.
    """
    parser = argparse.ArgumentParser(description="Collect popularity signals for the catalog's games.")
    parser.add_argument("--catalog", type=Path, required=True, help="data/v1/games.json")
    parser.add_argument("--out", type=Path, required=True, help="directory for tranco.json and the optional sources")
    parser.add_argument("--wikipedia", action="store_true", help="also collect Wikipedia pageviews (wikipedia.json)")
    parser.add_argument("--hn", action="store_true", help="also collect Hacker News story counts (hn.json)")
    parser.add_argument(
        "--radar", action="store_true", help=f"also collect Cloudflare Radar buckets (radar.json; needs {RADAR_ENV})"
    )
    args = parser.parse_args(argv)
    try:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
        with popularity_session() as default_session:
            http = session or default_session
            documents = {"tranco": collect(catalog, http)}
            if args.wikipedia:
                documents["wikipedia"] = collect_wikipedia(catalog, http)
            if args.hn:
                documents["hn"] = collect_hn(catalog, http)
            if args.radar:
                documents["radar"] = collect_radar(catalog, http, os.environ.get(RADAR_ENV))
        args.out.mkdir(parents=True, exist_ok=True)
        for name, data in documents.items():
            _write(args.out / f"{name}.json", data)
    except (OSError, KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"collect: {error}\n")
        return 2
    for name, data in documents.items():
        counts = data["health"]
        note = f" ({data['error']})" if "error" in data else ""
        sys.stderr.write(f"collect: {name} {counts['ok']} ok, {counts['failed']} failed of {counts['count']}{note}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
