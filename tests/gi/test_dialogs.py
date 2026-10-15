"""The Shortcuts and About dialogs bundled in the gresource; run by Meson (see tests/meson.build).

Dialogs are widgets and need a display, so the module starts a private Broadway daemon (it ships with GTK) rather
than depend on the session's display. It does so before importing Gtk, whose override opens the display on import.
"""

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gio, GLib


def start_broadway() -> None:
    """Point GDK at a Broadway daemon numbered after this process, so parallel runs don't clash."""
    http_dir = tempfile.mkdtemp()
    unittest.addModuleCleanup(shutil.rmtree, http_dir, ignore_errors=True)
    display = os.getpid()
    socket = Path(GLib.get_user_runtime_dir()) / f"broadway{display + 1}.socket"  # Where GDK looks for display :N.
    socket.parent.mkdir(parents=True, exist_ok=True)
    unittest.addModuleCleanup(socket.unlink, missing_ok=True)
    # Silenced, so a crashing test can't leave Meson waiting on a pipe the orphaned daemon holds.
    launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE)
    daemon = launcher.spawnv(["gtk4-broadwayd", "--unixsocket", str(Path(http_dir) / "http.socket"), f":{display}"])
    unittest.addModuleCleanup(daemon.wait)
    unittest.addModuleCleanup(daemon.force_exit)
    deadline = time.monotonic() + 10
    while not socket.exists():
        assert time.monotonic() < deadline, "gtk4-broadwayd did not start"
        time.sleep(0.05)
    os.environ.update(GDK_BACKEND="broadway", BROADWAY_DISPLAY=f":{display}")


start_broadway()

from gi.repository import Adw, Gdk, Gtk

GRESOURCE = os.environ["DAILIES_GRESOURCE"]
PREFIX = os.environ["DAILIES_PREFIX"]
APP_ID = os.environ["DAILIES_SCHEMA_ID"]

# Every accelerator of the application, per section of the Shortcuts dialog (#48).
EXPECTED_SECTIONS = {
    "General": {"<Control>question", "F10", "<Control>comma", "<Control>q"},
    "Library": {"<Control>f", "<Control>d", "<Control>r"},
    "Built-in Browser": {"<Alt>Left", "<Alt>Right", "<Control>r", "<Control>l", "<Control><Shift>o"},
}


def setUpModule() -> None:
    Adw.init()
    Gio.resources_register(Gio.Resource.load(GRESOURCE))


def parsed(accelerator: str) -> tuple[int, Gdk.ModifierType]:
    ok, key, mods = Gtk.accelerator_parse(accelerator)
    assert ok, accelerator
    return key, mods


class ShortcutsDialogTest(unittest.TestCase):
    def test_adw_application_wires_the_bundled_dialog_to_ctrl_question(self) -> None:
        app = Adw.Application(
            application_id=f"{APP_ID}.Test",
            resource_base_path=PREFIX,
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        accels: list[str] = []

        def on_activate(app: Adw.Application) -> None:
            accels.extend(app.get_accels_for_action("app.shortcuts"))
            app.quit()

        app.connect("activate", on_activate)
        app.run([])

        assert [parsed(a) for a in accels] == [parsed("<Control>question")]

    def test_the_dialog_lists_every_accelerator_by_section(self) -> None:
        builder = Gtk.Builder.new_from_resource(f"{PREFIX}/shortcuts-dialog.ui")
        assert isinstance(builder.get_object("shortcuts_dialog"), Adw.ShortcutsDialog)

        sections = [o for o in builder.get_objects() if isinstance(o, Adw.ShortcutsSection)]
        listed = {section.get_title(): {parsed(item.get_accelerator()) for item in section} for section in sections}

        assert listed == {title: {parsed(a) for a in accels} for title, accels in EXPECTED_SECTIONS.items()}
        assert all(item.get_title() for section in sections for item in section)


class AboutDialogTest(unittest.TestCase):
    def test_the_bundled_metainfo_gives_version_licence_and_release_notes(self) -> None:
        about = Adw.AboutDialog.new_from_appdata(f"{PREFIX}/{APP_ID}.metainfo.xml", "0.1.0")

        assert about.get_application_name() == "Dailies"
        assert about.get_version() == "0.1.0"
        assert about.get_license_type() == Gtk.License.GPL_3_0
        assert about.get_release_notes()


if __name__ == "__main__":
    unittest.main()
