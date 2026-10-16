"""The "Done today" marks: which games the user has played today, by the local calendar day.

The marks are the `done-today` setting, a mapping of game id to the local date (`YYYY-MM-DD`) the game was marked on.
A mark from any other day means nothing; `prune` drops it. The marks expire at local midnight
(`seconds_until_midnight`); with `auto-done-today` set, a game is marked once it has been open in the built-in browser
for `AUTO_MARK_SECONDS`.
"""

import math
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta

#: How long a game must stay open in the built-in browser before the automatic mode marks it as done: long enough that
#: a quick look or a misclick doesn't count, short enough for the quickest dailies.
AUTO_MARK_SECONDS = 60


def is_done(marks: Mapping[str, str], game_id: str, today: date) -> bool:
    """Return whether `game_id` was marked as done on `today`."""
    return marks.get(game_id) == today.isoformat()


def prune(marks: Mapping[str, str], today: date) -> dict[str, str]:
    """Return only today's marks: one from an earlier or a later day (the clock was set back) or no date is dropped."""
    return {game_id: day for game_id, day in marks.items() if day == today.isoformat()}


def toggle(marks: Mapping[str, str], game_id: str, today: date) -> dict[str, str]:
    """Return today's marks with `game_id` marked as done when it was not done today, unmarked when it was."""
    if is_done(marks, game_id, today):
        return {other: day for other, day in prune(marks, today).items() if other != game_id}
    return mark(marks, game_id, today)


def mark(marks: Mapping[str, str], game_id: str, today: date) -> dict[str, str]:
    """Return today's marks with `game_id` marked as done, whether or not it already was."""
    return {**prune(marks, today), game_id: today.isoformat()}


def seconds_until_midnight(now: datetime) -> int:
    """Return the whole seconds from `now`, the local time, until the next local midnight, rounded up.

    Rounding up means a timer set for it never fires before the day has changed. Midnight is taken at `now`'s UTC
    offset; when a daylight saving change comes first the result is an hour off, and whoever sets the timer checks
    the day again when it fires.
    """
    midnight = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=now.tzinfo)
    return math.ceil((midnight - now).total_seconds())
