import json
from datetime import date, datetime
from pathlib import Path

import pytest

from dailies.core import catalog
from dailies.core.models import Category, Difficulty, Game, Status

SEED = Path(__file__).resolve().parents[2] / "data" / "v1" / "games.json"


def game_record(**overrides: object) -> dict:
    record = {
        "id": "testle",
        "name": "Testle",
        "url": "https://testle.example/",
        "category": "words",
        "difficulty": "easy",
        "description": "Guess the test word in six tries, one puzzle a day.",
        "added": "2026-10-15",
        "status": "active",
        "domain": "testle.example",
    }
    record.update(overrides)
    return record


def catalog_bytes(*records: dict, **overrides: object) -> bytes:
    document = {"schema_version": 1, "generated_at": "2026-10-15T12:00:00Z", "games": list(records)}
    document.update(overrides)
    return json.dumps(document).encode()


def parse_one(**overrides: object) -> Game:
    (game,) = catalog.parse(catalog_bytes(game_record(**overrides))).games
    return game


def test_the_published_seed_parses() -> None:
    raw = json.loads(SEED.read_bytes())
    parsed = catalog.parse(SEED.read_bytes())
    # The data pipelines rewrite generated_at on every change, so compare it with the file instead of pinning it.
    assert parsed.generated_at == datetime.fromisoformat(raw["generated_at"])
    assert len(parsed.games) > 100
    worldle = parsed.get("worldle")
    assert worldle is not None
    assert worldle.name == "Worldle"
    assert worldle.url == "https://worldle.teuteuf.fr/"
    assert worldle.category is Category.GEOGRAPHY
    assert worldle.difficulty is Difficulty.EASY
    assert worldle.status is Status.ACTIVE
    assert worldle.domain == "teuteuf.fr"
    assert worldle.added == date(2026, 10, 15)
    assert "countries" in worldle.tags
    assert worldle.icon == "icons/worldle.png"


def test_an_unknown_category_is_shown_as_trivia() -> None:
    assert parse_one(category="cooking-shows").category is Category.TRIVIA


def test_an_unknown_status_is_treated_as_broken() -> None:
    assert parse_one(status="on-holiday").status is Status.BROKEN


def test_an_unknown_difficulty_is_treated_as_medium() -> None:
    assert parse_one(difficulty="fiendish").difficulty is Difficulty.MEDIUM


def test_unknown_fields_are_ignored() -> None:
    assert parse_one(sparkles=True).id == "testle"


def test_optional_fields_have_defaults() -> None:
    game = parse_one()
    assert game.tags == ()
    assert game.language == "en"
    assert game.free_no_account is None
    assert game.wikipedia is None
    assert game.source_issue is None
    assert game.icon is None


def test_optional_fields_are_read_when_present() -> None:
    game = parse_one(
        tags=["countries", "maps"],
        language="fr",
        free_no_account=False,
        wikipedia="Testle",
        source_issue=12,
        icon="icons/testle.png",
    )
    assert game.tags == ("countries", "maps")
    assert game.language == "fr"
    assert game.free_no_account is False
    assert game.wikipedia == "Testle"
    assert game.source_issue == 12
    assert game.icon == "icons/testle.png"


@pytest.mark.parametrize(
    "icon",
    [
        "../games.json",
        "icons/../../secret.png",
        "/icons/testle.png",
        "https://elsewhere.example/icons/testle.png",
        "icons/Testle.png",
        "icons/testle.svg",
        "icons/sub/testle.png",
        "icons/.png",
        "icons/testle.png\n",
        "",
    ],
)
def test_an_icon_outside_the_icons_directory_is_ignored(icon: str) -> None:
    # The app puts the path after its data URLs and names the cached file after it, so only icons/<id>.png will do.
    assert parse_one(icon=icon).icon is None


def test_games_are_hashable() -> None:
    assert len({parse_one(tags=["a"]), parse_one(tags=["a"])}) == 1


@pytest.mark.parametrize(
    "key", ["id", "name", "url", "category", "difficulty", "description", "added", "status", "domain"]
)
def test_a_game_missing_a_required_key_is_rejected(key: str) -> None:
    record = game_record()
    del record[key]
    with pytest.raises(catalog.CatalogError):
        catalog.parse(catalog_bytes(record))


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"{not json", id="invalid JSON"),
        pytest.param(b"\xff\xfe", id="not UTF-8"),
        pytest.param(b"[]", id="not an object"),
        pytest.param(catalog_bytes(schema_version=2), id="schema_version 2"),
        pytest.param(catalog_bytes(schema_version="1"), id="schema_version a string"),
        pytest.param(catalog_bytes(schema_version=True), id="schema_version a boolean"),
        pytest.param(json.dumps({"generated_at": "2026-10-15T12:00:00Z", "games": []}).encode(), id="no version"),
        pytest.param(json.dumps({"schema_version": 1, "games": []}).encode(), id="no generated_at"),
        pytest.param(json.dumps({"schema_version": 1, "generated_at": "2026-10-15T12:00:00Z"}).encode(), id="no games"),
        pytest.param(catalog_bytes(generated_at="yesterday"), id="generated_at not a date-time"),
        pytest.param(catalog_bytes(generated_at="2026-10-15T12:00:00"), id="generated_at without a time zone"),
        pytest.param(catalog_bytes(games={}), id="games not a list"),
        pytest.param(catalog_bytes("testle"), id="game not an object"),
    ],
)
def test_a_structurally_wrong_catalog_is_rejected(data: bytes) -> None:
    with pytest.raises(catalog.CatalogError):
        catalog.parse(data)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("id", 7),
        ("name", None),
        ("category", ["words"]),
        ("added", "15-10-2026"),
        ("added", 20261015),
        ("tags", "countries"),
        ("tags", ["countries", 3]),
        ("language", 1),
        ("free_no_account", "yes"),
        ("wikipedia", False),
        ("source_issue", "12"),
        ("source_issue", True),
        ("icon", 3),
    ],
)
def test_a_game_with_a_mistyped_field_is_rejected(key: str, value: object) -> None:
    with pytest.raises(catalog.CatalogError, match=key):
        catalog.parse(catalog_bytes(game_record(**{key: value})))


def test_catalog_error_is_a_value_error() -> None:
    assert issubclass(catalog.CatalogError, ValueError)


def test_get_returns_none_for_an_unknown_id() -> None:
    assert catalog.parse(catalog_bytes(game_record())).get("nopele") is None


def test_broken_and_retired_games_are_kept_but_not_active() -> None:
    parsed = catalog.parse(
        catalog_bytes(
            game_record(id="alive"),
            game_record(id="broken", status="broken"),
            game_record(id="gone", status="retired"),
            game_record(id="mystery", status="paused"),
        )
    )
    assert [game.id for game in parsed.games] == ["alive", "broken", "gone", "mystery"]
    assert [game.id for game in parsed.active()] == ["alive"]
    retired = parsed.get("gone")
    assert retired is not None
    assert retired.status is Status.RETIRED


def test_a_later_generated_at_is_newer() -> None:
    older = catalog.parse(catalog_bytes(generated_at="2026-10-15T12:00:00Z"))
    newer = catalog.parse(catalog_bytes(generated_at="2026-10-15T14:00:00+01:00"))
    assert catalog.is_newer(newer, older)
    assert not catalog.is_newer(older, newer)
    assert not catalog.is_newer(older, older)
