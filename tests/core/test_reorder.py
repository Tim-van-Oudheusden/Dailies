import pytest

from dailies.core import reorder
from dailies.core.reorder import Move

ORDER = ("wordle", "globle", "framed", "worldle")


@pytest.mark.parametrize(
    ("game_id", "index", "expected"),
    [
        ("framed", 0, ["framed", "wordle", "globle", "worldle"]),
        ("wordle", 3, ["globle", "framed", "worldle", "wordle"]),
        ("globle", 2, ["wordle", "framed", "globle", "worldle"]),
        ("globle", 1, list(ORDER)),
        ("globle", -5, ["globle", "wordle", "framed", "worldle"]),
        ("globle", 99, ["wordle", "framed", "worldle", "globle"]),
    ],
)
def test_moved_puts_the_game_at_the_index_of_the_new_order(game_id: str, index: int, expected: list[str]) -> None:
    assert reorder.moved(ORDER, game_id, index) == expected


def test_moving_an_unknown_game_changes_nothing() -> None:
    assert reorder.moved(ORDER, "pokedle", 0) == list(ORDER)


@pytest.mark.parametrize(
    ("game_id", "move", "expected"),
    [
        ("framed", Move.UP, 1),
        ("framed", Move.DOWN, 3),
        ("framed", Move.TOP, 0),
        ("wordle", Move.UP, None),
        ("wordle", Move.TOP, None),
        ("wordle", Move.DOWN, 1),
        ("worldle", Move.DOWN, None),
        ("worldle", Move.UP, 2),
        ("pokedle", Move.UP, None),
    ],
)
def test_destination_is_the_new_index_or_none_when_the_move_is_impossible(
    game_id: str, move: Move, expected: int | None
) -> None:
    assert reorder.destination(ORDER, game_id, move) == expected


def test_possible_moves_of_the_first_last_and_only_favourite() -> None:
    assert reorder.possible_moves(ORDER, "wordle") == {Move.DOWN}
    assert reorder.possible_moves(ORDER, "globle") == {Move.UP, Move.DOWN, Move.TOP}
    assert reorder.possible_moves(ORDER, "worldle") == {Move.UP, Move.TOP}
    assert reorder.possible_moves(("wordle",), "wordle") == set()
    assert reorder.possible_moves(ORDER, "pokedle") == set()


@pytest.mark.parametrize(
    ("game_id", "target", "after", "expected"),
    [
        # Dropped on the first half of a tile: it goes before that tile; on the second half: after it.
        ("worldle", "globle", False, ["wordle", "worldle", "globle", "framed"]),
        ("worldle", "globle", True, ["wordle", "globle", "worldle", "framed"]),
        ("wordle", "framed", False, ["globle", "wordle", "framed", "worldle"]),
        ("wordle", "framed", True, ["globle", "framed", "wordle", "worldle"]),
        ("wordle", "worldle", True, ["globle", "framed", "worldle", "wordle"]),
    ],
)
def test_drop_destination_places_the_game_beside_the_target(
    game_id: str, target: str, after: bool, expected: list[str]
) -> None:
    index = reorder.drop_destination(ORDER, game_id, target, after=after)
    assert reorder.moved(ORDER, game_id, index) == expected


@pytest.mark.parametrize(
    ("game_id", "target", "after"),
    [
        ("globle", "globle", False),
        ("globle", "wordle", True),  # Right after the tile before it: where it already is.
        ("globle", "framed", False),
        ("pokedle", "globle", False),
        ("globle", "pokedle", False),
    ],
)
def test_a_drop_that_changes_nothing_has_no_destination(game_id: str, target: str, after: bool) -> None:
    assert reorder.drop_destination(ORDER, game_id, target, after=after) is None
