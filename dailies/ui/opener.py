"""The link opener: turns the `open-mode` setting into the built-in browser or the host's default browser.

WebKit is probed the first time it is needed, never at startup, so a cold start does not load it.
"""

import functools
import importlib
import logging

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib, Gtk

from dailies import config
from dailies.core import opening
from dailies.core.opening import OpenMode

log = logging.getLogger(__name__)

_WEBKIT_VERSION = "6.0"


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


def resolve(settings: Gio.Settings) -> OpenMode:
    """Return how a game opens now. Host access for the custom command is never detected yet (#63)."""
    return opening.resolve(
        OpenMode.from_id(settings.get_string("open-mode")),
        have_webkit=have_webkit(),
        host_access=False,
        command=settings.get_string("external-browser-command"),
    )


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
