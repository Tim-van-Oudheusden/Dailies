import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dailies.core import popularity
from dailies.core.popularity import Shelf

PUBLISHED = Path(__file__).resolve().parents[2] / "data" / "v1" / "popularity.json"
VALID_UNTIL = datetime(2026, 10, 25, 12, tzinfo=UTC)


def ranked(*ids: str) -> list[dict]:
    return [{"id": game_id, "rank": rank, "score": 0.5} for rank, game_id in enumerate(ids, start=1)]


def popularity_bytes(**overrides: object) -> bytes:
    document = {
        "schema_version": 1,
        "method_version": 0,
        "week": "2026-W42",
        "generated_at": "2026-10-15T12:00:00Z",
        "valid_until": "2026-10-25T12:00:00Z",
        "popular": ranked("wordle", "worldle", "framed"),
        "trending": ranked("nyt-pips", "wordle"),
        "sources": {},
        "attribution": [],
    }
    document.update(overrides)
    return json.dumps(document).encode()


def test_the_published_file_parses() -> None:
    parsed = popularity.parse(PUBLISHED.read_bytes())
    assert parsed.week == "2026-W42"
    assert parsed.generated_at == datetime(2026, 10, 15, 12, tzinfo=UTC)
    assert parsed.valid_until == VALID_UNTIL
    assert parsed.popular[:3] == ("wordle", "nyt-connections", "nyt-strands")
    assert len(parsed.popular) == 11
    assert parsed.trending[0] == "nyt-pips"
    assert parsed.scores == {}


def test_shelves_are_ordered_by_rank_not_file_order() -> None:
    shuffled = [
        {"id": "c", "rank": 3, "score": 0.1},
        {"id": "a", "rank": 1, "score": 0.9},
        {"id": "b", "rank": 2, "score": 0.5},
    ]
    assert popularity.parse(popularity_bytes(popular=shuffled)).popular == ("a", "b", "c")


def test_scores_are_kept_when_present() -> None:
    scores = {"wordle": {"popularity": 0.95, "trend": None}}
    assert popularity.parse(popularity_bytes(scores=scores)).scores == scores


def test_rank_of_is_the_one_based_position_on_a_shelf() -> None:
    parsed = popularity.parse(popularity_bytes())
    assert parsed.rank_of("wordle", Shelf.POPULAR) == 1
    assert parsed.rank_of("framed", Shelf.POPULAR) == 3
    assert parsed.rank_of("wordle", Shelf.TRENDING) == 2


def test_rank_of_a_game_not_on_the_shelf_is_none() -> None:
    parsed = popularity.parse(popularity_bytes())
    assert parsed.rank_of("framed", Shelf.TRENDING) is None
    assert parsed.rank_of("nopele", Shelf.POPULAR) is None


def test_shelves_are_fresh_until_valid_until() -> None:
    parsed = popularity.parse(popularity_bytes())
    assert not parsed.is_stale(VALID_UNTIL - timedelta(seconds=1))
    assert not parsed.is_stale(VALID_UNTIL)


def test_shelves_are_stale_after_valid_until() -> None:
    parsed = popularity.parse(popularity_bytes())
    assert parsed.is_stale(VALID_UNTIL + timedelta(seconds=1))
    assert parsed.is_stale(datetime(2026, 10, 25, 14, 0, 1, tzinfo=UTC).astimezone())


def test_ids_missing_from_the_catalog_are_dropped() -> None:
    parsed = popularity.parse(
        popularity_bytes(scores={"wordle": {"popularity": 0.9}, "gone": {"popularity": 0.2}}),
    ).restricted_to({"wordle", "framed", "nyt-pips"})
    assert parsed.popular == ("wordle", "framed")
    assert parsed.trending == ("nyt-pips", "wordle")
    assert parsed.scores == {"wordle": {"popularity": 0.9}}
    assert parsed.rank_of("framed", Shelf.POPULAR) == 2
    assert parsed.week == "2026-W42"
    assert parsed.valid_until == VALID_UNTIL


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"null", id="not an object"),
        pytest.param(popularity_bytes(schema_version=2), id="schema_version 2"),
        pytest.param(popularity_bytes(week=42), id="week not a string"),
        pytest.param(popularity_bytes(valid_until="2026-10-25"), id="valid_until without a time"),
        pytest.param(popularity_bytes(valid_until="2026-10-25T12:00:00"), id="valid_until without a time zone"),
        pytest.param(popularity_bytes(generated_at=None), id="generated_at null"),
        pytest.param(popularity_bytes(popular="wordle"), id="popular not a list"),
        pytest.param(popularity_bytes(trending=["wordle"]), id="trending entry not an object"),
        pytest.param(popularity_bytes(popular=[{"id": "wordle"}]), id="entry without a rank"),
        pytest.param(popularity_bytes(popular=[{"rank": 1}]), id="entry without an id"),
        pytest.param(popularity_bytes(popular=[{"id": "wordle", "rank": "1"}]), id="rank not an integer"),
        pytest.param(popularity_bytes(scores=[]), id="scores not an object"),
    ],
)
def test_a_structurally_wrong_file_is_rejected(data: bytes) -> None:
    with pytest.raises(popularity.PopularityError):
        popularity.parse(data)


@pytest.mark.parametrize("key", ["schema_version", "week", "generated_at", "valid_until", "popular", "trending"])
def test_a_missing_key_the_app_reads_is_rejected(key: str) -> None:
    document = json.loads(popularity_bytes())
    del document[key]
    with pytest.raises(popularity.PopularityError, match=key):
        popularity.parse(json.dumps(document).encode())


@pytest.mark.parametrize("key", ["method_version", "sources", "attribution"])
def test_keys_the_app_does_not_read_may_be_missing(key: str) -> None:
    document = json.loads(popularity_bytes())
    del document[key]
    assert popularity.parse(json.dumps(document).encode()).week == "2026-W42"
