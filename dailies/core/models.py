"""The catalog's domain types: games, categories, difficulties and statuses.

Each enum's `from_id` is tolerant: a value this version of the app does not know maps to a safe fallback instead of
raising, so a catalog published for a newer app never crashes an older one.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Self


class Category(Enum):
    """The ten game categories, in sidebar order."""

    WORDS = "words"
    GEOGRAPHY = "geography"
    MUSIC = "music"
    MOVIES_TV = "movies-tv"
    VIDEO_GAMES = "video-games"
    NUMBERS_LOGIC = "numbers-logic"
    TRIVIA = "trivia"
    VISUAL = "visual"
    FOOD = "food"
    SPORTS = "sports"

    @classmethod
    def from_id(cls, value: str) -> Self:
        """Return the category with id `value`, or `TRIVIA` when the id is unknown."""
        return _lookup(cls, value, cls.TRIVIA)

    @property
    def label(self) -> str:
        """The English display name; the UI layer translates it with `_()`."""
        return _CATEGORY_LABELS[self]

    @property
    def icon_name(self) -> str:
        """The name of the category's symbolic glyph in the icon theme."""
        return f"dailies-category-{self.value}-symbolic"


_CATEGORY_LABELS = {
    Category.WORDS: "Words",
    Category.GEOGRAPHY: "Geography",
    Category.MUSIC: "Music",
    Category.MOVIES_TV: "Movies & TV",
    Category.VIDEO_GAMES: "Video Games",
    Category.NUMBERS_LOGIC: "Numbers & Logic",
    Category.TRIVIA: "Trivia",
    Category.VISUAL: "Pictures & Colors",
    Category.FOOD: "Food",
    Category.SPORTS: "Sports",
}


class Difficulty(Enum):
    """How hard a game is, in ascending order."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    @classmethod
    def from_id(cls, value: str) -> Self:
        """Return the difficulty with id `value`, or `MEDIUM` (the neutral middle) when the id is unknown."""
        return _lookup(cls, value, cls.MEDIUM)

    @property
    def sort_key(self) -> int:
        """A key that sorts easy before medium before hard."""
        return list(Difficulty).index(self)


class Status(Enum):
    """Whether a game is shown: only active games are; broken and retired ones are kept so favourites resolve."""

    ACTIVE = "active"
    BROKEN = "broken"
    RETIRED = "retired"

    @classmethod
    def from_id(cls, value: str) -> Self:
        """Return the status with id `value`, or `BROKEN` (hidden, but kept) when the id is unknown."""
        return _lookup(cls, value, cls.BROKEN)


@dataclass(frozen=True, kw_only=True)
class Game:
    """One catalog entry, built with keyword arguments; the fields the catalog schema makes optional have defaults."""

    id: str
    name: str
    url: str
    category: Category
    difficulty: Difficulty
    description: str
    tags: tuple[str, ...] = ()
    language: str = "en"
    added: date
    status: Status
    domain: str
    free_no_account: bool | None = None
    wikipedia: str | None = None
    source_issue: int | None = None
    #: The game's icon relative to the data URLs, always `icons/<name>.png`; None when it has none.
    icon: str | None = None


def _lookup[E: Enum](enum: type[E], value: str, fallback: E) -> E:
    try:
        return enum(value)
    except ValueError:
        return fallback
