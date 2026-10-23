#!/usr/bin/env bash
# Copy the MSYS2 UCRT64 runtime Dailies needs into a `meson install` tree, so the tree runs on a Windows machine
# without MSYS2: unzip it anywhere and start Dailies.cmd. Run it in an MSYS2 UCRT64 shell after `meson install`, with
# the install prefix as the only argument. The file list follows Cartridges' Inno Setup script
# (docs/research/stack-crossplatform.md, Appendix A.4).
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <install prefix>" >&2
    exit 2
fi
dest=$1
src=${MINGW_PREFIX:?run this in an MSYS2 UCRT64 shell}
here=$(dirname "${BASH_SOURCE[0]}")
python=$(python3 -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')

mkdir -p "$dest/bin" "$dest/lib" "$dest/share" "$dest/etc"

# The interpreter, every DLL (the GTK stack's and Python's extension modules'), the D-Bus helper GApplication starts
# and the helpers Gio.Subprocess spawns through.
cp "$src"/bin/*.dll "$dest/bin/"
cp "$src"/bin/{python.exe,pythonw.exe,gdbus.exe,gspawn-win64-helper.exe,gspawn-win64-helper-console.exe} "$dest/bin/"

# The standard library with PyGObject and pycairo in site-packages; the GI typelibs; the image loaders GTK uses for its
# own icons; GIO's TLS module (glib-networking), which every HTTPS request needs.
cp -r "$src/lib/$python" "$src/lib/girepository-1.0" "$src/lib/gdk-pixbuf-2.0" "$src/lib/gio" "$dest/lib/"
find "$dest/lib/$python" -depth -type d \( -name __pycache__ -o -name test -o -name tests \) -exec rm -rf {} +

# The CA bundle glib-networking checks certificates against, the icon themes, and GLib's and GTK's schemas next to
# Dailies' own, compiled together. MSYS2's hicolor cache overwrites the one `meson install` wrote, so it is rebuilt with
# Dailies' icons in it.
cp -r "$src/etc/ssl" "$dest/etc/"
cp -r "$src/share/icons" "$dest/share/"
gtk4-update-icon-cache --force --ignore-theme-index "$dest/share/icons/hicolor"
mkdir -p "$dest/share/glib-2.0/schemas"
cp "$src"/share/glib-2.0/schemas/*.xml "$dest/share/glib-2.0/schemas/"
glib-compile-schemas "$dest/share/glib-2.0/schemas"

cp "$here/Dailies.cmd" "$here/README.txt" "$dest/"
