import time
from dataclasses import replace
from datetime import date
from itertools import pairwise
from pathlib import Path

import pytest

from dailies.core import catalog
from dailies.core.models import Category, Difficulty, Game, Status
from dailies.core.search import Change, Tier, change, matches, rank

CATALOG = catalog.parse((Path(__file__).resolve().parents[2] / "data" / "v1" / "games.json").read_bytes()).games

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


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("pok", "poké", Change.MORE_STRICT),
        ("", "w", Change.MORE_STRICT),
        ("world", "wor", Change.LESS_STRICT),
        ("world", " ", Change.LESS_STRICT),
        ("world", "globe", Change.DIFFERENT),
        ("Poké", "poke ", Change.SAME),
    ],
)
def test_a_query_change_says_whether_it_can_only_narrow_or_widen_the_matches(
    old: str, new: str, expected: Change
) -> None:
    assert change(old, new) is expected


def named(name: str, description: str = "A daily puzzle.", tags: tuple[str, ...] = ()) -> Game:
    return replace(WORLDLE, id=fold_id(name), name=name, description=description, tags=tags)


def fold_id(name: str) -> str:
    return "".join(char for char in name.lower() if char.isalnum()) or "game"


WORDLE = named("Wordle")


def test_a_query_with_one_typo_finds_the_game() -> None:
    assert rank(WORDLE, "wordel", "Words") is Tier.FUZZY
    assert matches(WORDLE, "wodrle", "Words")
    assert matches(WORDLE, "wordke", "Words")
    assert matches(named("Crosswordle"), "crosswrdle", "Words")


def test_typos_are_tolerated_after_folding_accents_and_case() -> None:
    assert rank(POKEDLE, "POKEDEL", Category.VIDEO_GAMES.label) is Tier.FUZZY
    assert rank(named("Cémantix"), "cemantx", "Words") is Tier.FUZZY


def test_a_query_too_short_for_a_typo_must_match_exactly() -> None:
    assert not matches(WORDLE, "wrdle", "Words")
    assert not matches(WORDLE, "world", "Words")


def test_a_six_to_eight_letter_query_allows_one_typo_and_a_longer_one_two() -> None:
    assert not matches(WORDLE, "wxrdel", "Words")
    assert matches(named("GeoGuessr Daily Challenge"), "geogusser", "Geography")
    assert not matches(named("GeoGuessr Daily Challenge"), "gxogusser", "Geography")


def test_each_word_of_the_query_may_start_a_word_of_the_name() -> None:
    numbers = named("Numbers & Logic")
    assert rank(numbers, "n l", "Logic") is Tier.WORD_PREFIX
    assert rank(numbers, "NUM log", "Logic") is Tier.WORD_PREFIX
    assert rank(numbers, "logic", "Trivia") is Tier.WORD_PREFIX
    assert not matches(numbers, "l n", "Trivia")
    assert not matches(numbers, "n x", "Trivia")


def test_word_starts_find_multi_word_catalog_names() -> None:
    found = [game.name for game in CATALOG if rank(game, "t m c", "") is Tier.WORD_PREFIX]
    assert found == ["The Mini Crossword"]
    assert [game.name for game in CATALOG if rank(game, "s b", "") is Tier.WORD_PREFIX] == ["Spelling Bee"]


def test_a_typo_in_one_word_of_a_multi_word_query_is_tolerated() -> None:
    assert rank(named("Minute Cryptic"), "minute crytpic", "Words") is Tier.FUZZY


def test_results_rank_prefix_then_word_prefix_then_substring_then_other_fields_then_typos() -> None:
    games = [
        named("Wodrle"),
        named("Puzzle Hub", description="Like wordle, but harder."),
        named("Antiwordle"),
        named("Daily Wordle"),
        named("Wordle"),
    ]
    ranks = {game.name: rank(game, "wordle", "Words") for game in games}
    assert ranks == {
        "Wordle": Tier.PREFIX,
        "Daily Wordle": Tier.WORD_PREFIX,
        "Antiwordle": Tier.SUBSTRING,
        "Puzzle Hub": Tier.OTHER_FIELD,
        "Wodrle": Tier.FUZZY,
    }
    assert sorted(ranks, key=ranks.__getitem__, reverse=True) == [
        "Wordle",
        "Daily Wordle",
        "Antiwordle",
        "Puzzle Hub",
        "Wodrle",
    ]


def test_a_game_that_does_not_match_has_no_rank() -> None:
    assert rank(WORLDLE, "pokemon", Category.GEOGRAPHY.label) is None


def test_an_empty_query_ranks_every_game_alike() -> None:
    assert rank(WORLDLE, " ", "Geography") == rank(POKEDLE, "", "Video Games")


def catalog_words() -> set[str]:
    return {word for game in CATALOG for word in "".join(c if c.isalnum() else " " for c in game.name.lower()).split()}


def test_typos_do_not_flood_the_results_over_the_real_catalog() -> None:
    # Each catalog word of six letters or more, with its middle letter swapped for a "q": a one-letter typo. It finds
    # the game it came from and at most a couple of near-namesakes (Wordle, Dordle, Worldle), never a crowd.
    for word in sorted(catalog_words()):
        if len(word) < 6:
            continue
        middle = len(word) // 2
        typo = word[:middle] + "q" + word[middle + 1 :]
        found = [game.name for game in CATALOG if rank(game, typo, "") is Tier.FUZZY]
        assert 1 <= len(found) <= 3, (typo, found)


def test_short_queries_never_match_by_typo_over_the_real_catalog() -> None:
    for word in catalog_words():
        for end in range(1, min(len(word), 5) + 1):
            assert all(rank(game, word[:end], "") is not Tier.FUZZY for game in CATALOG), word[:end]


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("wordl", "wordle"),  # the longer query may now match by typo
        ("wxrd", "wxrdle"),  # "wxrdle" finds Wordle by typo, "wxrd" finds nothing
        ("wordel", "worde"),  # "wordel" found Wordle by typo; widening must test the games again
        ("s n", "is n"),  # word starts: "is n" starts "Island Numbers", "s n" occurs nowhere in it
    ],
)
def test_typos_and_word_starts_make_a_longer_or_shorter_query_a_different_one(old: str, new: str) -> None:
    assert change(old, new) is Change.DIFFERENT


def test_the_counterexamples_behind_the_different_changes() -> None:
    assert matches(WORDLE, "wxrdle", "Words")
    assert not matches(WORDLE, "wxrd", "Words")
    island = named("Island Numbers")
    assert matches(island, "is n", "Trivia")
    assert not matches(island, "s n", "Trivia")


def typing(text: str) -> list[str]:
    return [text[:end] for end in range(len(text) + 1)]


def test_a_narrowing_or_widening_change_never_lies_over_the_real_catalog() -> None:
    # Type and erase catalog names, typos and word starts; whenever `change` promises the matches only shrink (or only
    # grow), check that no game outside the old matches (or inside the old matches) is affected.
    queries = ["wordel", "geogusser daily", "t m c", "the mini", "cemantx", "box office", "pokedel"]
    for query in queries:
        steps = typing(query)
        for old, new in [*pairwise(steps), *((new, old) for old, new in pairwise(steps))]:
            verdict = change(old, new)
            before = {game.id for game in CATALOG if matches(game, old, game.category.label)}
            after = {game.id for game in CATALOG if matches(game, new, game.category.label)}
            if verdict is Change.MORE_STRICT:
                assert after <= before, (old, new)
            elif verdict is Change.LESS_STRICT:
                assert after >= before, (old, new)


def three_hundred_games() -> list[Game]:
    copies = (300 + len(CATALOG) - 1) // len(CATALOG)
    games = [
        replace(game, id=f"{game.id}-{n}", name=f"{game.name} {n}" if n else game.name)
        for n in range(copies)
        for game in CATALOG
    ]
    return games[:300]


def test_ranking_three_hundred_games_takes_under_five_milliseconds_per_keystroke() -> None:
    # Best of five runs per keystroke, so a busy machine does not fail it: the first run also folds every game's texts,
    # which the app does once and then reuses.
    games = three_hundred_games()
    slowest = 0.0
    for query in typing("geogusser daily") + typing("wordel"):
        best = float("inf")
        for _ in range(5):
            start = time.perf_counter()
            ranked = [(tier, game.id) for game in games if (tier := rank(game, query, game.category.label)) is not None]
            ranked.sort()
            best = min(best, time.perf_counter() - start)
        slowest = max(slowest, best)
    assert slowest < 0.005, f"{slowest * 1000:.2f} ms"
