from datetime import date, datetime, timedelta, timezone

from dailies.core import done_today

TODAY = date(2026, 10, 16)
# The local time zone, as `datetime.now(UTC).astimezone()` gives it.
CEST = timezone(timedelta(hours=2))


def test_a_game_marked_today_is_done() -> None:
    marks = {"wordle": "2026-10-16", "globle": "2026-10-15"}
    assert done_today.is_done(marks, "wordle", TODAY)
    assert not done_today.is_done(marks, "globle", TODAY)
    assert not done_today.is_done(marks, "worldle", TODAY)


def test_pruning_keeps_only_todays_marks() -> None:
    marks = {"wordle": "2026-10-16", "globle": "2026-10-15", "heardle": "2026-10-17", "worldle": "yesterday"}
    assert done_today.prune(marks, TODAY) == {"wordle": "2026-10-16"}
    assert marks["globle"] == "2026-10-15"


def test_toggling_marks_a_game_done_today_and_unmarks_it() -> None:
    marks = done_today.toggle({"globle": "2026-10-15"}, "wordle", TODAY)
    assert marks == {"wordle": "2026-10-16"}
    assert done_today.toggle(marks, "wordle", TODAY) == {}


def test_toggling_a_game_marked_on_an_earlier_day_marks_it_today() -> None:
    assert done_today.toggle({"wordle": "2026-10-15"}, "wordle", TODAY) == {"wordle": "2026-10-16"}


def test_marking_never_unmarks() -> None:
    marks = done_today.mark({"globle": "2026-10-15"}, "wordle", TODAY)
    assert marks == {"wordle": "2026-10-16"}
    assert done_today.mark(marks, "wordle", TODAY) == {"wordle": "2026-10-16"}


def test_the_marks_expire_at_the_next_local_midnight_never_before() -> None:
    assert done_today.seconds_until_midnight(datetime(2026, 10, 16, 23, 59, 30, tzinfo=CEST)) == 30
    assert done_today.seconds_until_midnight(datetime(2026, 10, 16, 12, 0, 0, 500_000, tzinfo=CEST)) == 43_200
    assert done_today.seconds_until_midnight(datetime(2026, 10, 16, tzinfo=CEST)) == 86_400
    assert done_today.seconds_until_midnight(datetime(2026, 12, 31, 23, 0, tzinfo=CEST)) == 3_600
