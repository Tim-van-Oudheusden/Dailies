"""The "Show games in other languages" filter: a game's language against the system's, by primary subtag."""

import re
from collections.abc import Collection, Iterable

from dailies.core.models import Game

#: What a game without a language, and the C locale, count as.
DEFAULT_LANGUAGE = "en"

_NOT_A_LANGUAGE = {"", "c", "posix"}


def primary_subtag(name: str) -> str | None:
    """Return the lower-case language of a locale name or language tag, or None for the C and POSIX locales.

    "nl_NL.UTF-8" and "nl" give "nl", "en-GB" gives "en" and "de_DE@euro" gives "de".
    """
    subtag = re.split(r"[_\-.@]", name, maxsplit=1)[0].casefold()
    return None if subtag in _NOT_A_LANGUAGE else subtag


def system_languages(names: Iterable[str]) -> set[str]:
    """Return the languages of the locale names the system lists (`GLib.get_language_names()`), English if none.

    The C locale that ends the list is not a language; on its own it means English.
    """
    languages = {subtag for name in names if (subtag := primary_subtag(name)) is not None}
    return languages or {DEFAULT_LANGUAGE}


def matches_language(game: Game, system_langs: Collection[str], show_other: bool) -> bool:
    """Return whether `game` is shown: always when `show_other` is set, else when its language is one of the system's.

    A game without a language counts as English.
    """
    return show_other or (primary_subtag(game.language) or DEFAULT_LANGUAGE) in system_langs
