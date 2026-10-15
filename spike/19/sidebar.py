import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, GLib, Gtk, WebKit

print("python", sys.version.split()[0])
print("pygobject", gi.__version__)
print("gtk", Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version())
print("adw", Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version())
print("webkit", WebKit.get_major_version(), WebKit.get_minor_version(), WebKit.get_micro_version())
print("UriLauncher", hasattr(Gtk, "UriLauncher"), "launch" in dir(Gtk.UriLauncher))

results = {}


def on_activate(app):
    win = Adw.ApplicationWindow(application=app, default_width=800, default_height=500)
    sidebar = Adw.Sidebar()
    favorites = Adw.SidebarSection()  # title-less
    favorites.append(Adw.SidebarItem(title="Favorites", icon_name="starred-symbolic"))
    week = Adw.SidebarSection(title="This Week")
    week.append(Adw.SidebarItem(title="Popular", icon_name="emblem-favorite-symbolic"))
    week.append(Adw.SidebarItem(title="Trending", icon_name="go-up-symbolic"))
    cats = Adw.SidebarSection(title="Categories")
    for s in (favorites, week, cats):
        sidebar.append(s)
    for name in ("Words", "Geography", "Music"):  # appended at runtime, after sections are in the sidebar
        cats.append(Adw.SidebarItem(title=name))

    activated = []
    sidebar.connect("activated", lambda _s, idx: activated.append(idx))
    notified = []
    sidebar.connect("notify::selected", lambda s, _p: notified.append(s.get_selected()))

    content = Adw.NavigationPage(title="Content", child=Adw.StatusPage(title="Grid"))
    side_page = Adw.NavigationPage(title="Dailies", child=sidebar)
    split = Adw.NavigationSplitView(sidebar=side_page, content=content)
    win.set_content(split)
    win.present()

    def probe():
        results["n_items"] = sidebar.get_items().get_n_items()
        results["n_sections"] = sidebar.get_sections().get_n_items()
        sidebar.set_selected(4)  # restore "last section": Geography (index 4)
        results["selected"] = sidebar.get_selected()
        item = sidebar.get_selected_item()
        results["selected_title"] = item.get_title() if item else None
        results["notified"] = list(notified)
        # Programmatic activation is not public API; emit to prove handler wiring takes the index.
        sidebar.emit("activated", 2)
        results["activated"] = list(activated)
        results["item_section"] = item.get_section().get_title() if item else None
        print("RESULTS", results)
        app.quit()
        return GLib.SOURCE_REMOVE

    GLib.timeout_add(500, probe)


app = Adw.Application(application_id="io.github.tim_van_oudheusden.DailiesSpike")
app.connect("activate", on_activate)
app.run([])
