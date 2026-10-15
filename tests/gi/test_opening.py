"""The custom open mode: the command runner and its Preferences rows; run by Meson (see tests/meson.build).

Preferences is a widget, so the module starts a private Broadway server like tests/gi/test_tile.py.
"""

import gettext
import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gio, GLib, GObject


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


def _load_config() -> None:
    # dailies/config.py exists only in the build directory.
    spec = importlib.util.spec_from_file_location("dailies.config", os.environ["DAILIES_CONFIG"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["dailies.config"] = module


_start_display()
_load_config()
gettext.install("dailies")

from gi.repository import Adw

Adw.init()
Gio.resources_register(Gio.Resource.load(os.environ["DAILIES_GRESOURCE"]))

from dailies.core.opening import Notice, OpenMode
from dailies.ui import opener
from dailies.ui.preferences import PreferencesDialog

CRAFTED_NAME = "game;id;$(id)`id` & a b|c"


class FakeStore(GObject.Object):
    """The one property of the store Preferences reads."""

    last_success = GObject.Property(type=object)


def wait_for(path: Path) -> None:
    context = GLib.MainContext.default()
    deadline = time.monotonic() + 10
    while not path.exists() and time.monotonic() < deadline:
        context.iteration(False)
        time.sleep(0.01)


class CustomCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(opener, "in_flatpak", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_url_reaches_the_command_as_one_argument_and_no_shell_runs(self) -> None:
        url = str(self.dir / CRAFTED_NAME)

        assert opener.launch_custom("touch", url)

        wait_for(self.dir / CRAFTED_NAME)
        assert [p.name for p in self.dir.iterdir()] == [CRAFTED_NAME]

    def test_the_command_is_split_like_a_shell_would_without_running_one(self) -> None:
        quoted = self.dir / "quoted name"
        url = self.dir / "url"

        assert opener.launch_custom(f"touch '{quoted}'", str(url))

        wait_for(url)
        assert sorted(p.name for p in self.dir.iterdir()) == ["quoted name", "url"]

    def test_a_command_that_does_not_parse_does_not_run(self) -> None:
        assert not opener.launch_custom("touch 'unbalanced", str(self.dir / "url"))

    def test_a_command_that_does_not_exist_does_not_run(self) -> None:
        assert not opener.launch_custom("dailies-no-such-command", str(self.dir / "url"))

    def test_outside_flatpak_the_command_needs_no_host_access(self) -> None:
        opener.host_access.cache_clear()
        self.addCleanup(opener.host_access.cache_clear)

        assert opener.host_access()


class OpenedToastTest(unittest.TestCase):
    def test_an_external_open_says_so_and_open_here_brings_it_back(self) -> None:
        brought_back: list[bool] = []

        toast = opener.opened_toast(
            Notice.OPENED_EXTERNALLY, OpenMode.EXTERNAL, open_here=lambda: brought_back.append(True)
        )

        assert toast.props.title == "Opened in your browser"
        assert toast.props.button_label == "Open Here"
        assert toast.props.timeout == 5
        toast.emit("button-clicked")
        assert brought_back == [True]

    def test_without_a_built_in_browser_there_is_no_open_here(self) -> None:
        toast = opener.opened_toast(Notice.OPENED_EXTERNALLY, OpenMode.EXTERNAL, open_here=None)

        assert toast.props.button_label is None

    def test_an_unavailable_custom_command_says_where_the_game_opened_instead(self) -> None:
        in_app = opener.opened_toast(Notice.CUSTOM_UNAVAILABLE, OpenMode.IN_APP, open_here=None)
        external = opener.opened_toast(Notice.CUSTOM_UNAVAILABLE, OpenMode.EXTERNAL, open_here=None)

        assert in_app.props.title == "Custom command unavailable — opened in the built-in browser"
        assert external.props.title == "Custom command unavailable — opened in your browser"
        assert in_app.props.timeout == external.props.timeout == 5


class PreferencesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Gio.Settings.new(os.environ["DAILIES_SCHEMA_ID"])
        for key in ("open-mode", "external-browser-command"):
            self.settings.reset(key)
        patcher = mock.patch.object(opener, "have_webkit", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def dialog(self, *, host_access: bool) -> PreferencesDialog:
        with mock.patch.object(opener, "host_access", return_value=host_access):
            dialog = PreferencesDialog(settings=self.settings, store=FakeStore())
        self.addCleanup(dialog.force_close)
        return dialog

    @staticmethod
    def titles(dialog: PreferencesDialog) -> list[str]:
        model = dialog.open_mode_row.props.model
        return [model.get_string(i) for i in range(model.get_n_items())]

    def test_without_host_access_there_is_no_custom_command(self) -> None:
        self.settings.set_string("open-mode", "custom")
        dialog = self.dialog(host_access=False)

        assert self.titles(dialog) == ["Built-in browser", "Default browser"]
        assert not dialog.command_row.get_visible()

    def test_with_host_access_custom_command_is_offered_with_its_command_row(self) -> None:
        dialog = self.dialog(host_access=True)

        assert self.titles(dialog) == ["Built-in browser", "Default browser", "Custom command"]
        assert not dialog.command_row.get_visible()

        dialog.open_mode_row.props.selected = 2
        assert self.settings.get_string("open-mode") == "custom"
        assert dialog.command_row.get_visible()

        dialog.open_mode_row.props.selected = 1
        assert not dialog.command_row.get_visible()

    def test_the_command_row_shows_and_applies_the_command(self) -> None:
        self.settings.set_string("open-mode", "custom")
        self.settings.set_string("external-browser-command", "firefox --new-window")
        dialog = self.dialog(host_access=True)

        assert dialog.command_row.props.text == "firefox --new-window"
        assert dialog.command_row.props.show_apply_button
        assert dialog.command_row.has_css_class("monospace")

        dialog.command_row.props.text = "librewolf -P games"
        dialog.command_row.emit("apply")
        assert self.settings.get_string("external-browser-command") == "librewolf -P games"


if __name__ == "__main__":
    unittest.main()
