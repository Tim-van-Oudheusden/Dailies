"""Export and import of favourites behind the primary menu; run by Meson (see tests/meson.build).

The import asks Merge or Replace in an Adw.AlertDialog, so the module starts a private Broadway server like
tests/gi/test_tile.py. The portal's file dialogs are not driven here: the tests start once a file is chosen.
"""

import gettext
import os
import tempfile
import time
import unittest
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gio, GLib


def _start_display() -> None:
    # The build sandbox has no display; a Broadway server needs nothing but a socket in the runtime directory.
    runtime = tempfile.mkdtemp()
    os.environ["XDG_RUNTIME_DIR"] = runtime
    display = str(510 + os.getpid() % 500)
    server = Gio.Subprocess.new(
        [os.environ["BROADWAYD"], f":{display}"],
        Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE,
    )
    deadline = time.monotonic() + 10
    while not any(Path(runtime).glob("broadway*.socket")) and time.monotonic() < deadline:
        time.sleep(0.05)
    os.environ.update(GDK_BACKEND="broadway", BROADWAY_DISPLAY=f":{display}")
    unittest.addModuleCleanup(server.force_exit)


_start_display()
gettext.install("dailies", names=["ngettext"])

from gi.repository import Adw

Adw.init()

from dailies.data.favorites import Favorites
from dailies.ui import favorites_transfer

SCHEMA_ID = os.environ["DAILIES_SCHEMA_ID"]


def iterate_until(condition: object) -> None:
    context = GLib.MainContext.default()
    deadline = time.monotonic() + 10
    while not condition() and time.monotonic() < deadline:
        context.iteration(False)
        time.sleep(0.01)


class TransferTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Gio.Settings.new(SCHEMA_ID)
        self.settings.reset("favorites")
        self.favorites = Favorites(self.settings)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "favorites.json"
        self.file = Gio.File.new_for_path(str(self.path))
        self.window = Adw.ApplicationWindow()
        self.window.present()
        self.addCleanup(self.window.destroy)
        self.toasts: list[Adw.Toast] = []

    def transfer(self) -> favorites_transfer.Transfer:
        return favorites_transfer.Transfer(self.window, self.favorites, self.toasts.append)

    def test_export_then_reset_then_import_gives_the_same_order(self) -> None:
        for game_id in ("wordle", "globle", "framed", "not-in-any-catalog"):
            self.favorites.toggle(game_id)
        exported = self.favorites.order()

        self.transfer().export_to(self.file)
        iterate_until(lambda: self.toasts)
        assert [toast.props.title for toast in self.toasts] == ["Favorites exported"]
        self.settings.reset("favorites")
        self.toasts.clear()
        self.transfer().import_from(self.file)
        iterate_until(lambda: self.toasts)

        assert self.favorites.order() == exported
        assert [toast.props.title for toast in self.toasts] == ["Imported 4 favorites"]

    def test_with_favorites_the_import_asks_and_merges_by_default(self) -> None:
        self.favorites.toggle("wordle")
        self.path.write_text('{"schema_version": 1, "favorites": ["globle", "wordle"]}', encoding="utf-8")

        self.transfer().import_from(self.file)
        iterate_until(lambda: isinstance(self.window.get_visible_dialog(), Adw.AlertDialog))
        dialog = self.window.get_visible_dialog()

        assert dialog.props.default_response == "merge"
        assert dialog.props.close_response == "cancel"
        assert self.favorites.order() == ["wordle"]
        dialog.emit("response", dialog.props.default_response)
        assert self.favorites.order() == ["wordle", "globle"]
        assert [toast.props.title for toast in self.toasts] == ["Imported 2 favorites"]

    def test_replace_takes_the_file_order(self) -> None:
        self.favorites.toggle("wordle")
        self.path.write_text('{"schema_version": 1, "favorites": ["globle"]}', encoding="utf-8")

        self.transfer().import_from(self.file)
        iterate_until(lambda: isinstance(self.window.get_visible_dialog(), Adw.AlertDialog))
        self.window.get_visible_dialog().emit("response", "replace")

        assert self.favorites.order() == ["globle"]
        assert [toast.props.title for toast in self.toasts] == ["Imported 1 favorite"]

    def test_cancel_changes_nothing(self) -> None:
        self.favorites.toggle("wordle")
        self.path.write_text('{"schema_version": 1, "favorites": ["globle"]}', encoding="utf-8")

        self.transfer().import_from(self.file)
        iterate_until(lambda: isinstance(self.window.get_visible_dialog(), Adw.AlertDialog))
        self.window.get_visible_dialog().emit("response", "cancel")

        assert self.favorites.order() == ["wordle"]
        assert self.toasts == []

    def test_a_malformed_file_shows_an_error_toast_and_changes_nothing(self) -> None:
        self.favorites.toggle("wordle")
        self.path.write_bytes(b'{"schema_version": 1, "favorites": ["globle", 3]}')

        self.transfer().import_from(self.file)
        iterate_until(lambda: self.toasts)

        assert self.window.get_visible_dialog() is None
        assert self.favorites.order() == ["wordle"]
        assert [toast.props.title for toast in self.toasts] == ["This file is not a Dailies favorites export"]


if __name__ == "__main__":
    unittest.main()
