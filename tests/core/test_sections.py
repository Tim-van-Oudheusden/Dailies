from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

from dailies.core import sections
from dailies.core.catalog import Catalog
from dailies.core.models import Category, Difficulty, Game, Status
from dailies.core.popularity import Popularity
from dailies.core.reorder import Move

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


def test_categories_whose_games_are_all_in_other_languages_are_hidden_while_those_are_not_shown() -> None:
    catalog = Catalog(
        GENERATED,
        (
            replace(game("woordle", Category.WORDS), language="nl"),
            game("heardle", Category.MUSIC),
            replace(game("worldle", Category.GEOGRAPHY), language="fr"),
            game("globle", Category.GEOGRAPHY),
        ),
    )
    assert sections.visible_categories(catalog, system_languages={"en"}, show_other=False) == {
        Category.MUSIC,
        Category.GEOGRAPHY,
    }
    assert sections.visible_categories(catalog, system_languages={"nl"}, show_other=False) == {Category.WORDS}
    assert sections.visible_categories(catalog, system_languages={"nl"}, show_other=True) == {
        Category.WORDS,
        Category.MUSIC,
        Category.GEOGRAPHY,
    }


def test_restore_keeps_a_visible_saved_section() -> None:
    assert sections.restore("music", {"favorites", "popular", "music"}) == "music"


def test_restore_falls_back_to_favorites_for_a_hidden_or_unknown_section() -> None:
    assert sections.restore("food", {"favorites", "popular", "music"}) == "favorites"
    assert sections.restore("", {"favorites"}) == "favorites"


def test_a_current_week_has_no_as_of_date() -> None:
    assert sections.week_as_of(week(), VALID_UNTIL) is None


def test_a_stale_week_is_dated_by_when_it_was_generated() -> None:
    assert sections.week_as_of(week(), VALID_UNTIL + timedelta(seconds=1)) == date(2026, 10, 12)


def named(game_id: str, name: str, difficulty: Difficulty = Difficulty.EASY) -> Game:
    return replace(game(game_id, Category.WORDS), name=name, difficulty=difficulty)


def listing(game_: Game, *, favorite: bool = False, popular: int = 0, trending: int = 0) -> sections.Listing:
    return sections.Listing(game=game_, favorite=favorite, popular_rank=popular, trending_rank=trending)


def test_favorites_hold_every_favourite_including_unavailable_ones() -> None:
    broken = game("a", Category.WORDS, Status.BROKEN)
    assert sections.contains(sections.FAVORITES, listing(broken, favorite=True))
    other = game("b", Category.WORDS)
    assert not sections.contains(sections.FAVORITES, listing(other, popular=1, trending=1))


def test_the_shelves_hold_the_games_ranked_on_them() -> None:
    ranked = game("a", Category.WORDS)
    assert sections.contains(sections.POPULAR, listing(ranked, popular=3))
    assert not sections.contains(sections.TRENDING, listing(ranked, popular=3))
    assert sections.contains(sections.TRENDING, listing(ranked, trending=1))
    assert not sections.contains(sections.POPULAR, listing(ranked, favorite=True))


def test_a_category_holds_its_available_games_only() -> None:
    active = game("a", Category.MUSIC)
    retired = game("b", Category.MUSIC, Status.RETIRED)
    assert sections.contains("music", listing(active))
    assert not sections.contains("words", listing(active))
    assert not sections.contains("music", listing(retired, favorite=True, popular=1))


def test_an_unknown_sort_mode_falls_back_to_the_default() -> None:
    assert sections.SortMode.from_id("difficulty") is sections.SortMode.DIFFICULTY
    assert sections.SortMode.from_id("not-done") is sections.SortMode.NOT_DONE
    assert sections.SortMode.from_id("newest") is sections.SortMode.DEFAULT


type Row = tuple[Game, int | None, int, int]


def sort(section: str, mode: sections.SortMode, rows: list[Row]) -> list[str]:
    def key(row: Row) -> tuple:
        game_, position, popular, trending = row
        entry = listing(game_, favorite=position is not None, popular=popular, trending=trending)
        return sections.sort_key(section, mode, entry, position)

    return [row[0].id for row in sorted(rows, key=key)]


def test_the_default_order_is_the_shelf_rank_the_favourite_order_or_the_name() -> None:
    rows: list[Row] = [
        (named("a", "Zebra"), 1, 2, 3),
        (named("b", "apple"), 2, 3, 1),
        (named("c", "Éclair"), 0, 1, 2),
    ]
    assert sort(sections.POPULAR, sections.SortMode.DEFAULT, rows) == ["c", "a", "b"]
    assert sort(sections.TRENDING, sections.SortMode.DEFAULT, rows) == ["b", "c", "a"]
    assert sort(sections.FAVORITES, sections.SortMode.DEFAULT, rows) == ["c", "a", "b"]
    assert sort("words", sections.SortMode.DEFAULT, rows) == ["b", "c", "a"]


def test_sorting_by_name_or_difficulty_overrides_every_section_default() -> None:
    rows: list[Row] = [
        (named("a", "Zebra", Difficulty.EASY), 1, 2, 3),
        (named("b", "apple", Difficulty.HARD), 2, 3, 1),
        (named("c", "Éclair", Difficulty.EASY), 0, 1, 2),
    ]
    for section in (sections.FAVORITES, sections.POPULAR, sections.TRENDING, "words"):
        assert sort(section, sections.SortMode.NAME, rows) == ["b", "c", "a"]
        assert sort(section, sections.SortMode.DIFFICULTY, rows) == ["c", "a", "b"]


def test_equal_names_sort_by_id_so_the_order_is_stable() -> None:
    rows: list[Row] = [(named("b", "Same"), None, 0, 0), (named("a", "same"), None, 0, 0)]
    assert sort("words", sections.SortMode.DEFAULT, rows) == ["a", "b"]


def test_not_done_first_puts_todays_played_games_last_in_the_section_order() -> None:
    games = [named("a", "Zebra"), named("b", "apple"), named("c", "Éclair"), named("d", "Dune")]
    done = {"b", "c"}
    positions = {"a": 3, "b": 0, "c": 1, "d": 2}

    def order(section: str) -> list[str]:
        def key(game_: Game) -> tuple:
            entry = sections.Listing(
                game=game_, favorite=True, popular_rank=positions[game_.id] + 1, done=game_.id in done
            )
            return sections.sort_key(section, sections.SortMode.NOT_DONE, entry, positions[game_.id])

        return [game_.id for game_ in sorted(games, key=key)]

    assert order(sections.FAVORITES) == ["d", "a", "b", "c"]
    assert order(sections.POPULAR) == ["d", "a", "b", "c"]
    assert order("words") == ["d", "a", "b", "c"]


def test_the_other_orders_ignore_whether_a_game_is_done() -> None:
    rows = [named("a", "Zebra"), named("b", "apple")]

    def key(game_: Game) -> tuple:
        entry = sections.Listing(game=game_, done=game_.id == "b")
        return sections.sort_key("words", sections.SortMode.NAME, entry, None)

    assert [game_.id for game_ in sorted(rows, key=key)] == ["b", "a"]


def test_a_section_with_games_shows_the_grid() -> None:
    for section in (sections.FAVORITES, sections.POPULAR, "music"):
        assert sections.page(section, empty=False, searching=True) is sections.Page.GRID
        assert sections.page(section, empty=False, searching=False) is sections.Page.GRID


def test_an_empty_search_result_says_no_games_were_found() -> None:
    for section in (sections.FAVORITES, sections.POPULAR, "music"):
        assert sections.page(section, empty=True, searching=True) is sections.Page.NO_RESULTS


def test_an_empty_section_without_a_search_explains_itself() -> None:
    assert sections.page(sections.FAVORITES, empty=True, searching=False) is sections.Page.EMPTY_FAVORITES
    assert sections.page(sections.TRENDING, empty=True, searching=False) is sections.Page.EMPTY_SECTION
    assert sections.page("music", empty=True, searching=False) is sections.Page.EMPTY_SECTION


def test_the_stack_page_names_match_the_window() -> None:
    assert [page.value for page in sections.Page] == ["grid", "empty-favorites", "no-results", "empty-section"]


def test_tiles_are_styled_by_category_and_difficulty() -> None:
    assert sections.category_style(Category.MOVIES_TV) == "cat-movies-tv"
    assert sections.difficulty_style(Difficulty.HARD) == "difficulty-hard"


def test_favourites_move_only_in_favorites_in_their_own_order() -> None:
    order = ("wordle", "globle", "framed")
    default = sections.SortMode.DEFAULT
    assert sections.favorite_moves(sections.FAVORITES, default, order, "globle") == set(Move)
    assert sections.favorite_moves(sections.FAVORITES, default, order, "wordle") == {Move.DOWN}
    assert sections.favorite_moves(sections.FAVORITES, sections.SortMode.NAME, order, "globle") == set()
    assert sections.favorite_moves(sections.POPULAR, default, order, "globle") == set()
