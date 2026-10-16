"""Export Favorites… and Import Favorites… from the primary menu.

The files are chosen with `Gtk.FileDialog`, which goes through the FileChooser portal inside the Flatpak, so the app
needs no filesystem permission. The file format and the merge are `dailies.core.favorites_file`; the asynchronous file
I/O is `dailies.data.favorites`.
"""

import logging
from collections.abc import Callable

from gi.repository import Adw, Gio, GLib, Gtk

from dailies.core.favorites_file import FavoritesFileError, ImportMode
from dailies.data import favorites as favorites_io
from dailies.data.favorites import Favorites

log = logging.getLogger(__name__)

_CANCEL = "cancel"


class Transfer:
    """Exports and imports the favourites for one window, telling the outcome in a toast."""

    def __init__(self, parent: Gtk.Window, favorites: Favorites, add_toast: Callable[[Adw.Toast], None]) -> None:
        self._parent = parent
        self._favorites = favorites
        self._add_toast = add_toast

    def ask_export(self) -> None:
        """Ask where to save the favourites, then export them there."""
        dialog = _file_dialog(_("Export Favorites"))
        dialog.props.initial_name = "dailies-favorites.json"
        dialog.save(self._parent, None, self._on_export_chosen)

    def ask_import(self) -> None:
        """Ask for a favourites file, then import it."""
        _file_dialog(_("Import Favorites")).open(self._parent, None, self._on_import_chosen)

    def export_to(self, file: Gio.File) -> None:
        """Write the favourites, in display order, to `file`."""
        favorites_io.export(file, self._favorites.order(), self._on_exported)

    def import_from(self, file: Gio.File) -> None:
        """Read and check `file`; with favourites already set, ask whether to merge (the default) or replace them."""
        favorites_io.read_export(file, self._on_read)

    def _on_export_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        if (file := _finish(dialog.save_finish, result)) is not None:
            self.export_to(file)

    def _on_import_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        if (file := _finish(dialog.open_finish, result)) is not None:
            self.import_from(file)

    def _on_exported(self, error: GLib.Error | None) -> None:
        if error is not None:
            log.warning("could not export favorites: %s", error.message)
            self._add_toast(Adw.Toast(title=_("Could not export favorites")))
            return
        self._add_toast(Adw.Toast(title=_("Favorites exported")))

    def _on_read(self, ids: list[str] | None, error: GLib.Error | FavoritesFileError | None) -> None:
        if isinstance(error, FavoritesFileError):
            log.warning("not a favorites export: %s", error)
            self._add_toast(Adw.Toast(title=_("This file is not a Dailies favorites export")))
            return
        if error is not None:
            log.warning("could not read favorites: %s", error.message)
            self._add_toast(Adw.Toast(title=_("Could not read the file")))
            return
        if not self._favorites.order():
            # Merging into nothing and replacing nothing give the same list: there is nothing to ask.
            self._import(ids, ImportMode.MERGE)
            return
        dialog = Adw.AlertDialog(
            heading=_("Import Favorites?"),
            body=_("Merge adds the games you do not have yet after your favorites. Replace uses the list in the file."),
            default_response=ImportMode.MERGE.value,
            close_response=_CANCEL,
        )
        dialog.add_response(_CANCEL, _("_Cancel"))
        dialog.add_response(ImportMode.REPLACE.value, _("_Replace"))
        dialog.add_response(ImportMode.MERGE.value, _("_Merge"))
        dialog.set_response_appearance(ImportMode.REPLACE.value, Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance(ImportMode.MERGE.value, Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", lambda _dialog, response: self._on_response(response, ids))
        dialog.present(self._parent)

    def _on_response(self, response: str, ids: list[str]) -> None:
        if response != _CANCEL:
            self._import(ids, ImportMode(response))

    def _import(self, ids: list[str], mode: ImportMode) -> None:
        self._favorites.import_ids(ids, mode)
        title = ngettext("Imported {n} favorite", "Imported {n} favorites", len(ids)).format(n=len(ids))
        self._add_toast(Adw.Toast(title=title))


def _file_dialog(title: str) -> Gtk.FileDialog:
    json_filter = Gtk.FileFilter(name=_("Favorites (JSON)"), mime_types=["application/json"], suffixes=["json"])
    filters = Gio.ListStore(item_type=Gtk.FileFilter)
    filters.append(json_filter)
    return Gtk.FileDialog(title=title, modal=True, filters=filters, default_filter=json_filter)


def _finish(finish: Callable[[Gio.AsyncResult], Gio.File], result: Gio.AsyncResult) -> Gio.File | None:
    """Return the chosen file, or None when the dialog was dismissed or failed."""
    try:
        return finish(result)
    except GLib.Error as e:
        if not e.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
            log.warning("file dialog failed: %s", e.message)
        return None
