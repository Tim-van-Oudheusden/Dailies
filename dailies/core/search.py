"""Library search: ranked, case- and accent-insensitive matching that tolerates a typo in longer queries."""

import re
import unicodedata
from enum import Enum, IntEnum
from functools import lru_cache
from typing import NamedTuple

from dailies.core.models import Game

FUZZY_MIN_LENGTH = 6
"""The shortest query (counting letters and digits only) that may match with a typo; shorter ones match exactly.

A shorter query is usually a name still being typed, which prefix matching already finds, and one typo is a fifth of a
five-letter query. Matching short queries exactly also keeps the cheap narrowing while the first letters are typed
(see `change`).
"""
TWO_TYPOS_LENGTH = 9
"""The shortest query (counting letters and digits only) that may contain two typos."""

_WORD = re.compile(r"\w+")


def fold(text: str) -> str:
    """Return `text` case-folded, in compatibility form and without combining marks, so "Pokédle" folds to "pokedle"."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def typos_allowed(length: int) -> int:
    """Return how many typos a query of `length` letters and digits may contain.

    A typo is an inserted, missing or wrong character, or two neighbours swapped. None below `FUZZY_MIN_LENGTH`, one
    below `TWO_TYPOS_LENGTH`, two from there on.
    """
    if length < FUZZY_MIN_LENGTH:
        return 0
    return 1 if length < TWO_TYPOS_LENGTH else 2


class Tier(IntEnum):
    """How well a game matches a query; a higher tier ranks first."""

    FUZZY = 1
    """The query is a name word, or each query word a name word, give or take the allowed typos."""
    OTHER_FIELD = 2
    """The query occurs in the description, a tag or the category label."""
    SUBSTRING = 3
    """The query occurs inside the name."""
    WORD_PREFIX = 4
    """Each word of the query starts a word of the name, in order: "n l" for "Numbers & Logic"."""
    PREFIX = 5
    """The name starts with the query."""


def rank(game: Game, query: str, category_label: str) -> Tier | None:
    """Return how well `game` matches `query`, or None if it does not match.

    Args:
        game: The game to rank.
        query: What the user typed; an empty or all-whitespace query ranks every game `Tier.PREFIX`.
        category_label: The category's display name as shown, so a translated label is searchable.
    """
    parsed = _parse(query)
    if not parsed.needle:
        return Tier.PREFIX
    return _tier(parsed, _haystack(game.name, game.description, game.tags, category_label))


def matches(game: Game, query: str, category_label: str) -> bool:
    """Return whether `game` matches `query` at all (see `rank`); an empty query matches every game."""
    return rank(game, query, category_label) is not None


class Change(Enum):
    """How a new query relates to the previous one, so a list filter knows which games it has to test again."""

    SAME = "same"
    MORE_STRICT = "more-strict"
    LESS_STRICT = "less-strict"
    DIFFERENT = "different"


def change(old: str, new: str) -> Change:
    """Return how replacing the query `old` by `new` changes the matches.

    A query that extends the old one can only drop matches, one the old one extends can only add matches, as long as
    the longer of the two cannot match with a typo: "wxrdle" finds Wordle by typo, "wxrd" finds nothing. A query
    containing the old one elsewhere than at its start only narrows if the old one is a single word: "is n" starts the
    words of "Island Numbers", "s n" occurs nowhere in it.
    """
    old, new = _parse(old).needle, _parse(new).needle
    if old == new:
        return Change.SAME
    if _narrows(old, new):
        return Change.MORE_STRICT
    if _narrows(new, old):
        return Change.LESS_STRICT
    return Change.DIFFERENT


def _narrows(short: str, long: str) -> bool:
    """Whether every game that matches the query `long` also matches the query `short`."""
    if _parse(long).typos:
        return False
    return long.startswith(short) or (short in long and _WORD.fullmatch(short) is not None)


class _Query(NamedTuple):
    needle: str
    words: tuple[str, ...]
    typos: int


@lru_cache(maxsize=64)
def _parse(query: str) -> _Query:
    needle = " ".join(fold(query).split())
    words = tuple(_WORD.findall(needle))
    return _Query(needle, words, typos_allowed(sum(map(len, words))))


class _Haystack(NamedTuple):
    name: str
    words: tuple[str, ...]
    compact: str
    others: tuple[str, ...]


@lru_cache(maxsize=2048)
def _haystack(name: str, description: str, tags: tuple[str, ...], category_label: str) -> _Haystack:
    """Fold a game's searchable texts once; every keystroke after the first reuses them."""
    folded = fold(name)
    words = tuple(_WORD.findall(folded))
    return _Haystack(folded, words, "".join(words), tuple(fold(text) for text in (description, *tags, category_label)))


def _tier(query: _Query, haystack: _Haystack) -> Tier | None:
    needle = query.needle
    if haystack.name.startswith(needle):
        return Tier.PREFIX
    if query.words and _start_words(query.words, haystack.words, typos=False):
        return Tier.WORD_PREFIX
    if needle in haystack.name:
        return Tier.SUBSTRING
    if any(needle in text for text in haystack.others):
        return Tier.OTHER_FIELD
    if query.typos and _close(query, haystack):
        return Tier.FUZZY
    return None


def _start_words(query_words: tuple[str, ...], name_words: tuple[str, ...], *, typos: bool) -> bool:
    """Whether each query word starts (or, with `typos`, is close to) a name word, in order; earliest match first."""
    position = 0
    for query_word in query_words:
        allowed = typos_allowed(len(query_word)) if typos else 0
        while position < len(name_words) and not (
            name_words[position].startswith(query_word)
            or (allowed and _within(query_word, name_words[position], allowed))
        ):
            position += 1
        if position == len(name_words):
            return False
        position += 1
    return True


def _close(query: _Query, haystack: _Haystack) -> bool:
    """Whether the query, its spaces left out, is close to a name word or the whole name, or each of its words is."""
    compact = "".join(query.words)
    if any(_within(compact, target, query.typos) for target in (*haystack.words, haystack.compact)):
        return True
    return len(query.words) > 1 and _start_words(query.words, haystack.words, typos=True)


def _within(a: str, b: str, limit: int) -> bool:
    """Whether `a` and `b` are at most `limit` edits apart (optimal string alignment: a swap of neighbours is one)."""
    if abs(len(a) - len(b)) > limit:
        return False
    # Every letter of `a` that `b` lacks costs an edit: a cheap way to skip most names without filling the table.
    letters = set(b)
    if sum(char not in letters for char in a) > limit:
        return False
    before: list[int] = []
    previous = list(range(len(b) + 1))
    for i, char in enumerate(a, start=1):
        current = [i] + [0] * len(b)
        for j, other in enumerate(b, start=1):
            cost = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char != other))
            if i > 1 and j > 1 and char == b[j - 2] and a[i - 2] == other:
                cost = min(cost, before[j - 2] + 1)
            current[j] = cost
        # A swap reaches two rows back, so stop only when neither this row nor that one can still lead within the limit.
        if min(current) > limit and min(previous) >= limit:
            return False
        before, previous = previous, current
    return previous[-1] <= limit
