"""The built-in browser: an `Adw.NavigationPage` around one `WebKit.WebView` with a persistent session.

Imported only when `opener.have_webkit()` is true; importing this module loads WebKit.

By default all games share one `WebKit.NetworkSession` per app run, so sibling games share a login. With
`session-isolation` set to per-game, or a game's own `isolated-session` key set, a game gets a session of its own in
`web/games/<id>` (`dailies.core.web.session_dir`). Every session stores its cookies in its own SQLite file so that
logins and streaks survive a restart, and follows the `cookie-policy` and `itp-enabled` settings. Pages are shown as
the sites ship them: no injected scripts or styles, no content blocking, and the user agent changes only when the user
sets `user-agent`. Pop-ups and downloads go to the external browser and permission requests are denied.
"""

import logging
from collections.abc import Callable
from pathlib import Path, PurePosixPath

import gi

gi.require_version("WebKit", "6.0")

from gi.repository import Adw, Gio, GLib, Gtk, WebKit

from dailies import config
from dailies.core import web
from dailies.core.web import SessionIsolation, display_host, site_matches
from dailies.ui import opener

log = logging.getLogger(__name__)

#: How long quitting waits for the website data to be cleared when `clear-web-data-on-exit` is set.
_CLEAR_ON_EXIT_TIMEOUT_SECONDS = 5

_BACK_BUTTON = 8
_FORWARD_BUTTON = 9

_SHORTCUTS = (
    ("<Alt>Left", "browser.back"),
    ("<Alt>Right", "browser.forward"),
    ("<Control>r", "browser.reload"),
    ("<Control>l", "browser.show-address"),
    ("<Control><Shift>o", "browser.open-external"),
)

#: The settings every live session follows as they change.
_SESSION_KEYS = ("cookie-policy", "itp-enabled")

#: The network sessions of this app run, by session directory, made the first time a page or a clear needs them.
_sessions: dict[PurePosixPath, WebKit.NetworkSession] = {}
#: The settings objects whose session keys the live sessions follow.
_watched: list[Gio.Settings] = []


def _web_dirs() -> tuple[Path, Path]:
    """The data and cache directories that hold every session's directory."""
    return (
        Path(GLib.get_user_data_dir()) / "dailies" / "web",
        Path(GLib.get_user_cache_dir()) / "dailies" / "web",
    )


def session_dir_for(settings: Gio.Settings, game_id: str | None) -> PurePosixPath:
    """The session directory the game `game_id` uses now (the shared one when there is no game)."""
    game = opener.game_settings(game_id) if game_id else None
    return web.session_dir(
        SessionIsolation.from_id(settings.get_string("session-isolation")),
        game_id,
        isolated=game is not None and game.get_boolean("isolated-session"),
    )


def session_for(settings: Gio.Settings, game_id: str | None) -> WebKit.NetworkSession:
    """The network session the game `game_id` uses now, following the session settings."""
    return _session(settings, session_dir_for(settings, game_id))


def _session(settings: Gio.Settings, name: PurePosixPath) -> WebKit.NetworkSession:
    if settings not in _watched:
        _watched.append(settings)
        for key in _SESSION_KEYS:
            settings.connect(f"changed::{key}", _on_session_setting_changed)
    if (session := _sessions.get(name)) is not None:
        return session
    data_root, cache_root = _web_dirs()
    data_dir = data_root / name
    session = WebKit.NetworkSession.new(str(data_dir), str(cache_root / name))
    # Without persistent storage cookies live in memory only, and every streak is lost on quit.
    session.get_cookie_manager().set_persistent_storage(
        str(data_dir / "cookies.sqlite"), WebKit.CookiePersistentStorage.SQLITE
    )
    session.set_tls_errors_policy(WebKit.TLSErrorsPolicy.FAIL)
    session.connect("download-started", _on_download_started)
    _apply_session_settings(settings, session)
    _sessions[name] = session
    return session


def _apply_session_settings(settings: Gio.Settings, session: WebKit.NetworkSession) -> None:
    # The default, always, keeps log-in flows working (the New York Times redirects through third-party domains that
    # must be able to set cookies). While ITP is on, WebKit treats no-third-party as always.
    policy = web.cookie_accept_policy(settings.get_string("cookie-policy"))
    session.get_cookie_manager().set_accept_policy(getattr(WebKit.CookieAcceptPolicy, policy))
    session.set_itp_enabled(settings.get_boolean("itp-enabled"))


def _on_session_setting_changed(settings: Gio.Settings, _key: str) -> None:
    for session in _sessions.values():
        _apply_session_settings(settings, session)


def web_settings(settings: Gio.Settings) -> WebKit.Settings:
    """The WebKit settings of a new page: the built-in browser's hardening plus the user's browser settings."""
    web_view_settings = WebKit.Settings(
        javascript_can_open_windows_automatically=False,
        allow_top_navigation_to_data_urls=False,
        enable_webrtc=False,
        enable_back_forward_navigation_gestures=True,
        enable_smooth_scrolling=True,
        enable_developer_extras=settings.get_boolean("developer-extras"),
    )
    if policy := web.hardware_acceleration_policy(settings.get_string("hardware-acceleration")):
        web_view_settings.set_hardware_acceleration_policy(getattr(WebKit.HardwareAccelerationPolicy, policy))
    if user_agent := web.custom_user_agent(settings.get_string("user-agent")):
        web_view_settings.set_user_agent(user_agent)
    else:
        web_view_settings.set_user_agent_with_application_details("Dailies", config.VERSION)
    return web_view_settings


def _on_download_started(_session: WebKit.NetworkSession, download: WebKit.Download) -> None:
    # The sandbox has no download folder: hand the link to the external browser before anything is written.
    download.cancel()
    window = Gio.Application.get_default().props.active_window
    if window is not None:
        window.open_external(download.get_request().get_uri())


def _game_dirs_on_disk() -> set[str]:
    names: set[str] = set()
    for root in _web_dirs():
        games = root / "games"
        if games.is_dir():
            names.update(child.name for child in games.iterdir() if child.is_dir())
    return names


def clear_all(settings: Gio.Settings, callback: Callable[[], None] | None = None) -> None:
    """Remove all website data (cookies, storage, caches) of every session, then call `callback`.

    That is the shared session and every per-game session on disk, also those this run has not opened.
    """
    names = web.all_sessions(_game_dirs_on_disk())
    pending = len(names)

    def on_cleared(manager: WebKit.WebsiteDataManager, result: Gio.AsyncResult) -> None:
        nonlocal pending
        try:
            manager.clear_finish(result)
        except GLib.Error as e:
            log.warning("Could not clear the website data: %s", e.message)
        pending -= 1
        if pending == 0 and callback:
            callback()

    for name in names:
        manager = _session(settings, name).get_website_data_manager()
        manager.clear(WebKit.WebsiteDataTypes.ALL, 0, None, on_cleared)


def clear_all_blocking(settings: Gio.Settings) -> None:
    """Clear all website data of every session before the app quits, waiting a few seconds at most."""
    loop = GLib.MainLoop()
    clear_all(settings, loop.quit)
    GLib.timeout_add_seconds(_CLEAR_ON_EXIT_TIMEOUT_SECONDS, loop.quit)
    loop.run()


def clear_site_data(session: WebKit.NetworkSession, host: str, callback: Callable[[], None] | None = None) -> None:
    """Remove the website data in `session` of the site at `host` and its parent domains, then call `callback`."""
    manager = session.get_website_data_manager()

    def on_fetched(manager: WebKit.WebsiteDataManager, result: Gio.AsyncResult) -> None:
        try:
            data = [item for item in manager.fetch_finish(result) if site_matches(item.get_name(), host)]
        except GLib.Error as e:
            log.warning("Could not read the website data of %s: %s", host, e.message)
            data = []
        if not data:
            if callback:
                callback()
            return
        manager.remove(WebKit.WebsiteDataTypes.ALL, data, None, on_removed)

    def on_removed(manager: WebKit.WebsiteDataManager, result: Gio.AsyncResult) -> None:
        try:
            manager.remove_finish(result)
        except GLib.Error as e:
            log.warning("Could not clear the website data of %s: %s", host, e.message)
        if callback:
            callback()

    manager.fetch(WebKit.WebsiteDataTypes.ALL, None, on_fetched)


@Gtk.Template(resource_path=f"{config.PREFIX}/ui/browser-page.ui")
class BrowserPage(Adw.NavigationPage):
    """A game's website, with history buttons, the real host in the header and "Open in Browser" in the menu.

    The page uses the network session of `game_id` (`session`), and the browser settings as they are when it is made.
    `open_external` opens a link in the default browser; `hand_off_pop_up` does the same for a script's pop-up, and
    tells the user so. Call `close()` when the page is popped: it closes the web view, which ends its web process.
    """

    __gtype_name__ = "DailiesBrowserPage"

    reload_button: Gtk.Button = Gtk.Template.Child()
    url_button: Gtk.MenuButton = Gtk.Template.Child()
    url_entry: Gtk.Entry = Gtk.Template.Child()
    window_title: Adw.WindowTitle = Gtk.Template.Child()
    overlay: Gtk.Overlay = Gtk.Template.Child()
    progress_bar: Gtk.ProgressBar = Gtk.Template.Child()

    def __init__(
        self,
        *,
        settings: Gio.Settings,
        game_id: str | None,
        open_external: Callable[[str], None],
        hand_off_pop_up: Callable[[str], None],
        add_toast: Callable[[Adw.Toast], None],
    ) -> None:
        super().__init__()
        self.session = session_dir_for(settings, game_id)
        self._network_session = _session(settings, self.session)
        self._open_external = open_external
        self._hand_off_pop_up = hand_off_pop_up
        self._add_toast = add_toast

        # A context of its own: its web processes end with it, while the network session (logins) outlives it.
        context = WebKit.WebContext()
        context.set_cache_model(WebKit.CacheModel.DOCUMENT_VIEWER)
        view = WebKit.WebView(
            web_context=context,
            network_session=self._network_session,
            settings=web_settings(settings),
            hexpand=True,
            vexpand=True,
        )
        view.connect("notify::title", lambda *_args: self._update_title())
        view.connect("notify::uri", lambda *_args: self._update_title())
        view.connect("notify::is-loading", lambda *_args: self._update_loading())
        view.connect("notify::estimated-load-progress", lambda *_args: self._update_progress())
        view.connect("load-changed", lambda *_args: self._update_history())
        view.get_back_forward_list().connect("changed", lambda *_args: self._update_history())
        view.connect("decide-policy", self._on_decide_policy)
        view.connect("create", self._on_create)
        view.connect("permission-request", self._on_permission_request)
        view.connect("close", self._on_close)
        history_buttons = Gtk.GestureClick(button=0, propagation_phase=Gtk.PropagationPhase.CAPTURE)
        history_buttons.connect("pressed", self._on_mouse_pressed)
        view.add_controller(history_buttons)
        self.overlay.set_child(view)
        self._web_view: WebKit.WebView | None = view

        # The handlers look the view up, never capture it: after `close()` nothing may keep it alive.
        self._actions = Gio.SimpleActionGroup()
        for name, activate in (
            ("back", lambda view: view.go_back()),
            ("forward", lambda view: view.go_forward()),
            ("reload", lambda view: view.reload()),
            ("stop", lambda view: view.stop_loading()),
            ("open-external", self._open_current_externally),
            ("copy-link", self._copy_link),
            ("clear-site-data", self._clear_site_data),
            ("show-address", self._show_address),
        ):
            action = Gio.SimpleAction(name=name)
            action.connect("activate", self._on_action, activate)
            self._actions.add_action(action)
        self.insert_action_group("browser", self._actions)

        # Page-scoped and in the capture phase, so the keys work while the web content has the focus.
        shortcuts = Gtk.ShortcutController(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        for trigger, action_name in _SHORTCUTS:
            shortcuts.add_shortcut(
                Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(trigger), action=Gtk.NamedAction.new(action_name))
            )
        self.add_controller(shortcuts)
        self.connect("shown", self._on_shown)

        self._update_title()
        self._update_loading()
        self._update_history()

    def load(self, uri: str) -> None:
        """Show the page at `uri`; until the page names itself, the header shows the host being loaded."""
        if self._web_view is not None:
            self._web_view.load_uri(uri)
            if not self.window_title.props.title:
                self.window_title.props.title = display_host(uri)

    def close(self) -> None:
        """Close the web view, so that its web process ends; the page shows nothing afterwards."""
        if self._web_view is not None:
            self._web_view.try_close()

    def _on_action(self, _action: Gio.SimpleAction, _param: None, activate: Callable[[WebKit.WebView], None]) -> None:
        if self._web_view is not None:
            activate(self._web_view)

    def _on_shown(self, _page: Adw.NavigationPage) -> None:
        if self._web_view is not None:
            self._web_view.grab_focus()

    def _on_close(self, view: WebKit.WebView) -> None:
        view.disconnect_by_func(self._on_close)
        # The page has run its unload handlers: dropping the last reference destroys the view and its web context,
        # which ends their web processes.
        self.overlay.set_child(None)
        self._web_view = None

    def _uri(self) -> str:
        return (self._web_view and self._web_view.get_uri()) or ""

    def _update_title(self) -> None:
        host = display_host(self._uri())
        title = self._web_view.get_title() if self._web_view else None
        self.window_title.props.title = title or host
        self.window_title.props.subtitle = host
        self.url_entry.props.text = self._uri()

    def _update_loading(self) -> None:
        loading = self._web_view is not None and self._web_view.is_loading()
        self.reload_button.props.visible = not loading
        self.progress_bar.props.visible = loading
        self._update_progress()

    def _update_progress(self) -> None:
        if self._web_view is not None:
            self.progress_bar.props.fraction = self._web_view.get_estimated_load_progress()

    def _update_history(self) -> None:
        view = self._web_view
        self._actions.lookup_action("back").props.enabled = view is not None and view.can_go_back()
        self._actions.lookup_action("forward").props.enabled = view is not None and view.can_go_forward()

    def _on_decide_policy(
        self, view: WebKit.WebView, decision: WebKit.PolicyDecision, decision_type: WebKit.PolicyDecisionType
    ) -> bool:
        if decision_type == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
            action = decision.get_navigation_action()
            if action.get_navigation_type() == WebKit.NavigationType.LINK_CLICKED:
                # A target="_blank" link: there is one view, so it loads here.
                view.load_request(action.get_request())
                decision.ignore()
                return True
            # A script's window.open(): WebKit goes on to emit `create`, which hands it to the external browser.
            return False
        if (
            decision_type == WebKit.PolicyDecisionType.RESPONSE
            and decision.is_main_frame_main_resource()
            and not decision.is_mime_type_supported()
        ):
            decision.ignore()
            self._open_external(decision.get_request().get_uri())
            return True
        return False

    def _on_create(self, _view: WebKit.WebView, action: WebKit.NavigationAction) -> None:
        uri = action.get_request().get_uri()
        if uri and uri != "about:blank":
            self._hand_off_pop_up(uri)

    def _on_permission_request(self, _view: WebKit.WebView, request: WebKit.PermissionRequest) -> bool:
        request.deny()
        return True

    def _on_mouse_pressed(self, gesture: Gtk.GestureClick, _n_press: int, _x: float, _y: float) -> None:
        button = gesture.get_current_button()
        if button in {_BACK_BUTTON, _FORWARD_BUTTON}:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self._actions.activate_action("back" if button == _BACK_BUTTON else "forward", None)

    def _open_current_externally(self, _view: WebKit.WebView) -> None:
        if uri := self._uri():
            self._open_external(uri)

    def _copy_link(self, _view: WebKit.WebView) -> None:
        if uri := self._uri():
            self.get_clipboard().set(uri)

    def _show_address(self, _view: WebKit.WebView) -> None:
        self.url_button.popup()
        self.url_entry.grab_focus()
        self.url_entry.select_region(0, -1)

    def _clear_site_data(self, _view: WebKit.WebView) -> None:
        if not (host := display_host(self._uri())):
            return

        def on_cleared() -> None:
            self._add_toast(Adw.Toast(title=_("Website data for {host} cleared").format(host=host)))
            if self._web_view is not None:
                self._web_view.reload()

        clear_site_data(self._network_session, host, on_cleared)
