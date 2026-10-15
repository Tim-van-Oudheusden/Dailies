import re

import gi

gi.require_version("Adw", "1")
from gi.repository import Adw, Gio

Adw.init()
found = set()


def walk(path):
    for child in Gio.resources_enumerate_children(path, 0):
        p = path + child
        if child.endswith("/"):
            walk(p)
        elif p.endswith(".css"):
            text = Gio.resources_lookup_data(p, 0).get_data().decode()
            found.update(re.findall(r"--(?:success|warning|error|accent)-(?:bg-|fg-)?color", text))


walk("/org/gnome/Adwaita/")
print(sorted(found))
