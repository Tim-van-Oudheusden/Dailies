from dailies.core.models import Category, Difficulty, Status


def test_categories_are_in_sidebar_order() -> None:
    assert [category.value for category in Category] == [
        "words",
        "geography",
        "music",
        "movies-tv",
        "video-games",
        "numbers-logic",
        "trivia",
        "visual",
        "food",
        "sports",
    ]


def test_every_category_has_a_display_name() -> None:
    assert [category.label for category in Category] == [
        "Words",
        "Geography",
        "Music",
        "Movies & TV",
        "Video Games",
        "Numbers & Logic",
        "Trivia",
        "Pictures & Colors",
        "Food",
        "Sports",
    ]


def test_every_category_has_a_symbolic_glyph() -> None:
    assert Category.MOVIES_TV.icon_name == "dailies-category-movies-tv-symbolic"
    assert all(category.icon_name == f"dailies-category-{category.value}-symbolic" for category in Category)


def test_a_known_category_id_is_looked_up() -> None:
    assert Category.from_id("video-games") is Category.VIDEO_GAMES


def test_an_unknown_category_id_falls_back_to_trivia() -> None:
    assert Category.from_id("cooking-shows") is Category.TRIVIA


def test_difficulties_sort_from_easy_to_hard() -> None:
    shuffled = [Difficulty.HARD, Difficulty.EASY, Difficulty.MEDIUM]
    assert sorted(shuffled, key=lambda difficulty: difficulty.sort_key) == [
        Difficulty.EASY,
        Difficulty.MEDIUM,
        Difficulty.HARD,
    ]


def test_an_unknown_difficulty_falls_back_to_medium() -> None:
    assert Difficulty.from_id("hard") is Difficulty.HARD
    assert Difficulty.from_id("extreme") is Difficulty.MEDIUM


def test_an_unknown_status_falls_back_to_broken() -> None:
    assert Status.from_id("retired") is Status.RETIRED
    assert Status.from_id("removed") is Status.BROKEN
