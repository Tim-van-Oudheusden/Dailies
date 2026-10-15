from datetime import UTC, date, datetime, timedelta

from dailies.core import sections
from dailies.core.catalog import Catalog
from dailies.core.models import Category, Difficulty, Game, Status
from dailies.core.popularity import Popularity

GENERATED = datetime(2026, 10, 12, 6, tzinfo=UTC)
VALID_UNTIL = datetime(2026, 10, 19, 6, tzinfo=UTC)


def game(game_id: str, category: Category, status: Status = Status.ACTIVE) -> Game:
    return Game(
        id=game_id,
        name=game_id.title(),
        url=f"https://{game_id}.example/",
        category=category,
        difficulty=Difficulty.EASY,
        description="A test game.",
        added=date(2026, 10, 1),
        status=status,
        domain=f"{game_id}.example",
    )


def week() -> Popularity:
    return Popularity("2026-W42", GENERATED, VALID_UNTIL, ("a",), ("b",), {})


def test_the_fixed_sections_come_first_favorites_on_top() -> None:
    assert sections.FIXED == ("favorites", "popular", "trending")


def test_only_categories_with_an_active_game_are_visible() -> None:
    catalog = Catalog(
        GENERATED,
        (
            game("a", Category.WORDS),
            game("b", Category.MUSIC, Status.BROKEN),
            game("c", Category.FOOD, Status.RETIRED),
            game("d", Category.MUSIC),
            game("e", Category.SPORTS, Status.BROKEN),
        ),
    )
    assert sections.visible_categories(catalog) == {Category.WORDS, Category.MUSIC}


def test_restore_keeps_a_visible_saved_section() -> None:
    assert sections.restore("music", {"favorites", "popular", "music"}) == "music"


def test_restore_falls_back_to_favorites_for_a_hidden_or_unknown_section() -> None:
    assert sections.restore("food", {"favorites", "popular", "music"}) == "favorites"
    assert sections.restore("", {"favorites"}) == "favorites"


def test_a_current_week_has_no_as_of_date() -> None:
    assert sections.week_as_of(week(), VALID_UNTIL) is None


def test_a_stale_week_is_dated_by_when_it_was_generated() -> None:
    assert sections.week_as_of(week(), VALID_UNTIL + timedelta(seconds=1)) == date(2026, 10, 12)
