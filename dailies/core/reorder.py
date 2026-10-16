"""Reordering the favourites: where a game goes when it moves up, down or to the top, or is dropped beside another.

An order is the list of favourite ids in display order. An index is a position in the order after the move.
"""

from collections.abc import Sequence
from enum import Enum


class Move(Enum):
    """A move of the tile menu and the keyboard: one place up or down, or to the top."""

    UP = "up"
    DOWN = "down"
    TOP = "top"


def moved(order: Sequence[str], game_id: str, index: int) -> list[str]:
    """Return `order` with `game_id` at `index`, clamped to the list; unchanged when `game_id` is not in it."""
    if game_id not in order:
        return list(order)
    rest = [other for other in order if other != game_id]
    rest.insert(max(0, min(index, len(rest))), game_id)
    return rest


def destination(order: Sequence[str], game_id: str, move: Move) -> int | None:
    """Return the index `move` takes `game_id` to, or None when it is not a favourite or cannot move that way."""
    if game_id not in order:
        return None
    current = order.index(game_id)
    index = {Move.UP: current - 1, Move.DOWN: current + 1, Move.TOP: 0}[move]
    return index if 0 <= index < len(order) and index != current else None


def possible_moves(order: Sequence[str], game_id: str) -> set[Move]:
    """Return the moves that change where `game_id` is; the menu disables the others."""
    return {move for move in Move if destination(order, game_id, move) is not None}


def drop_destination(order: Sequence[str], game_id: str, target_id: str, *, after: bool) -> int | None:
    """Return the index of `game_id` dropped before (or `after`) `target_id`, or None when the drop changes nothing."""
    if game_id == target_id or game_id not in order or target_id not in order:
        return None
    rest = [other for other in order if other != game_id]
    index = rest.index(target_id) + (1 if after else 0)
    return None if index == order.index(game_id) else index
