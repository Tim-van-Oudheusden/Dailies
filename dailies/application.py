import gettext
import locale
import signal
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio

from dailies import config


class Application(Adw.Application):
    """The Dailies application: one main window, resources under `config.PREFIX`."""

    def __init__(self) -> None:
        super().__init__(
            application_id=config.APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            resource_base_path=config.PREFIX,
        )

    def do_activate(self) -> None:
        """Present the main window, creating it on first activation."""
        window = self.props.active_window
        if window is None:
            # Imported here: its Gtk.Template needs the gresource that main() registers.
            from dailies.window import Window

            window = Window(application=self)
            if config.PROFILE == "development":
                window.add_css_class("devel")
        window.present()


def main() -> int:
    """Set up gettext and resources, then run the application."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    locale.bindtextdomain("dailies", config.LOCALEDIR)
    locale.textdomain("dailies")
    gettext.install("dailies", config.LOCALEDIR)
    Gio.resources_register(Gio.Resource.load(str(Path(config.PKGDATADIR) / "dailies.gresource")))
    return Application().run(sys.argv)
