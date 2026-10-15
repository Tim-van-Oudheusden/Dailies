"""The built-in browser: an `Adw.NavigationPage` around one `WebKit.WebView` with a persistent, shared session.

Imported only when `opener.have_webkit()` is true; importing this module loads WebKit.

All games share one `WebKit.NetworkSession` per app run, so sibling games share a login, and its cookies are stored in
SQLite so that logins and streaks survive a restart. Pages are shown as the sites ship them: no injected scripts or
styles, no content blocking, no user-agent spoofing. Pop-ups and downloads go to the external browser and permission
requests are denied.
"""

import functools
import logging
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("WebKit", "6.0")

from gi.repository import Adw, Gio, GLib, Gtk, WebKit

from dailies import config
from dailies.core.web import display_host, site_matches

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


def _web_dirs() -> tuple[Path, Path]:
    """The data and cache directories of the shared session (per-game sessions are #74)."""
    return (
        Path(GLib.get_user_data_dir()) / "dailies" / "web" / "shared",
        Path(GLib.get_user_cache_dir()) / "dailies" / "web" / "shared",
    )


@functools.cache
def _shared_session() -> WebKit.NetworkSession:
    """Create the one network session of this app run, the first time a page or a clear needs it."""
    data_dir, cache_dir = _web_dirs()
    session = WebKit.NetworkSession.new(str(data_dir), str(cache_dir))
    cookies = session.get_cookie_manager()
    # Without persistent storage cookies live in memory only, and every streak is lost on quit.
    cookies.set_persistent_storage(str(data_dir / "cookies.sqlite"), WebKit.CookiePersistentStorage.SQLITE)
    # Log-in flows (the New York Times) redirect through third-party domains that must be able to set cookies.
    cookies.set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)
    session.set_tls_errors_policy(WebKit.TLSErrorsPolicy.FAIL)
    session.connect("download-started", _on_download_started)
    return session


def _on_download_started(_session: WebKit.NetworkSession, download: WebKit.Download) -> None:
    # The sandbox has no download folder: hand the link to the external browser before anything is written.
    download.cancel()
    window = Gio.Application.get_default().props.active_window
    if window is not None:
        window.open_external(download.get_request().get_uri())


def clear_all(callback: Callable[[], None] | None = None) -> None:
    """Remove all website data of the shared session (cookies, storage, caches), then call `callback`."""

    def on_cleared(manager: WebKit.WebsiteDataManager, result: Gio.AsyncResult) -> None:
        try:
            manager.clear_finish(result)
        except GLib.Error as e:
            log.warning("Could not clear the website data: %s", e.message)
        if callback:
            callback()

    _shared_session().get_website_data_manager().clear(WebKit.WebsiteDataTypes.ALL, 0, None, on_cleared)


def clear_all_blocking() -> None:
    """Clear all website data before the app quits, waiting a few seconds at most."""
    loop = GLib.MainLoop()
    clear_all(loop.quit)
    GLib.timeout_add_seconds(_CLEAR_ON_EXIT_TIMEOUT_SECONDS, loop.quit)
    loop.run()


def clear_site_data(host: str, callback: Callable[[], None] | None = None) -> None:
    """Remove the website data of the site at `host` and its parent domains, then call `callback`."""
    manager = _shared_session().get_website_data_manager()

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

    Call `close()` when the page is popped: it closes the web view, which ends its web process.
    """

    __gtype_name__ = "DailiesBrowserPage"

    reload_button: Gtk.Button = Gtk.Template.Child()
    url_button: Gtk.MenuButton = Gtk.Template.Child()
    url_entry: Gtk.Entry = Gtk.Template.Child()
    window_title: Adw.WindowTitle = Gtk.Template.Child()
    overlay: Gtk.Overlay = Gtk.Template.Child()
    progress_bar: Gtk.ProgressBar = Gtk.Template.Child()

    def __init__(self, *, open_external: Callable[[str], None], add_toast: Callable[[Adw.Toast], None]) -> None:
        super().__init__()
        self._open_external = open_external
        self._add_toast = add_toast

        settings = WebKit.Settings(
            javascript_can_open_windows_automatically=False,
            allow_top_navigation_to_data_urls=False,
            enable_webrtc=False,
            enable_back_forward_navigation_gestures=True,
            enable_smooth_scrolling=True,
        )
        settings.set_user_agent_with_application_details("Dailies", config.VERSION)
        # A context of its own: its web processes end with it, while the network session (logins) is shared.
        context = WebKit.WebContext()
        context.set_cache_model(WebKit.CacheModel.DOCUMENT_VIEWER)
        view = WebKit.WebView(
            web_context=context, network_session=_shared_session(), settings=settings, hexpand=True, vexpand=True
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
            self._open_external(uri)

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

        clear_site_data(host, on_cleared)
