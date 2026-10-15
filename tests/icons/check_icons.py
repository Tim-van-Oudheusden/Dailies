"""Meson test: every bundled symbolic icon the UI asks for by name resolves from the gresource.

Usage: check_icons.py <dailies.gresource> <resource base path>

Gtk.Application adds `<resource base path>/icons` to the display's icon theme; this check builds a theme with only
that resource path (no search path, so the system theme can't stand in for a missing icon) and needs no display.
"""

import sys

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, Gtk

from dailies.core.models import Category

# Icons the UI uses besides the category glyphs.
OTHER_ICONS = (
    "dailies-trending-symbolic",
    "dailies-popular-symbolic",
    "dailies-starred-symbolic",
    "dailies-non-starred-symbolic",
)


def main(gresource: str, base_path: str) -> int:
    """Return 0 when every icon resolves, 1 (after listing the missing ones) otherwise."""
    Gio.resources_register(Gio.Resource.load(gresource))
    theme = Gtk.IconTheme()
    theme.set_search_path([])
    theme.add_resource_path(f"{base_path}/icons")
    missing = [name for name in (*(c.icon_name for c in Category), *OTHER_ICONS) if not theme.has_icon(name)]
    for name in missing:
        sys.stderr.write(f"missing icon: {name}\n")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
