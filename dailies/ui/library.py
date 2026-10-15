"""The library's translated texts: category titles, the This Week subtitle and the stale-list banner."""

from datetime import date

from gi.repository import GLib

from dailies.core.models import Category


def category_title(category: Category) -> str:
    """Return the translated name of `category`, as shown in the sidebar."""
    # Spelled out, not `_(category.label)`, so that xgettext finds the strings.
    titles = {
        Category.WORDS: _("Words"),
        Category.GEOGRAPHY: _("Geography"),
        Category.MUSIC: _("Music"),
        Category.MOVIES_TV: _("Movies & TV"),
        Category.VIDEO_GAMES: _("Video Games"),
        Category.NUMBERS_LOGIC: _("Numbers & Logic"),
        Category.TRIVIA: _("Trivia"),
        Category.VISUAL: _("Pictures & Colors"),
        Category.FOOD: _("Food"),
        Category.SPORTS: _("Sports"),
    }
    return titles[category]


def week_subtitle(week: str, as_of: date | None) -> str:
    """Return the This Week subtitle: "Week 2026-W42", or "Week 2026-W42 (as of 12 Oct)" when the shelves are stale."""
    if as_of is None:
        return _("Week {week}").format(week=week)
    # Translators: a short day and month in GLib's strftime format, e.g. "12 Oct".
    day = _format_date(as_of, _("%-d %b"))
    return _("Week {week} (as of {date})").format(week=week, date=day)


def stale_banner_title(last_success: date) -> str:
    """Return the banner text shown when the game list has not been updated for a long time."""
    return _("Showing the game list from {date}").format(date=_format_date(last_success, "%x"))


def _format_date(day: date, pattern: str) -> str:
    return GLib.DateTime.new_utc(day.year, day.month, day.day, 0, 0, 0).format(pattern)
