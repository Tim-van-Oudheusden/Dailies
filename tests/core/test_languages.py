from dataclasses import replace
from datetime import date

import pytest

from dailies.core.languages import matches_language, primary_subtag, system_languages
from dailies.core.models import Category, Difficulty, Game, Status

WORDLE = Game(
    id="wordle",
    name="Wordle",
    url="https://www.nytimes.com/games/wordle/",
    category=Category.WORDS,
    difficulty=Difficulty.EASY,
    description="Guess the five-letter word in six tries.",
    added=date(2026, 10, 1),
    status=Status.ACTIVE,
    domain="nytimes.com",
)
WOORDLE = replace(WORDLE, id="woordle", name="Woordle", language="nl", domain="woordle.nl")


@pytest.mark.parametrize(
    ("name", "subtag"),
    [
        ("nl_NL.UTF-8", "nl"),
        ("nl_NL", "nl"),
        ("nl", "nl"),
        ("en-GB", "en"),
        ("de_DE@euro", "de"),
        ("sr_RS.UTF-8@latin", "sr"),
        ("pt_BR.utf8", "pt"),
        ("FR", "fr"),
        ("C", None),
        ("C.UTF-8", None),
        ("POSIX", None),
        ("", None),
    ],
)
def test_the_primary_subtag_is_the_language_without_region_encoding_or_modifier(name: str, subtag: str | None) -> None:
    assert primary_subtag(name) == subtag


def test_the_system_languages_are_the_primary_subtags_of_the_locale_names() -> None:
    names = ["nl_NL.UTF-8", "nl_NL", "nl.UTF-8", "nl", "C"]
    assert system_languages(names) == {"nl"}


def test_a_language_priority_list_keeps_every_language() -> None:
    assert system_languages(["fr_FR.UTF-8", "fr", "en_GB", "en", "C"]) == {"fr", "en"}


def test_the_c_locale_alone_means_english() -> None:
    assert system_languages(["C"]) == {"en"}
    assert system_languages(["C.UTF-8", "C"]) == {"en"}


def test_every_game_matches_while_other_languages_are_shown() -> None:
    assert matches_language(WOORDLE, {"en"}, show_other=True)


def test_an_english_system_hides_a_dutch_game() -> None:
    assert matches_language(WORDLE, {"en"}, show_other=False)
    assert not matches_language(WOORDLE, {"en"}, show_other=False)


def test_a_dutch_system_hides_english_games() -> None:
    assert matches_language(WOORDLE, {"nl"}, show_other=False)
    assert not matches_language(WORDLE, {"nl"}, show_other=False)


def test_a_game_without_a_language_counts_as_english() -> None:
    assert matches_language(replace(WORDLE, language=""), {"en"}, show_other=False)
    assert not matches_language(replace(WORDLE, language=""), {"nl"}, show_other=False)


def test_a_regional_game_language_matches_on_its_primary_subtag() -> None:
    assert matches_language(replace(WORDLE, language="en-GB"), {"en"}, show_other=False)
