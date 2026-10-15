"""The Preferences dialog: how games open, the built-in browser's website data, and when the catalog was updated."""

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


@Gtk.Template(resource_path=f"{config.PREFIX}/ui/preferences.ui")
class PreferencesDialog(Adw.PreferencesDialog):
    """The app's settings; the built-in browser's rows only show when WebKit is available.

    "Open games" offers only what this installation can do (`dailies.core.opening.choices`); the combo row's index is
    mapped to the `open-mode` nick by hand, as PyGObject has no closure mapping for it.
    """

    __gtype_name__ = "DailiesPreferencesDialog"

    open_mode_row: Adw.ComboRow = Gtk.Template.Child()
    browser_group: Adw.PreferencesGroup = Gtk.Template.Child()
    clear_on_exit_row: Adw.SwitchRow = Gtk.Template.Child()
    clear_row: Adw.ButtonRow = Gtk.Template.Child()
    last_updated_row: Adw.ActionRow = Gtk.Template.Child()
    show_other_languages_row: Adw.SwitchRow = Gtk.Template.Child()

    def __init__(self, *, settings: Gio.Settings, store: Store) -> None:
        super().__init__()
        self._settings = settings
        self._store = store
        self._have_webkit = opener.have_webkit()
        # Host access for the custom command is detected in #63; until then "Custom command" stays hidden.
        self._choices = opening.choices(have_webkit=self._have_webkit, host_access=False)

        self.open_mode_row.props.model = Gtk.StringList.new([_choice_title(mode) for mode in self._choices])
        self._show_open_mode()
        self.open_mode_row.connect("notify::selected", self._on_open_mode_selected)
        self._mode_handler = settings.connect("changed::open-mode", lambda *_args: self._show_open_mode())

        self.browser_group.props.visible = self._have_webkit
        settings.bind("clear-web-data-on-exit", self.clear_on_exit_row, "active", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("show-other-languages", self.show_other_languages_row, "active", Gio.SettingsBindFlags.DEFAULT)

        self._show_last_updated()
        self._store_handler = store.connect("notify::last-success", lambda *_args: self._show_last_updated())
        self.connect("closed", self._on_closed)

    def _on_closed(self, _dialog: Adw.PreferencesDialog) -> None:
        # The settings and the store outlive the dialog: let go of it.
        self._settings.disconnect(self._mode_handler)
        self._store.disconnect(self._store_handler)

    def _shown_choice(self) -> OpenMode:
        mode = OpenMode.from_id(self._settings.get_string("open-mode"))
        return opening.shown_choice(mode, have_webkit=self._have_webkit, host_access=False)

    def _show_open_mode(self) -> None:
        index = self._choices.index(self._shown_choice())
        if self.open_mode_row.props.selected != index:
            self.open_mode_row.props.selected = index

    def _on_open_mode_selected(self, row: Adw.ComboRow, _pspec: object) -> None:
        if row.props.selected == Gtk.INVALID_LIST_POSITION:
            return
        chosen = self._choices[row.props.selected]
        # Selecting what is already shown keeps the setting, so a hidden mode (custom, before #63) is not overwritten.
        if chosen is not self._shown_choice():
            self._settings.set_string("open-mode", chosen.value)

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

        browser_page.clear_all(lambda: self.add_toast(Adw.Toast(title=_("Website data cleared"))))
