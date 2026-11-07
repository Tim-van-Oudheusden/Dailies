"""The main window's built-in browser page on the navigation view; run by Meson (see tests/meson.build).

The window is a widget with animated page transitions, so the module starts a private Broadway server like
tests/gi/test_tile.py, and keeps animations on.
"""

import dataclasses
import gettext
import http.server
import importlib.util
import os
import sys
import tempfile
import threading
import time
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

# The built-in browser writes its website data here, not into the home directory of whoever runs the tests.
_HOME = Path(tempfile.mkdtemp())
os.environ.update(XDG_DATA_HOME=str(_HOME / "data"), XDG_CACHE_HOME=str(_HOME / "cache"))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

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

from gi.repository import Adw, Gtk, WebKit

Adw.init()
Gio.resources_register(Gio.Resource.load(os.environ["DAILIES_GRESOURCE"]))

from dailies.application import _SEARCH_ACCELS, Application
from dailies.core.cache import CacheDir
from dailies.core.web import display_host
from dailies.data.done_today import DoneToday
from dailies.data.favorites import Favorites
from dailies.data.store import Store
from dailies.ui import opener
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


class Site(http.server.BaseHTTPRequestHandler):
    """A page with a `target="_blank"` link, a file type WebKit cannot show, a frame of that type and a download."""

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/x-dailies-test" if self.path == "/unknown" else "text/html")
        if self.path == "/download":
            self.send_header("Content-Disposition", "attachment; filename=page.html")
        self.end_headers()
        self.wfile.write(b'<title>Site</title><a id="link" target="_blank" href="/linked">Rules</a>')
        if self.path == "/framed":
            self.wfile.write(b'<iframe src="/unknown"></iframe>')

    def log_message(self, *_args: object) -> None:
        pass


class WindowTest(unittest.TestCase):
    def setUp(self) -> None:
        Gtk.Settings.get_default().props.gtk_enable_animations = True
        # One application id per test: a registered application stays exported on the bus for the whole run.
        self.app = Adw.Application(
            application_id=f"{SCHEMA_ID}.Test.{self._testMethodName}", flags=Gio.ApplicationFlags.NON_UNIQUE
        )
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


class BrowserPageTest(WindowTest):
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

    def test_a_game_with_another_session_replaces_the_shown_page(self) -> None:
        self.app.settings.set_string("session-isolation", "per-game")
        self.addCleanup(self.app.settings.reset, "session-isolation")
        first, second = (
            dataclasses.replace(game, id=name) for game, name in zip(self.games, ("first", "second"), strict=True)
        )
        self.window.open_game(first)
        assert run_until(lambda: self.view.props.navigation_stack.get_n_items() == 2)
        old_page = self.view.props.visible_page
        spin(0.6)

        self.window.open_game(second)

        assert self.criticals == [], self.criticals
        page = self.view.props.visible_page
        assert page is not old_page
        assert page.session != old_page.session
        assert self.view.props.navigation_stack.get_n_items() == 2
        spin(0.6)
        assert self.view.props.visible_page is page
        assert self.criticals == [], self.criticals
        sessions = _HOME / "data" / "dailies" / "web" / "games"
        assert sorted(p.name for p in sessions.iterdir()) == ["first", "second"]

    def test_ctrl_f_belongs_to_the_web_page_while_the_browser_is_shown(self) -> None:
        # The real handler, which Application connects once it creates the window, on this harness's application.
        handler = Application._on_visible_page  # noqa: SLF001 - the harness's application is not an Application
        self.view.connect("notify::visible-page", lambda view, pspec: handler(self.app, view, pspec))
        self.app.set_accels_for_action("win.search", _SEARCH_ACCELS)

        self.window.open_game(self.games[0])
        assert run_until(lambda: self.view.props.visible_page.props.tag == "browser")
        assert self.app.get_accels_for_action("win.search") == []

        self.view.pop()
        assert run_until(lambda: self.view.props.visible_page.props.tag == "library")
        assert self.app.get_accels_for_action("win.search") == ["<Control>f"]

    def test_search_shows_the_content_of_a_collapsed_window(self) -> None:
        split_view = self.window.split_view
        split_view.props.collapsed = True
        split_view.props.show_content = False

        self.window.lookup_action("search").activate(None)

        assert split_view.props.show_content
        assert self.window.search_bar.props.search_mode_enabled


class PageDecisionsTest(WindowTest):
    """What the built-in browser does with what a real page asks for; only the host's browser at the end is fake."""

    def setUp(self) -> None:
        super().setUp()
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.site = f"http://127.0.0.1:{server.server_address[1]}"
        launch = mock.patch.object(opener, "launch_external")
        self.launched = launch.start()
        self.addCleanup(launch.stop)
        toast = mock.patch.object(self.window.toast_overlay, "add_toast")
        self.toast = toast.start()
        self.addCleanup(toast.stop)
        self.window.open_game(dataclasses.replace(self.games[0], url=f"{self.site}/"))
        page = self.view.props.visible_page
        self.addCleanup(self.close_page, page)
        self.web_view = page.overlay.get_child()
        assert run_until(lambda: self.web_view.get_title() == "Site")
        self.toast.reset_mock()

    def close_page(self, page: Adw.NavigationPage) -> None:
        # WebKit crashes taking the snapshot of a navigation that commits in a live view with no window, and this test
        # holds on to the view: let the last navigation end before the window goes.
        assert run_until(lambda: not self.web_view.is_loading())
        page.close()
        assert run_until(lambda: page.overlay.get_child() is None)

    def run_script(self, script: str) -> None:
        """Run `script` in the page as a user's click would: a pop-up needs one."""
        finished: list[bool] = []
        self.web_view.evaluate_javascript(script, -1, None, None, None, lambda *_args: finished.append(True))
        assert run_until(lambda: bool(finished))

    def launched_urls(self) -> list[str]:
        return [launch.args[1] for launch in self.launched.call_args_list]

    def test_a_script_pop_up_goes_to_the_browser_and_says_so(self) -> None:
        self.run_script(f"window.open('{self.site}/pop-up')")

        assert run_until(lambda: self.launched.called)
        self.launched.assert_called_once_with(self.window, f"{self.site}/pop-up")
        assert self.web_view.get_uri() == f"{self.site}/"
        assert self.toast.call_args.args[0].props.title == "Opened in your browser"

    def test_open_here_loads_a_pop_up_in_the_page_that_opened_it(self) -> None:
        page = self.view.props.visible_page
        self.run_script(f"window.open('{self.site}/pop-up')")
        assert run_until(lambda: self.toast.called)

        toast = self.toast.call_args.args[0]
        assert toast.props.button_label == "Open Here"
        toast.emit("button-clicked")

        assert run_until(lambda: self.web_view.get_uri() == f"{self.site}/pop-up")
        assert self.view.props.visible_page is page

    def test_a_pop_up_on_any_other_scheme_starts_nothing_on_the_host(self) -> None:
        for uri in ("file:///etc/passwd", "smb://host/share", "x-dailies-test://run", "about:blank"):
            self.run_script(f"window.open('{uri}')")
        # WebKit answers in order, so once this one is through the ones before it have been decided.
        self.run_script(f"window.open('{self.site}/last')")

        assert run_until(lambda: self.launched.called)
        assert self.launched_urls() == [f"{self.site}/last"]
        assert self.toast.call_count == 1

    def test_a_download_with_a_link_that_is_not_a_web_link_starts_nothing_on_the_host(self) -> None:
        self.window.open_external("file:///etc/passwd")
        self.window.open_external("data:text/plain,hello")

        self.launched.assert_not_called()

    def test_a_target_blank_link_loads_in_the_page(self) -> None:
        self.run_script("document.getElementById('link').click()")

        assert run_until(lambda: self.web_view.get_uri() == f"{self.site}/linked")
        self.launched.assert_not_called()

    def test_a_file_type_webkit_cannot_show_goes_to_the_browser(self) -> None:
        self.web_view.load_uri(f"{self.site}/unknown")

        assert run_until(lambda: self.launched.called)
        assert self.launched_urls() == [f"{self.site}/unknown"]
        assert run_until(lambda: self.web_view.get_uri() == f"{self.site}/")

    def test_a_frame_of_such_a_type_starts_nothing_on_the_host(self) -> None:
        finished: list[bool] = []
        self.web_view.connect(
            "load-changed", lambda _view, event: event != WebKit.LoadEvent.FINISHED or finished.append(True)
        )

        self.web_view.load_uri(f"{self.site}/framed")

        assert run_until(lambda: bool(finished))
        spin(0.2)
        self.launched.assert_not_called()

    def test_a_download_goes_to_the_browser_and_writes_nothing(self) -> None:
        self.addCleanup(Gio.Application.set_default, Gio.Application.get_default())
        Gio.Application.set_default(self.app)
        failures: list[GLib.Error] = []
        self.web_view.get_network_session().connect(
            "download-started", lambda _session, download: download.connect("failed", lambda _d, e: failures.append(e))
        )

        self.web_view.load_uri(f"{self.site}/download")

        assert run_until(lambda: self.launched.called and bool(failures))
        assert self.launched_urls() == [f"{self.site}/download"]
        assert failures[0].matches(WebKit.download_error_quark(), WebKit.DownloadError.CANCELLED_BY_USER)

    def answer_of(self, body: str) -> str:
        """The value the async function with `body` resolves to in the page."""
        answers: list[str] = []
        self.web_view.call_async_javascript_function(
            body,
            -1,
            None,
            None,
            None,
            None,
            lambda view, result: answers.append(view.call_async_javascript_function_finish(result).to_string()),
        )
        assert run_until(lambda: bool(answers))
        return answers[0]

    def test_a_page_is_refused_what_it_asks_permission_for(self) -> None:
        assert self.answer_of("return await Notification.requestPermission()") == "denied"
        location = """return await new Promise(answer => navigator.geolocation.getCurrentPosition(
            () => answer("allowed"), error => answer(error.code == error.PERMISSION_DENIED ? "denied" : "other")))"""
        assert self.answer_of(location) == "denied"

    def test_a_page_that_closes_itself_returns_to_the_library(self) -> None:
        page = self.view.props.visible_page

        # A page with one history entry may close itself, as a page a game opened does.
        self.run_script("window.close()")

        assert run_until(lambda: self.view.props.visible_page.props.tag == "library")
        assert page.overlay.get_child() is None
        assert not self.window.lookup_action("game-done").props.enabled
        assert self.criticals == [], self.criticals

    def test_a_page_that_asks_to_stay_is_closed_when_left(self) -> None:
        page = self.view.props.visible_page
        self.run_script("addEventListener('beforeunload', event => { event.preventDefault(); event.returnValue = '' })")

        self.view.pop()

        assert run_until(lambda: page.overlay.get_child() is None)

    def test_a_page_still_shown_keeps_its_own_questions(self) -> None:
        self.run_script("addEventListener('beforeunload', event => { event.preventDefault(); event.returnValue = '' })")

        self.run_script(f"location.href = '{self.site}/pop-up'")

        # WebKit shows its dialog as a child of the view, next to the web content. Only Back answers for the user.
        assert run_until(lambda: self.web_view.get_first_child().get_next_sibling() is not None)
        assert self.web_view.get_uri() == f"{self.site}/"


if __name__ == "__main__":
    unittest.main()
