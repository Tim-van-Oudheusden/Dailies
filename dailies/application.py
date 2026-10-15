import gettext
import locale
import logging
import os
import signal
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, GObject

from dailies import config
from dailies.core import cache
from dailies.core.cache import CacheDir, Outcome
from dailies.data.favorites import Favorites
from dailies.data.fetcher import Fetcher
from dailies.data.store import Store
from dailies.ui import opener

_REFRESH_ACCELS = ["<Control>r"]


class Application(Adw.Application):
    """The Dailies application: one main window, resources under `config.PREFIX`."""

    def __init__(self) -> None:
        super().__init__(
            application_id=config.APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            resource_base_path=config.PREFIX,
        )
        # For tests/e2e/test_smoke.py: skip the network refresh and quit once the window has mapped.
        self._smoke = False
        self.add_main_option("smoke", 0, GLib.OptionFlags.HIDDEN, GLib.OptionArg.NONE, "", None)

    def do_handle_local_options(self, options: GLib.VariantDict) -> int:
        """Note `--smoke`; -1 lets the application carry on starting up."""
        self._smoke = options.contains("smoke")
        return -1

    def do_startup(self) -> None:
        """Load the game list from the cache or the bundled snapshot, before any window is shown."""
        Adw.Application.do_startup(self)
        self.settings = Gio.Settings.new(config.APP_ID)
        self.favorites = Favorites(self.settings)
        cache_dir = CacheDir(Path(GLib.get_user_cache_dir()) / "dailies" / "v1")
        fetcher = Fetcher(cache_dir, _data_urls(), config.VERSION)
        self.store = Store(cache_dir, Path(config.PKGDATADIR) / "data" / "v1", self.favorites, fetcher)
        self.store.load_initial()
        self.set_accels_for_action("win.toggle-favorite", ["<Control>d"])
        self.set_accels_for_action("win.search", ["<Control>f"])

        for name, activate, accels in (
            ("preferences", self._on_preferences, ["<Control>comma"]),
            ("refresh", self._on_refresh, _REFRESH_ACCELS),
        ):
            action = Gio.SimpleAction(name=name)
            action.connect("activate", lambda _action, _param, activate=activate: activate())
            self.add_action(action)
            self.set_accels_for_action(f"app.{name}", accels)

    def do_activate(self) -> None:
        """Present the main window, creating it on first activation; the game list is refreshed once it maps."""
        window = self.props.active_window
        if window is None:
            # Imported here: its Gtk.Template needs the gresource that main() registers.
            from dailies.window import Window

            window = Window(application=self, store=self.store, state=Gio.Settings.new(f"{config.APP_ID}.State"))
            if config.PROFILE == "development":
                window.add_css_class("devel")
            window.connect("map", self._on_first_map)
            window.navigation_view.connect("notify::visible-page", self._on_visible_page)
        window.present()

    def _on_first_map(self, window: Adw.ApplicationWindow) -> None:
        window.disconnect_by_func(self._on_first_map)
        if self._smoke:
            # Give the first frame time to draw, so errors while rendering it reach the test too.
            GLib.timeout_add(500, self.quit)
            return
        self.store.refresh_all()

    def _on_visible_page(self, view: Adw.NavigationView, _pspec: GObject.ParamSpec) -> None:
        # Ctrl+R refreshes the game list on the library and reloads the page in the built-in browser; application
        # accelerators win over page shortcuts, so the browser page borrows it while it is shown.
        browser = view.props.visible_page.props.tag == "browser"
        self.set_accels_for_action("app.refresh", [] if browser else _REFRESH_ACCELS)

    def _on_preferences(self) -> None:
        # Imported here: its Gtk.Template needs the gresource that main() registers.
        from dailies.ui.preferences import PreferencesDialog

        window = self.props.active_window
        if not isinstance(window.get_visible_dialog(), PreferencesDialog):
            PreferencesDialog(settings=self.settings, store=self.store).present(window)

    def _on_refresh(self) -> None:
        self.store.refresh_all(self._on_refreshed, force=True)

    def _on_refreshed(self, outcomes: dict[str, Outcome]) -> None:
        messages = {
            Outcome.UPDATED: _("Game list updated"),
            Outcome.NOT_MODIFIED: _("The game list is up to date"),
            Outcome.SKIPPED: _("The game list is not updated on a metered connection"),
            Outcome.FAILED: _("Could not update the game list"),
        }
        toast = Adw.Toast(title=messages[cache.summarize(outcomes)])
        window = self.props.active_window
        if window is None:
            return
        # Shown where the user is looking: in Preferences when its refresh button was used.
        dialog = window.get_visible_dialog()
        if isinstance(dialog, Adw.PreferencesDialog):
            dialog.add_toast(toast)
        else:
            window.toast_overlay.add_toast(toast)

    def do_shutdown(self) -> None:
        """Clear the built-in browser's website data when the user asked for that on exit."""
        if self.settings.get_boolean("clear-web-data-on-exit") and opener.have_webkit():
            from dailies.ui import browser_page

            browser_page.clear_all_blocking()
        Adw.Application.do_shutdown(self)


def _data_urls() -> list[str]:
    # Development builds can point at a local server, e.g. DAILIES_DATA_URLS=http://127.0.0.1:8000/v1/
    if config.PROFILE == "development" and (override := os.environ.get("DAILIES_DATA_URLS")):
        return override.split()
    return config.DATA_URLS


def main() -> int:
    """Set up gettext and resources, then run the application."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    logging.basicConfig(
        format="%(name)s: %(message)s",
        level=logging.DEBUG if os.environ.get("G_MESSAGES_DEBUG") else logging.WARNING,
    )
    locale.bindtextdomain("dailies", config.LOCALEDIR)
    locale.textdomain("dailies")
    gettext.install("dailies", config.LOCALEDIR)
    Gio.resources_register(Gio.Resource.load(str(Path(config.PKGDATADIR) / "dailies.gresource")))
    return Application().run(sys.argv)
