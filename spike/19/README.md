# Spike #19: GNOME 51 SDK assumptions

Throwaway branch; nothing here merges into `main`. Findings are on issue #19.

- `window.blp`, `game-tile.blp`, `preferences.blp`, `browser-view.blp`, `shortcuts-dialog.blp`:
  `libadwaita-ui-patterns.md` Appendix A.1–A.5, corrected so that each compiles with blueprint-compiler 0.22.2 in
  `org.gnome.Sdk//51`:

  ```sh
  flatpak run --user --filesystem="$PWD" --command=bash org.gnome.Sdk//51 \
    -c 'for f in *.blp; do blueprint-compiler compile --output /dev/null "$f"; done'
  ```

- `sidebar.py`: `Adw.ApplicationWindow` → `Adw.NavigationSplitView` → `Adw.Sidebar` with a title-less section, "This
  Week" and "Categories" (items appended at runtime); prints runtime versions and the `selected`/`activated` results.
- `cssvars.py`: lists the `--{accent,success,warning,error}-{,bg-,fg-}color` variables in libadwaita's stylesheets.

  ```sh
  flatpak run --user --filesystem="$PWD" --socket=wayland --socket=fallback-x11 --socket=session-bus \
    --device=dri --share=ipc --command=python3 org.gnome.Platform//51 sidebar.py
  ```
