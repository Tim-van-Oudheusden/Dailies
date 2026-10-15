#!/usr/bin/env python3
"""Collect this week's Tranco ranks for every registrable domain in the catalog.

Asks the Tranco API (https://tranco-list.eu/api/ranks/domain/{domain}, no key, about 30 daily ranks per domain) once
for each distinct `domain` of an active game, at most one request per second, retrying once on a 5xx answer and up to
three times, 2 s apart, on a 429. The catalog's `domain` field is the registrable domain of the game's URL, as the
submission validator computes it.

Usage:
    python -I scripts/popularity/collect.py --catalog data/v1/games.json --out "$RUNNER_TEMP/raw/"

Writes OUT/tranco.json: {source, fetched_at, health: {ok, failed, count}, domains: {domain: {ok, fetched_at, status,
ranks: [{date, rank}], error?}}}. A domain Tranco does not rank is ok with no ranks. The collector never decides
whether the week is usable: compute.py fails closed when too many domains failed. Exits 0 once the file is written,
2 on a usage or I/O error.
"""

import argparse
import json
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

import requests

API = "https://tranco-list.eu/api/ranks/domain/"
USER_AGENT = "DailiesPopularity/1.0 (+https://github.com/Tim-van-Oudheusden/Dailies)"
TIMEOUT = 10
# Tranco allows one request per second, counted where it receives them; retries count too. Spacing each request a
# second after the previous answer arrived keeps network jitter from bunching two into one second.
INTERVAL = 1.0
SERVER_ERROR_RETRIES = 1
# A 429 still happens now and then: wait, then try again (docs/research/data-pipeline.md section 5.2).
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_PAUSE = 2.0


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


def fetch_domain(domain: str, session: Session, throttle: Throttle, fetched_at: str) -> dict[str, Any]:
    """Ask Tranco for one domain's ranks, retrying once on a server error and up to three times when rate-limited."""
    url = API + quote(domain, safe="")
    entry: dict[str, Any] = {"ok": False, "fetched_at": fetched_at, "status": None, "ranks": []}
    server_retries, rate_retries = SERVER_ERROR_RETRIES, RATE_LIMIT_RETRIES
    while True:
        throttle.wait()
        try:
            response = session.get(url, timeout=TIMEOUT)
        except requests.RequestException as error:
            return {**entry, "error": f"request failed: {error}"}
        finally:
            throttle.done()
        entry["status"] = response.status_code
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS and rate_retries:
            rate_retries -= 1
            throttle.sleep(RATE_LIMIT_PAUSE)
        elif response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR and server_retries:
            server_retries -= 1
        else:
            break
    if entry["status"] != HTTPStatus.OK:
        return {**entry, "error": f"HTTP {entry['status']}"}
    try:
        ranks = parse_ranks(response.json())
    except (TypeError, ValueError) as error:
        return {**entry, "error": f"malformed response: {error}"}
    return {**entry, "ok": True, "ranks": ranks}


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
    throttle = Throttle(INTERVAL, monotonic, sleep)
    started = timestamp(now())
    domains = {domain: fetch_domain(domain, session, throttle, timestamp(now())) for domain in active_domains(catalog)}
    failed = sum(1 for entry in domains.values() if not entry["ok"])
    return {
        "source": "tranco",
        "fetched_at": started,
        "health": {"ok": len(domains) - failed, "failed": failed, "count": len(domains)},
        "domains": domains,
    }


def tranco_session() -> requests.Session:
    """A session that names Dailies in its User-Agent."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def main(argv: list[str] | None = None, *, session: Session | None = None) -> int:
    """Collect the ranks for the catalog named on the command line and write OUT/tranco.json.

    Args:
        argv: The command-line arguments; sys.argv by default.
        session: Sends the HTTP requests; a new ``requests.Session`` by default.

    Returns:
        0 when the file was written, 2 on a usage or I/O error.
    """
    parser = argparse.ArgumentParser(description="Collect Tranco ranks for the catalog's domains.")
    parser.add_argument("--catalog", type=Path, required=True, help="data/v1/games.json")
    parser.add_argument("--out", type=Path, required=True, help="directory for tranco.json")
    args = parser.parse_args(argv)
    try:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
        with tranco_session() as default_session:
            data = collect(catalog, session or default_session)
        args.out.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        (args.out / "tranco.json").write_text(text, encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"collect: {error}\n")
        return 2
    health = data["health"]
    sys.stderr.write(f"collect: tranco {health['ok']} ok, {health['failed']} failed of {health['count']} domains\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
