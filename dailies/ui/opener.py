"""The link opener: turns `open-mode` into the built-in browser, the default browser or the user's own command.

WebKit is probed the first time it is needed, never at startup, so a cold start does not load it. Host access for the
custom command is probed the first time the custom mode needs it, once per session.
"""

import functools
import importlib
import logging
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib, Gtk

from dailies import config
from dailies.core import opening
from dailies.core.opening import OpenMode

log = logging.getLogger(__name__)

_WEBKIT_VERSION = "6.0"

# The probe: HostCommand with no arguments on the session helper of `flatpak-spawn --host`. It can never run anything.
_FLATPAK_NAME = "org.freedesktop.Flatpak"
_DEVELOPMENT_PATH = "/org/freedesktop/Flatpak/Development"
_DEVELOPMENT_INTERFACE = "org.freedesktop.Flatpak.Development"
_PROBE_TIMEOUT_MS = 2000


@functools.cache
def in_flatpak() -> bool:
    """Whether the app runs inside a Flatpak sandbox, which always has `/.flatpak-info`."""
    return Path("/.flatpak-info").exists()


@functools.cache
def host_access() -> bool:
    """Whether the custom command can run: always outside Flatpak; inside, only once the user granted host access.

    Inside Flatpak this calls HostCommand with no arguments. Verified with flatpak 1.18.4 and the sandbox's D-Bus proxy:
    without `flatpak override --talk-name=org.freedesktop.Flatpak` the proxy answers
    `org.freedesktop.DBus.Error.ServiceUnknown`; with it flatpak-session-helper answers
    `org.freedesktop.DBus.Error.InvalidArgs` ("Type of message, “()”, does not match expected type"). Only the latter
    counts as granted (`dailies.core.opening.host_access_granted`).
    """
    if not in_flatpak():
        return True
    error_name = None
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call_sync(
            _FLATPAK_NAME,
            _DEVELOPMENT_PATH,
            _DEVELOPMENT_INTERFACE,
            "HostCommand",
            None,
            None,
            Gio.DBusCallFlags.NONE,
            _PROBE_TIMEOUT_MS,
            None,
        )
    except GLib.Error as e:
        error_name = Gio.DBusError.get_remote_error(e)
        log.debug("Host-access probe: %s", e.message)
    granted = opening.host_access_granted(error_name)
    log.info("Host access for the custom command: %s", "granted" if granted else "not granted")
    return granted


@functools.cache
def have_webkit() -> bool:
    """Whether the built-in browser can run: WebKitGTK 6.0 imports. Imports WebKit on the first call."""
    if not config.HAVE_WEBKIT:
        return False
    try:
        gi.require_version("WebKit", _WEBKIT_VERSION)
        importlib.import_module("gi.repository.WebKit")
    except (ValueError, ImportError) as e:
        log.info("The built-in browser is unavailable: %s", e)
        return False
    return True


def webkit_installed() -> bool:
    """Whether WebKitGTK 6.0 looks installed, without importing it: for decisions made while the app starts."""
    return config.HAVE_WEBKIT and _WEBKIT_VERSION in gi.Repository.get_default().enumerate_versions("WebKit")


def resolve(settings: Gio.Settings, *, custom_failed: bool = False) -> OpenMode:
    """Return how a game opens now; `custom_failed` when the custom command just failed to start."""
    mode = OpenMode.from_id(settings.get_string("open-mode"))
    return opening.resolve(
        mode,
        have_webkit=have_webkit(),
        # Probed only for the custom mode, which is the only one that needs it.
        host_access=mode is OpenMode.CUSTOM and not custom_failed and host_access(),
        command=settings.get_string("external-browser-command"),
    )


def launch_custom(command: str, url: str) -> bool:
    """Run the user's `command` with `url` appended as one argument, on the host when in Flatpak; False if it can't.

    The command is split like a shell would (`GLib.shell_parse_argv`), but no shell runs it: nothing in the command or
    the URL is interpreted.
    """
    try:
        _ok, argv = GLib.shell_parse_argv(command)
        process = Gio.Subprocess.new(
            opening.custom_command_argv(argv, url, in_flatpak=in_flatpak()), Gio.SubprocessFlags.NONE
        )
    except GLib.Error as e:
        log.warning("Could not run the custom command %r: %s", command, e.message)
        return False

    def on_exited(process: Gio.Subprocess, result: Gio.AsyncResult) -> None:
        try:
            process.wait_check_finish(result)
        except GLib.Error as e:
            log.warning("The custom command %r failed: %s", command, e.message)

    process.wait_check_async(None, on_exited)
    return True


def launch_external(parent: Gtk.Window | None, url: str) -> None:
    """Open `url` in the host's default browser: the OpenURI portal first, then the default URI handler."""

    def on_launched(launcher: Gtk.UriLauncher, result: Gio.AsyncResult) -> None:
        try:
            launcher.launch_finish(result)
        except GLib.Error as e:
            if e.matches(Gtk.dialog_error_quark(), Gtk.DialogError.DISMISSED):
                return
            log.info("The portal could not open %s (%s), trying the default handler", url, e.message)
            Gio.AppInfo.launch_default_for_uri_async(url, None, None, on_default_launched)

    def on_default_launched(_source: object, result: Gio.AsyncResult) -> None:
        try:
            Gio.AppInfo.launch_default_for_uri_finish(result)
        except GLib.Error as e:
            log.warning("Could not open %s: %s", url, e.message)

    Gtk.UriLauncher(uri=url).launch(parent, None, on_launched)
