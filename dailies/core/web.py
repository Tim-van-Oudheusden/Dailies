"""Decisions of the built-in browser that need no WebKit.

The host shown in its header, which data a site owns, and which network session a game uses with which policies.
"""

import re
from collections.abc import Iterable
from enum import Enum
from pathlib import PurePosixPath
from typing import Self
from urllib.parse import urlsplit

#: The session directory of all games while they share one, relative to the web data and cache directories (v0.1).
SHARED_SESSION = PurePosixPath("shared")
#: Per-game session directories live in here, one per game id, so no game id can collide with `shared`.
_GAMES = PurePosixPath("games")
#: A catalog id (`data/v1/schema/catalog.schema.json`); only these ever name a directory or a settings path.
_GAME_ID = re.compile(r"[a-z0-9][a-z0-9-]{1,48}")


class SessionIsolation(Enum):
    """The values of the `session-isolation` setting."""

    SHARED = "shared"
    PER_GAME = "per-game"

    @classmethod
    def from_id(cls, value: str) -> Self:
        """Return the value with nick `value`, or `SHARED` (the schema default) when the nick is unknown."""
        try:
            return cls(value)
        except ValueError:
            return cls.SHARED


def is_game_id(value: str | None) -> bool:
    """Whether `value` is a catalog id, and so safe as a directory name and a GSettings path element."""
    return bool(value) and _GAME_ID.fullmatch(value) is not None


def session_dir(isolation: SessionIsolation, game_id: str | None, *, isolated: bool) -> PurePosixPath:
    """The session directory the game `game_id` uses, relative to the web data and cache directories.

    Games share `shared` unless the setting is per-game or the game's own `isolated-session` key is set; then the game
    gets `games/<id>`. An id that is not a catalog id never names a directory: that game shares.
    """
    if (isolation is SessionIsolation.PER_GAME or isolated) and is_game_id(game_id):
        return _GAMES / game_id
    return SHARED_SESSION


def isolated_session_toggle(isolation: SessionIsolation, *, isolated: bool) -> tuple[bool, bool]:
    """A game's "Isolated Session" toggle as (checked, changeable), for its `isolated-session` key `isolated`.

    While `isolation` is per-game every game has a session of its own already: the toggle is checked and cannot change.
    """
    if isolation is SessionIsolation.PER_GAME:
        return True, False
    return isolated, True


def all_sessions(game_dirs: Iterable[str]) -> list[PurePosixPath]:
    """Every session to clear: the shared one and one per game directory found on disk (`game_dirs`, their names).

    Clearing website data must reach per-game sessions this run has not opened yet; names that are not game ids are
    not sessions Dailies made, and are left alone.
    """
    return [SHARED_SESSION, *(_GAMES / name for name in sorted(set(game_dirs)) if is_game_id(name))]


def game_settings_path(prefix: str, game_id: str | None) -> str | None:
    """The path of the relocatable `<app id>.Game` settings of `game_id` under the schema path `prefix`, or None.

    Only catalog ids get a path, so no id can reach another schema's settings.
    """
    return f"{prefix}/games/{game_id}/" if is_game_id(game_id) else None


def cookie_accept_policy(nick: str) -> str:
    """The `WebKit.CookieAcceptPolicy` member the `cookie-policy` setting `nick` names; `ALWAYS` (v0.1) by default."""
    policies = {"always": "ALWAYS", "no-third-party": "NO_THIRD_PARTY", "never": "NEVER"}
    return policies.get(nick, "ALWAYS")


def hardware_acceleration_policy(nick: str) -> str | None:
    """The `WebKit.HardwareAccelerationPolicy` member to force for the `hardware-acceleration` setting `nick`.

    `always` forces nothing: WebKit already accelerates where the system can and turns it off where it cannot, and
    forcing `ALWAYS` there would break rendering. Only `never` is forced.
    """
    return "NEVER" if nick == "never" else None


def custom_user_agent(value: str) -> str | None:
    """The user agent the `user-agent` setting asks for, or None to keep WebKit's with "Dailies/<version>" appended.

    The setting is for compatibility fixes the user makes; Dailies never spoofs another browser by default.
    """
    return value.strip() or None


def display_host(uri: str | None) -> str:
    """Return the host of `uri` as the header shows it: lower case, ASCII, without port or user name; or ""."""
    if not uri:
        return ""
    try:
        return urlsplit(uri).hostname or ""
    except ValueError:
        return ""


def is_web_uri(uri: str | None) -> bool:
    """Whether `uri` is an http or https URL with a host: the only links Dailies hands to the browser or reloads.

    A page in the built-in browser chooses the URIs of its pop-ups and downloads. Any other scheme (`file:`, `smb:`, an
    app's own `x-scheme-handler`) would start whatever host application handles it, so those are dropped.
    """
    if not uri:
        return False
    try:
        parts = urlsplit(uri)
        return parts.scheme in {"http", "https"} and bool(parts.hostname)
    except ValueError:
        return False


def site_matches(name: str, host: str) -> bool:
    """Whether website data stored under `name` (a domain, as WebKit groups it) belongs to the site at `host`."""
    name = name.lower().lstrip(".")
    host = host.lower()
    return bool(name and host) and (host == name or host.endswith(f".{name}"))
