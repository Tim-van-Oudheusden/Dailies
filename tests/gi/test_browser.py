"""The built-in browser's network sessions and WebKit settings (#74); run by Meson (see tests/meson.build).

WebKit needs a display, so the module starts a private Broadway server like tests/gi/test_opening.py, and points the
XDG data and cache directories at a temporary directory before GLib reads them.
"""

import gettext
import importlib.util
import os
import shutil
import sys
import tempfile
import time
import unittest
from collections.abc import Callable
from pathlib import Path

HOME = Path(tempfile.mkdtemp())
os.environ.update(XDG_DATA_HOME=str(HOME / "data"), XDG_CACHE_HOME=str(HOME / "cache"))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
gi.require_version("Soup", "3.0")

from gi.repository import Gio, GLib


def _start_display() -> None:
    runtime = tempfile.mkdtemp()
    os.environ["XDG_RUNTIME_DIR"] = runtime
    display = str(1010 + os.getpid() % 500)
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
    spec = importlib.util.spec_from_file_location("dailies.config", os.environ["DAILIES_CONFIG"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["dailies.config"] = module


_start_display()
_load_config()
gettext.install("dailies")
unittest.addModuleCleanup(shutil.rmtree, HOME, ignore_errors=True)

from gi.repository import Adw, Soup, WebKit

Adw.init()
Gio.resources_register(Gio.Resource.load(os.environ["DAILIES_GRESOURCE"]))

from dailies.ui import browser_page, opener

WEB_DATA = HOME / "data" / "dailies" / "web"
WEB_CACHE = HOME / "cache" / "dailies" / "web"
KEYS = ("session-isolation", "cookie-policy", "itp-enabled", "hardware-acceleration", "user-agent", "developer-extras")


def run_until(done: list) -> None:
    context = GLib.MainContext.default()
    deadline = time.monotonic() + 15
    while not done and time.monotonic() < deadline:
        context.iteration(False)
        time.sleep(0.005)
    assert done, "WebKit did not answer"


def add_cookie(session: WebKit.NetworkSession, name: str) -> None:
    done: list[bool] = []
    cookie = Soup.Cookie.new(name, "1", "www.nytimes.com", "/", 3600)
    session.get_cookie_manager().add_cookie(cookie, None, lambda m, r: done.append(m.add_cookie_finish(r)))
    run_until(done)


def cookie_names(session: WebKit.NetworkSession) -> set[str]:
    done: list[list] = []
    manager = session.get_cookie_manager()
    manager.get_all_cookies(None, lambda m, r: done.append(m.get_all_cookies_finish(r)))
    run_until(done)
    return {cookie.get_name() for cookie in done[0]}


def accept_policy(session: WebKit.NetworkSession) -> WebKit.CookieAcceptPolicy:
    done: list = []
    manager = session.get_cookie_manager()
    manager.get_accept_policy(None, lambda m, r: done.append(m.get_accept_policy_finish(r)))
    run_until(done)
    return done[0]


def data_dir(session: WebKit.NetworkSession) -> Path:
    return Path(session.get_website_data_manager().props.base_data_directory)


def cache_dir(session: WebKit.NetworkSession) -> Path:
    return Path(session.get_website_data_manager().props.base_cache_directory)


def user_agent_of(view: WebKit.WebView) -> str:
    done: list[str] = []
    view.evaluate_javascript(
        "navigator.userAgent",
        -1,
        None,
        None,
        None,
        lambda v, r: done.append(v.evaluate_javascript_finish(r).to_string()),
    )
    run_until(done)
    return done[0]


def load(view: WebKit.WebView, start: Callable[[], None]) -> None:
    """Run `start` and wait until the page it loads (or reloads) has finished."""
    done: list[bool] = []

    def on_load_changed(_view: WebKit.WebView, event: WebKit.LoadEvent) -> None:
        if event == WebKit.LoadEvent.FINISHED:
            done.append(True)

    handler = view.connect("load-changed", on_load_changed)
    start()
    run_until(done)
    view.disconnect(handler)


class BrowserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Gio.Settings.new(os.environ["DAILIES_SCHEMA_ID"])
        for key in KEYS:
            self.settings.reset(key)
            self.addCleanup(self.settings.reset, key)


class SessionTest(BrowserTest):
    def test_by_default_every_game_shares_the_v0_1_session(self) -> None:
        wordle = browser_page.session_for(self.settings, "wordle")
        connections = browser_page.session_for(self.settings, "connections")

        assert wordle is connections
        assert data_dir(wordle) == WEB_DATA / "shared"
        assert cache_dir(wordle) == WEB_CACHE / "shared"
        assert browser_page.session_for(self.settings, None) is wordle

    def test_per_game_sessions_have_their_own_directories_and_cookies(self) -> None:
        self.settings.set_string("session-isolation", "per-game")
        wordle = browser_page.session_for(self.settings, "wordle")
        connections = browser_page.session_for(self.settings, "connections")

        assert wordle is not connections
        assert browser_page.session_for(self.settings, "wordle") is wordle
        assert data_dir(wordle) == WEB_DATA / "games" / "wordle"
        assert cache_dir(connections) == WEB_CACHE / "games" / "connections"

        add_cookie(wordle, "nyt-s-wordle")
        add_cookie(connections, "nyt-s-connections")

        assert cookie_names(wordle) == {"nyt-s-wordle"}
        assert cookie_names(connections) == {"nyt-s-connections"}
        assert (WEB_DATA / "games" / "wordle" / "cookies.sqlite").exists()
        assert (WEB_DATA / "games" / "connections" / "cookies.sqlite").exists()

    def test_a_game_set_to_an_isolated_session_gets_one_while_others_share(self) -> None:
        game = opener.game_settings("absurdle")
        game.set_boolean("isolated-session", True)
        self.addCleanup(game.reset, "isolated-session")

        assert data_dir(browser_page.session_for(self.settings, "absurdle")) == WEB_DATA / "games" / "absurdle"
        assert data_dir(browser_page.session_for(self.settings, "wordle")) == WEB_DATA / "shared"

    def test_the_cookie_policy_and_itp_settings_reach_the_session(self) -> None:
        session = browser_page.session_for(self.settings, None)
        assert accept_policy(session) == WebKit.CookieAcceptPolicy.ALWAYS
        assert not session.get_itp_enabled()

        self.settings.set_string("cookie-policy", "never")
        assert accept_policy(session) == WebKit.CookieAcceptPolicy.NEVER
        self.settings.set_string("cookie-policy", "no-third-party")
        assert accept_policy(session) == WebKit.CookieAcceptPolicy.NO_THIRD_PARTY

        # While ITP is on WebKit accepts third-party cookies under its own rules, so it reports ALWAYS.
        self.settings.set_boolean("itp-enabled", True)
        assert session.get_itp_enabled()

    def test_clearing_reaches_every_session_including_ones_not_opened_yet(self) -> None:
        self.settings.set_string("session-isolation", "per-game")
        shared = browser_page.session_for(self.settings, None)
        add_cookie(shared, "shared-cookie")
        wordle = browser_page.session_for(self.settings, "wordle")
        add_cookie(wordle, "wordle-cookie")
        # A per-game session from an earlier run, with a cookie on disk that nothing in this run has opened.
        framed_dir = WEB_DATA / "games" / "framed"
        framed_dir.mkdir(parents=True)
        shutil.copy(WEB_DATA / "games" / "wordle" / "cookies.sqlite", framed_dir / "cookies.sqlite")

        done: list[bool] = []
        browser_page.clear_all(self.settings, lambda: done.append(True))
        run_until(done)

        assert cookie_names(shared) == set()
        assert cookie_names(wordle) == set()
        framed = browser_page.session_for(self.settings, "framed")
        assert data_dir(framed) == WEB_DATA / "games" / "framed"
        assert cookie_names(framed) == set()


class WebSettingsTest(BrowserTest):
    def test_the_defaults_are_those_of_v0_1(self) -> None:
        settings = browser_page.web_settings(self.settings)

        assert settings.get_hardware_acceleration_policy() == WebKit.Settings().get_hardware_acceleration_policy()
        assert settings.get_user_agent().endswith(" Dailies/" + sys.modules["dailies.config"].VERSION)
        assert not settings.get_enable_developer_extras()
        assert not settings.get_javascript_can_open_windows_automatically()
        assert not settings.get_enable_webrtc()

    def test_the_settings_reach_webkit(self) -> None:
        self.settings.set_string("hardware-acceleration", "never")
        self.settings.set_string("user-agent", "Mozilla/5.0 Compat/1.0")
        self.settings.set_boolean("developer-extras", True)

        settings = browser_page.web_settings(self.settings)

        assert settings.get_hardware_acceleration_policy() == WebKit.HardwareAccelerationPolicy.NEVER
        assert settings.get_user_agent() == "Mozilla/5.0 Compat/1.0"
        assert settings.get_enable_developer_extras()


class OpenPageTest(BrowserTest):
    def open_page(self) -> WebKit.WebView:
        page = browser_page.BrowserPage(
            settings=self.settings,
            game_id=None,
            open_external=lambda _uri: None,
            hand_off_pop_up=lambda _uri: None,
            add_toast=lambda _toast: None,
        )
        self.addCleanup(page.close)
        self.page = page
        return page.overlay.get_child()

    def test_changing_a_browser_setting_updates_the_open_page(self) -> None:
        view = self.open_page()

        self.settings.set_string("hardware-acceleration", "never")
        self.settings.set_boolean("developer-extras", True)

        assert view.get_settings().get_hardware_acceleration_policy() == WebKit.HardwareAccelerationPolicy.NEVER
        assert view.get_settings().get_enable_developer_extras()

        self.settings.reset("hardware-acceleration")
        self.settings.reset("developer-extras")

        assert (
            view.get_settings().get_hardware_acceleration_policy()
            == WebKit.Settings().get_hardware_acceleration_policy()
        )
        assert not view.get_settings().get_enable_developer_extras()

    def test_a_new_user_agent_reaches_the_shown_page_through_a_reload(self) -> None:
        view = self.open_page()
        load(view, lambda: view.load_html("<p>Wordle</p>", "http://127.0.0.1/"))
        assert user_agent_of(view).endswith(" Dailies/" + sys.modules["dailies.config"].VERSION)

        load(view, lambda: self.settings.set_string("user-agent", "Mozilla/5.0 Compat/1.0"))

        assert view.get_settings().get_user_agent() == "Mozilla/5.0 Compat/1.0"
        assert user_agent_of(view) == "Mozilla/5.0 Compat/1.0"

        load(view, lambda: self.settings.reset("user-agent"))

        assert user_agent_of(view).endswith(" Dailies/" + sys.modules["dailies.config"].VERSION)

    def test_a_closed_page_no_longer_follows_the_settings(self) -> None:
        view = self.open_page()

        self.page.close()
        self.settings.set_boolean("developer-extras", True)

        assert not view.get_settings().get_enable_developer_extras()


if __name__ == "__main__":
    unittest.main()
