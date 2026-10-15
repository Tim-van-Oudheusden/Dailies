from datetime import date

import pytest

from dailies.core.models import Category, Difficulty, Game, Status
from dailies.core.search import matches

POKEDLE = Game(
    id="pokedle",
    name="Pokédle",
    url="https://pokedle.net/",
    category=Category.VIDEO_GAMES,
    difficulty=Difficulty.EASY,
    description="Guess the Pokémon from its type, habitat, colour and evolution stage.",
    tags=("pokemon", "classic-mode"),
    added=date(2026, 10, 15),
    status=Status.ACTIVE,
    domain="pokedle.net",
)
WORLDLE = Game(
    id="worldle",
    name="Worldle",
    url="https://worldle.teuteuf.fr/",
    category=Category.GEOGRAPHY,
    difficulty=Difficulty.EASY,
    description="Identify a country from its silhouette, with distance and direction hints.",
    tags=("teuteuf", "countries"),
    added=date(2026, 10, 15),
    status=Status.ACTIVE,
    domain="teuteuf.fr",
)


def test_an_unaccented_query_matches_an_accented_name() -> None:
    assert matches(POKEDLE, "pokedle", Category.VIDEO_GAMES.label)


def test_an_accented_query_matches_too() -> None:
    assert matches(POKEDLE, "POKÉ", Category.VIDEO_GAMES.label)


def test_the_category_label_matches_case_insensitively() -> None:
    assert matches(WORLDLE, "GEO", Category.GEOGRAPHY.label)


def test_the_category_label_is_the_one_passed_in() -> None:
    assert matches(WORLDLE, "erdkunde", "Erdkunde")
    assert not matches(WORLDLE, "geo", "Erdkunde")


def test_tags_match() -> None:
    assert matches(WORLDLE, "teuteuf", Category.GEOGRAPHY.label)
    assert matches(POKEDLE, "classic-mode", Category.VIDEO_GAMES.label)


def test_the_description_matches() -> None:
    assert matches(WORLDLE, "silhouette", Category.GEOGRAPHY.label)


def test_a_query_found_nowhere_does_not_match() -> None:
    assert not matches(WORLDLE, "pokemon", Category.GEOGRAPHY.label)


def test_surrounding_whitespace_is_ignored() -> None:
    assert matches(WORLDLE, "  world ", Category.GEOGRAPHY.label)


def test_folding_handles_compatibility_forms_and_special_cases() -> None:
    full_width_world = "".join(chr(ord(letter) + 0xFEE0) for letter in "WORLD")
    assert matches(WORLDLE, full_width_world, Category.GEOGRAPHY.label)
    assert matches(WORLDLE, "STRASSE", "Straße")


@pytest.mark.parametrize("query", ["", " ", "\t\n"])
def test_an_empty_query_matches_everything(query: str) -> None:
    assert matches(POKEDLE, query, Category.VIDEO_GAMES.label)
    assert matches(WORLDLE, query, Category.GEOGRAPHY.label)
