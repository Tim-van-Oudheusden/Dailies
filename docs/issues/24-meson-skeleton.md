---
key: 24
title: build: Meson build and Python package skeleton with release/development profiles
type: Task
labels: milestone::M0, type::task, priority::high, app, flatpak
parent: 2
blocked_by: 19, 20
---
> **Risk tier:** high (`meson.build`, `data/*.in`) · **Size:** M

## Why

One source tree has to yield both `io.github.tim_van_oudheusden.Dailies` (release) and `io.github.tim_van_oudheusden.Dailies.Devel`, following Cartridges' `profile` pattern. Every later UI and data ticket installs into this structure.

## Tasks

### Root
- [ ] `meson.build`: `project('dailies', version: '0.1.0', meson_version: '>= 1.4')` with modules `gnome`, `python`, `i18n`. Map `profile` to `app_id` / `prefix` (`/io/github/tim_van_oudheusden/Dailies[/Devel]`) / `PROFILE`. Dependencies `gtk4 >= 4.24` and `libadwaita-1 >= 1.10`, plus `webkitgtk-6.0 >= 2.54` as **`required: false`** (the result feeds `HAVE_WEBKIT`). Add `gnome.post_install(glib_compile_schemas: true, gtk_update_icon_cache: true, update_desktop_database: true)`
- [ ] `meson_options.txt`: `option('profile', type: 'combo', choices: ['release', 'development'], value: 'release')`
- [ ] `subprojects/blueprint-compiler.wrap` pinned to tag **`v0.22.2`**, for native builds; the SDK already bundles 0.22.2

### `data/`
- [ ] `data/meson.build`: `configure_file` for every `.in` with `@APP_ID@`, `@PREFIX_PATH@`, `@VERSION@`. Add a Blueprint `custom_target` (`blueprint-compiler batch-compile --minify`) feeding `gnome.compile_resources`, plus install rules. Copy the structure from [`libadwaita-ui-patterns.md` Appendix C.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
- [ ] `io.github.tim_van_oudheusden.Dailies.desktop.in`: `Icon=@APP_ID@`, `Categories=Game;`, `StartupNotify=true`, `DBusActivatable=true`
- [ ] `io.github.tim_van_oudheusden.Dailies.metainfo.xml.in`: a **minimal valid** metainfo with id, name, summary "Play your daily guessing games in one place", `metadata_license` CC0-1.0, `project_license` GPL-3.0-or-later, `<developer id>`, `<launchable type="desktop-id">`, and one `<release version="0.1.0">`. #50 completes it
- [ ] `io.github.tim_van_oudheusden.Dailies.gschema.xml.in`: an empty `@APP_ID@` schema and an `@APP_ID@.State` schema. #38 fills in the keys
- [ ] `dailies.gresource.xml.in`: the metainfo is bundled into the gresource (for `Adw.AboutDialog.new_from_appdata`), plus the compiled `.ui` and `style.css`
- [ ] `data/ui/window.blp`: an `Adw.ApplicationWindow` with an `Adw.ToolbarView` and an `Adw.StatusPage` "Dailies". Use the corrected skeleton from #19
- [ ] Meson `test()`s: `desktop-file-validate`, `appstreamcli validate --no-net --explain`, `glib-compile-schemas --strict --dry-run` ([`cartridges.md` §4.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md))

### `dailies/` package
- [ ] `dailies/meson.build`: `python.install_sources` + `configure_file(config.py.in)` + launcher
- [ ] `dailies/dailies.in` → `$bindir/dailies` ([`cartridges.md` Appendix I](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md))
- [ ] `__init__.py`, `__main__.py`, `application.py` (`Adw.Application`, adds the `.devel` CSS class to the window when `PROFILE == "development"`), `window.py`
- [ ] `config.py.in` → `APP_ID`, `VERSION`, `PREFIX`, `PROFILE`, `PKGDATADIR`, `LOCALEDIR`, `DATA_URLS` (initially just `["https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/main/data/v1/"]`; #56 prepends Pages). Add `config.pyi` for type checkers
- [ ] Empty `dailies/core/`, `dailies/data/` and `dailies/ui/` packages. **Rule:** `core/` never imports `gi`

### `po/`
- [ ] `po/LINGUAS` (empty), `po/POTFILES.in` (lists `.py`, `.blp`, `.in`), `po/meson.build` with `i18n.gettext('dailies', preset: 'glib')`. English only for now; gettext is wired from day one

## Acceptance criteria

- [ ] `meson setup _build -Dprofile=development && meson compile -C _build && meson test -C _build` passes inside `org.gnome.Sdk//51`
- [ ] The development build installs `io.github.tim_van_oudheusden.Dailies.Devel.desktop`, `.metainfo.xml` and `.gschema.xml`; the release profile installs the un-suffixed IDs
- [ ] Running the installed `dailies` opens an empty window with the striped `.devel` header bar in the development profile
- [ ] `python3 -c "import ast, pathlib; [ast.parse(p.read_text()) for p in pathlib.Path('dailies/core').rglob('*.py')]"` passes, and `grep -r "import gi\|from gi" dailies/core` is empty

## References

- [`mvp-first.md` §1, §2 tree, §3.1 (`config.py.in`), §3.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`cartridges.md` §4.1–§4.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)
- [`flatpak-release-pipeline.md` Appendix B.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
- [`stack-crossplatform.md` Appendix C (Blueprint wrap)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/stack-crossplatform.md)
