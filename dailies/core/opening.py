"""How a game opens: the `open-mode` setting resolved against what this installation can do.

Inside a Flatpak a specific host browser is only reachable with host access the user grants themselves, and the
built-in browser needs WebKitGTK. `ui/opener.py` probes both and acts on the mode `resolve` returns.
"""

from collections.abc import Sequence
from enum import Enum
from typing import Self

# The error flatpak-session-helper answers a HostCommand call with no arguments with. Only the helper itself can send
# it, so the sandbox's D-Bus proxy let the call through: the user granted `--talk-name=org.freedesktop.Flatpak`.
# Without that the proxy answers `ServiceUnknown` (observed with flatpak 1.18.4; `AccessDenied` is its other refusal).
_HELPER_REJECTED_ARGUMENTS = "org.freedesktop.DBus.Error.InvalidArgs"


class Notice(Enum):
    """What the window tells the user after a game opened, besides the game itself."""

    # The custom command was chosen but cannot run (no host access, no command, or it failed to start).
    CUSTOM_UNAVAILABLE = "custom-unavailable"


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


def host_access_granted(error_name: str | None) -> bool:
    """Whether the custom command can reach the host, given the D-Bus error name the host-access probe got.

    The probe calls HostCommand with no arguments, which can never succeed: only the helper's own refusal of the
    arguments proves the call reached it. Anything else (no error name, a proxy refusal, a timeout) means no access.
    """
    return error_name == _HELPER_REJECTED_ARGUMENTS


def custom_command_argv(command: Sequence[str], url: str, *, in_flatpak: bool) -> list[str]:
    """The argv that runs the user's split `command` with `url` as one last argument, never through a shell.

    Inside a Flatpak it runs on the host through `flatpak-spawn --host`; `--` ends flatpak-spawn's own options.
    """
    argv = [*command, url]
    return ["flatpak-spawn", "--host", "--", *argv] if in_flatpak else argv


def notice(mode: OpenMode, resolved: OpenMode, *, custom_notice_shown: bool) -> Notice | None:
    """What to tell the user after a game set to open with `mode` opened as `resolved`.

    A custom command that could not run is mentioned once per session (`custom_notice_shown`).
    """
    if mode is OpenMode.CUSTOM and resolved is not OpenMode.CUSTOM and not custom_notice_shown:
        return Notice.CUSTOM_UNAVAILABLE
    return None
