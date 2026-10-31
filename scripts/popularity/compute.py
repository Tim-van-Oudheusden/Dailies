#!/usr/bin/env python3
"""Compute the weekly Popular and Trending shelves from the collected popularity signals (method_version 2 or 4).

Every number is deterministic: the same catalog, raw signals, previous file, weights file and --now give a
byte-identical popularity.json and summary.json. The method (docs/proposals/mvp-first.md section 8, decision #88):

- tranco_score = clamp(1 - (log10(rank) - 2) / 4.5, 0, 1) on the mean of the last 7 daily ranks; no rank scores 0.
- With only raw/tranco.json (method_version 2), popularity = tranco_score. Every game gets its registrable domain's
  full score.
- With any of raw/wikipedia.json, raw/hn.json or raw/radar.json (written by collect.py --wikipedia, --hn, --radar;
  method_version 4), popularity is the weighted mean of the scores a game has (docs/research/data-pipeline.md 4.2):
  tranco 0.80, wiki_score = clamp(log10(views_7d + 1) / 6, 0, 1) 0.15, hn_score = clamp(log10(stories_28d + 1) / 2,
  0, 1) 0.05, radar_score = tranco_score of the Radar rank or bucket 0.20. A missing score (no `wikipedia` article,
  a failed fetch, a source that is off or unusable) drops out and the remaining weights are renormalised. Wikipedia
  is a bonus (#136): popularity = max(mean without wiki_score, mean with it), so an article never costs a game score.
  (method_version 3 was the plain weighted mean.)
- An optional source is unusable when its collector reported an error (e.g. no Radar token) or more than 20 % of its
  items failed; its health says so in `sources` and the week still computes.
- A domain whose Tranco fetch failed keeps the game's popularity of last week (reason "carried_forward"), or 0
  without one.
- trend = popularity - mean of the previous 4 weeks' popularity; null until two prior weeks exist. The history comes
  from the previous popularity.json (up to 8 weeks per game) when its method_version matches.
- N = max(5, min(12, 10 % of active games)). Popular: top N by popularity. Trending: trend > 0.02 outside the top 5
  popular, by trend, top N; with fewer than 3, the newest added games fill it to 3 with reason "new".
- At most 2 games of one registrable domain go on each shelf; the next games take the freed slots. Ties, and so the
  choice within a domain, follow data/v1/domain_weights.json ({"nytimes.com": {"wordle": 0.35, ...}}): listed games
  first, the highest weight first, then unlisted ones; then id. The weights only order the games; they split nothing.
- Fail closed: when Tranco failed for more than 20 % of the domains, nothing is written and the exit status is 1.

Usage:
    python -I scripts/popularity/compute.py --catalog data/v1/games.json --raw "$RUNNER_TEMP/raw/" \
        --out data/v1/popularity.json --summary "$RUNNER_TEMP/summary.json"

Exits 0 when both files were written, 1 when the sources failed, 2 on a usage error or invalid input.
"""

import argparse
import json
import math
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jsonschema

METHOD_VERSION = 2
COMPOSITE_METHOD_VERSION = 4
ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "data" / "v1" / "schema" / "popularity.schema.json"
VALIDITY = timedelta(days=10)
RANK_DAYS = 7
TREND_WEEKS = 4
MIN_TREND_WEEKS = 2
HISTORY_WEEKS = 8
TREND_THRESHOLD = 0.02
TRENDING_EXCLUDES_TOP = 5
TRENDING_MINIMUM = 3
DOMAIN_CAP = 2
MAX_FAILED_SHARE = 0.2
TOP_MOVERS = 5
DIGITS = 4
WEIGHT_TOLERANCE = 1e-9
ATTRIBUTION = [
    "Tranco (https://tranco-list.eu): domain ranks, used with attribution; licence not stated by its maintainers",
]
# The optional sources, the raw file key holding their items, and the scores field of their raw number.
OPTIONAL_SOURCES = ("wikipedia", "hn", "radar")
ITEMS = {"wikipedia": "articles", "hn": "games", "radar": "domains"}
FIELDS = {"wikipedia": "wiki_views_7d", "hn": "hn_stories_28d", "radar": "radar_bucket"}
# Proposed in docs/research/data-pipeline.md section 4.2 and issue #78; Radar's weight is ours (#78 left it open).
WEIGHTS = {"tranco": 0.80, "wikipedia": 0.15, "hn": 0.05, "radar": 0.20}
SOURCE_ATTRIBUTION = {
    "wikipedia": "Wikimedia Analytics API (https://wikimedia.org/api/rest_v1/): English Wikipedia pageviews, CC0 1.0",
    "hn": "Hacker News Search by Algolia (https://hn.algolia.com/api): Hacker News story counts",
    "radar": (
        "Cloudflare Radar (https://radar.cloudflare.com): domain ranking buckets, CC BY-NC 4.0; "
        "used for non-commercial purposes only"
    ),
}


class WeightsError(ValueError):
    """data/v1/domain_weights.json is malformed."""


class SourceFailedError(RuntimeError):
    """Too many domains failed to fetch; the shelves would be wrong."""


def tranco_score(rank: float | None) -> float:
    """1.0 at rank 100 and above, 0.0 at rank 10^6.5 and below, log-linear between; 0.0 without a rank."""
    if rank is None:
        return 0.0
    return min(1.0, max(0.0, 1 - (math.log10(rank) - 2) / 4.5))


def wiki_score(views: int) -> float:
    """0.0 without views, 1.0 at a million views a week and above, log-linear between."""
    return min(1.0, max(0.0, math.log10(views + 1) / 6))


def hn_score(stories: int) -> float:
    """0.0 without stories, 1.0 at 99 stories in 28 days and above, log-linear between."""
    return min(1.0, max(0.0, math.log10(stories + 1) / 2))


def weighted_mean(parts: list[tuple[str, float]]) -> float:
    """The mean of (source, score) pairs weighted by WEIGHTS; a single score is returned as is."""
    if len(parts) == 1:
        return parts[0][1]
    return sum(WEIGHTS[name] * score for name, score in parts) / sum(WEIGHTS[name] for name, _ in parts)


def composite(parts: list[tuple[str, float]]) -> float:
    """The weighted mean of a game's scores, where a Wikipedia score only counts when it raises the mean (#136)."""
    others = [part for part in parts if part[0] != "wikipedia"]
    return max(weighted_mean(others), weighted_mean(parts))


def mean_rank(ranks: list[dict[str, Any]]) -> float | None:
    """The mean of the newest RANK_DAYS daily ranks, or None when there are none."""
    newest = sorted(ranks, key=lambda item: item["date"], reverse=True)[:RANK_DAYS]
    if not newest:
        return None
    return sum(item["rank"] for item in newest) / len(newest)


def shelf_size(active: int) -> int:
    """N = max(5, min(12, 10 % of the active games)), never more than there are games."""
    return min(active, max(5, min(12, active // 10)))


def iso_week(moment: datetime) -> str:
    """The ISO 8601 week, e.g. 2026-W43."""
    year, week, _ = moment.isocalendar()
    return f"{year}-W{week:02d}"


def timestamp(moment: datetime) -> str:
    """UTC time in whole seconds, e.g. 2026-10-19T04:21:09Z."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def active_games(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """The active games, sorted by id."""
    return sorted((game for game in catalog["games"] if game.get("status") == "active"), key=lambda game: game["id"])


def load_weights(path: Path, catalog: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Read and check the shared-domain order file; no file means no order beyond id.

    Raises:
        WeightsError: A domain's weights are not numbers between 0 and 1 summing to 1, or name a game that does not
            exist or is not on that domain.
    """
    if not path.exists():
        return {}
    weights = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(weights, dict):
        msg = f"{path.name} must be an object of domain -> {{id: weight}}"
        raise WeightsError(msg)
    domains = {game["id"]: game["domain"] for game in catalog["games"]}
    for domain, shares in weights.items():
        if not isinstance(shares, dict):
            msg = f"{domain}: weights must be an object of id -> weight"
            raise WeightsError(msg)
        for game_id, weight in shares.items():
            if game_id not in domains:
                msg = f"{domain}: unknown game {game_id!r}"
                raise WeightsError(msg)
            if domains[game_id] != domain:
                msg = f"{domain}: {game_id!r} is not on {domain}"
                raise WeightsError(msg)
            if isinstance(weight, bool) or not isinstance(weight, int | float) or not 0 <= weight <= 1:
                msg = f"{domain}: the weight of {game_id!r} must be a number between 0 and 1"
                raise WeightsError(msg)
        if abs(sum(shares.values()) - 1) > WEIGHT_TOLERANCE:
            msg = f"{domain}: weights must sum to 1, not {sum(shares.values())}"
            raise WeightsError(msg)
    return weights


def weight_order(overrides: dict[str, dict[str, float]]) -> dict[str, tuple[int, float]]:
    """A sort key per listed game: listed games come before unlisted ones (key (1, 0)), the heaviest weight first."""
    return {game_id: (0, -weight) for shares in overrides.values() for game_id, weight in shares.items()}


def capped(ordered: list[str], domains: dict[str, str], size: int, taken: list[str] | None = None) -> list[str]:
    """The first `size` games of `ordered`, skipping a game once DOMAIN_CAP games of its domain are on the shelf.

    `taken` lists games already on the shelf; they count towards the cap but are not returned.
    """
    counts = Counter(domains[game_id] for game_id in taken or [])
    shelf: list[str] = []
    for game_id in ordered:
        if len(shelf) == size:
            break
        if counts[domains[game_id]] < DOMAIN_CAP:
            counts[domains[game_id]] += 1
            shelf.append(game_id)
    return shelf


def prior_weeks(previous: dict[str, Any] | None, week: str, method_version: int) -> dict[str, list[float]]:
    """Each game's popularity in the weeks before this one, newest first, at most HISTORY_WEEKS.

    A rerun in the same week replaces that week instead of counting it twice; history computed with another
    method_version is not comparable and is dropped.
    """
    if not previous or previous.get("method_version") != method_version:
        return {}
    weeks = {}
    for game_id, score in previous.get("scores", {}).items():
        history = list(score.get("history", []))
        if previous.get("week") != week:
            history.insert(0, score["popularity"])
        weeks[game_id] = history[:HISTORY_WEEKS]
    return weeks


def tranco_health(raw: dict[str, Any], domains: set[str]) -> tuple[int, list[str], list[str]]:
    """The number of resolved domains, the failed ones and the unranked ones, each list sorted."""
    entries = raw.get("domains", {})
    failed = sorted(domain for domain in domains if not entries.get(domain, {}).get("ok"))
    unranked = sorted(domain for domain in domains if domain not in failed and not entries[domain]["ranks"])
    return len(domains) - len(failed) - len(unranked), failed, unranked


def signal_key(name: str, game: dict[str, Any]) -> str:
    """What an optional source is asked about: the domain for Radar, the game for the others."""
    return game["domain"] if name == "radar" else game["id"]


@dataclass(frozen=True)
class Signal:
    """One optional source of one week: what was asked, what failed, and whether it is used at all."""

    name: str
    fetched_at: str
    keys: frozenset[str]
    failed: list[str]
    error: str | None
    entries: dict[str, dict[str, Any]]

    def key(self, game: dict[str, Any]) -> str:
        """What the source was asked about for `game`."""
        return signal_key(self.name, game)

    def value(self, game: dict[str, Any]) -> tuple[int | None, float | None]:
        """The game's raw number for its scores field and its score in [0, 1]; (None, None) when it has none."""
        entry = self.entries.get(self.key(game))
        if entry is None:
            return None, None
        if self.name == "wikipedia":
            return entry["views_7d"], wiki_score(entry["views_7d"])
        if self.name == "hn":
            return entry["stories_28d"], hn_score(entry["stories_28d"])
        return entry.get("bucket"), tranco_score(entry.get("rank") or entry.get("bucket"))

    def health(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """The entry for popularity.json `sources` and the one for summary.json."""
        source: dict[str, Any] = {"ok": self.error is None, "fetched_at": self.fetched_at}
        summary: dict[str, Any] = {
            "ok": len(self.keys) - len(self.failed),
            "failed": len(self.failed),
            "count": len(self.keys),
            "fetched_at": self.fetched_at,
            "used": self.error is None,
            "failed_domains" if self.name == "radar" else "failed_games": self.failed,
        }
        if self.error is not None:
            source["error"] = summary["error"] = self.error
        elif self.name == "radar":
            source["domains_requested"] = len(self.keys)
            source["domains_resolved"] = sum(1 for entry in self.entries.values() if entry.get("bucket") is not None)
        return source, summary


def read_signal(name: str, data: dict[str, Any], games: list[dict[str, Any]], now: datetime) -> Signal:
    """An optional source's raw file, checked against the active games.

    Wikipedia is asked about games with a `wikipedia` article, HN about every game, Radar about every domain. The
    source is unused when its collector reported an error (e.g. no Radar token) or more than MAX_FAILED_SHARE of its
    keys failed.
    """
    keys = frozenset(signal_key(name, game) for game in games if name != "wikipedia" or game.get("wikipedia"))
    entries = data.get(ITEMS[name], {})
    failed = sorted(key for key in keys if not entries.get(key, {}).get("ok"))
    error = data.get("error")
    if error is None and len(failed) > MAX_FAILED_SHARE * len(keys):
        error = f"{name} failed for {len(failed)} of {len(keys)} (more than {MAX_FAILED_SHARE:.0%})"
    resolved = {} if error else {key: entries[key] for key in keys if key not in failed}
    return Signal(name, data.get("fetched_at", timestamp(now)), keys, failed, error, resolved)


def _scores(
    games: list[dict[str, Any]],
    tranco: dict[str, Any],
    failed: list[str],
    priors: dict[str, list[float]],
    signals: list[Signal],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Each game's scores entry and its shelf reason."""
    scores: dict[str, dict[str, Any]] = {}
    reasons: dict[str, str] = {}
    for game in games:
        game_id, domain = game["id"], game["domain"]
        prior = priors.get(game_id, [])
        fields: dict[str, int | None] = {}
        parts: list[tuple[str, float]] = []
        for source in signals:
            value, score = source.value(game)
            fields[FIELDS[source.name]] = value
            if score is not None:
                parts.append((source.name, score))
        if domain in failed:
            rank = None
            popularity = prior[0] if prior else 0.0
            reasons[game_id] = "carried_forward" if prior else "score"
        else:
            rank = mean_rank(tranco["domains"][domain]["ranks"])
            popularity = round(composite([*parts, ("tranco", tranco_score(rank))]), DIGITS)
            reasons[game_id] = "score"
        recent = prior[:TREND_WEEKS]
        trend = round(popularity - sum(recent) / len(recent), DIGITS) if len(recent) >= MIN_TREND_WEEKS else None
        scores[game_id] = {
            "popularity": popularity,
            "trend": trend,
            "tranco_rank": None if rank is None else round(rank),
            **fields,
            "history": prior,
        }
    return scores, reasons


def _shelves(
    games: list[dict[str, Any]],
    scores: dict[str, dict[str, Any]],
    reasons: dict[str, str],
    overrides: dict[str, dict[str, float]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The popular[] and trending[] shelves."""
    size = shelf_size(len(games))
    domain_of = {game["id"]: game["domain"] for game in games}
    order = weight_order(overrides)

    def tie_break(game_id: str) -> tuple[int, float, str]:
        return (*order.get(game_id, (1, 0.0)), game_id)

    by_popularity = sorted(scores, key=lambda game_id: (-scores[game_id]["popularity"], *tie_break(game_id)))
    shelf = capped(by_popularity, domain_of, size)
    popular = [
        {"id": game_id, "rank": index, "score": scores[game_id]["popularity"], "reason": reasons[game_id]}
        for index, game_id in enumerate(shelf, start=1)
    ]

    top = set(shelf[:TRENDING_EXCLUDES_TOP])
    rising = [
        game_id
        for game_id in scores
        if game_id not in top and scores[game_id]["trend"] is not None and scores[game_id]["trend"] > TREND_THRESHOLD
    ]
    rising.sort(key=lambda game_id: (-scores[game_id]["trend"], *tie_break(game_id)))
    risers = capped(rising, domain_of, size)
    picks = [(game_id, scores[game_id]["trend"], reasons[game_id]) for game_id in risers]
    if len(picks) < TRENDING_MINIMUM:
        added = {game["id"]: game["added"] for game in games}
        # A stable sort of the popularity order: newest added first, ties in popularity order.
        newest = sorted(
            (game_id for game_id in by_popularity if game_id not in top and game_id not in rising),
            key=lambda game_id: added[game_id],
            reverse=True,
        )
        fill = capped(newest, domain_of, TRENDING_MINIMUM - len(picks), taken=risers)
        picks += [(game_id, 0.0, "new") for game_id in fill]
    trending = [
        {"id": game_id, "rank": index, "score": score, "delta": scores[game_id]["trend"], "reason": reason}
        for index, (game_id, score, reason) in enumerate(picks, start=1)
    ]
    return popular, trending


def compute(
    catalog: dict[str, Any],
    raw: dict[str, dict[str, Any]],
    previous: dict[str, Any] | None,
    overrides: dict[str, dict[str, float]],
    now: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute popularity.json and summary.json.

    Args:
        catalog: The parsed games.json.
        raw: The collector's raw files by source: "tranco" always; any of "wikipedia", "hn" and "radar" makes the
            score composite (method_version 4).
        previous: Last week's popularity.json, or None.
        overrides: The checked domain_weights.json, from load_weights.
        now: The generation time (UTC).

    Returns:
        The popularity.json and summary.json documents.

    Raises:
        SourceFailedError: Tranco failed for more than 20 % of the domains.
    """
    tranco = raw["tranco"]
    games = active_games(catalog)
    domains = {game["domain"] for game in games}
    resolved, failed, unranked = tranco_health(tranco, domains)
    if len(failed) > MAX_FAILED_SHARE * len(domains) or not domains:
        msg = f"Tranco failed for {len(failed)} of {len(domains)} domains (more than {MAX_FAILED_SHARE:.0%})"
        raise SourceFailedError(msg)

    signals = [read_signal(name, raw[name], games, now) for name in OPTIONAL_SOURCES if name in raw]
    method_version = COMPOSITE_METHOD_VERSION if signals else METHOD_VERSION
    week = iso_week(now)
    scores, reasons = _scores(games, tranco, failed, prior_weeks(previous, week, method_version), signals)
    popular, trending = _shelves(games, scores, reasons, overrides)

    fetched_at = tranco["fetched_at"]
    sources = {
        "tranco": {
            "ok": True,
            "fetched_at": fetched_at,
            "domains_requested": len(domains),
            "domains_resolved": resolved,
        },
    }
    summary_sources = {
        "tranco": {
            "ok": len(domains) - len(failed),
            "failed": len(failed),
            "count": len(domains),
            "fetched_at": fetched_at,
            "failed_domains": failed,
            "unranked_domains": unranked,
        },
    }
    for source in signals:
        sources[source.name], summary_sources[source.name] = source.health()
    used = [SOURCE_ATTRIBUTION[source.name] for source in signals if source.error is None]

    popularity_doc = {
        "schema_version": 1,
        "method_version": method_version,
        "week": week,
        "generated_at": timestamp(now),
        "valid_until": timestamp(now + VALIDITY),
        "stale": False,
        "popular": popular,
        "trending": trending,
        "scores": scores,
        "sources": sources,
        "attribution": ATTRIBUTION + used,
    }
    names = {game["id"]: game.get("name", game["id"]) for game in games}
    summary = {
        "week": week,
        "generated_at": timestamp(now),
        "method_version": method_version,
        "sources": summary_sources,
        "popular": [{"id": item["id"], "name": names[item["id"]], "score": item["score"]} for item in popular],
        "trending": [
            {"id": item["id"], "name": names[item["id"]], "delta": item["delta"], "reason": item["reason"]}
            for item in trending
        ],
        "top_movers": _movers(scores, names),
    }
    return popularity_doc, summary


def _movers(scores: dict[str, dict[str, Any]], names: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    """The TOP_MOVERS biggest rises and falls by trend."""
    moved = [game_id for game_id, score in scores.items() if score["trend"]]
    up = sorted((game_id for game_id in moved if scores[game_id]["trend"] > 0), key=lambda g: (-scores[g]["trend"], g))
    down = sorted((game_id for game_id in moved if scores[game_id]["trend"] < 0), key=lambda g: (scores[g]["trend"], g))

    def mover(game_id: str) -> dict[str, Any]:
        score = scores[game_id]
        return {"id": game_id, "name": names[game_id], "popularity": score["popularity"], "trend": score["trend"]}

    return {"up": [mover(g) for g in up[:TOP_MOVERS]], "down": [mover(g) for g in down[:TOP_MOVERS]]}


def render(document: dict[str, Any]) -> str:
    """Stable JSON text: sorted keys, two-space indent, UTF-8 without escaping, final newline."""
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as file:
        file.write(text)
    temporary = Path(file.name)
    temporary.chmod(0o644)
    temporary.replace(path)


def _utc_datetime(text: str) -> datetime:
    """Parse --now; it needs an explicit offset, e.g. 2026-10-19T04:21:09Z."""
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        msg = f"{text!r} has no time zone"
        raise argparse.ArgumentTypeError(msg)
    return moment.astimezone(UTC)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        msg = f"{path}: expected a JSON object"
        raise TypeError(msg)
    return value


def main(argv: list[str] | None = None) -> int:
    """Compute the shelves from the files named on the command line.

    Args:
        argv: The command-line arguments; sys.argv by default.

    Returns:
        0 when both files were written, 1 when the sources failed, 2 on a usage error or invalid input.
    """
    parser = argparse.ArgumentParser(description="Compute the weekly popularity shelves from the collected signals.")
    parser.add_argument("--catalog", type=Path, required=True, help="data/v1/games.json")
    parser.add_argument(
        "--raw", type=Path, required=True, help="the collector's output directory (tranco.json; optional sources)"
    )
    parser.add_argument("--out", type=Path, required=True, help="where to write popularity.json")
    parser.add_argument("--summary", type=Path, required=True, help="where to write summary.json")
    parser.add_argument("--previous", type=Path, help="last week's popularity.json; --out by default")
    parser.add_argument("--weights", type=Path, help="domain_weights.json; next to --catalog by default")
    parser.add_argument("--schema", type=Path, default=SCHEMA, help="popularity.schema.json to validate against")
    parser.add_argument("--now", type=_utc_datetime, help="generation time with offset; now by default")
    args = parser.parse_args(argv)
    previous_path = args.previous or args.out
    weights_path = args.weights or args.catalog.parent / "domain_weights.json"
    try:
        catalog = _load(args.catalog)
        raw = {"tranco": _load(args.raw / "tranco.json")}
        raw |= {name: _load(path) for name in OPTIONAL_SOURCES if (path := args.raw / f"{name}.json").exists()}
        previous = _load(previous_path) if previous_path.exists() else None
        overrides = load_weights(weights_path, catalog)
        popularity, summary = compute(catalog, raw, previous, overrides, args.now or datetime.now(UTC))
        jsonschema.Draft202012Validator(_load(args.schema)).validate(popularity)
    except SourceFailedError as error:
        sys.stderr.write(f"compute: {error}; {args.out} left untouched\n")
        return 1
    except (OSError, KeyError, TypeError, ValueError, jsonschema.ValidationError) as error:
        sys.stderr.write(f"compute: {error}\n")
        return 2
    _write_atomically(args.out, render(popularity))
    _write_atomically(args.summary, render(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
