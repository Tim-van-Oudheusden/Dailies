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
    """Collector output by source, only Tranco; None marks a domain whose fetch failed."""
    entries = {
        domain: {"ok": False, "fetched_at": FETCHED, "status": 503, "ranks": [], "error": "HTTP 503"}
        if value is None
        else {"ok": True, "fetched_at": FETCHED, "status": 200, "ranks": value}
        for domain, value in domains.items()
    }
    failed = sum(1 for value in domains.values() if value is None)
    tranco = {
        "source": "tranco",
        "fetched_at": FETCHED,
        "health": {"ok": len(domains) - failed, "failed": failed, "count": len(domains)},
        "domains": entries,
    }
    return {"tranco": tranco}


def simple(count: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """`count` games on their own domains, game-00 the most popular."""
    games = [game(f"game-{index:02d}") for index in range(count)]
    data = raw({entry["domain"]: ranks(100 * 2**index) for index, entry in enumerate(games)})
    return catalog(*games), data


def previous(week: str, scores: dict[str, tuple[float, list[float]]], method_version: int = 2) -> dict[str, Any]:
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


def test_four_games_on_one_domain_all_score_the_full_domain_score() -> None:
    games = [game(game_id, "nytimes.com") for game_id in NYT]
    popularity, _ = compute.compute(catalog(*games), raw({"nytimes.com": ranks(1000)}), None, {}, NOW)
    expected = round(1 - (math.log10(1000) - 2) / 4.5, 4)
    for game_id in NYT:
        assert popularity["scores"][game_id]["popularity"] == expected
        assert "shared_domain_weight" not in popularity["scores"][game_id]


def test_inactive_games_do_not_share_the_domain() -> None:
    games = [game("wordle", "nytimes.com"), game("nyt-old", "nytimes.com", status="retired")]
    popularity, _ = compute.compute(catalog(*games), raw({"nytimes.com": ranks(100)}), None, {}, NOW)
    assert popularity["scores"]["wordle"]["popularity"] == 1.0
    assert "nyt-old" not in popularity["scores"]


# nytimes.com outranks everything. Its weights put wordle first, then nyt-connections and nyt-strands (a tie broken by
# id); nyt-mini-crossword and nyt-spelling-bee are unlisted. merriam-webster.com lists only octordle, so blossom and
# quordle follow it by id.
WEIGHTS = {
    "nytimes.com": {"wordle": 0.5, "nyt-strands": 0.25, "nyt-connections": 0.25},
    "merriam-webster.com": {"octordle": 1},
}
CAPPED_NYT = [*NYT, "nyt-mini-crossword"]
MW = ["blossom", "octordle", "quordle"]


def capped_catalog(added: dict[str, str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """5 nytimes.com games, 3 merriam-webster.com games, then solo-0 to solo-5 on domains of their own."""
    added = added or {}
    games = [game(game_id, "nytimes.com", added.get(game_id, "2026-10-01")) for game_id in CAPPED_NYT]
    games += [game(game_id, "merriam-webster.com", added.get(game_id, "2026-10-01")) for game_id in MW]
    games += [game(f"solo-{index}", added=added.get(f"solo-{index}", "2026-10-01")) for index in range(6)]
    data = raw(
        {
            "nytimes.com": ranks(100),
            "merriam-webster.com": ranks(200),
            **{f"solo-{index}.com": ranks(400 * 2**index) for index in range(6)},
        }
    )
    return catalog(*games), data


def risen(cat: dict[str, Any], data: dict[str, Any], rises: dict[str, float]) -> dict[str, Any]:
    """Last week's file: four steady weeks at this week's popularity minus each game's rise."""
    scores = compute.compute(cat, data, None, {}, NOW)[0]["scores"]
    before = {key: round(value["popularity"] - rises.get(key, 0), 4) for key, value in scores.items()}
    return previous("2026-W42", {key: (value, [value] * 3) for key, value in before.items()})


def test_popular_keeps_two_games_per_domain_by_weight_then_id() -> None:
    cat, data = capped_catalog()
    popularity, _ = compute.compute(cat, data, None, WEIGHTS, NOW)
    # The cap frees three nytimes.com slots: two go to merriam-webster.com (listed octordle first), one to solo-0.
    assert [(item["id"], item["rank"]) for item in popularity["popular"]] == [
        ("wordle", 1),
        ("nyt-connections", 2),
        ("octordle", 3),
        ("blossom", 4),
        ("solo-0", 5),
    ]
    assert popularity["scores"]["nyt-strands"]["popularity"] == 1.0


def test_trending_keeps_two_games_per_domain_by_weight_then_id() -> None:
    cat, data = capped_catalog()
    # Three nytimes.com games rise outside the top five; listed nyt-strands first, then the unlisted ones by id.
    rises = {"nyt-strands": 0.1, "nyt-mini-crossword": 0.1, "nyt-spelling-bee": 0.1}
    rises |= {f"solo-{index}": 0.05 for index in range(1, 6)}
    popularity, _ = compute.compute(cat, data, risen(cat, data, rises), WEIGHTS, NOW)
    assert [(item["id"], item["delta"], item["reason"]) for item in popularity["trending"]] == [
        ("nyt-strands", 0.1, "score"),
        ("nyt-mini-crossword", 0.1, "score"),
        ("solo-1", 0.05, "score"),
        ("solo-2", 0.05, "score"),
        ("solo-3", 0.05, "score"),
    ]


def test_trending_excludes_the_capped_top_five_and_caps_the_new_backfill() -> None:
    newest = {"nyt-mini-crossword": "2026-10-12", "nyt-spelling-bee": "2026-10-12", "quordle": "2026-10-10"}
    cat, data = capped_catalog(newest)
    # The top five of the capped shelf rise but cannot trend. nyt-strands, pushed off it by the cap, can; the two newest
    # nytimes.com games would then make three from one domain, so the backfill skips nyt-spelling-bee for quordle.
    rises = dict.fromkeys(["wordle", "nyt-connections", "octordle", "blossom", "solo-0", "nyt-strands"], 0.1)
    popularity, _ = compute.compute(cat, data, risen(cat, data, rises), WEIGHTS, NOW)
    assert [(item["id"], item["score"], item["reason"]) for item in popularity["trending"]] == [
        ("nyt-strands", 0.1, "score"),
        ("nyt-mini-crossword", 0.0, "new"),
        ("quordle", 0.0, "new"),
    ]


def test_committed_weights_file_is_valid_and_puts_wordle_and_connections_first() -> None:
    games = json.loads((ROOT / "data" / "v1" / "games.json").read_text(encoding="utf-8"))
    weights = compute.load_weights(ROOT / "data" / "v1" / "domain_weights.json", games)
    assert {"nytimes.com", "merriam-webster.com", "teuteuf.fr"} <= weights.keys()
    nyt = sorted(weights["nytimes.com"], key=lambda game_id: (-weights["nytimes.com"][game_id], game_id))
    assert nyt[:2] == ["wordle", "nyt-connections"]


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


@pytest.mark.parametrize("method_version", [0, 1])
def test_history_from_another_method_version_is_ignored(method_version: int) -> None:
    last = previous("2026-W42", {"game-00": (0.5, [0.5])}, method_version=method_version)
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
    assert popularity["method_version"] == 2
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
    tranco = data["tranco"]
    shuffled_raw = {"tranco": {**tranco, "domains": dict(reversed(list(tranco["domains"].items())))}}
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
    write_json(tmp_path / "raw" / "tranco.json", data["tranco"])
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


# --- method_version 2 fixture ---------------------------------------------------------------------------------------

FIXTURE = ROOT / "tests" / "scripts" / "fixtures" / "popularity"


def test_without_optional_sources_output_is_byte_identical_to_method_version_2(tmp_path: Path) -> None:
    # expected-*.json were written by the method_version 2 compute.py before the optional sources existed.
    args = ["--catalog", str(FIXTURE / "games.json"), "--raw", str(FIXTURE / "raw")]
    args += ["--previous", str(FIXTURE / "previous.json"), "--weights", str(tmp_path / "none.json")]
    args += ["--out", str(tmp_path / "popularity.json"), "--summary", str(tmp_path / "summary.json")]
    assert compute.main([*args, "--now", "2026-10-19T04:21:09Z"]) == 0
    for name in ("popularity", "summary"):
        expected = (FIXTURE / f"expected-{name}.json").read_bytes()
        assert (tmp_path / f"{name}.json").read_bytes() == expected


# --- composite score (method_version 4) ------------------------------------------------------------------------------


def wikipedia(views: dict[str, int | None], error: str | None = None) -> dict[str, Any]:
    """Collector output for Wikipedia; None marks an article whose fetch failed."""
    articles = {
        game_id: {"ok": False, "fetched_at": FETCHED, "status": 404, "article": game_id, "error": "HTTP 404"}
        if value is None
        else {"ok": True, "fetched_at": FETCHED, "status": 200, "article": game_id, "views_7d": value}
        for game_id, value in views.items()
    }
    document: dict[str, Any] = {"source": "wikipedia", "fetched_at": FETCHED, "articles": articles}
    return {**document, "error": error} if error else document


def hn(stories: dict[str, int | None]) -> dict[str, Any]:
    games = {
        game_id: {"ok": False, "fetched_at": FETCHED, "status": 503, "error": "HTTP 503"}
        if value is None
        else {"ok": True, "fetched_at": FETCHED, "status": 200, "stories_28d": value}
        for game_id, value in stories.items()
    }
    return {"source": "hn", "fetched_at": FETCHED, "games": games}


def radar(buckets: dict[str, int | None] | None = None, error: str | None = None) -> dict[str, Any]:
    domains = {
        domain: {"ok": False, "fetched_at": FETCHED, "status": 500, "error": "HTTP 500"}
        if value is None
        else {"ok": True, "fetched_at": FETCHED, "status": 200, "bucket": value, "rank": None}
        for domain, value in (buckets or {}).items()
    }
    document: dict[str, Any] = {"source": "radar", "fetched_at": FETCHED, "domains": domains}
    return {**document, "error": error} if error else document


def wiki_game(game_id: str, article: str) -> dict[str, Any]:
    return {**game(game_id), "wikipedia": article}


def test_wikipedia_and_hn_scores_follow_the_formulas() -> None:
    assert compute.wiki_score(10**6 - 1) == pytest.approx(1.0)
    assert compute.wiki_score(999) == pytest.approx(0.5)
    assert compute.wiki_score(0) == 0.0
    assert compute.wiki_score(10**9) == 1.0
    assert compute.hn_score(9) == pytest.approx(0.5)
    assert compute.hn_score(0) == 0.0
    assert compute.hn_score(10**4) == 1.0


def test_composite_weighs_tranco_wikipedia_and_hn() -> None:
    # tranco 1.0, wikipedia 1.0, hn 0.5: 0.8 * 1 + 0.15 * 1 + 0.05 * 0.5 = 0.975, above 0.825 / 0.85 without Wikipedia.
    cat = catalog(wiki_game("solo", "Solo"))
    extras = {"wikipedia": wikipedia({"solo": 10**6}), "hn": hn({"solo": 9})}
    popularity, _ = compute.compute(cat, {**raw({"solo.com": ranks(100)}), **extras}, None, {}, NOW)
    assert popularity["method_version"] == 4
    assert popularity["scores"]["solo"] == {
        "popularity": 0.975,
        "trend": None,
        "tranco_rank": 100,
        "wiki_views_7d": 10**6,
        "hn_stories_28d": 9,
        "history": [],
    }


def test_game_without_a_wikipedia_article_is_renormalised_over_the_other_sources() -> None:
    # No article: (0.8 * 1 + 0.05 * 0.5) / (0.8 + 0.05), not a 0.15 penalty.
    cat = catalog(game("solo"))
    extras = {"wikipedia": wikipedia({}), "hn": hn({"solo": 9})}
    popularity, _ = compute.compute(cat, {**raw({"solo.com": ranks(100)}), **extras}, None, {}, NOW)
    assert popularity["scores"]["solo"]["popularity"] == round(0.825 / 0.85, 4)
    assert popularity["scores"]["solo"]["wiki_views_7d"] is None


def test_wikipedia_raises_a_score_but_never_lowers_it() -> None:
    # tranco 0.5 (rank 10^4.25): 999 views (0.5) leave it, 10^6 views (1.0) give (0.8 * 0.5 + 0.15) / 0.95. Tranco 1.0:
    # 999 views would give (0.8 + 0.15 * 0.5) / 0.95, so they count for nothing and the game keeps 1.0.
    games = [wiki_game("low", "Low"), wiki_game("high", "High"), wiki_game("top", "Top")]
    data = raw({"low.com": ranks(round(10**4.25)), "high.com": ranks(round(10**4.25)), "top.com": ranks(100)})
    views = wikipedia({"low": 999, "high": 10**6, "top": 999})
    popularity, _ = compute.compute(catalog(*games), {**data, "wikipedia": views}, None, {}, NOW)
    tranco = compute.tranco_score(round(10**4.25))
    assert popularity["scores"]["low"]["popularity"] == round(tranco, 4)
    assert popularity["scores"]["high"]["popularity"] == round((0.8 * tranco + 0.15) / 0.95, 4)
    assert popularity["scores"]["top"]["popularity"] == 1.0
    assert popularity["scores"]["top"]["wiki_views_7d"] == 999


def test_wikipedia_is_a_bonus_over_the_other_sources() -> None:
    # tranco 1.0, hn 0.0: 0.8 / 0.85 without Wikipedia; 999 views (0.5) would lower that, 10^6 views raise it.
    games = [wiki_game("some", "Some"), wiki_game("many", "Many")]
    data = raw({"some.com": ranks(100), "many.com": ranks(100)})
    extras = {"wikipedia": wikipedia({"some": 999, "many": 10**6}), "hn": hn({"some": 0, "many": 0})}
    popularity, _ = compute.compute(catalog(*games), {**data, **extras}, None, {}, NOW)
    assert popularity["scores"]["some"]["popularity"] == round(0.8 / 0.85, 4)
    assert popularity["scores"]["many"]["popularity"] == round(0.95 / 1.0, 4)


def test_an_article_does_not_reorder_a_shared_domain() -> None:
    # #136: every nytimes.com game has the same Tranco score. Wordle's and Connections' articles score below it, and
    # used to drop them below The Mini, which has none, ahead of the order in domain_weights.json.
    nyt = [wiki_game("wordle", "Wordle"), wiki_game("nyt-connections", "Connections"), game("nyt-mini-crossword")]
    nyt = [{**entry, "domain": "nytimes.com"} for entry in nyt]
    solos = [game(f"solo-{index}") for index in range(3)]
    data = raw({"nytimes.com": ranks(156), **{entry["domain"]: ranks(40000) for entry in solos}})
    views = wikipedia({"wordle": 93522, "nyt-connections": 1776})
    weights = {"nytimes.com": {"wordle": 0.35, "nyt-connections": 0.2, "nyt-mini-crossword": 0.1}}
    popularity, _ = compute.compute(catalog(*nyt, *solos), {**data, "wikipedia": views}, None, weights, NOW)
    domain_score = round(compute.tranco_score(156), 4)
    assert {popularity["scores"][entry["id"]]["popularity"] for entry in nyt} == {domain_score}
    assert [item["id"] for item in popularity["popular"]][:2] == ["wordle", "nyt-connections"]


def test_failed_article_is_renormalised_and_listed_in_the_summary() -> None:
    games = [wiki_game(f"game-{index}", f"Game {index}") for index in range(6)]
    data = raw({entry["domain"]: ranks(100) for entry in games})
    views = {f"game-{index}": None if index == 0 else 10**6 for index in range(6)}
    popularity, summary = compute.compute(catalog(*games), {**data, "wikipedia": wikipedia(views)}, None, {}, NOW)
    assert popularity["scores"]["game-0"]["popularity"] == 1.0
    assert popularity["scores"]["game-1"]["popularity"] == round((0.8 + 0.15 * 1.0) / 0.95, 4)
    assert popularity["sources"]["wikipedia"] == {"ok": True, "fetched_at": FETCHED}
    assert summary["sources"]["wikipedia"]["failed"] == 1
    assert summary["sources"]["wikipedia"]["failed_games"] == ["game-0"]


def test_radar_bucket_scores_like_a_tranco_rank() -> None:
    # tranco rank 100 -> 1.0, radar bucket 10^4.25 -> 0.5: (0.8 * 1 + 0.2 * 0.5) / 1.0 = 0.9.
    cat = catalog(game("solo"))
    extras = {"radar": radar({"solo.com": 10000})}
    popularity, _ = compute.compute(cat, {**raw({"solo.com": ranks(100)}), **extras}, None, {}, NOW)
    expected = round((0.8 + 0.2 * compute.tranco_score(10000)) / 1.0, 4)
    assert popularity["scores"]["solo"]["popularity"] == expected
    assert popularity["scores"]["solo"]["radar_bucket"] == 10000
    assert popularity["sources"]["radar"] == {
        "ok": True,
        "fetched_at": FETCHED,
        "domains_requested": 1,
        "domains_resolved": 1,
    }
    assert any("CC BY-NC 4.0" in line and "non-commercial" in line for line in popularity["attribution"])


def test_radar_without_a_token_is_reported_and_left_out() -> None:
    cat = catalog(game("solo"))
    extras = {"radar": radar(error="CLOUDFLARE_RADAR_TOKEN is not set")}
    popularity, summary = compute.compute(cat, {**raw({"solo.com": ranks(1000)}), **extras}, None, {}, NOW)
    assert popularity["method_version"] == 4
    assert popularity["scores"]["solo"]["popularity"] == round(compute.tranco_score(1000), 4)
    assert popularity["scores"]["solo"]["radar_bucket"] is None
    assert popularity["sources"]["radar"] == {
        "ok": False,
        "fetched_at": FETCHED,
        "error": "CLOUDFLARE_RADAR_TOKEN is not set",
    }
    assert not any("Radar" in line for line in popularity["attribution"])
    assert summary["sources"]["radar"]["used"] is False
    jsonschema.Draft202012Validator(SCHEMA).validate(popularity)


def test_optional_source_failing_for_more_than_twenty_percent_is_left_out() -> None:
    games = [game(f"game-{index}") for index in range(5)]
    data = raw({entry["domain"]: ranks(100) for entry in games})
    stories = {f"game-{index}": None if index < 2 else 99 for index in range(5)}
    popularity, summary = compute.compute(catalog(*games), {**data, "hn": hn(stories)}, None, {}, NOW)
    assert {score["popularity"] for score in popularity["scores"].values()} == {1.0}
    assert {score["hn_stories_28d"] for score in popularity["scores"].values()} == {None}
    assert popularity["sources"]["hn"]["ok"] is False
    assert "2 of 5" in popularity["sources"]["hn"]["error"]
    assert summary["sources"]["hn"] == {
        "ok": 3,
        "failed": 2,
        "count": 5,
        "fetched_at": FETCHED,
        "used": False,
        "error": popularity["sources"]["hn"]["error"],
        "failed_games": ["game-0", "game-1"],
    }


@pytest.mark.parametrize("method_version", [2, 3])
def test_composite_ignores_history_from_an_earlier_method_version(method_version: int) -> None:
    # method_version 3 let a Wikipedia score below the others lower the game's popularity (#136).
    last = previous("2026-W42", {"game-00": (0.5, [0.5])}, method_version=method_version)
    cat, data = simple(1)
    popularity, _ = compute.compute(cat, {**data, "hn": hn({"game-00": 0})}, last, {}, NOW)
    assert popularity["scores"]["game-00"]["history"] == []
    assert popularity["scores"]["game-00"]["trend"] is None


def test_composite_keeps_method_version_4_history() -> None:
    last = previous("2026-W42", {"game-00": (0.5, [0.5])}, method_version=4)
    cat, data = simple(1)
    popularity, _ = compute.compute(cat, {**data, "hn": hn({"game-00": 0})}, last, {}, NOW)
    assert popularity["scores"]["game-00"]["history"] == [0.5, 0.5]
    assert popularity["scores"]["game-00"]["trend"] == round(0.8 / 0.85 - 0.5, 4)


def test_composite_output_validates_against_the_schema() -> None:
    solos = [f"solo-{index}" for index in range(4)]
    games = [wiki_game("wordle", "Wordle"), game("tiny"), *(game(game_id) for game_id in solos)]
    data = raw({"wordle.com": ranks(156), "tiny.com": [], **{f"{game_id}.com": ranks(40000) for game_id in solos}})
    extras = {
        "wikipedia": wikipedia({"wordle": 96000}),
        "hn": hn({"wordle": 12, "tiny": 1, **dict.fromkeys(solos, 0)}),
        "radar": radar({"wordle.com": 200, "tiny.com": None, **{f"{game_id}.com": 50000 for game_id in solos}}),
    }
    popularity, summary = compute.compute(catalog(*games), {**data, **extras}, None, {}, NOW)
    jsonschema.Draft202012Validator(SCHEMA).validate(popularity)
    assert set(popularity["sources"]) == {"tranco", "wikipedia", "hn", "radar"}
    assert summary["method_version"] == 4
    assert summary["sources"]["radar"]["failed_domains"] == ["tiny.com"]
    assert len(popularity["attribution"]) == 4


def test_main_reads_the_optional_raw_files(tmp_path: Path) -> None:
    args = cli_args(tmp_path, 0)
    write_json(tmp_path / "raw" / "hn.json", hn({f"game-{index:03d}": 0 for index in range(100)}))
    assert compute.main(args) == 0
    popularity = json.loads((tmp_path / "popularity.json").read_text(encoding="utf-8"))
    assert popularity["method_version"] == 4
    assert popularity["sources"]["hn"] == {"ok": True, "fetched_at": FETCHED}
