"""Parse the weekly Popular and Trending shelves, `data/v1/popularity.json`.

The app reads only `week`, `generated_at`, `valid_until`, `popular` and `trending`; `scores` is kept as raw JSON for
transparency. Structural problems raise `PopularityError`, so the caller keeps its last good copy.
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Self

from dailies.core._fields import Fields


class PopularityError(ValueError):
    """The popularity file is structurally wrong and must not replace the last good copy."""


class Shelf(Enum):
    """The two weekly shelves."""

    POPULAR = "popular"
    TRENDING = "trending"


@dataclass(frozen=True)
class Popularity:
    """One week's shelves: game ids, best first."""

    week: str
    generated_at: datetime
    valid_until: datetime
    popular: tuple[str, ...]
    trending: tuple[str, ...]
    scores: Mapping[str, object]

    def rank_of(self, game_id: str, shelf: Shelf) -> int | None:
        """Return the 1-based position of `game_id` on `shelf`, or None when it is not on that shelf."""
        ids = self.popular if shelf is Shelf.POPULAR else self.trending
        return ids.index(game_id) + 1 if game_id in ids else None

    def is_stale(self, now: datetime) -> bool:
        """Return whether `now` (timezone-aware) is past `valid_until`; stale shelves are still shown, with a date."""
        return now > self.valid_until

    def restricted_to(self, known_ids: Collection[str]) -> Self:
        """Return a copy without the ids that are not in `known_ids`, typically the catalog's.

        Later games move up, so ranks stay contiguous. A popularity file can name a game this app's catalog does not
        have yet; such ids are dropped silently.
        """
        return replace(
            self,
            popular=tuple(game_id for game_id in self.popular if game_id in known_ids),
            trending=tuple(game_id for game_id in self.trending if game_id in known_ids),
            scores={game_id: score for game_id, score in self.scores.items() if game_id in known_ids},
        )


def parse(data: bytes) -> Popularity:
    """Parse a popularity file.

    Args:
        data: The raw bytes of a `popularity.json` file.

    Returns:
        The parsed shelves, each ordered by its `rank` field.

    Raises:
        PopularityError: The data is not JSON, has another `schema_version`, or misses or mistypes a field the app
            reads.
    """
    document = Fields.load(data, PopularityError)
    return Popularity(
        week=document.required("week", str),
        generated_at=document.timestamp("generated_at"),
        valid_until=document.timestamp("valid_until"),
        popular=_shelf(document, "popular"),
        trending=_shelf(document, "trending"),
        scores=document.optional("scores", dict, {}),
    )


def _shelf(document: Fields, key: str) -> tuple[str, ...]:
    entries = [(entry.required("rank", int), entry.required("id", str)) for entry in document.objects(key)]
    return tuple(game_id for _, game_id in sorted(entries, key=lambda entry: entry[0]))
