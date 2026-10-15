"""How a game opens: the `open-mode` setting resolved against what this installation can do.

Inside a Flatpak a specific host browser is only reachable with host access the user grants themselves, and the
built-in browser needs WebKitGTK. `ui/opener.py` probes both and acts on the mode `resolve` returns.
"""

from enum import Enum
from typing import Self


class OpenMode(Enum):
    """The values of the `open-mode` setting, which are also the three ways a game can open."""

    IN_APP = "in-app"
    EXTERNAL = "external"
    CUSTOM = "custom"

    @classmethod
    def from_id(cls, value: str) -> Self:
        """Return the mode with nick `value`, or `IN_APP` (the schema default) when the nick is unknown."""
        try:
            return cls(value)
        except ValueError:
            return cls.IN_APP


def resolve(mode: OpenMode, *, have_webkit: bool, host_access: bool, command: str) -> OpenMode:
    """Return how a game opens when the setting says `mode`.

    The custom command runs only with host access and a command; otherwise custom behaves like in-app. In-app needs
    WebKit; without it the game opens in the default browser.
    """
    if mode is OpenMode.CUSTOM and host_access and command.strip():
        return OpenMode.CUSTOM
    if mode in {OpenMode.IN_APP, OpenMode.CUSTOM} and have_webkit:
        return OpenMode.IN_APP
    return OpenMode.EXTERNAL


def show_first_run_banner(mode: OpenMode, *, have_webkit: bool, dismissed: bool) -> bool:
    """Whether the library tells the user that games open inside Dailies: until dismissed, while they really do."""
    in_app = resolve(mode, have_webkit=have_webkit, host_access=False, command="") is OpenMode.IN_APP
    return in_app and not dismissed


def choices(*, have_webkit: bool, host_access: bool) -> tuple[OpenMode, ...]:
    """The modes Preferences offers, in order: the built-in browser needs WebKit, the custom command host access."""
    offered = {OpenMode.IN_APP: have_webkit, OpenMode.EXTERNAL: True, OpenMode.CUSTOM: host_access}
    return tuple(mode for mode, available in offered.items() if available)


def shown_choice(mode: OpenMode, *, have_webkit: bool, host_access: bool) -> OpenMode:
    """The choice Preferences selects for the setting `mode`: the mode itself, or what it does when it is hidden."""
    if mode in choices(have_webkit=have_webkit, host_access=host_access):
        return mode
    return resolve(mode, have_webkit=have_webkit, host_access=False, command="")
