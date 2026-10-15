import importlib.util
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "popularity" / "compute.py"
SCHEMA = json.loads((ROOT / "data" / "v1" / "schema" / "popularity.schema.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 10, 19, 4, 21, 9, tzinfo=UTC)
FETCHED = "2026-10-19T04:18:00Z"
NYT = ["nyt-connections", "nyt-spelling-bee", "nyt-strands", "wordle"]


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("compute", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compute = load_script()


def game(game_id: str, domain: str | None = None, added: str = "2026-10-01", status: str = "active") -> dict[str, Any]:
    return {
        "id": game_id,
        "name": game_id.title(),
        "domain": domain or f"{game_id}.com",
        "added": added,
        "status": status,
    }


def catalog(*games: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "generated_at": "2026-10-15T00:00:00Z", "games": list(games)}


def ranks(*values: int) -> list[dict[str, Any]]:
    """Daily ranks, newest first, ending on 2026-10-18."""
    return [{"date": f"2026-10-{18 - day:02d}", "rank": value} for day, value in enumerate(values)]


def raw(domains: dict[str, list[dict[str, Any]] | None]) -> dict[str, Any]:
    """Collector output; None marks a domain whose fetch failed."""
    entries = {
        domain: {"ok": False, "fetched_at": FETCHED, "status": 503, "ranks": [], "error": "HTTP 503"}
        if value is None
        else {"ok": True, "fetched_at": FETCHED, "status": 200, "ranks": value}
        for domain, value in domains.items()
    }
    failed = sum(1 for value in domains.values() if value is None)
    return {
        "source": "tranco",
        "fetched_at": FETCHED,
        "health": {"ok": len(domains) - failed, "failed": failed, "count": len(domains)},
        "domains": entries,
    }


def simple(count: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """`count` games on their own domains, game-00 the most popular."""
    games = [game(f"game-{index:02d}") for index in range(count)]
    data = raw({entry["domain"]: ranks(100 * 2**index) for index, entry in enumerate(games)})
    return catalog(*games), data


def previous(week: str, scores: dict[str, tuple[float, list[float]]], method_version: int = 1) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "method_version": method_version,
        "week": week,
        "scores": {key: {"popularity": value, "history": history} for key, (value, history) in scores.items()},
    }


# --- score formula --------------------------------------------------------------------------------------------------


def test_score_is_one_at_rank_100() -> None:
    assert compute.tranco_score(100) == 1.0


def test_score_is_zero_at_rank_ten_to_the_six_and_a_half() -> None:
    assert compute.tranco_score(10**6.5) == pytest.approx(0.0, abs=1e-12)


def test_score_is_clamped_to_zero_and_one() -> None:
    assert compute.tranco_score(1) == 1.0
    assert compute.tranco_score(10**8) == 0.0


def test_score_is_zero_without_a_rank() -> None:
    assert compute.tranco_score(None) == 0.0


def test_score_uses_the_mean_of_the_last_seven_daily_ranks() -> None:
    # The seven newest days average 1,000; the older days would drag the mean far up.
    daily = ranks(400, 1600, 1000, 1000, 1000, 1000, 1000, 10**6, 10**6)
    assert compute.mean_rank(list(reversed(daily))) == 1000
    assert compute.mean_rank([]) is None


def test_game_score_follows_the_formula() -> None:
    data = raw({"solo.com": ranks(*[1000] * 7)})
    popularity, _ = compute.compute(catalog(game("solo")), data, None, {}, NOW)
    expected = round(1 - (math.log10(1000) - 2) / 4.5, 4)
    assert popularity["scores"]["solo"]["popularity"] == expected
    assert popularity["scores"]["solo"]["tranco_rank"] == 1000


def test_unranked_domain_scores_zero() -> None:
    data = raw({"solo.com": [], "big.com": ranks(100)})
    popularity, _ = compute.compute(catalog(game("solo"), game("big")), data, None, {}, NOW)
    assert popularity["scores"]["solo"]["popularity"] == 0.0
    assert popularity["scores"]["solo"]["tranco_rank"] is None
    assert popularity["popular"][-1] == {"id": "solo", "rank": 2, "score": 0.0, "reason": "score"}


# --- shared domains -------------------------------------------------------------------------------------------------


def test_equal_split_across_four_nyt_games() -> None:
    games = [game(game_id, "nytimes.com") for game_id in NYT]
    popularity, _ = compute.compute(catalog(*games), raw({"nytimes.com": ranks(100)}), None, {}, NOW)
    for game_id in NYT:
        assert popularity["scores"][game_id]["popularity"] == 0.25
        assert popularity["scores"][game_id]["shared_domain_weight"] == 0.25


def test_unshared_domain_has_no_weight() -> None:
    popularity, _ = compute.compute(catalog(game("solo")), raw({"solo.com": ranks(100)}), None, {}, NOW)
    assert "shared_domain_weight" not in popularity["scores"]["solo"]


def test_inactive_games_do_not_share_the_domain() -> None:
    games = [game("wordle", "nytimes.com"), game("nyt-old", "nytimes.com", status="retired")]
    popularity, _ = compute.compute(catalog(*games), raw({"nytimes.com": ranks(100)}), None, {}, NOW)
    assert popularity["scores"]["wordle"]["popularity"] == 1.0
    assert "nyt-old" not in popularity["scores"]


def test_override_file_is_respected(tmp_path: Path) -> None:
    games = [game(game_id, "nytimes.com") for game_id in NYT]
    weights = {"nytimes.com": {"wordle": 0.4, "nyt-connections": 0.3, "nyt-strands": 0.2, "nyt-spelling-bee": 0.1}}
    path = tmp_path / "domain_weights.json"
    path.write_text(json.dumps(weights), encoding="utf-8")
    overrides = compute.load_weights(path, catalog(*games))
    popularity, _ = compute.compute(catalog(*games), raw({"nytimes.com": ranks(100)}), None, overrides, NOW)
    assert [item["id"] for item in popularity["popular"]] == [
        "wordle",
        "nyt-connections",
        "nyt-strands",
        "nyt-spelling-bee",
    ]
    assert popularity["scores"]["wordle"]["popularity"] == 0.4
    assert popularity["scores"]["nyt-spelling-bee"]["shared_domain_weight"] == 0.1


def test_missing_override_file_means_no_overrides(tmp_path: Path) -> None:
    assert compute.load_weights(tmp_path / "domain_weights.json", catalog(game("wordle", "nytimes.com"))) == {}


@pytest.mark.parametrize(
    ("weights", "message"),
    [
        ({"nytimes.com": {"wordle": 0.5, "nyt-strands": 0.4}}, "sum to 1"),
        ({"nytimes.com": {"wordle": 0.5, "no-such-game": 0.5}}, "unknown game"),
        ({"nytimes.com": {"wordle": 0.5, "solo": 0.5}}, "not on nytimes.com"),
        ({"nytimes.com": {"wordle": 1.5, "nyt-strands": -0.5}}, "between 0 and 1"),
        ({"nytimes.com": {"wordle": "1"}}, "between 0 and 1"),
        ({"nytimes.com": ["wordle"]}, "object"),
        (["nytimes.com"], "object"),
    ],
)
def test_invalid_override_file_is_rejected(tmp_path: Path, weights: object, message: str) -> None:
    games = [game("wordle", "nytimes.com"), game("nyt-strands", "nytimes.com"), game("solo")]
    path = tmp_path / "domain_weights.json"
    path.write_text(json.dumps(weights), encoding="utf-8")
    with pytest.raises(compute.WeightsError, match=message):
        compute.load_weights(path, catalog(*games))


# --- trend ----------------------------------------------------------------------------------------------------------


def test_trend_is_null_without_history() -> None:
    popularity, _ = compute.compute(*simple(1), None, {}, NOW)
    assert popularity["scores"]["game-00"]["trend"] is None
    assert popularity["scores"]["game-00"]["history"] == []


def test_trend_is_null_with_one_prior_week() -> None:
    last = previous("2026-W42", {"game-00": (0.5, [])})
    popularity, _ = compute.compute(*simple(1), last, {}, NOW)
    assert popularity["scores"]["game-00"]["trend"] is None
    assert popularity["scores"]["game-00"]["history"] == [0.5]


def test_trend_is_popularity_minus_the_mean_of_four_prior_weeks() -> None:
    # Six prior weeks: the trend uses the newest four (0.5, 0.6, 0.7, 0.8 -> 0.65), history keeps all six.
    last = previous("2026-W42", {"game-00": (0.5, [0.6, 0.7, 0.8, 0.1, 0.1])})
    popularity, _ = compute.compute(*simple(1), last, {}, NOW)
    assert popularity["scores"]["game-00"]["trend"] == 0.35
    assert popularity["scores"]["game-00"]["history"] == [0.5, 0.6, 0.7, 0.8, 0.1, 0.1]


def test_history_keeps_at_most_eight_weeks() -> None:
    last = previous("2026-W42", {"game-00": (0.9, [0.8] * 8)})
    popularity, _ = compute.compute(*simple(1), last, {}, NOW)
    assert popularity["scores"]["game-00"]["history"] == [0.9] + [0.8] * 7


def test_rerun_in_the_same_week_does_not_count_that_week_twice() -> None:
    last = previous("2026-W43", {"game-00": (0.2, [0.5, 0.5])})
    popularity, _ = compute.compute(*simple(1), last, {}, NOW)
    assert popularity["scores"]["game-00"]["history"] == [0.5, 0.5]
    assert popularity["scores"]["game-00"]["trend"] == 0.5


def test_history_from_another_method_version_is_ignored() -> None:
    last = previous("2026-W42", {"game-00": (0.5, [0.5])}, method_version=0)
    popularity, _ = compute.compute(*simple(1), last, {}, NOW)
    assert popularity["scores"]["game-00"]["history"] == []


# --- shelves --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("active", "size"), [(3, 3), (20, 5), (59, 5), (60, 6), (114, 11), (300, 12)])
def test_shelf_size(active: int, size: int) -> None:
    assert compute.shelf_size(active) == min(size, active)


def test_popular_is_sorted_by_score_then_id() -> None:
    games = [game("b-game"), game("a-game"), game("c-game")]
    data = raw({"b-game.com": ranks(1000), "a-game.com": ranks(1000), "c-game.com": ranks(100)})
    popularity, _ = compute.compute(catalog(*games), data, None, {}, NOW)
    assert [(item["id"], item["rank"]) for item in popularity["popular"]] == [
        ("c-game", 1),
        ("a-game", 2),
        ("b-game", 3),
    ]


def test_trending_excludes_the_top_five_popular() -> None:
    cat, data = simple(20)
    # Every game rose by 0.05 over four steady weeks; only games outside the top 5 may trend.
    scores = compute.compute(cat, data, None, {}, NOW)[0]["scores"]
    last = previous(
        "2026-W42",
        {key: (value["popularity"] - 0.05, [value["popularity"] - 0.05] * 3) for key, value in scores.items()},
    )
    popularity, _ = compute.compute(cat, data, last, {}, NOW)
    top_five = {item["id"] for item in popularity["popular"][:5]}
    trending = popularity["trending"]
    assert len(trending) == 5
    assert top_five.isdisjoint(item["id"] for item in trending)
    assert all(item["reason"] == "score" and item["delta"] == 0.05 for item in trending)
    assert [item["id"] for item in trending] == ["game-05", "game-06", "game-07", "game-08", "game-09"]


def test_trending_needs_a_rise_above_the_threshold() -> None:
    cat, data = simple(20)
    scores = compute.compute(cat, data, None, {}, NOW)[0]["scores"]
    rises = {"game-10": 0.3, "game-11": 0.02, "game-12": 0.1, "game-13": 0.021, "game-14": 0.2}
    last = previous(
        "2026-W42",
        {
            key: (value["popularity"] - rises.get(key, 0), [value["popularity"] - rises.get(key, 0)])
            for key, value in scores.items()
        },
    )
    popularity, _ = compute.compute(cat, data, last, {}, NOW)
    assert [(item["id"], item["score"], item["delta"]) for item in popularity["trending"]] == [
        ("game-10", 0.3, 0.3),
        ("game-14", 0.2, 0.2),
        ("game-12", 0.1, 0.1),
        ("game-13", 0.021, 0.021),
    ]


def test_trending_is_backfilled_with_the_newest_games() -> None:
    games = [game(f"game-{index:02d}", added=f"2026-10-{index + 1:02d}") for index in range(20)]
    data = raw({entry["domain"]: ranks(100 * 2**index) for index, entry in enumerate(games)})
    cat = catalog(*games)
    scores = compute.compute(cat, data, None, {}, NOW)[0]["scores"]
    last = previous(
        "2026-W42",
        {
            key: (value["popularity"] - (0.1 if key == "game-07" else 0), [value["popularity"]])
            for key, value in scores.items()
        },
    )
    popularity, _ = compute.compute(cat, data, last, {}, NOW)
    assert [(item["id"], item["reason"]) for item in popularity["trending"]] == [
        ("game-07", "score"),
        ("game-19", "new"),
        ("game-18", "new"),
    ]
    assert popularity["trending"][1]["score"] == 0.0
    scores = [item["score"] for item in popularity["trending"]]
    assert scores == sorted(scores, reverse=True)


def test_trending_is_never_empty() -> None:
    popularity, _ = compute.compute(*simple(20), None, {}, NOW)
    assert [(item["id"], item["reason"], item["delta"]) for item in popularity["trending"]] == [
        ("game-05", "new", None),
        ("game-06", "new", None),
        ("game-07", "new", None),
    ]


def test_backfill_skips_the_top_five_popular() -> None:
    games = [game(f"game-{index:02d}", added="2026-10-01" if index > 1 else "2026-10-10") for index in range(8)]
    data = raw({entry["domain"]: ranks(100 * 2**index) for index, entry in enumerate(games)})
    popularity, _ = compute.compute(catalog(*games), data, None, {}, NOW)
    assert [item["id"] for item in popularity["trending"]] == ["game-05", "game-06", "game-07"]


# --- fail closed ----------------------------------------------------------------------------------------------------


def hundred_domains(failed: int) -> tuple[dict[str, Any], dict[str, Any]]:
    games = [game(f"game-{index:03d}") for index in range(100)]
    data = raw({entry["domain"]: None if index < failed else ranks(1000) for index, entry in enumerate(games)})
    return catalog(*games), data


def test_twenty_percent_failed_domains_still_computes() -> None:
    popularity, summary = compute.compute(*hundred_domains(20), None, {}, NOW)
    assert popularity["sources"]["tranco"] == {
        "ok": True,
        "fetched_at": FETCHED,
        "domains_requested": 100,
        "domains_resolved": 80,
    }
    assert summary["sources"]["tranco"]["failed"] == 20


def test_twenty_one_percent_failed_domains_fails_closed() -> None:
    with pytest.raises(compute.SourceFailedError, match="21 of 100"):
        compute.compute(*hundred_domains(21), None, {}, NOW)


def test_domain_missing_from_the_raw_data_counts_as_failed() -> None:
    games = [game(f"game-{index}") for index in range(5)]
    data = raw({entry["domain"]: ranks(1000) for entry in games[:3]})
    with pytest.raises(compute.SourceFailedError, match="2 of 5"):
        compute.compute(catalog(*games), data, None, {}, NOW)


def test_failed_domain_carries_last_week_forward() -> None:
    games = [game(f"game-{index}") for index in range(10)]
    data = raw({entry["domain"]: None if index == 9 else ranks(10**6) for index, entry in enumerate(games)})
    last = previous("2026-W42", {"game-9": (0.9, [])})
    popularity, _ = compute.compute(catalog(*games), data, last, {}, NOW)
    assert popularity["popular"][0] == {"id": "game-9", "rank": 1, "score": 0.9, "reason": "carried_forward"}
    assert popularity["scores"]["game-9"]["tranco_rank"] is None
    assert popularity["scores"]["game-9"]["history"] == [0.9]


def test_failed_domain_without_history_scores_zero() -> None:
    games = [game(f"game-{index}") for index in range(10)]
    data = raw({entry["domain"]: None if index == 0 else ranks(1000) for index, entry in enumerate(games)})
    popularity, _ = compute.compute(catalog(*games), data, None, {}, NOW)
    assert popularity["scores"]["game-0"]["popularity"] == 0.0
    assert popularity["popular"][-1]["reason"] == "score"


# --- output ---------------------------------------------------------------------------------------------------------


def test_output_validates_against_the_schema() -> None:
    games = [game(game_id, "nytimes.com") for game_id in NYT] + [game(f"game-{index:02d}") for index in range(30)]
    data = raw(
        {"nytimes.com": ranks(156), **{f"game-{index:02d}.com": ranks(1000 * (index + 1)) for index in range(30)}}
    )
    popularity, _ = compute.compute(catalog(*games), data, previous("2026-W42", {"wordle": (0.2, [0.1])}), {}, NOW)
    jsonschema.Draft202012Validator(SCHEMA).validate(popularity)


def test_output_header() -> None:
    popularity, _ = compute.compute(*simple(6), None, {}, NOW)
    assert popularity["schema_version"] == 1
    assert popularity["method_version"] == 1
    assert popularity["week"] == "2026-W43"
    assert popularity["generated_at"] == "2026-10-19T04:21:09Z"
    assert popularity["valid_until"] == "2026-10-29T04:21:09Z"
    assert popularity["stale"] is False
    assert any("Tranco" in line for line in popularity["attribution"])


def test_summary_lists_top_movers() -> None:
    cat, data = simple(10)
    scores = compute.compute(cat, data, None, {}, NOW)[0]["scores"]
    changes = {"game-03": 0.1, "game-04": -0.2}
    last = previous(
        "2026-W42",
        {
            key: (value["popularity"] - changes.get(key, 0), [value["popularity"] - changes.get(key, 0)])
            for key, value in scores.items()
        },
    )
    _, summary = compute.compute(cat, data, last, {}, NOW)
    assert [mover["id"] for mover in summary["top_movers"]["up"]] == ["game-03"]
    assert [mover["id"] for mover in summary["top_movers"]["down"]] == ["game-04"]
    assert summary["top_movers"]["up"][0]["name"] == "Game-03"
    assert summary["popular"][0] == {"id": "game-00", "name": "Game-00", "score": 1.0}


def test_same_input_gives_byte_identical_output() -> None:
    cat, data = simple(30)
    first = [compute.render(document) for document in compute.compute(cat, data, None, {}, NOW)]
    shuffled = catalog(*reversed(cat["games"]))
    shuffled_raw = {**data, "domains": dict(reversed(list(data["domains"].items())))}
    second = [compute.render(document) for document in compute.compute(shuffled, shuffled_raw, None, {}, NOW)]
    assert first == second
    assert first[0].endswith("}\n")


# --- command line ---------------------------------------------------------------------------------------------------


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def cli_args(tmp_path: Path, failed: int) -> list[str]:
    cat, data = hundred_domains(failed)
    (tmp_path / "raw").mkdir()
    write_json(tmp_path / "raw" / "tranco.json", data)
    return [
        "--catalog",
        str(write_json(tmp_path / "games.json", cat)),
        "--raw",
        str(tmp_path / "raw"),
        "--out",
        str(tmp_path / "popularity.json"),
        "--summary",
        str(tmp_path / "summary.json"),
        "--weights",
        str(tmp_path / "domain_weights.json"),
        "--now",
        "2026-10-19T04:21:09Z",
    ]


def test_main_writes_both_files(tmp_path: Path) -> None:
    assert compute.main(cli_args(tmp_path, 0)) == 0
    popularity = json.loads((tmp_path / "popularity.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(popularity)
    assert popularity["week"] == "2026-W43"
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["week"] == "2026-W43"


def test_main_reads_last_weeks_file_for_history(tmp_path: Path) -> None:
    args = cli_args(tmp_path, 0)
    write_json(tmp_path / "popularity.json", previous("2026-W42", {"game-000": (0.1, [0.1])}))
    assert compute.main(args) == 0
    popularity = json.loads((tmp_path / "popularity.json").read_text(encoding="utf-8"))
    assert popularity["scores"]["game-000"]["history"] == [0.1, 0.1]


def test_main_fails_closed_and_leaves_the_old_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = cli_args(tmp_path, 21)
    old = '{"old": true}\n'
    (tmp_path / "popularity.json").write_text(old, encoding="utf-8")
    assert compute.main(args) == 1
    assert (tmp_path / "popularity.json").read_text(encoding="utf-8") == old
    assert not (tmp_path / "summary.json").exists()
    assert "21 of 100" in capsys.readouterr().err


def test_main_rejects_an_invalid_override_file(tmp_path: Path) -> None:
    args = cli_args(tmp_path, 0)
    write_json(tmp_path / "domain_weights.json", {"game-000.com": {"game-000": 0.5}})
    assert compute.main(args) == 2
    assert not (tmp_path / "popularity.json").exists()


def test_main_rejects_a_bad_timestamp(tmp_path: Path) -> None:
    args = cli_args(tmp_path, 0)
    args[-1] = "2026-10-19T04:21:09"
    with pytest.raises(SystemExit):
        compute.main(args)
