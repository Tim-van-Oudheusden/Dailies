#!/usr/bin/env python3
"""Compute the weekly Popular and Trending shelves from the collected Tranco ranks (method_version 1).

Every number is deterministic: the same catalog, raw ranks, previous file, override file and --now give a
byte-identical popularity.json and summary.json. The method (docs/proposals/mvp-first.md section 8):

- tranco_score = clamp(1 - (log10(rank) - 2) / 4.5, 0, 1) on the mean of the last 7 daily ranks; no rank scores 0.
- popularity = tranco_score while the other sources are off. Games sharing a registrable domain split its score
  equally, unless data/v1/domain_weights.json ({"nytimes.com": {"wordle": 0.4, ...}}) gives their weights.
- A domain whose fetch failed keeps the game's popularity of last week (reason "carried_forward"), or 0 without one.
- trend = popularity - mean of the previous 4 weeks' popularity; null until two prior weeks exist. The history comes
  from the previous popularity.json (up to 8 weeks per game) when its method_version matches.
- N = max(5, min(12, 10 % of active games)). Popular: top N by popularity, ties by id. Trending: trend > 0.02 outside
  the top 5 popular, by trend, top N; with fewer than 3, the newest added games fill it to 3 with reason "new".
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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jsonschema

METHOD_VERSION = 1
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
MAX_FAILED_SHARE = 0.2
TOP_MOVERS = 5
DIGITS = 4
WEIGHT_TOLERANCE = 1e-9
ATTRIBUTION = [
    "Tranco (https://tranco-list.eu): domain ranks, used with attribution; licence not stated by its maintainers",
]


class WeightsError(ValueError):
    """data/v1/domain_weights.json is malformed."""


class SourceFailedError(RuntimeError):
    """Too many domains failed to fetch; the shelves would be wrong."""


def tranco_score(rank: float | None) -> float:
    """1.0 at rank 100 and above, 0.0 at rank 10^6.5 and below, log-linear between; 0.0 without a rank."""
    if rank is None:
        return 0.0
    return min(1.0, max(0.0, 1 - (math.log10(rank) - 2) / 4.5))


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
    """Read and check the shared-domain override file; no file means no overrides.

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


def shares(games: list[dict[str, Any]], overrides: dict[str, dict[str, float]]) -> dict[str, float | None]:
    """Each game's share of its domain's score: None for a domain of its own, 1/n or the override when shared."""
    by_domain: dict[str, list[str]] = {}
    for game in games:
        by_domain.setdefault(game["domain"], []).append(game["id"])
    result: dict[str, float | None] = {}
    for domain, ids in by_domain.items():
        override = overrides.get(domain)
        for game_id in ids:
            if override is not None:
                result[game_id] = float(override.get(game_id, 0.0))
            else:
                result[game_id] = 1 / len(ids) if len(ids) > 1 else None
    return result


def prior_weeks(previous: dict[str, Any] | None, week: str) -> dict[str, list[float]]:
    """Each game's popularity in the weeks before this one, newest first, at most HISTORY_WEEKS.

    A rerun in the same week replaces that week instead of counting it twice; history computed with another
    method_version is not comparable and is dropped.
    """
    if not previous or previous.get("method_version") != METHOD_VERSION:
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


def compute(
    catalog: dict[str, Any],
    raw: dict[str, Any],
    previous: dict[str, Any] | None,
    overrides: dict[str, dict[str, float]],
    now: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute popularity.json and summary.json.

    Args:
        catalog: The parsed games.json.
        raw: The collector's raw/tranco.json.
        previous: Last week's popularity.json, or None.
        overrides: The checked domain_weights.json, from load_weights.
        now: The generation time (UTC).

    Returns:
        The popularity.json and summary.json documents.

    Raises:
        SourceFailedError: Tranco failed for more than 20 % of the domains.
    """
    games = active_games(catalog)
    domains = {game["domain"] for game in games}
    resolved, failed, unranked = tranco_health(raw, domains)
    if len(failed) > MAX_FAILED_SHARE * len(domains) or not domains:
        msg = f"Tranco failed for {len(failed)} of {len(domains)} domains (more than {MAX_FAILED_SHARE:.0%})"
        raise SourceFailedError(msg)

    week = iso_week(now)
    priors = prior_weeks(previous, week)
    weights = shares(games, overrides)
    scores: dict[str, dict[str, Any]] = {}
    reasons: dict[str, str] = {}
    for game in games:
        game_id, domain = game["id"], game["domain"]
        prior = priors.get(game_id, [])
        if domain in failed:
            rank = None
            popularity = prior[0] if prior else 0.0
            reasons[game_id] = "carried_forward" if prior else "score"
        else:
            rank = mean_rank(raw["domains"][domain]["ranks"])
            weight = weights[game_id]
            popularity = round(tranco_score(rank) * (1.0 if weight is None else weight), DIGITS)
            reasons[game_id] = "score"
        recent = prior[:TREND_WEEKS]
        trend = round(popularity - sum(recent) / len(recent), DIGITS) if len(recent) >= MIN_TREND_WEEKS else None
        scores[game_id] = {
            "popularity": popularity,
            "trend": trend,
            "tranco_rank": None if rank is None else round(rank),
            "history": prior,
        }
        if weights[game_id] is not None:
            scores[game_id]["shared_domain_weight"] = round(weights[game_id], DIGITS)

    size = shelf_size(len(games))
    by_popularity = sorted(scores, key=lambda game_id: (-scores[game_id]["popularity"], game_id))
    popular = [
        {"id": game_id, "rank": index, "score": scores[game_id]["popularity"], "reason": reasons[game_id]}
        for index, game_id in enumerate(by_popularity[:size], start=1)
    ]

    top = set(by_popularity[:TRENDING_EXCLUDES_TOP])
    rising = [
        game_id
        for game_id in scores
        if game_id not in top and scores[game_id]["trend"] is not None and scores[game_id]["trend"] > TREND_THRESHOLD
    ]
    rising.sort(key=lambda game_id: (-scores[game_id]["trend"], game_id))
    picks = [(game_id, scores[game_id]["trend"], "score") for game_id in rising[:size]]
    if len(picks) < TRENDING_MINIMUM:
        added = {game["id"]: game["added"] for game in games}
        # A stable sort of the popularity order: newest added first, ties by popularity, then id.
        newest = sorted(
            (game_id for game_id in by_popularity if game_id not in top and game_id not in rising),
            key=lambda game_id: added[game_id],
            reverse=True,
        )
        picks += [(game_id, 0.0, "new") for game_id in newest[: TRENDING_MINIMUM - len(picks)]]
    trending = [
        {"id": game_id, "rank": index, "score": score, "delta": scores[game_id]["trend"], "reason": reason}
        for index, (game_id, score, reason) in enumerate(picks, start=1)
    ]

    fetched_at = raw["fetched_at"]
    popularity_doc = {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "week": week,
        "generated_at": timestamp(now),
        "valid_until": timestamp(now + VALIDITY),
        "stale": False,
        "popular": popular,
        "trending": trending,
        "scores": scores,
        "sources": {
            "tranco": {
                "ok": True,
                "fetched_at": fetched_at,
                "domains_requested": len(domains),
                "domains_resolved": resolved,
            },
        },
        "attribution": ATTRIBUTION,
    }
    names = {game["id"]: game.get("name", game["id"]) for game in games}
    summary = {
        "week": week,
        "generated_at": timestamp(now),
        "method_version": METHOD_VERSION,
        "sources": {
            "tranco": {
                "ok": len(domains) - len(failed),
                "failed": len(failed),
                "count": len(domains),
                "fetched_at": fetched_at,
                "failed_domains": failed,
                "unranked_domains": unranked,
            },
        },
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
    parser = argparse.ArgumentParser(description="Compute the weekly popularity shelves from collected Tranco ranks.")
    parser.add_argument("--catalog", type=Path, required=True, help="data/v1/games.json")
    parser.add_argument("--raw", type=Path, required=True, help="the collector's output directory (tranco.json)")
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
        raw = _load(args.raw / "tranco.json")
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
