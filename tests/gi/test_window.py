"""The main window's built-in browser page on the navigation view; run by Meson (see tests/meson.build).

The window is a widget with animated page transitions, so the module starts a private Broadway server like
tests/gi/test_tile.py, and keeps animations on.
"""

import dataclasses
import gettext
import importlib.util
import os
import sys
import tempfile
import time
import unittest
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gio, GLib


def _start_display() -> None:
    # The build sandbox has no display; a Broadway server needs nothing but a socket in the runtime directory.
    runtime = tempfile.mkdtemp()
    os.environ["XDG_RUNTIME_DIR"] = runtime
    display = str(10 + os.getpid() % 500)
    server = Gio.Subprocess.new(
        [os.environ["BROADWAYD"], f":{display}"],
        Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE,
    )
    deadline = time.monotonic() + 10
    while not any(Path(runtime).glob("broadway*.socket")) and time.monotonic() < deadline:
        time.sleep(0.05)
    os.environ.update(GDK_BACKEND="broadway", BROADWAY_DISPLAY=f":{display}")
    unittest.addModuleCleanup(server.force_exit)


def _load_config() -> None:
    # dailies/config.py exists only in the build directory.
    spec = importlib.util.spec_from_file_location("dailies.config", os.environ["DAILIES_CONFIG"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["dailies.config"] = module


_start_display()
_load_config()
gettext.install("dailies")

from gi.repository import Adw, Gtk

Adw.init()
Gio.resources_register(Gio.Resource.load(os.environ["DAILIES_GRESOURCE"]))

from dailies.core.cache import CacheDir
from dailies.core.web import display_host
from dailies.data.done_today import DoneToday
from dailies.data.favorites import Favorites
from dailies.data.store import Store
from dailies.window import Window

BUNDLE = Path(__file__).resolve().parents[2] / "data" / "v1"
SCHEMA_ID = os.environ["DAILIES_SCHEMA_ID"]


def run_until(done: Callable[[], bool], timeout: float = 10) -> bool:
    context = GLib.MainContext.default()
    deadline = time.monotonic() + timeout
    while not done() and time.monotonic() < deadline:
        context.iteration(False)
        time.sleep(0.005)
    return done()


def spin(seconds: float) -> None:
    """Run the main loop for `seconds`, e.g. through a page transition."""
    run_until(lambda: False, timeout=seconds)


class BrowserPageTest(unittest.TestCase):
    def setUp(self) -> None:
        Gtk.Settings.get_default().props.gtk_enable_animations = True
        self.app = Adw.Application(application_id=f"{SCHEMA_ID}.Test", flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.app.register(None)
        self.app.settings = Gio.Settings.new(SCHEMA_ID)
        self.app.settings.set_string("open-mode", "in-app")
        self.app.favorites = Favorites(self.app.settings)
        self.app.done_today = DoneToday(self.app.settings)
        self.addCleanup(self.app.done_today.close)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = Store(CacheDir(Path(directory.name) / "v1"), BUNDLE, self.app.favorites, done_today=self.app.done_today)
        store.load_initial()
        # Hosts that never resolve: the test needs no network, and no site retitles the page.
        game = store.model.get_item(0).props.game
        self.games = [dataclasses.replace(game, url=f"https://{name}.invalid/") for name in ("first", "second")]
        self.window = Window(application=self.app, store=store, state=Gio.Settings.new(f"{SCHEMA_ID}.State"))
        self.addCleanup(self.window.destroy)
        self.view = self.window.navigation_view
        self.window.present()
        assert run_until(self.window.get_mapped)

        self.criticals: list[str] = []
        handler = GLib.log_set_handler(
            "Adwaita",
            GLib.LogLevelFlags.LEVEL_CRITICAL | GLib.LogLevelFlags.LEVEL_WARNING,
            lambda _domain, _level, message, *_args: self.criticals.append(message),
        )
        self.addCleanup(GLib.log_remove_handler, "Adwaita", handler)

    def test_a_game_opened_while_the_last_one_animates_out_is_shown(self) -> None:
        first, second = self.games
        self.window.open_game(first)
        assert run_until(lambda: self.view.props.navigation_stack.get_n_items() == 2)
        old_page = self.view.props.visible_page
        # Let the push animation finish, so the pop below animates.
        spin(0.6)

        self.view.pop()
        assert self.view.find_page("browser") is old_page, "the popped page slides out"
        self.window.open_game(second)

        assert self.criticals == [], self.criticals
        page = self.view.props.visible_page
        assert page is not old_page
        assert page.props.tag == "browser"
        assert page.props.title == display_host(second.url)
        spin(0.6)
        assert self.view.props.visible_page is page
        self.view.pop()
        assert run_until(lambda: self.view.props.visible_page.props.tag == "library")
        assert self.criticals == [], self.criticals


if __name__ == "__main__":
    unittest.main()
