"""The Preferences dialog: how games open, browser website data, the category badge, and the catalog's last update."""

from gi.repository import Adw, Gio, GLib, Gtk

from dailies import config
from dailies.core import opening
from dailies.core.opening import OpenMode
from dailies.data.store import Store
from dailies.ui import opener


def _choice_title(mode: OpenMode) -> str:
    titles = {
        OpenMode.IN_APP: _("Built-in browser"),
        OpenMode.EXTERNAL: _("Default browser"),
        OpenMode.CUSTOM: _("Custom command"),
    }
    return titles[mode]


#: The nicks of the `session-isolation` and `cookie-policy` choices, in the order preferences.blp lists them.
_SESSION_ISOLATION_NICKS = ("shared", "per-game")
_COOKIE_POLICY_NICKS = ("always", "no-third-party", "never")


@Gtk.Template(resource_path=f"{config.PREFIX}/ui/preferences.ui")
class PreferencesDialog(Adw.PreferencesDialog):
    """The app's settings; the built-in browser's rows only show when WebKit is available.

    "Open games" offers only what this installation can do (`dailies.core.opening.choices`); the combo row's index is
    mapped to the `open-mode` nick by hand, as PyGObject has no closure mapping for it. "Custom command" is offered
    once host access is detected (`opener.host_access`), and its command row shows while it is chosen. The built-in
    browser's privacy and compatibility options sit in one expander row; its combo rows are mapped the same way.
    """

    __gtype_name__ = "DailiesPreferencesDialog"

    open_mode_row: Adw.ComboRow = Gtk.Template.Child()
    command_row: Adw.EntryRow = Gtk.Template.Child()
    custom_help_label: Gtk.Label = Gtk.Template.Child()
    browser_group: Adw.PreferencesGroup = Gtk.Template.Child()
    clear_on_exit_row: Adw.SwitchRow = Gtk.Template.Child()
    browser_options_row: Adw.ExpanderRow = Gtk.Template.Child()
    session_isolation_row: Adw.ComboRow = Gtk.Template.Child()
    cookie_policy_row: Adw.ComboRow = Gtk.Template.Child()
    itp_row: Adw.SwitchRow = Gtk.Template.Child()
    hardware_acceleration_row: Adw.SwitchRow = Gtk.Template.Child()
    user_agent_row: Adw.EntryRow = Gtk.Template.Child()
    developer_extras_row: Adw.SwitchRow = Gtk.Template.Child()
    clear_row: Adw.ButtonRow = Gtk.Template.Child()
    last_updated_row: Adw.ActionRow = Gtk.Template.Child()
    show_other_languages_row: Adw.SwitchRow = Gtk.Template.Child()
    category_badge_row: Adw.SwitchRow = Gtk.Template.Child()
    auto_done_row: Adw.SwitchRow = Gtk.Template.Child()

    def __init__(self, *, settings: Gio.Settings, store: Store) -> None:
        super().__init__()
        self._settings = settings
        self._store = store
        self._have_webkit = opener.have_webkit()
        self._host_access = opener.host_access()
        self._choices = opening.choices(have_webkit=self._have_webkit, host_access=self._host_access)

        self.open_mode_row.props.model = Gtk.StringList.new([_choice_title(mode) for mode in self._choices])
        self._show_open_mode()
        self._update_command_row()
        self.open_mode_row.connect("notify::selected", self._on_open_mode_selected)
        self._mode_handler = settings.connect("changed::open-mode", lambda *_args: self._show_open_mode())
        self.command_row.props.text = settings.get_string("external-browser-command")
        # Outside Flatpak the command needs no host access, so there is nothing to explain.
        self.custom_help_label.props.visible = opener.in_flatpak()

        self.browser_group.props.visible = self._have_webkit
        settings.bind("clear-web-data-on-exit", self.clear_on_exit_row, "active", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("auto-done-today", self.auto_done_row, "active", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("show-other-languages", self.show_other_languages_row, "active", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("show-category-badge", self.category_badge_row, "active", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("itp-enabled", self.itp_row, "active", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("developer-extras", self.developer_extras_row, "active", Gio.SettingsBindFlags.DEFAULT)
        self._choice_handlers = [
            self._bind_choice(self.session_isolation_row, "session-isolation", _SESSION_ISOLATION_NICKS),
            self._bind_choice(self.cookie_policy_row, "cookie-policy", _COOKIE_POLICY_NICKS),
            self._bind_hardware_acceleration(),
        ]
        self.user_agent_row.props.text = settings.get_string("user-agent")

        self._show_last_updated()
        self._store_handler = store.connect("notify::last-success", lambda *_args: self._show_last_updated())
        self.connect("closed", self._on_closed)

    def _on_closed(self, _dialog: Adw.PreferencesDialog) -> None:
        # The settings and the store outlive the dialog: let go of it.
        for handler in (self._mode_handler, *self._choice_handlers):
            self._settings.disconnect(handler)
        self._store.disconnect(self._store_handler)

    def _bind_choice(self, row: Adw.ComboRow, key: str, nicks: tuple[str, ...]) -> int:
        """Keep `row`'s selected index and the enum `key` in step, index i being `nicks[i]`; return the handler id."""

        def show(*_args: object) -> None:
            nick = self._settings.get_string(key)
            index = nicks.index(nick) if nick in nicks else 0
            if row.props.selected != index:
                row.props.selected = index

        def on_selected(row: Adw.ComboRow, _pspec: object) -> None:
            if row.props.selected != Gtk.INVALID_LIST_POSITION and row.props.selected < len(nicks):
                self._settings.set_string(key, nicks[row.props.selected])

        show()
        row.connect("notify::selected", on_selected)
        return self._settings.connect(f"changed::{key}", show)

    def _bind_hardware_acceleration(self) -> int:
        """The switch is on for `always` and off for `never`; return the settings handler id."""
        row = self.hardware_acceleration_row

        def show(*_args: object) -> None:
            row.props.active = self._settings.get_string("hardware-acceleration") != "never"

        show()
        row.connect(
            "notify::active",
            lambda row, _pspec: self._settings.set_string(
                "hardware-acceleration", "always" if row.props.active else "never"
            ),
        )
        return self._settings.connect("changed::hardware-acceleration", show)

    @Gtk.Template.Callback()
    def on_user_agent_applied(self, row: Adw.EntryRow) -> None:
        """Save the user agent only when applied; empty keeps the browser's own."""
        self._settings.set_string("user-agent", row.props.text.strip())

    def _shown_choice(self) -> OpenMode:
        mode = OpenMode.from_id(self._settings.get_string("open-mode"))
        return opening.shown_choice(mode, have_webkit=self._have_webkit, host_access=self._host_access)

    def _show_open_mode(self) -> None:
        index = self._choices.index(self._shown_choice())
        if self.open_mode_row.props.selected != index:
            self.open_mode_row.props.selected = index

    def _on_open_mode_selected(self, row: Adw.ComboRow, _pspec: object) -> None:
        if row.props.selected == Gtk.INVALID_LIST_POSITION:
            return
        self._update_command_row()
        chosen = self._choices[row.props.selected]
        # Selecting what is already shown keeps the setting, so a hidden mode (custom without host access) is kept.
        if chosen is not self._shown_choice():
            self._settings.set_string("open-mode", chosen.value)

    def _update_command_row(self) -> None:
        selected = self.open_mode_row.props.selected
        custom = selected != Gtk.INVALID_LIST_POSITION and self._choices[selected] is OpenMode.CUSTOM
        self.command_row.props.visible = custom

    @Gtk.Template.Callback()
    def on_command_applied(self, row: Adw.EntryRow) -> None:
        """Save the command only when applied, so a half-typed command never runs."""
        self._settings.set_string("external-browser-command", row.props.text.strip())

    def _show_last_updated(self) -> None:
        last_success = self._store.props.last_success
        if last_success is None:
            self.last_updated_row.props.subtitle = _("Never (using built-in list)")
        else:
            local = GLib.DateTime.new_from_unix_local(int(last_success.timestamp()))
            self.last_updated_row.props.subtitle = local.format("%x")

    @Gtk.Template.Callback()
    def on_clear_activated(self, _row: Adw.ButtonRow) -> None:
        """Ask before clearing: the user is signed out of games and loses progress and streaks."""
        alert = Adw.AlertDialog(
            heading=_("Clear website data?"),
            body=_("You will be signed out of games and lose saved progress and streaks."),
            default_response="cancel",
            close_response="cancel",
        )
        alert.add_response("cancel", _("_Cancel"))
        alert.add_response("clear", _("_Clear"))
        alert.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        alert.choose(self, None, self._on_clear_chosen)

    def _on_clear_chosen(self, alert: Adw.AlertDialog, result: Gio.AsyncResult) -> None:
        if alert.choose_finish(result) != "clear":
            return
        # Imported here: it loads WebKit, and this row only shows when WebKit is available.
        from dailies.ui import browser_page

        # Every session: the shared one and each game's, also those of games not opened since the app started.
        browser_page.clear_all(self._settings, lambda: self.add_toast(Adw.Toast(title=_("Website data cleared"))))
