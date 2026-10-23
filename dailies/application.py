import ctypes
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

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from dailies import config
from dailies.core import cache
from dailies.core.cache import CacheDir, Outcome
from dailies.data.done_today import DoneToday
from dailies.data.favorites import Favorites
from dailies.data.fetcher import Fetcher
from dailies.data.store import Store
from dailies.ui import opener
from dailies.ui.favorites_transfer import Transfer

_REFRESH_ACCELS = ["<Control>r"]
_GAME_MENU_ACCELS = ["<Shift>F10", "Menu"]


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
        # Prunes the marks of earlier days.
        self.done_today = DoneToday(self.settings)
        cache_dir = CacheDir(Path(GLib.get_user_cache_dir()) / "dailies" / "v1")
        fetcher = Fetcher(cache_dir, _data_urls(), config.VERSION)
        self.store = Store(
            cache_dir, Path(config.PKGDATADIR) / "data" / "v1", self.favorites, fetcher, done_today=self.done_today
        )
        self.store.load_initial()
        self._add_actions()

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
        # accelerators win over page shortcuts, so the browser page borrows it while it is shown. Shift+F10 and Menu
        # are left to the web page's own context menu there.
        browser = view.props.visible_page.props.tag == "browser"
        self.set_accels_for_action("app.refresh", [] if browser else _REFRESH_ACCELS)
        self.set_accels_for_action("win.show-game-menu", [] if browser else _GAME_MENU_ACCELS)

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

            browser_page.clear_all_blocking(self.settings)
        Adw.Application.do_shutdown(self)

    def _add_actions(self) -> None:
        # app.shortcuts comes from Adw.Application, which finds shortcuts-dialog.ui in the gresource; the browser
        # page's own keys live on the page. data/ui/shortcuts-dialog.blp lists every accelerator set here.
        for name, activate, accels in (
            ("quit", self.quit, ["<Control>q"]),
            ("about", self._show_about, []),
            ("preferences", self._on_preferences, ["<Control>comma"]),
            ("refresh", self._on_refresh, _REFRESH_ACCELS),
            ("export-favorites", lambda: self._favorites_transfer().ask_export(), []),
            ("import-favorites", lambda: self._favorites_transfer().ask_import(), []),
        ):
            action = Gio.SimpleAction(name=name)
            action.connect("activate", lambda _action, _param, activate=activate: activate())
            self.add_action(action)
            self.set_accels_for_action(f"app.{name}", accels)
        # The window adds these actions (dailies/window.py).
        self.set_accels_for_action("win.toggle-favorite", ["<Control>d"])
        self.set_accels_for_action("win.search", ["<Control>f"])
        self.set_accels_for_action("win.show-game-menu", _GAME_MENU_ACCELS)

    def _favorites_transfer(self) -> Transfer:
        window = self.props.active_window
        return Transfer(window, self.favorites, window.toast_overlay.add_toast)

    def _show_about(self) -> None:
        # Name, icon, developer, version, URLs, licence and release notes come from the bundled metainfo.
        about = Adw.AboutDialog.new_from_appdata(f"{config.PREFIX}/{config.APP_ID}.metainfo.xml", config.VERSION)
        about.set_developers(["Tim van Oudheusden https://github.com/Tim-van-Oudheusden"])
        about.set_designers(["Tim van Oudheusden https://github.com/Tim-van-Oudheusden"])
        # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
        about.set_translator_credits(_("translator-credits"))
        about.add_legal_section(
            _("Trademarks"),
            None,
            Gtk.License.CUSTOM,
            _(
                "Dailies is not affiliated with The New York Times, Merriam-Webster, LinkedIn or any game listed. "
                "Game names are trademarks of their owners; Dailies only opens their public websites."
            ),
        )
        about.present(self.props.active_window)


def _data_urls() -> list[str]:
    # Development builds can point at a local server, e.g. DAILIES_DATA_URLS=http://127.0.0.1:8000/v1/
    if config.PROFILE == "development" and (override := os.environ.get("DAILIES_DATA_URLS")):
        return override.split()
    return config.DATA_URLS


def _install_gettext(localedir: str) -> None:
    """Install _() and ngettext() for the Python strings, and bind the C gettext GtkBuilder translates the UI with."""
    if hasattr(locale, "bindtextdomain"):
        locale.bindtextdomain("dailies", localedir)
        locale.textdomain("dailies")
        gettext.install("dailies", localedir, names=["ngettext"])
        return
    # MSYS2's Python, the Windows build's (#84), has no locale.bindtextdomain: bind GLib's libintl directly. Its
    # translations come in the ANSI code page unless asked for UTF-8, which GTK expects.
    libintl = ctypes.CDLL("libintl-8.dll")
    libintl.libintl_wbindtextdomain.argtypes = [ctypes.c_char_p, ctypes.c_wchar_p]
    libintl.libintl_wbindtextdomain(b"dailies", localedir)
    libintl.libintl_bind_textdomain_codeset.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    libintl.libintl_bind_textdomain_codeset(b"dailies", b"UTF-8")
    libintl.libintl_textdomain.argtypes = [ctypes.c_char_p]
    libintl.libintl_textdomain(b"dailies")
    # Windows sets no LANGUAGE or LANG for Python's gettext to read; GLib asks Windows for the user's languages.
    gettext.translation("dailies", localedir, languages=GLib.get_language_names(), fallback=True).install(
        names=["ngettext"]
    )


def main() -> int:
    """Set up gettext and resources, then run the application."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    logging.basicConfig(
        format="%(name)s: %(message)s",
        level=logging.DEBUG if os.environ.get("G_MESSAGES_DEBUG") else logging.WARNING,
    )
    _install_gettext(config.LOCALEDIR)
    Gio.resources_register(Gio.Resource.load(str(Path(config.PKGDATADIR) / "dailies.gresource")))
    return Application().run(sys.argv)
