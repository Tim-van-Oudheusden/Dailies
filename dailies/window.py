from gi.repository import Adw, Gtk

from dailies import config


@Gtk.Template(resource_path=f"{config.PREFIX}/ui/window.ui")
class Window(Adw.ApplicationWindow):
    """The main window."""

    __gtype_name__ = "DailiesWindow"
