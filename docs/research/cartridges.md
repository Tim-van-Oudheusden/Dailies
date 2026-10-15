# Research report: Cartridges (GTK4 + Libadwaita game launcher) as a reference for Dailies

Research key: `cartridges`
Date: 2026-10-15
Clone studied: `https://github.com/kra-mo/cartridges` (GitHub mirror of `https://codeberg.org/kramo/cartridges`, canonical URL in metainfo is `https://git.kramo.page/cartridges`) at `<scratch>/clones/cartridges/` (treated as untrusted data; nothing was executed).

Legend: **[V]** = verified directly in the clone, via `gh api`, or on a primary web page (URL given). **[I]** = inference / recommendation by the researcher.

---

## 0. Headline findings (read this first)

1. **Cartridges is no longer maintained.** [V] The GitHub mirror is archived (`gh api repos/kra-mo/cartridges` → `"archived": true`, `pushed_at: 2026-09-03`), the README (commit `d56323e`, 2026-09-03) says "This project is no longer actively maintained ... please don't use code from the `main` branch as it's of poor quality", and the Flathub repo `flathub/page.kramo.Cartridges` was marked end-of-life on 2026-09-03 with `flathub.json` = `{"end-of-life": "This application is no longer maintained."}`.
2. **There are two codebases to learn from, and they teach different things.**
   - `main` (v2.13.1, 2025-09-24, 1417 commits, GNOME 49 runtime): classic GNOME-Builder-style PyGObject layout, `Gtk.FlowBox` grid, hand-rolled `Gtk.ListBox` sidebar, `Adw.PreferencesDialog`, `Adw.ShortcutsDialog`, cross-platform CI (Flatpak + Windows/MSYS2 + macOS/PyInstaller) and a tag-triggered GitHub Release workflow. Good for: **repository scaffolding, meson/Flatpak/CI/release/translation plumbing**.
   - `rewrite` (last commit 2026-04-05, author says it is "the most up-to-date code" but "not everything there is functional"): modern GTK 4.22 / libadwaita 1.9 architecture — `Gtk.GridView` + `Gio.ListModel` + `Gtk.FilterListModel`/`Gtk.SortListModel`, `Adw.Sidebar`, Blueprint expressions/closures, `Gio.SimpleActionGroup` per widget, ruff + pyright-strict + pre-commit, `python.install_sources()`, gresources per package, "Collections" feature (user-defined groups stored in GSettings as `aa{sv}`) that is the closest analogue to Dailies' **Favorites**. Good for: **UI architecture and code-style tooling**.
3. **Launching things outside the sandbox**: Cartridges runs `flatpak-spawn --host /bin/sh -c <cmd>` (needs `--talk-name=org.freedesktop.Flatpak`) for arbitrary executables, but opens **URLs** with `Gio.AppInfo.launch_default_for_uri(...)`, which goes through the OpenURI portal and needs no extra permission. Dailies only needs the latter for the "external browser" path. [V]
4. **Current versions to target (as of 2026-10-15)** [V]: GNOME 51 was released 2026-09-16 with its Flatpak SDK on Flathub (https://discourse.gnome.org/t/gnome-51-released/38820); GNOME 50 was released March 2026. `Adw.Sidebar` requires libadwaita ≥ 1.9 (GNOME 50 runtime) and `Gtk.TryExpression` (Blueprint `try { }`) requires GTK ≥ 4.22 (GNOME 51 runtime). blueprint-compiler latest tag v0.22.2 (2026-07-10). flatpak-github-actions latest release v6.8 (2026-08-30); the `flathub-infra/flatpak-github-actions` container images are only published up to `gnome-48` (README table + `docker.yml` matrix), so the manifest's `runtime-version` will be downloaded at build time if it is newer than the image's pre-cached runtime (Cartridges itself builds a `runtime-version: 49` manifest inside a `gnome-47` image — this works, it just downloads more).

---

## 1. Repository metadata [V]

| Item | Value | Source |
|---|---|---|
| App ID (release) | `page.kramo.Cartridges` | `meson.build` |
| App ID (development profile) | `page.kramo.Cartridges.Devel` | `meson.build` |
| Former ID | `hu.kramo.Cartridges` (kept via `<replaces>` in metainfo) | `data/page.kramo.Cartridges.metainfo.xml.in` |
| Licence | GPL-3.0-or-later (code), CC0-1.0 (metadata) | `LICENSE`, metainfo |
| Latest tag | `v2.13.1` (2025-09-24) | `git tag`, `git log` |
| Latest GitHub Release | `v2.12.1` (2025-03-23) with assets `Cartridges.Windows.exe`, `Cartridges.macOS.zip` (no Linux asset: Linux = Flathub) | `gh release view` |
| Stars (GitHub mirror) | 828 | `gh api` |
| Default branch | `main`; notable branch `rewrite` | `git branch -r` |
| Membership | GNOME Circle (badge in README; homepage `https://apps.gnome.org/Cartridges/`) | README, metainfo |
| Translations | Hosted Weblate `https://hosted.weblate.org/engage/cartridges/` (38 languages in `po/LINGUAS`) | README, `po/LINGUAS` (direct fetch of hosted.weblate.org returned HTTP 403, so the project page itself was not verified) |
| Flathub manifest repo | `https://github.com/flathub/page.kramo.Cartridges` — files `flathub.json`, `page.kramo.Cartridges.json` | `gh api` |

---

## 2. Language and toolchain

### 2.1 `main` branch [V]
- **Language**: Python 3 + PyGObject (`gi.require_version("Gtk", "4.0")`, `gi.require_version("Adw", "1")`). Third-party Python deps: `pyyaml`, `pillow`, `requests` (installed in the Flatpak via `pip3 install --no-index --find-links=file://${PWD}` modules).
- **UI language**: Blueprint (`.blp`) compiled to `.ui` at build time by `blueprint-compiler batch-compile`. Blueprint is pulled in as a Meson wrap subproject: `subprojects/blueprint-compiler.wrap` →

  ```ini
  [wrap-git]
  directory = blueprint-compiler
  url = https://gitlab.gnome.org/jwestman/blueprint-compiler.git
  revision = v0.16.0
  depth = 1

  [provide]
  program_names = blueprint-compiler
  ```
  (Current upstream is `https://gitlab.gnome.org/GNOME/blueprint-compiler`, latest tag v0.22.2, 2026-07-10. [V])
- **Build system**: Meson ≥ 0.59 with `i18n`, `gnome`, `python` modules; `gnome.post_install(glib_compile_schemas: true, gtk_update_icon_cache: true, update_desktop_database: true)`.
- **Dependencies declared**: `dependency('gtk4', version: '>= 4.15.0')`, `dependency('libadwaita-1', version: '>= 1.6.beta')`.
- **Meson options** (`meson_options.txt`): `profile` combo `release|development` (default `release`) and `tiff_compression` combo `webp|jpeg` (default `webp`, app-specific).
- **Code style**: Black + Pylint + isort (documented in `CONTRIBUTING.md`); `.pylintrc` disables docstring checks etc. and declares `additional-builtins=_`; `pyrightconfig.json` only sets `reportRedeclaration` and `reportMissingModuleSource` to `none`. No `pyproject.toml`, no pre-commit, no ruff on `main`.

### 2.2 `rewrite` branch [V]
- `pyproject.toml`: `requires-python = ">= 3.13"`, a `dev` dependency group (`blueprint-compiler @ git+https://gitlab.gnome.org/GNOME/blueprint-compiler.git`, `pillow`, `pre-commit`, `pygobject-stubs @ git+https://github.com/jamiethecat/pygobject-stubs.git`, `ruff`), `[tool.pyright] typeCheckingMode = "strict"` with a tuned ignore list, `[tool.ruff] builtins = ["_"]`, `select = ["ALL"]` with an explicit ignore list (reproduced in Appendix F).
- `.pre-commit-config.yaml`: pre-commit-hooks v6.0.0 (large files, trailing whitespace, EOF fixer, `file-contents-sorter` for `po/LINGUAS|po/POTFILES.in`), `ruff-pre-commit v0.14.10` (`ruff-check --select I --fix`, `ruff-check`, `ruff-format`), local hooks for `pyright`, `blueprint-compiler format --fix --no-diff`, `meson format --inplace`, `prettier` (css/json/yaml), `svgo` (svg). Full file in Appendix F.
- Meson ≥ 1.1.0, `meson.options` (new name), `python.install_sources(...)`, project version `49.0` (GNOME-style versioning), `blueprint-compiler batch-compile --minify`.
- Entry point is `data/cartridges.in` → `runpy.run_module("cartridges")`, with `cartridges/__main__.py` using `gi.events.GLibEventLoopPolicy` (asyncio integration from PyGObject ≥ 3.50).
- Resources are loaded at import time by iterating `importlib.resources.files("cartridges.resources")` and registering every `.gresource` found (data, icons, ui are three separate bundles installed into `<python site-packages>/cartridges/resources`).
- Runtime: `org.gnome.Platform` `master`, uses `Adw.Sidebar` (libadwaita 1.9), `Adw.WrapBox`, `Adw.ShortcutsDialog`, Blueprint `try { }` (GTK 4.22 `Gtk.TryExpression`), `Manette 0.2` for gamepads.

---

## 3. Project layout

### 3.1 `main` (v2.13.1) [V]
```
.
├── .github/
│   ├── FUNDING.yml                      # github: [kra-mo], liberapay: kramo
│   ├── ISSUE_TEMPLATE/bug_report.md     # classic md templates (labels: bug / enhancement)
│   ├── ISSUE_TEMPLATE/feature_request.md
│   └── workflows/{ci.yml, publish-release.yml}
├── .gitignore  .pylintrc  pyrightconfig.json
├── CODE_OF_CONDUCT.md  CONTRIBUTING.md  LICENSE  README.md
├── cartridges.doap                      # GNOME DOAP project file (GNOME Circle requirement)
├── meson.build  meson_options.txt
├── build-aux/
│   ├── flatpak/page.kramo.Cartridges.Devel.json   # dev manifest (release manifest lives on Flathub, .gitignored locally)
│   ├── macos/{cartridges.spec, icon.icns}         # PyInstaller
│   └── windows/{Cartridges.iss.in, icon.ico, meson.build}   # Inno Setup
├── cartridges/                          # Python package, installed to <site-packages>/cartridges
│   ├── cartridges.in                    # launcher script template → $bindir/cartridges
│   ├── shared.py.in  shared.pyi  __builtins__.pyi   # build-time constants (APP_ID, VERSION, PREFIX, PROFILE)
│   ├── main.py  window.py  preferences.py  details_dialog.py  game.py  game_cover.py
│   ├── errors/  importer/  logging/  store/  utils/
│   └── meson.build
├── data/
│   ├── cartridges.gresource.xml.in
│   ├── gtk/{window,game,preferences,details-dialog,shortcuts-dialog}.blp  gtk/style.css  gtk/style-dark.css
│   ├── icons/hicolor/scalable/apps/page.kramo.Cartridges{,.Devel}.svg
│   ├── icons/hicolor/symbolic/apps/page.kramo.Cartridges{,.Devel}-symbolic.svg
│   ├── icons/sources/*-source-symbolic.svg         # bundled into gresource under /icons/scalable/categories/
│   ├── icons/meson.build
│   ├── library_placeholder.svg  library_placeholder_small.svg
│   ├── page.kramo.Cartridges.desktop.in
│   ├── page.kramo.Cartridges.gschema.xml.in
│   ├── page.kramo.Cartridges.metainfo.xml.in
│   ├── screenshots/{1,2,3,4}.png
│   └── meson.build
├── docs/game_id.json.md                 # on-disk data format spec
├── po/{LINGUAS, POTFILES, cartridges.pot, *.po, meson.build}
├── search-provider/                      # GNOME Shell search provider (D-Bus service)
└── subprojects/blueprint-compiler.wrap
```

### 3.2 `rewrite` [V]
```
.pre-commit-config.yaml  pyproject.toml  meson.build  meson.options  LICENSE  README.md
cartridges/{__init__.py, __main__.py, application.py, collections.py, config.py.in, config.pyi, cover.py, gamepads.py, games.py, meson.build}
cartridges/sources/{__init__.py, desktop.py, heroic.py, imported.py, itch.py, legendary.py, lutris.py, steam.py}
cartridges/ui/{__init__.py, closures.py, window.blp, window.py, game-item.blp, game_item.py, cover.blp, cover.py,
               game-details.blp, game_details.py, collection-details.blp, collection_details.py, collections.py,
               games.py, sources.py, shortcuts-dialog.blp, shortcuts-dialog-mac.blp, style.css, ui.gresource.xml.in, meson.build}
data/{cartridges.in, data.gresource.xml.in, meson.build, page.kramo.Cartridges.{desktop,gschema.xml,metainfo.xml,service}.in}
data/icons/{meson.build, icons.gresource.xml.in, page.kramo.Cartridges{,.Devel}{,-symbolic}.svg, <30 custom -symbolic.svg>}
flatpak/{page.kramo.Cartridges.Devel.json, python3-pillow.json, python3-pybind11.json}
po/{LINGUAS, POTFILES.in, meson.build}
```
No `.github/` directory exists on `rewrite` (CI was not ported). [V]

---

## 4. Build system details worth copying

### 4.1 Profile → App ID / resource prefix [V] (`meson.build`, main)
```meson
profile = get_option('profile')
if profile == 'development'
  app_id = 'page.kramo.Cartridges.Devel'
  prefix = '/page/kramo/Cartridges/Devel'
elif profile == 'release'
  app_id = 'page.kramo.Cartridges'
  prefix = '/page/kramo/Cartridges'
endif

conf = configuration_data()
conf.set('PYTHON', py_installation.full_path())
conf.set('APP_ID', app_id)
conf.set('PREFIX', prefix)
conf.set('VERSION', meson.project_version())
conf.set('PROFILE', profile)
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)
```
Every `*.in` file (`desktop`, `gschema.xml`, `metainfo.xml`, `gresource.xml`, `shared.py`, launcher script) is passed through `configure_file(... configuration: conf)` so one source tree yields both the `.Devel` and release app. The window adds the `devel` CSS class when `PROFILE == "development"` (striped header bar).

### 4.2 Blueprint compilation [V] (`data/meson.build`)
```meson
blueprints = custom_target(
  'blueprints',
  input: files('gtk/details-dialog.blp', 'gtk/game.blp', 'gtk/preferences.blp', 'gtk/shortcuts-dialog.blp', 'gtk/window.blp'),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)
```
Then `gnome.compile_resources('cartridges', configure_file(input: 'cartridges.gresource.xml.in', ...), gresource_bundle: true, install: true, install_dir: pkgdatadir, dependencies: [blueprints, appstream_file])`. The metainfo is included in the gresource so `Adw.AboutDialog.new_from_appdata()` can read it at runtime.

### 4.3 Validation tests run by `meson test` / `flatpak-builder --run-tests` [V]
- `desktop-file-validate <desktop>`
- `appstreamcli validate --no-net --explain <metainfo>`
- `glib-compile-schemas --strict --dry-run <schema dir>`
The Devel Flatpak manifest sets `"run-tests": true` so these run in CI.

### 4.4 Translations [V]
- `po/meson.build`: `i18n.gettext('cartridges', preset: 'glib', args: ['--copyright-holder=kramo', '--package-name=Cartridges'])` (rewrite: `i18n.gettext(meson.project_name(), preset: 'glib')`).
- `po/POTFILES` lists `.desktop.in`, `.gschema.xml.in`, `.metainfo.xml.in`, every `.blp`, and every `.py` with user-visible strings.
- `.desktop` and `.metainfo.xml` are produced with `i18n.merge_file(..., po_dir: '../po')`.
- Translator credits via `about.set_translator_credits(_("translator-credits"))` with a translator comment.
- `__builtins__.pyi` declares `def _(_msg: str, /) -> str: ...` so type checkers know about `gettext.install`'s global `_`.

---

## 5. How the UI is built

### 5.1 `main` window (`data/gtk/window.blp`) [V]
Full file reproduced in Appendix A. Structure:
```
Adw.ApplicationWindow (title, width-request 360, height-request 100)
└── Adw.Breakpoint "max-width: 564px" → overlay_split_view.collapsed = true; details view switches to vertical layout
└── Adw.ToastOverlay
    └── Adw.NavigationView navigation_view
        ├── Adw.NavigationPage library_page  (title "All Games")
        │   └── Adw.OverlaySplitView overlay_split_view (sidebar-width-fraction .2)
        │       ├── [sidebar] Adw.NavigationPage → Adw.ToolbarView → Adw.HeaderBar(+ sidebar toggle)
        │       │                                  → ScrolledWindow → ListBox sidebar  styles["navigation-sidebar"]
        │       │        rows: "All Games" (view-grid-symbolic + count), "Added" (list-add-symbolic + count),
        │       │              heading row "Imported" (non-selectable), then one row per import source added in Python
        │       └── Adw.ToolbarView library_view
        │           ├── [top] Adw.HeaderBar: [start] sidebar toggle (visible: bind overlay_split_view.show-sidebar inverted),
        │           │        [start] MenuButton "Add Game" (menu add_games), [end] MenuButton primary_menu (open-menu-symbolic),
        │           │        [end] ToggleButton search_button (system-search-symbolic, action win.toggle_search)
        │           ├── [top] SearchBar search_bar (search-mode-enabled: bind search_button.active bidirectional;
        │           │        key-capture-widget: navigation_view) → Adw.Clamp(500) → SearchEntry
        │           └── Overlay library_overlay → ScrolledWindow → FlowBox library
        │                 (homogeneous, halign center, column/row-spacing 12, margins 15, selection-mode none, styles["no-hover"])
        │                 Adw.StatusPage notice_empty / notice_no_results are added as overlay children when needed
        ├── Adw.NavigationPage hidden_library_page ("Hidden Games") – same header/search/FlowBox pattern, styles["background"]
        └── Adw.NavigationPage details_page ("Game Details") – Overlay with blurred cover Picture behind an Adw.ToolbarView
              containing Picture cover (200×300, "card"), title-1 label, heading label for developer,
              Added/Last played labels, "Play" pill button, and circular raised buttons: Edit, Hide/Unhide, Remove, Search▾
menus: primary_menu (Sort submenu with stateful win.sort_by targets a-z/z-a/newest/oldest/last_played; "Show Hidden";
       Preferences / Keyboard Shortcuts / About), add_games, search ("Search on…" IGDB, SteamGridDB, ProtonDB, PCGamingWiki, Lutris, HowLongToBeat)
```
Python side (`window.py`): `Gtk.FlowBox.set_filter_func` / `set_sort_func` with `invalidate_filter()` on each keystroke; `max_children_per_line` 10 (or GSettings `library-rows`); sidebar rows are created in `create_source_rows()` and sorted by game count; selecting a row sets `filter_state` and, when collapsed, hides the sidebar. Window geometry is persisted through `Gio.Settings.bind("width"/"height"/"is-maximized", window, "default-width"/...)` to the `<APP_ID>.State` schema.

### 5.2 `main` game tile (`data/gtk/game.blp`) [V] — Appendix B
`template $Game: Box` (vertical) → `Adw.Clamp(maximum-size 200, unit px)` → `Overlay` with two `Revealer` overlays (crossfade): a circular `osd` play button top-left and a circular `osd` `MenuButton` (view-more-symbolic) top-right, revealed by `Gtk.EventControllerMotion` enter/leave; the main child is `Button cover_button` (`overflow: hidden`, styles `card`, `accessibility { labelled-by: title; }`) containing `Overlay(Adw.Spinner, Picture cover 200×300)` + ellipsized title `Label`. Menus `game_options` / `hidden_game_options` (Edit / Hide or Unhide / Remove) are swapped by `DisplayManager` depending on `game.hidden`. Clicking the cover shows details; the overlay play button launches (swappable via GSettings `cover-launches-game`).

### 5.3 `rewrite` window (`cartridges/ui/window.blp`) [V] — Appendix C (full)
The modern, model-driven version. Key widgets:
- `Adw.OverlaySplitView split_view` with pixel sidebar width (`min-sidebar-width: 224`, `max-sidebar-width: bind split_view.min-sidebar-width`), breakpoint `max-width: 730px` (comment: "3 columns + 48px of inherent padding") collapses it.
- Sidebar is **`Adw.Sidebar`** (libadwaita 1.9) with `Adw.SidebarSection`s: fixed "All Games" item, a `sources` section bound to a `Gio.ListModel` with `self.sources.bind_model(sources.model, SourceSidebarItem)`, a `collections` section bound the same way (with a `menu-model` for Edit/Remove context menu), and a "New Collection" item that acts like a button. Signals: `activated => $_navigate()`, `setup-menu => $_setup_sidebar_menu()`, `notify::selected => $_update_selection()`.
- The header bar's `title-widget` is an `Adw.Clamp` → `CenterBox` whose centre is a `SearchEntry` (always visible, `key-capture-widget: template`, placeholder bound to the page title) and whose end is a `MenuButton sort_button` (icon `filter-symbolic`, "Sort & Filter") with sections for Sort (stateful `win.sort-mode`) and "Show Hidden Games" (`Gio.PropertyAction`).
- Content: `Adw.ToastOverlay` → `Adw.ViewStack view_stack` whose `visible-child-name` is a Blueprint closure expression choosing `grid` / `empty-search` / `empty-collection` / `empty-hidden` / `empty` based on `grid.model.n-items`, `search-text`, `collection`, `show-hidden`.
- Grid: `ScrolledWindow(hscrollbar-policy never)` → **`GridView grid`** (`max-columns: 12`, `single-click-activate: true`, `activate => $_show_details()`), model `NoSelection → FilterListModel(watch-items: true)` with an `EveryFilter` of `$CollectionFilter`, an `AnyFilter` of two `StringFilter`s (name/developer against `template.search-text`) and a `BoolFilter` on `hidden`. Factory is `BuilderListItemFactory { template ListItem { child: $GameItem { game: bind template.item; position: bind template.position; } } }`.
- The details page `$GameDetails details {}` is a second `Adw.NavigationPage` (tag `details`) pushed with `navigation_view.push_by_tag("details")`.
- Keyboard shortcuts are declared in the window's `ShortcutController` with a closure `$shortcut("<Control>f")` that swaps `<Control>` → `<Meta>` on macOS.
- Window state binding: `STATE_SETTINGS.bind("show-sidebar", self.split_view, "show-sidebar", flags)` and `self.add_action(STATE_SETTINGS.create_action("sort-mode"))` (GSettings-backed stateful action, no hand-written handler).

### 5.4 `rewrite` tile (`game-item.blp`) and cover (`cover.blp`) [V] — Appendix C
`template $GameItem: Box { name: "game-item"; orientation: vertical; spacing: 12; EventControllerMotion motion { notify::contains-pointer => $_reveal_buttons(); } Overlay { child: $Cover cover { paintable: bind template.game as <$Game>.cover; }; [overlay] MenuButton options (circular, top-right, PopoverMenu with Edit / Hide / Unhide (hidden-when action-disabled) / Remove + "New Collection" + custom "collections" item hosting an Adw.WrapBox of toggle buttons); [overlay] Button play ("Play", pill, bottom-centre) } Label { label: bind template.game as <$Game>.name; ellipsize: middle; } }`. Buttons are hidden with a CSS class `hidden` (opacity 0 + translateY) instead of `Gtk.Revealer`; CSS uses `backdrop-filter: blur(9px) brightness(30%) saturate(600%)` for glassy OSD buttons. `$Cover` is an `Adw.Bin` with a custom `Gtk.LayoutManager` forcing an exact size and an `Adw.ViewStack` switching between `Picture` (content-fit chosen by aspect ratio) and a dimmed symbolic app-icon fallback (`icon-name: bind $format("{}-symbolic", application-id)`), styles `card`.

### 5.5 Preferences dialog (`data/gtk/preferences.blp`, main) [V] — Appendix D
`template $CartridgesPreferences: Adw.PreferencesDialog { search-enabled: true; }` with three `Adw.PreferencesPage`s (`name`, `title`, `icon-name`: `user-home-symbolic`, `document-save-symbolic`, `image-x-generic-symbolic`). Rows used: `Adw.SwitchRow` (bound to GSettings with `schema.bind(key, row, "active", Gio.SettingsBindFlags.DEFAULT)` — helper `bind_switches({...})` maps `"exit-after-launch"` → attribute `exit_after_launch_switch`), `Adw.ExpanderRow { show-enable-switch: true; [prefix] Image {...} }` bound to a boolean key via `"enable-expansion"`, `Adw.ActionRow` styles `property` with a flat folder `Button` suffix that opens `Gtk.FileDialog().select_folder(...)`, `Adw.EntryRow` for an API key, `Adw.ButtonRow` styles `destructive-action` in a "Danger Zone" group with `separate-rows: true`. Single-instance guard: class attribute `is_open` set in `__init__` and reset on `closed`. Opened from the app with `CartridgesPreferences().present(shared.win)`, optionally `set_visible_page_name(page_name)`.

### 5.6 Shortcuts dialog [V]
`data/gtk/shortcuts-dialog.blp` is a standalone (non-template) `Adw.ShortcutsDialog shortcuts_dialog { Adw.ShortcutsSection { title: _("General"); Adw.ShortcutsItem { title: _("Search"); action-name: "win.toggle_search"; } ... } }` — items reference **action names**, and libadwaita looks up the accelerators registered with `set_accels_for_action`. (The rewrite variant hard-codes `accelerator: "<Control>f"` instead and keeps a separate `shortcuts-dialog-mac.blp` selected in `meson.build` with `host_machine.system() == 'darwin' ? ... : ...`.) Release note for 2.13.1: "Updated for GNOME 49, using the new keyboard shortcuts dialog." so `Adw.ShortcutsDialog` is a GNOME 49 / libadwaita 1.8 widget. [V]

### 5.7 About dialog [V] (`main.py`)
```python
about = Adw.AboutDialog.new_from_appdata(shared.PREFIX + "/" + shared.APP_ID + ".metainfo.xml", shared.VERSION)
about.set_developers(("kramo https://kramo.page", ...))
about.set_designers(("kramo https://kramo.page",))
about.set_copyright("© 2022-2024 kramo")
about.set_translator_credits(_("translator-credits"))
about.set_debug_info(debug_str)                 # contents of the session log files
about.set_debug_info_filename("cartridges.log")
about.add_legal_section("Steam Branding", "© 2023 Valve Corporation", Gtk.License.CUSTOM, "...")
about.present(shared.win)
```
Rewrite: `Adw.AboutDialog(appdata_resource_path=f"{PREFIX}/{APP_ID}.metainfo.xml")`.

### 5.8 Keyboard shortcuts / actions (`main.py`) [V]
A compact `create_actions({...})` helper takes tuples `(name, (accels...), scope)`; scope defaults to the application (`app.`) or `shared.win` (`win.`); on macOS `<primary>` is replaced by `<meta>`. Defaults: `quit <primary>q`, `preferences <primary>comma`, `add_game <primary>n`, `import <primary>i`, `remove_game_details_view Delete`, `show_sidebar F9`, `show_hidden <primary>h`, `go_to_parent <alt>Up`, `go_home <alt>Home`, `toggle_search <primary>f`, `undo <primary>z`, `open_menu F10`, `close <primary>w`. Sort is a `Gio.SimpleAction.new_stateful("sort_by", GLib.VariantType.new("s"), ...)` persisted to GSettings `sort-mode`. Search entry has an inline `ShortcutController { Shortcut { trigger: "Escape"; action: "action(win.toggle_search)"; } }`.

### 5.9 CSS (`data/gtk/style.css`, main) [V]
```css
:root { --accent-color: var(--purple-5); --accent-bg-color: var(--purple-3); }
.no-hover > flowboxchild:hover { background-color: transparent; }
#details_view { background-color: white; }
#details_view_play_button { color: white; background-color: rgba(0, 0, 0, 0.8); }
@media (prefers-color-scheme: dark) { :root { --accent-color: var(--purple-1); --accent-bg-color: var(--purple-4); } ... }
```
Per-app accent colour override via libadwaita CSS variables; loaded from the gresource alias `style.css` (`style-dark.css` is a legacy leftover not listed in the gresource). The rewrite's `style.css` (Appendix C) sets `--accent-bg-color: var(--accent-purple)` and styles `#grid > child` to remove GridView's default child chrome (`padding: 0; border-radius: 0; background: none; outline: none; box-shadow: none;`).

---

## 6. Data storage

### 6.1 `main` [V]
- **One JSON file per game**: `$XDG_DATA_HOME/cartridges/games/<game_id>.json` (`shared.games_dir = data_dir / "cartridges" / "games"`), written by `FileManager` with `json.dump({...}, indent=4, sort_keys=True)`. Attributes (spec in `docs/game_id.json.md`, spec version 1.5 in code, doc says 2.0): `added` (unix ts), `executable` (str or argv list), `game_id` (`<source>_<id>`), `source`, `hidden` (bool), `last_played` (unix ts, 0 = never), `name`, `developer` (optional), `removed` (bool, tombstone deleted at next start), `blacklisted` (bool), `version`.
- **Covers**: `$XDG_DATA_HOME/cartridges/covers/<game_id>.tiff` (webp- or jpeg-compressed TIFF via Pillow) or `.gif` for animated covers; placeholder SVGs come from the gresource.
- **Settings**: GSettings schema `<APP_ID>` (preferences: booleans, source locations as strings, `sgdb-key`, `library-rows` `u`) and `<APP_ID>.State` (`width` i 1170, `height` i 795, `is-maximized`, `sort-mode` s with `<choices>`, `show-sidebar`, `steam-limiter-tokens-history`). Full schema in Appendix E.
- Deleting is "soft": `removed = True` + save + toast with Undo; `Store.add_game()` cleans up the files of a removed game on the next load.

### 6.2 `rewrite` [V]
- `Game` is a `GObject` with `GObject.Property` for every field (`Game(Gio.SimpleActionGroup)`), loaded with `Game.from_data(dict)` which type-checks against a `PROPERTIES` tuple; `save()` writes the same JSON. `GAMES_DIR = Path(GLib.get_user_data_dir(), "cartridges") / "games"`.
- `sources.model` is a `Gio.ListStore(item_type=Source)` where each `Source` implements `Gio.ListModel[Game]`; the library model is `Gtk.SortListModel(Gtk.FilterListModel(Gtk.FlattenListModel(sources.model), filter=EveryFilter[not removed, not blacklisted], watch_items=True), sorter=Gtk.CustomSorter)`. Sorting reads `STATE_SETTINGS.get_string("sort-mode")` and re-sorts via `sorter.changed(Gtk.SorterChange.DIFFERENT)` on `changed::sort-mode`.
- **Collections** (user-defined groups; nearest thing to Favorites) are stored entirely in GSettings key `collections` of type `aa{sv}` — each entry `{name: s, icon: s, game-ids: as, removed: b}` — loaded in `collections.load()` and written back wholesale in `collections.save()`. The schema shrank to just that one key plus the `.State` schema (`width` 920, `height` 700, `is-maximized`, `sort-mode`, `show-sidebar`).

---

## 7. Favorites / hidden implementation (what Dailies can reuse)

Cartridges has **no "favorite" flag**; the two relevant mechanisms are:

1. **Hidden** [V]: a boolean on the record. `main`: `Game.toggle_hidden()` flips `hidden`, saves, pops the details page if open, re-emits `update-ready` (which moves the widget between the `library` and `hidden_library` FlowBoxes) and shows a toast `"{} hidden"` with an **Undo** button (`toast.set_button_label(_("Undo"))`, `toast.connect("button-clicked", win.on_undo_action, game, "hide")`, toasts tracked in `win.toasts[(game, action)]`, `<primary>z` undoes the last). `rewrite`: `game.hidden = True; window.send_toast(_("{} hidden").format(game.name), undo=lambda: setattr(game, "hidden", False))`, while the view simply has `BoolFilter { expression: expr item as <$Game>.hidden; invert: bind template.show-hidden inverted; }` so visibility is declarative.
2. **Collections** [V] (rewrite): a `Collection(GObject.Object)` with `name`, `icon`, `removed`, an internal `set` of game IDs, and an `items-changed` signal; `CollectionFilter(Gtk.Filter)` whose `do_match` returns `item.game_id in self.collection`; `CollectionSidebarItem(Adw.SidebarItem)` bound to the collection with a `GObject.BindingGroup`; a `CollectionsBox(Adw.Bin)` holding an `Adw.WrapBox` of `CollectionButton(Gtk.ToggleButton)` that is built when the item's popover opens and committed (`add`/`discard`, then `collections.save()`) when it closes. Icons for collections are a fixed list of bundled symbolic SVGs (`star`, `heart`, …) with emoji a11y labels.

**[I] For Dailies "Favorites"**: model it as a single implicit collection: a `favorites` GSettings key of type `as` (list of DLE IDs), a `Gtk.Filter` subclass identical to `CollectionFilter`, a pinned first `Adw.SidebarItem` ("Favorites", `starred-symbolic`), and a `ToggleButton` with `starred-symbolic`/`non-starred-symbolic` on each tile and on the details page. Toast-with-undo on unfavorite is a nice touch that Cartridges demonstrates.

---

## 8. Opening external programs / URLs from inside Flatpak [V]

`cartridges/utils/run_executable.py` (main):
```python
def run_executable(executable) -> None:
    args = (
        "flatpak-spawn --host /bin/sh -c " + quote(executable)  # Flatpak
        if os.getenv("FLATPAK_ID") == shared.APP_ID
        else executable  # Others
    )
    subprocess.Popen(args, cwd=shared.home, shell=True, start_new_session=True,
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
```
Rewrite detects the sandbox with `Path("/.flatpak-info").exists()` instead of `FLATPAK_ID`. `flatpak-spawn --host` requires the manifest permission `--talk-name=org.freedesktop.Flatpak` (present in both manifests) and is a sandbox escape that Flathub flags in review; Cartridges needs it because it launches arbitrary host binaries.

For **web links** Cartridges uses `Gio.AppInfo.launch_default_for_uri(f"{uri}{quote(name)}")` (`main.py: search()`), which inside Flatpak goes through the `org.freedesktop.portal.OpenURI` portal and needs **no** `finish-args`. The `docs/game_id.json.md` spec also recommends `xdg-open url://...` style executables for sources with URL handlers.

**[I] For Dailies**: the "open in external browser" path should use `Gtk.UriLauncher(uri=...).launch(window, None, callback)` (GTK ≥ 4.10, portal-aware) or `Gio.AppInfo.launch_default_for_uri`; neither needs `--talk-name=org.freedesktop.Flatpak`. The "configured browser" preference (e.g. launch a specific Flatpak browser) is the only case that would need `flatpak-spawn --host flatpak run <id>` and thus the `org.freedesktop.Flatpak` talk-name, which Flathub reviewers scrutinise — consider making it optional or implementing it as "set default browser in system settings" guidance instead. The built-in browser option implies a WebKitGTK dependency (`org.gnome.Platform` ships `webkitgtk-6.0`), which is outside this report's scope.

---

## 9. Flatpak manifests

### 9.1 Development manifest (in-tree, `build-aux/flatpak/page.kramo.Cartridges.Devel.json`, main) [V] — Appendix G (full)
- `"runtime": "org.gnome.Platform"`, `"runtime-version": "49"`, `"sdk": "org.gnome.Sdk"`, `"command": "cartridges"`.
- `finish-args`: `--share=network`, `--share=ipc`, `--socket=fallback-x11`, `--device=dri`, `--socket=wayland`, `--talk-name=org.freedesktop.Flatpak`, `--filesystem=host`, plus many read-only `--filesystem=~/.var/app/<other-app>/...:ro` and `/var/lib/flatpak/{app,exports}:ro`, `xdg-data/flatpak/{app,exports}:ro` (all import-source specific; Dailies needs none of these).
- `cleanup`: `/include`, `/lib/pkgconfig`, `/man`, `/share/doc`, `/share/gtk-doc`, `/share/man`, `/share/pkgconfig`, `*.la`, `*.a`.
- Modules: a `python3-modules` wrapper containing `python3-pyyaml`, `python3-pillow`, `python3-requests` (each `buildsystem: simple` with `pip3 install --verbose --exists-action=i --no-index --find-links="file://${PWD}" --prefix=${FLATPAK_DEST} "<pkg>" --no-build-isolation` and pinned `files.pythonhosted.org` sources with sha256 — the output format of `flatpak-pip-generator`), then the app module: `{"name": "cartridges", "builddir": true, "buildsystem": "meson", "run-tests": true, "config-opts": ["-Dprofile=development"], "sources": [{"type": "dir", "path": "../.."}]}`.
- Rewrite manifest (`flatpak/page.kramo.Cartridges.Devel.json`) is leaner: `runtime-version: "master"`, adds `--device=input` (gamepads), uses `--filesystem=host:ro`, and splits pip modules into separate files referenced with `"modules": ["python3-pillow.json"]` (nested `python3-pybind11.json`). Pillow 12.1.1 at that time.

### 9.2 Flathub manifest (`flathub/page.kramo.Cartridges`) [V]
Identical to the dev manifest except `"id": "page.kramo.Cartridges"`, no `config-opts`, and the app source is a pinned git tag:
```json
{ "name": "cartridges", "builddir": true, "buildsystem": "meson",
  "sources": [ { "type": "git", "url": "https://git.kramo.page/cartridges", "tag": "v2.13.1", "commit": "4c49baddbc49053b1b9c64b49aa032dffb2d79b9" } ] }
```
The release manifest is **not** kept in the app repo (`.gitignore` contains `build-aux/flatpak/page.kramo.Cartridges.json`). Flathub commit history shows the v2.13 update was reverted/re-applied four times between 2025-09-24 and 2025-11-12 before the 2026-09-03 `EOL` commit — a reminder that Flathub updates are PRs to a separate repo. [V]

---

## 10. CI (`.github/workflows/ci.yml`, main) [V] — Appendix H (full)
Triggers: `push` to `main`, `pull_request`. `concurrency.group: release-${{ github.sha }}`.
- **flatpak** job: `runs-on: ubuntu-latest`, `container: image: bilelmoussaoui/flatpak-github-actions:gnome-47, options: --privileged`, steps `actions/checkout@v4` then `flatpak/flatpak-github-actions/flatpak-builder@v6.5` with `bundle: page.kramo.Cartridges.Devel.flatpak`, `manifest-path: build-aux/flatpak/page.kramo.Cartridges.Devel.json`. The action uploads the `.flatpak` bundle as a workflow artifact by default (`upload-artifact: true`, `artifact-name: app-${arch}.flatpak`). Note the image is the old Docker Hub name; the current documented image is `ghcr.io/flathub-infra/flatpak-github-actions:<runtime>` with tags `freedesktop-23.08`, `freedesktop-24.08`, `gnome-47`, `gnome-48`, `kde-5.15-24.08`, `kde-6.7`, `kde-6.8`, `kde-6.9` (README table and `docker.yml` matrix of `flathub-infra/flatpak-github-actions`, master). The image is built `FROM ghcr.io/flathub/flatpak-builder-lint:latest` and pre-adds the `flathub`, `flathub-beta` and `gnome-nightly` remotes, so a manifest with `runtime-version: 49/50/51` will still build (runtime fetched at build time).
- **windows** job: `windows-latest`, `msys2/setup-msys2@v2` (`msystem: UCRT64`) installing `mingw-w64-ucrt-x86_64-{gtk4,libadwaita,python-gobject,python-yaml,python-requests,python-pillow,desktop-file-utils,ca-certificates,meson}` + git; `meson setup _build && ninja -C _build install`; smoke test `timeout 2 cartridges; [ "$?" -eq "124" ]`; `iscc` builds an Inno Setup installer from the meson-configured `Cartridges.iss`; artifact "Windows Installer".
- **macos** job: `macos-latest`, Homebrew `meson pygobject3 libadwaita adwaita-icon-theme desktop-file-utils pyinstaller pillow`, `pip3 install --break-system-packages requests PyYAML`, `meson setup _build -Dtiff_compression=jpeg`, PyInstaller with `build-aux/macos/cartridges.spec` (bundles `_build/data/cartridges.gresource` into `Resources`, `bundle_identifier` = app id), zip, artifact "macOS Application".
- There is **no lint/format job** in CI on `main` (style is enforced socially via CONTRIBUTING.md); on `rewrite` it would be `pre-commit`, but no workflow exists there.

---

## 11. Release process [V]

Reconstructed from files and history:
1. Bump `version:` in `meson.build` (e.g. `2.13.1`).
2. Add a `<release version="2.13.1" date="2025-09-24"><description translate="no"><p>…</p></description></release>` entry at the top of `<releases>` in `data/page.kramo.Cartridges.metainfo.xml.in` (21 entries kept historically; `translate="no"` keeps release notes out of the PO files).
3. Tag `vX.Y[.Z]` and push. `.github/workflows/publish-release.yml` (trigger `push: tags: "*"`) then:
   - downloads the CI artifacts for the same commit with `dawidd6/action-download-artifact@v9` (`workflow: ci.yml`, `commit: ${{ github.sha }}`),
   - extracts the **first** `<release>` description from the metainfo with an inline Python step (regex `<release.*>\s*<description.*>\n([\s\S]*?)\s*</description>\s*<\/release>`, `textwrap.dedent`) into `release_notes`,
   - creates the GitHub Release with `softprops/action-gh-release@v2.2.2` (`files: Windows Installer/Cartridges Windows.exe`, `macOS Application/Cartridges macOS.zip`, `fail_on_unmatched_files: true`, `tag_name`, `body_path: release_notes`).
4. Open a PR on `flathub/page.kramo.Cartridges` updating `tag` + `commit` of the git source (Flathub builds and publishes).
Linux users were never offered a `.flatpak` bundle on GitHub Releases — only Flathub. [V]

**[I] For Dailies** the same workflow can attach the CI-built `page.kramo.Cartridges.Devel.flatpak`-style bundle (`<AppId>.flatpak`) to the Release so users can `flatpak install --user ./Dailies.flatpak` before a Flathub remote exists; the `flatpak-builder` action already produces it as an artifact.

---

## 12. App ID, metainfo and desktop file [V] — Appendix E (full head)

- `<component type="desktop-application">`, `<id>@APP_ID@</id>`, `<replaces><id>hu.kramo.Cartridges</id></replaces>`, `<metadata_license>CC0-1.0</metadata_license>`, `<project_license>GPL-3.0-or-later</project_license>`, `<name>`, `<summary>Launch all your games</summary>` (≤ 35 chars, no trailing period), one-paragraph `<description>`.
- `<url type="...">` for `homepage`, `bugtracker`, `translate`, `contact`, `vcs-browser`, `contribute`.
- `<developer id="page.kramo"><name translate="no">kramo</name></developer>`, `<launchable type="desktop-id">@APP_ID@.desktop</launchable>`, `<translation type="gettext">cartridges</translation>`.
- `<branding><color type="primary" scheme_preference="light">#d5b0e7</color><color type="primary" scheme_preference="dark">#501a5c</color></branding>` (used by GNOME Software / Flathub banners).
- `<supports><control>pointing|keyboard|touch</control></supports>`, `<requires><display_length compare="ge">360</display_length></requires>` (declares mobile-friendliness; matches the window's `width-request: 360`).
- `<screenshots>`: 4 `<screenshot>` entries, first `type="default"`, each with `<image>https://codeberg.org/kramo/cartridges/raw/branch/main/data/screenshots/N.png</image>` and a `<caption>`.
- `<content_rating type="oars-1.1" />` (empty = no content descriptors).
- Desktop file (`data/page.kramo.Cartridges.desktop.in`):
  ```ini
  [Desktop Entry]
  Name=Cartridges
  GenericName=Game Launcher
  Comment=Launch all your games
  Exec=cartridges
  Icon=@APP_ID@
  Terminal=false
  Type=Application
  Categories=GNOME;GTK;Game;PackageManager;
  # Translators: Leave "cartridges" untranslated here.
  Keywords=gaming;games;play;cartridges;launch;launcher;steam;lutris;heroic;epic;bottles;itch;legendary;retroarch;
  StartupNotify=true
  ```
- `cartridges.doap`: DOAP file with name, shortdesc, description, homepage/download-page/bug-database, `<programming-language>Python</programming-language>`, `<platform>GTK 4</platform>`, `<platform>Libadwaita</platform>`, maintainer with GitHub/GitLab accounts — required for GNOME Circle / apps.gnome.org listing.

### Screenshot conventions [V]
Files `data/screenshots/1.png … 4.png`; measured sizes 1146×698, 1146×698, 602×727, 482×812 (two landscape main-window shots, two portrait dialog shots). Referenced by absolute raw-URL in metainfo. (Flathub quality guidelines on screenshot sizes were not checked in this report.)

---

## 13. App icon source files [V]

- Full-colour: `data/icons/hicolor/scalable/apps/page.kramo.Cartridges.svg` — SVG, `width="128" height="128"`, 2.7 KB, hand-optimised; a purple cartridge (`#C061CB`, gradient stops `#613583`/`#9141AC`, dark details `#3D3846`) drawn on the standard 128 px GNOME icon canvas. The `.Devel.svg` variant is 10.4 KB (contains the extra "development" striping/gradient geometry) and is installed only for the `development` profile because `data/icons/meson.build` installs `('@0@.svg').format(app_id)`.
- Symbolic: `data/icons/hicolor/symbolic/apps/page.kramo.Cartridges-symbolic.svg` — 16×16, single `fill="black"` path with `fill-rule="evenodd"`, 618 bytes; the Devel symbolic is byte-identical content under another name. The symbolic icon is used in the empty-state `Adw.StatusPage` (`set_icon_name(APP_ID + "-symbolic")`) and in the rewrite's cover placeholder.
- No icon source project file (e.g. `.svg` with Inkscape layers / `icon-source.svg`) is committed; only exported SVGs. [V] The colour palette is the GNOME HIG palette (Purple 3/4/5, Dark 4). [I: by colour value]
- Install dirs: `share/icons/hicolor/scalable/apps/<APP_ID>.svg` and `share/icons/hicolor/symbolic/apps/<APP_ID>-symbolic.svg`.

---

## 14. Recommendations for Dailies

**Architecture (take from `rewrite`, not `main`)** [I unless noted]
1. Target `org.gnome.Platform//51` (released 2026-09-16 [V]) so you can use `Adw.Sidebar` (libadwaita 1.9 [V]), `Adw.ShortcutsDialog` (1.8), `Adw.WrapBox`, `Gtk.GridView`, and Blueprint `try { }`/`Gtk.TryExpression` (GTK 4.22 [V]). If you want to stay one release behind for distro Builder users, GNOME 50 still gives you `Adw.Sidebar` but not `try {}`.
2. Window skeleton: `Adw.ApplicationWindow` → `Adw.NavigationView` (library page + details page by tag) → `Adw.OverlaySplitView` with pixel-width sidebar + `Adw.Breakpoint` collapse → `Adw.Sidebar` sections: **Favorites** (always first, per the brief), Popular, Trending (weekly), then one `Adw.SidebarSection` bound to a `Gio.ListModel` of categories, with `Adw.SidebarItem` subclasses bound via `GObject.BindingGroup` exactly like `CollectionSidebarItem`.
3. Grid of tiles: `Gtk.GridView` (`max-columns`, `single-click-activate`) over `NoSelection(FilterListModel(EveryFilter[CategoryFilter, AnyFilter[StringFilter name, StringFilter category], BoolFilter favorites-only], SortListModel))` with a `BuilderListItemFactory` whose child is a `$DleItem` template; tile = `$Cover`-like `Adw.Bin` with a fixed-size layout manager (DLE logos are square, so use 1:1 instead of 200×300) with a star `ToggleButton` overlay and an open/"Play" pill. Copy the `#grid > child { padding:0; background:none; … }` CSS reset.
4. Data: ship the curated DLE list as a JSON file in the gresource (and/or fetch an updated `dailies.json` + `popularity.json` from GitHub raw at startup, cached under `GLib.get_user_cache_dir()`); keep per-user state (favorites `as`, last-opened `a{sx}`, window state) in two GSettings schemas `<APP_ID>` and `<APP_ID>.State` as Cartridges does. Use `Gio.Settings.create_action("sort-mode")` for stateful menu actions and `Gio.PropertyAction` for booleans.
5. Opening links: external = `Gtk.UriLauncher`/`Gio.AppInfo.launch_default_for_uri` (portal, no extra permissions); only add `--talk-name=org.freedesktop.Flatpak` if you truly ship "launch a specific host browser", and document why in the Flathub submission.
6. Undo-able toasts (`Adw.Toast` + `button-clicked`, history dict, `<primary>z`) for un-favoriting.

**Repository scaffolding (take from `main`)**
7. Copy the meson skeleton: `profile` option → `.Devel` App ID + resource prefix + `devel` CSS class; `configure_file` on every `.in`; `blueprint-compiler batch-compile --minify` custom target; `gnome.compile_resources(... gresource_bundle: true)` including the metainfo for `Adw.AboutDialog.new_from_appdata`; the three validation `test()`s; `gnome.post_install(...)`; `po/` with `LINGUAS`, `POTFILES.in`, `i18n.gettext(..., preset: 'glib')`. Use the `rewrite` variants (`python.install_sources`, `meson.options`, Meson ≥ 1.1, `install_mode: 'r-xr-xr-x'` for the launcher).
8. Dev manifest at `build-aux/flatpak/<AppId>.Devel.json` (or `flatpak/`) with `"sources": [{"type": "dir", "path": "../.."}]`, `"config-opts": ["-Dprofile=development"]`, `"run-tests": true`; keep the release manifest for Flathub separate and pinned by `tag` + `commit`. Minimal `finish-args` for Dailies: `--share=network`, `--share=ipc`, `--socket=fallback-x11`, `--socket=wayland`, `--device=dri` (WebKit needs it).
9. CI: `flatpak/flatpak-github-actions/flatpak-builder@v6` (latest v6.8, 2026-08-30 [V]) inside `ghcr.io/flathub-infra/flatpak-github-actions:gnome-48` (newest published image tag [V]; the GNOME 51 runtime will be downloaded) with `bundle: <AppId>.Devel.flatpak`; add a `pre-commit` job (ruff, ruff-format, pyright, `blueprint-compiler format`, `meson format`) that `main` lacks. Consider the `arch: [x86_64, aarch64]` matrix from the action README.
10. Releases: copy `publish-release.yml` — tag push → download CI artifacts for the same SHA → extract newest `<release>` notes from metainfo → `softprops/action-gh-release` — but attach the **`.flatpak` bundle** so Linux users have an install path (`flatpak install --user ./Dailies.flatpak`) until Flathub. Version/date live in exactly two places: `meson.build` and the metainfo `<release>`.
11. Metainfo: include `<branding>` colours, `<supports>`/`<requires display_length ge 360>`, `url` types `homepage|bugtracker|vcs-browser|contribute|translate`, `<developer id>`, `<content_rating type="oars-1.1"/>`, screenshots as raw GitHub URLs under `data/screenshots/`. Add a `.doap` only if you aim for GNOME Circle.
12. Icons: commit `data/icons/hicolor/scalable/apps/<AppId>.svg` (128 px canvas) and `…/symbolic/apps/<AppId>-symbolic.svg` (16 px, single black path), plus a `.Devel` variant; install via `install_data(f'@app_id@.svg', ...)` so the profile decides which icon ships. Unlike Cartridges, also commit the icon *source* (`data/icons/source/<AppId>.svg` with GNOME icon template layers) — reviewers and Hive ACMM maturity checks benefit from it.
13. Translations: wire Weblate (`url type="translate"`), `translator-credits` string, `__builtins__.pyi` for `_`.
14. Issue templates: Cartridges uses legacy Markdown templates with `labels: bug|enhancement`; Dailies' DLE-submission flow should use YAML issue forms (`.github/ISSUE_TEMPLATE/new-dle.yml`) with required fields name/URL/category/difficulty so a GitHub Action can parse them — Cartridges offers no precedent for this.

---

## 15. Open questions / not verified
- The hosted Weblate project page returned HTTP 403 to automated fetch; the Weblate badge/URL in README is taken as evidence it existed.
- The exact pixel/aspect requirements Flathub applies to screenshots were not checked.
- Whether `ghcr.io/flathub-infra/flatpak-github-actions:gnome-49/50/51` images exist beyond what the README/`docker.yml` list (they are not listed as of master); the `gnome-48` image provably builds newer runtimes by download.
- Codeberg (`codeberg.org/kramo/cartridges`) may have commits newer than the GitHub mirror; the mirror's last push is 2026-09-03 and the author's README notice suggests no further work.
- The `rewrite` branch is explicitly "not everything functional"; patterns were read, not run.

---

## Sources
- Clone: https://github.com/kra-mo/cartridges (commit d56323e6dd0ba9b500ee4f2b11d95f2e6240b05f, 2026-09-03; tag v2.13.1 at 2025-09-24; branch `origin/rewrite` at d82bdf1b, 2026-04-05)
- Canonical upstream per metainfo: https://git.kramo.page/cartridges ; Codeberg: https://codeberg.org/kramo/cartridges
- GitHub API: `repos/kra-mo/cartridges` (archived, stars), `releases` (v2.12.1 assets)
- Flathub manifest repo: https://github.com/flathub/page.kramo.Cartridges (`page.kramo.Cartridges.json`, `flathub.json`, commit history incl. "EOL" 2026-09-03)
- Flatpak GitHub Actions: https://github.com/flatpak/flatpak-github-actions (README; releases v6.5 2025-04-19, v6.6 2025-10-19, v6.7 2026-04-06, v6.8 2026-08-30)
- Container images: https://github.com/flathub-infra/flatpak-github-actions (README table, `Dockerfile`, `.github/workflows/docker.yml`)
- blueprint-compiler tags: https://gitlab.gnome.org/GNOME/blueprint-compiler/-/tags (v0.22.2, 2026-07-10)
- libadwaita `AdwSidebar` "since 1.9": https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Sidebar.html
- GTK `GtkTryExpression` "since 4.22": https://docs.gtk.org/gtk4/class.TryExpression.html
- GNOME 51 release (2026-09-16, SDK on Flathub): https://discourse.gnome.org/t/gnome-51-released/38820
- GNOME 50 release (March 2026): https://discourse.gnome.org/t/introducing-gnome-50/34400 , https://phoronix.com/news/GNOME-50-Released
- Flatpak available runtimes: https://docs.flatpak.org/en/latest/available-runtimes.html

---

# Appendices (reproduced files from the clone; copyright kramo, GPL-3.0-or-later)

## Appendix A — `data/gtk/window.blp` (main) — structure excerpt (library page + menus)
```blueprint
using Gtk 4.0;
using Adw 1;

Adw.StatusPage notice_no_results {
  icon-name: "system-search-symbolic";
  title: _("No Games Found");
  description: _("Try a different search");
  vexpand: true;
  valign: center;
}

Adw.StatusPage notice_empty {
  title: _("No Games");
  description: _("Use the + button to add games");
  vexpand: true;
  valign: center;

  Button {
    label: _("Import");
    halign: center;
    action-name: "app.import";
    styles [ "pill", "suggested-action" ]
  }
}

template $CartridgesWindow: Adw.ApplicationWindow {
  title: _("Cartridges");
  width-request: 360;
  height-request: 100;

  Adw.Breakpoint {
    condition ("max-width: 564px")
    setters {
      overlay_split_view.collapsed: true;
      details_view_box.orientation: vertical;
      /* …details page re-layout setters… */
    }
  }

  Adw.ToastOverlay toast_overlay {
    Adw.NavigationView navigation_view {
      Adw.NavigationPage library_page {
        title: _("All Games");

        Adw.OverlaySplitView overlay_split_view {
          sidebar-width-fraction: .2;

          [sidebar]
          Adw.NavigationPage sidebar_navigation_page {
            title: _("Cartridges");
            Adw.ToolbarView {
              [top]
              Adw.HeaderBar {
                [start]
                Button { icon-name: "sidebar-show-symbolic"; action-name: "win.show_sidebar"; tooltip-text: _("Toggle Sidebar"); }
              }
              ScrolledWindow {
                hscrollbar-policy: never;
                ListBox sidebar {
                  Box all_games_row_box { margin-top: 12; margin-bottom: 12; margin-start: 6; margin-end: 6; spacing: 12;
                    Image { icon-name: "view-grid-symbolic"; }
                    Label { halign: start; label: _("All Games"); wrap: true; wrap-mode: char; }
                    Label all_games_no_label { hexpand: true; halign: end; styles [ "dim-label" ] }
                  }
                  Box added_row_box { /* same shape, icon list-add-symbolic, label _("Added") */ }
                  ListBoxRow { selectable: false; activatable: false;
                    Label { label: _("Imported"); styles [ "heading" ] halign: start; }
                  }
                  styles [ "navigation-sidebar" ]
                }
              }
            }
          }

          Adw.ToolbarView library_view {
            [top]
            Adw.HeaderBar header_bar {
              [start] Button show_sidebar_button { icon-name: "sidebar-show-symbolic"; action-name: "win.show_sidebar";
                        tooltip-text: _("Toggle Sidebar"); visible: bind overlay_split_view.show-sidebar inverted; }
              [start] MenuButton { tooltip-text: _("Add Game"); icon-name: "list-add-symbolic"; menu-model: add_games; }
              [end]   MenuButton primary_menu_button { tooltip-text: _("Main Menu"); icon-name: "open-menu-symbolic"; menu-model: primary_menu; }
              [end]   ToggleButton search_button { tooltip-text: _("Search"); icon-name: "system-search-symbolic"; action-name: "win.toggle_search"; }
            }

            [top]
            SearchBar search_bar {
              search-mode-enabled: bind search_button.active bidirectional;
              key-capture-widget: navigation_view;
              Adw.Clamp { maximum-size: 500; tightening-threshold: 500;
                SearchEntry search_entry { placeholder-text: _("Search"); hexpand: true;
                  ShortcutController { Shortcut { trigger: "Escape"; action: "action(win.toggle_search)"; } }
                }
              }
            }

            Overlay library_overlay {
              ScrolledWindow scrolledwindow {
                FlowBox library {
                  homogeneous: true; halign: center; valign: start;
                  column-spacing: 12; row-spacing: 12;
                  margin-top: 15; margin-bottom: 15; margin-start: 15; margin-end: 15;
                  selection-mode: none;
                  styles [ "no-hover" ]
                }
              }
            }
          }
        }
      }
    }
  }
}

menu primary_menu {
  section {
    submenu {
      label: _("Sort");
      item { label: _("A-Z"); action: "win.sort_by"; target: "a-z"; }
      item { label: _("Z-A"); action: "win.sort_by"; target: "z-a"; }
      item { label: _("Newest"); action: "win.sort_by"; target: "newest"; }
      item { label: _("Oldest"); action: "win.sort_by"; target: "oldest"; }
      item { label: _("Last Played"); action: "win.sort_by"; target: "last_played"; }
    }
    item { label: _("Show Hidden"); action: "win.show_hidden"; hidden-when: "action-disabled"; }
  }
  section {
    item (_("Preferences"), "app.preferences")
    item (_("Keyboard Shortcuts"), "app.shortcuts")
    item (_("About Cartridges"), "app.about")
  }
}
```

## Appendix B — `data/gtk/game.blp` (main, full)
```blueprint
using Gtk 4.0;
using Adw 1;

template $Game: Box {
  orientation: vertical;
  halign: center;
  valign: start;

  Adw.Clamp {
    maximum-size: 200;
    unit: px;

    Overlay {
      [overlay]
      Revealer play_revealer {
        transition-type: crossfade;
        valign: start;
        halign: start;

        Button play_button {
          icon-name: "media-playback-start-symbolic";
          margin-start: 6; margin-end: 3; margin-top: 6; margin-bottom: 3;
          styles [ "circular", "osd" ]
        }
      }

      [overlay]
      Revealer menu_revealer {
        transition-type: crossfade;
        valign: start;
        halign: end;

        MenuButton menu_button {
          icon-name: "view-more-symbolic";
          margin-start: 3; margin-end: 6; margin-top: 6; margin-bottom: 3;
          styles [ "circular", "osd" ]
        }
      }

      Button cover_button {
        name: "cover_button";
        overflow: hidden;

        accessibility { labelled-by: title; }

        Box {
          orientation: vertical;

          Overlay {
            [overlay]
            Adw.Spinner spinner { visible: false; }

            Picture cover {
              width-request: 200;
              height-request: 300;
              hexpand: true;
              vexpand: true;
            }
          }

          Label title {
            label: _("Title");
            ellipsize: end;
            hexpand: true;
            halign: start;
            margin-top: 15; margin-bottom: 15; margin-start: 12; margin-end: 12;
          }
        }

        styles [ "card" ]
      }
    }
  }
}

menu game_options {
  section {
    item (_("Edit"), "app.edit_game")
    item (_("Hide"), "app.hide_game")
    item (_("Remove"), "app.remove_game")
  }
}

menu hidden_game_options {
  section {
    item (_("Edit"), "app.edit_game")
    item (_("Unhide"), "app.hide_game")
    item (_("Remove"), "app.remove_game")
  }
}
```

## Appendix C — `rewrite` UI files

### C.1 `cartridges/ui/window.blp` (full)
```blueprint
using Gtk 4.0;
using Adw 1;
using GObject 2.0;
using Gio 2.0;

$GameActions game_actions {}

$CollectionActions menu_collection_actions {
  collection: bind template.menu-collection;
}

GObject.SignalGroup collection_signals {
  target: bind template.collection;
  target-type: typeof<$Collection>;
}

GObject.SignalGroup model_signals {
  target: bind template.model;
  target-type: typeof<Gio.ListModel>;
}

template $Window: Adw.ApplicationWindow {
  realize => $_setup_gamepad_monitor();
  title: _("Cartridges");

  ShortcutController {
    Shortcut { trigger: bind $shortcut("<Control>f"); action: "action(win.search)"; }
    Shortcut { trigger: bind $shortcut("<Control>h", "<Meta><Shift>h"); action: "action(win.show-hidden)"; }
    Shortcut { trigger: bind $shortcut("<Control>z"); action: "action(win.undo)"; }
    Shortcut { trigger: "F9"; action: "action(win.show-sidebar)"; }
    Shortcut { trigger: bind $shortcut("<Control>w"); action: "action(window.close)"; }
    Shortcut { trigger: bind $shortcut("<Control>n"); action: "action(game.add)"; }
    Shortcut { trigger: bind $shortcut("<Control><Shift>n"); action: "action(collection.add)"; }
  }

  Adw.Breakpoint {
    condition ("max-width: 730px") // 3 columns + 48px of inherent padding
    setters { split_view.collapsed: true; }
  }

  content: Adw.NavigationView navigation_view {
    Adw.NavigationPage {
      title: bind template.title;
      tag: "games";
      styles [ "view" ]

      child: Adw.OverlaySplitView split_view {
        sidebar-width-unit: px;
        min-sidebar-width: 224; // Width of 1 column
        max-sidebar-width: bind split_view.min-sidebar-width;

        sidebar: Adw.NavigationPage {
          title: bind template.title;

          child: Adw.ToolbarView {
            [top]
            Adw.HeaderBar {
              show-title: bind $_show_sidebar_title(template.settings as <Settings>.gtk-decoration-layout);

              [start]
              Button {
                visible: bind split_view.show-sidebar;
                action-name: "win.show-sidebar";
                icon-name: "sidebar-show-symbolic";
                tooltip-text: _("Toggle Sidebar");
              }
            }

            content: Adw.Sidebar sidebar {
              activated => $_navigate();
              setup-menu => $_setup_sidebar_menu();
              notify::selected => $_update_selection();

              Adw.SidebarSection {
                Adw.SidebarItem { icon-name: "view-grid-symbolic"; title: _("All Games"); }
              }

              Adw.SidebarSection sources { title: _("Sources"); }

              Adw.SidebarSection collections {
                title: _("Collections");
                menu-model: menu {
                  item (_("Edit"), "collection.edit")
                  item (_("Remove"), "collection.remove")
                };
              }

              Adw.SidebarSection {
                Adw.SidebarItem new_collection_item { icon-name: "list-add-symbolic"; title: _("New Collection"); }
              }
            };
          };
        };

        content: Adw.NavigationPage navigation_page {
          title: bind sidebar.selected-item.title;

          child: Adw.ToolbarView {
            [top]
            Adw.HeaderBar header_bar {
              title-widget: Adw.Clamp clamp {
                tightening-threshold: bind clamp.maximum-size;

                child: CenterBox title_box {
                  hexpand: true;

                  center-widget: SearchEntry search_entry {
                    key-capture-widget: template;
                    hexpand: true;
                    placeholder-text: bind navigation_page.title;
                    search-started => $_search_started();
                    search-changed => $_search_changed();
                    activate => $_search_activate();
                    stop-search => $_stop_search();
                  };

                  end-widget: MenuButton sort_button {
                    icon-name: "filter-symbolic";
                    tooltip-text: _("Sort & Filter");
                    margin-start: 6;

                    menu-model: menu {
                      section {
                        label: _("Sort");
                        item { label: _("Last Played"); action: "win.sort-mode"; target: "last_played"; }
                        item { label: _("A-Z"); action: "win.sort-mode"; target: "a-z"; }
                        item { label: _("Z-A"); action: "win.sort-mode"; target: "z-a"; }
                        item { label: _("Newest"); action: "win.sort-mode"; target: "newest"; }
                        item { label: _("Oldest"); action: "win.sort-mode"; target: "oldest"; }
                      }
                      section { item (_("Show Hidden Games"), "win.show-hidden") }
                    };
                  };
                };
              };

              [start]
              Button {
                visible: bind split_view.show-sidebar inverted;
                action-name: "win.show-sidebar";
                icon-name: "sidebar-show-symbolic";
                tooltip-text: _("Toggle Sidebar");
              }

              [start]
              Button { icon-name: "list-add-symbolic"; tooltip-text: _("Add Game"); action-name: "game.add"; }

              [end]
              MenuButton main_menu_button {
                icon-name: "open-menu-symbolic";
                tooltip-text: _("Main Menu");
                primary: true;
                menu-model: menu {
                  item (_("Keyboard Shortcuts"), "app.shortcuts")
                  item (_("About Cartridges"), "app.about")
                };
              }
            }

            content: Adw.ToastOverlay toast_overlay {
              child: Adw.ViewStack view_stack {
                visible-child-name: bind $if(
                  grid.model as <NoSelection>.n-items,
                  "grid",
                  $if(template.search-text, "empty-search",
                    $if(template.collection, "empty-collection",
                      $if(template.show-hidden, "empty-hidden", "empty") as <string>
                    ) as <string>
                  ) as <string>
                );

                Adw.ViewStackPage {
                  name: "grid";
                  child: ScrolledWindow {
                    hscrollbar-policy: never;
                    child: GridView grid {
                      name: "grid";
                      max-columns: 12;
                      single-click-activate: true;
                      activate => $_show_details();

                      model: NoSelection {
                        model: FilterListModel {
                          watch-items: true;
                          filter: EveryFilter {
                            $CollectionFilter { collection: bind template.collection; }
                            AnyFilter {
                              StringFilter { expression: expr item as <$Game>.name; search: bind template.search-text; }
                              StringFilter { expression: expr item as <$Game>.developer; search: bind template.search-text; }
                            }
                            BoolFilter { expression: expr item as <$Game>.hidden; invert: bind template.show-hidden inverted; }
                          };
                          model: bind template.model;
                        };
                      };

                      factory: BuilderListItemFactory {
                        template ListItem {
                          child: $GameItem { game: bind template.item; position: bind template.position; };
                        }
                      };
                    };
                  };
                }

                Adw.ViewStackPage { name: "empty-search";
                  child: Adw.StatusPage { icon-name: "edit-find-symbolic"; title: _("No Games Found"); description: _("Try a different search"); }; }
                Adw.ViewStackPage { name: "empty-hidden";
                  child: Adw.StatusPage { icon-name: "view-conceal-symbolic"; title: _("No Hidden Games"); description: _("Games you hide will appear here"); }; }
                Adw.ViewStackPage { name: "empty-collection";
                  child: Adw.StatusPage { icon-name: bind template.collection as <$Collection>.icon-name;
                    title: bind $format(_("No Games in {}"), template.collection as <$Collection>.name); }; }
                Adw.ViewStackPage { name: "empty";
                  child: Adw.StatusPage { icon-name: bind template.application as <Application>.application-id;
                    title: _("No Games"); description: _("Use the + button to add games"); }; }
              };
            };
          };
        };
      };
    }

    $GameDetails details {}
  };
}
```

### C.2 `cartridges/ui/game-item.blp` (full)
```blueprint
using Gtk 4.0;

$GameActions game_actions { game: bind template.game; }
$CollectionActions collection_actions { game: bind template.game; }

template $GameItem: Box {
  name: "game-item";
  orientation: vertical;
  spacing: 12;

  EventControllerMotion motion { notify::contains-pointer => $_reveal_buttons(); }

  Overlay {
    halign: center;
    child: $Cover cover { paintable: bind template.game as <$Game>.cover; };

    [overlay]
    MenuButton options {
      icon-name: "view-more-symbolic";
      tooltip-text: _("Options");
      halign: end; valign: start;
      margin-top: 6; margin-end: 6;
      notify::active => $_reveal_buttons();
      notify::active => $_setup_collections();

      popover: PopoverMenu {
        menu-model: menu {
          section {
            item (_("Edit"), "game.edit")
            item { label: _("Hide"); action: "game.hide"; hidden-when: "action-disabled"; }
            item { label: _("Unhide"); action: "game.unhide"; hidden-when: "action-disabled"; }
            item (_("Remove"), "game.remove")
          }
          section {
            item (_("New Collection"), "collection.add")
            item { custom: "collections"; }
          }
        };

        [collections]
        Box {
          orientation: vertical;
          visible: bind collections_box.visible;
          Separator {}
          Label { label: _("Collections"); halign: start; margin-top: 6; margin-bottom: 9; margin-start: 12; margin-end: 12; styles [ "heading" ] }
          $CollectionsBox collections_box { game: bind template.game; }
        }
      };

      styles [ "circular" ]
    }

    [overlay]
    Button play {
      action-name: "game.play";
      label: _("Play");
      halign: center; valign: end;
      margin-bottom: 12;
      styles [ "pill" ]
    }
  }

  Label { label: bind template.game as <$Game>.name; ellipsize: middle; }
}
```

### C.3 `cartridges/ui/cover.blp` (full)
```blueprint
using Gtk 4.0;
using Adw 1;

template $Cover: Adw.Bin {
  layout-manager: $CoverLayoutManager {};

  child: Adw.ViewStack {
    name: "cover";
    visible-child-name: bind $if(template.paintable, "cover", "icon");
    overflow: hidden;
    enable-transitions: true;

    Adw.ViewStackPage { name: "cover";
      child: Picture { paintable: bind template.paintable; content-fit: bind $_content_fit(template.paintable); }; }

    Adw.ViewStackPage { name: "icon";
      child: Image { icon-name: bind $format("{}-symbolic", template.root as <Window>.application.application-id); pixel-size: 96; styles [ "dimmed" ] }; }

    styles [ "card" ]
  };
}
```

### C.4 `cartridges/ui/style.css` (rewrite, full)
```css
:root { --accent-bg-color: var(--accent-purple); }

#grid { padding: 6px 12px 12px; }

#grid > child { padding: 0; border-radius: 0; background: none; outline: none; box-shadow: none; }

/* https://gitlab.gnome.org/World/highscore/-/blob/cea3c7492d0b3c78a8b79ca60e9a86e8cdd4ceaf/src/library/library.css#L86 */
.controller-connected #grid > child:focus-within #cover,
#grid > child:focus-within:focus-visible #cover { outline: 5px solid rgb(from var(--accent-color) r g b / 50%); }

#game-item { padding: 12px; }

#game-item overlay > button,
#game-item overlay > menubutton > button {
  color: white;
  backdrop-filter: blur(9px) brightness(30%) saturate(600%);
  box-shadow: 0 0 0 1px rgb(from currentcolor r g b / 10%) inset, 0 1px rgb(from currentcolor r g b / 30%) inset;
  transition-property: outline-color, outline-width, outline-offset, background, box-shadow, opacity, transform;
}

#game-item overlay > button.hidden { opacity: 0; transform: translateY(3px); }
#game-item overlay > menubutton.hidden > button { opacity: 0; transform: translateY(-6px); }

#details {
  --accent-fg-color: var(--view-bg-color);
  --accent-bg-color: var(--view-fg-color);
  --accent-color: oklab(from var(--accent-bg-color) var(--standalone-color-oklab));
}
#details list { background: rgb(from white r g b / 20%); }
#background { filter: saturate(300%) opacity(50%); }

@media (prefers-color-scheme: dark) {
  #details list { background: rgb(from white r g b / 10%); }
  #background { filter: saturate(300%) brightness(50%); }
}

@media (prefers-contrast: more) {
  .controller-connected #grid > child:focus-within #cover,
  #grid > child:focus-within:focus-visible #cover { outline: 5px solid var(--accent-color); }
  #game-item overlay > button, #game-item overlay > menubutton > button { backdrop-filter: blur(9px) brightness(20%) saturate(600%); }
  #background { filter: saturate(300%) opacity(20%); }
  @media (prefers-color-scheme: dark) { #background { filter: saturate(300%) brightness(25%); } }
}
```

### C.5 `cartridges/ui/closures.py` (rewrite) — Blueprint closure helpers
```python
def add[T: type[Gtk.Widget]](*closures: Callable[..., object]) -> Callable[[T], T]:
    """Add `closures` to a widget."""
    def decorator(cls: T) -> T:
        for closure in closures:
            name = closure.__name__.rstrip("_")
            cb = Gtk.Template.Callback(name)(staticmethod(closure))
            setattr(cls, f"_closure_{name}", cb)
        return cls
    return decorator

def _closure[**P, R](func: Callable[P, R]) -> Callable[Concatenate[object, P], R]:
    @functools.wraps(func)
    def wrapper(_this, *args: P.args, **kwargs: P.kwargs) -> R:
        return func(*args, **kwargs)
    return wrapper

@_closure
def all_(*values: object) -> bool: return all(values)
@_closure
def bool_(value: object) -> bool: return bool(value)
@_closure
def format_(string: str, *args: object) -> str: return string.format(*args)
@_closure
def if_[T](condition: object, first: T, second: T) -> T: return first if condition else second
@_closure
def not_(value: object) -> bool: return not value
@_closure
def shortcut(default: str, macos: str | None = None) -> Gtk.ShortcutTrigger | None:
    return Gtk.ShortcutTrigger.parse_string(
        (macos or default.replace("<Control>", "<Meta>")) if sys.platform.startswith("darwin") else default
    )
```
Usage: `@Gtk.Template(resource_path=f"{PREFIX}/window.ui") @closures.add(closures.format_, closures.if_, closures.shortcut) class Window(Adw.ApplicationWindow): ...` then `$format(...)`, `$if(...)`, `$shortcut(...)` in Blueprint.

### C.6 Favorites-style filter and sidebar item (`cartridges/ui/collections.py`, excerpt)
```python
class CollectionFilter(Gtk.Filter):
    __gtype_name__ = __qualname__

    @GObject.Property(type=Collection)
    def collection(self) -> Collection | None:
        return self._collection

    @collection.setter
    def collection(self, collection: Collection | None):
        self._collection = collection
        self.changed(Gtk.FilterChange.DIFFERENT)

    def do_match(self, item: GObject.Object | None = None) -> bool:
        if not (self.collection and isinstance(item, Game)):
            return True
        return item.game_id in self.collection

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._collection_signals = GObject.SignalGroup(target_type=Collection)
        self._collection_signals.connect_closure("items-changed", lambda *_: self.changed(Gtk.FilterChange.DIFFERENT), after=False)
        self.bind_property("collection", self._collection_signals, "target")


class CollectionSidebarItem(Adw.SidebarItem):
    __gtype_name__ = __qualname__
    collection = GObject.Property(type=Collection)

    def __init__(self, collection: Collection | None = None, **kwargs):
        super().__init__(**kwargs)
        self.bind_property("title", self, "tooltip", GObject.BindingFlags.SYNC_CREATE, lambda _, name: GLib.markup_escape_text(name))
        flags = GObject.BindingFlags.DEFAULT
        self._collection_bindings = GObject.BindingGroup()
        self._collection_bindings.bind("name", self, "title", flags)
        self._collection_bindings.bind("icon-name", self, "icon-name", flags)
        self.bind_property("collection", self._collection_bindings, "source")
        self.collection = collection
```
Persistence (`cartridges/collections.py`): `SETTINGS.set_value("collections", GLib.Variant("aa{sv}", ({"name": GLib.Variant("s", c.name), "icon": GLib.Variant("s", c.icon), "game-ids": GLib.Variant("as", tuple(c)), "removed": GLib.Variant("b", c.removed)} for c in model)))`.

### C.7 Toast with undo (`cartridges/ui/window.py`, excerpt)
```python
def send_toast(self, title: str, *, undo: _UndoFunc | None = None):
    toast = Adw.Toast(title=title, use_markup=False)
    if undo:
        toast.props.button_label = _("Undo")
        toast.props.priority = Adw.ToastPriority.HIGH
        toast.connect("button-clicked", self._undo)
        self._history[toast] = undo
    self.toast_overlay.add_toast(toast)

def _undo(self, toast: Adw.Toast | None = None):
    if toast:
        self._history.pop(toast)()
        return
    try:
        toast, undo = self._history.popitem()
    except KeyError:
        return
    toast.dismiss()
    undo()
```

## Appendix D — `data/gtk/preferences.blp` (main) — representative excerpt
```blueprint
using Gtk 4.0;
using Adw 1;

template $CartridgesPreferences: Adw.PreferencesDialog {
  search-enabled: true;

  Adw.PreferencesPage general_page {
    name: "general";
    title: _("General");
    icon-name: "user-home-symbolic";

    Adw.PreferencesGroup behavior_group {
      title: _("Behavior");

      Adw.SwitchRow exit_after_launch_switch { title: _("Exit After Launching Games"); }

      Adw.SwitchRow cover_launches_game_switch {
        title: _("Cover Image Launches Game");
        subtitle: _("Swaps the behavior of the cover image and the play button");
      }
    }

    Adw.PreferencesGroup danger_zone_group {
      title: _("Danger Zone");
      separate-rows: true;

      Adw.ButtonRow remove_all_games_button_row {
        title: _("Remove All Games");
        styles [ "destructive-action" ]
      }
    }
  }

  Adw.PreferencesPage import_page {
    name: "import";
    title: _("Import");
    icon-name: "document-save-symbolic";

    Adw.PreferencesGroup sources_group {
      title: _("Sources");
      separate-rows: true;

      Adw.ExpanderRow steam_expander_row {
        title: _("Steam");
        show-enable-switch: true;

        [prefix]
        Image { icon-name: "steam-source-symbolic"; }

        Adw.ActionRow steam_data_action_row {
          title: _("Install Location");

          Button steam_data_file_chooser_button {
            icon-name: "folder-symbolic";
            valign: center;
            styles [ "flat" ]
          }

          styles [ "property" ]
        }
      }

      Adw.SwitchRow desktop_switch {
        title: _("Desktop Entries");
        [prefix]
        Image { icon-name: "user-desktop-symbolic"; }
      }
    }
  }

  Adw.PreferencesPage sgdb_page {
    name: "sgdb";
    title: _("SteamGridDB");
    icon-name: "image-x-generic-symbolic";

    Adw.PreferencesGroup sgdb_key_group {
      title: _("Authentication");
      Adw.EntryRow sgdb_key_entry_row { title: _("API Key"); }
    }

    Adw.PreferencesGroup {
      Adw.ActionRow {
        title: _("Update Covers");
        subtitle: _("Fetch covers for games already in your library");
        sensitive: bind sgdb_switch.active;

        Stack sgdb_stack {
          Button sgdb_fetch_button { label: _("Update"); valign: center; }
          Adw.Spinner sgdb_spinner { visible: false; valign: center; }
        }
      }
    }
  }
}
```
Binding helper in `preferences.py`:
```python
def bind_switches(self, settings: set[str]) -> None:
    for setting in settings:
        shared.schema.bind(setting, getattr(self, f'{setting.replace("-", "_")}_switch'), "active", Gio.SettingsBindFlags.DEFAULT)
```

## Appendix E — Metadata files (main)

### E.1 `data/page.kramo.Cartridges.gschema.xml.in` (State schema + representative keys)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<schemalist gettext-domain="cartridges">
  <schema id="@APP_ID@" path="@PREFIX@/">
    <key name="exit-after-launch" type="b"><default>false</default></key>
    <key name="cover-launches-game" type="b"><default>false</default></key>
    <key name="steam-location" type="s"><default>"~/.steam/steam"</default></key>
    <key name="sgdb-key" type="s"><default>""</default></key>
    <key name="library-rows" type="u"><default>0</default></key>
    <!-- … -->
  </schema>

  <schema id="@APP_ID@.State" path="@PREFIX@/State/">
    <key name="width" type="i"><default>1170</default></key>
    <key name="height" type="i"><default>795</default></key>
    <key name="is-maximized" type="b"><default>false</default></key>
    <key name="sort-mode" type="s">
      <choices>
        <choice value="a-z" /><choice value="z-a" /><choice value="newest" /><choice value="oldest" /><choice value="last_played" />
      </choices>
      <default>"last_played"</default>
    </key>
    <key name="show-sidebar" type="b"><default>false</default></key>
  </schema>
</schemalist>
```

### E.2 `data/page.kramo.Cartridges.metainfo.xml.in` (head, through first release)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>@APP_ID@</id>
  <replaces>
    <id>hu.kramo.Cartridges</id>
  </replaces>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <name>Cartridges</name>
  <summary>Launch all your games</summary>
  <description>
    <p>Cartridges is a simple game launcher for all of your games. It has support for importing games from Steam, Lutris, Heroic and more with no login necessary. You can sort and hide games or download cover art from SteamGridDB.</p>
  </description>
  <url type="homepage">https://apps.gnome.org/Cartridges/</url>
  <url type="bugtracker">https://git.kramo.page/cartridges/issues</url>
  <url type="translate">https://hosted.weblate.org/engage/cartridges/</url>
  <url type="contact">https://www.kramo.page/about/</url>
  <url type="vcs-browser">https://git.kramo.page/cartridges</url>
  <url type="contribute">https://git.kramo.page/cartridges/blob/main/CONTRIBUTING.md</url>
  <developer id="page.kramo">
    <name translate="no">kramo</name>
  </developer>
  <launchable type="desktop-id">@APP_ID@.desktop</launchable>
  <translation type="gettext">cartridges</translation>
  <branding>
    <color type="primary" scheme_preference="light">#d5b0e7</color>
    <color type="primary" scheme_preference="dark">#501a5c</color>
  </branding>
  <supports>
    <control>pointing</control>
    <control>keyboard</control>
    <control>touch</control>
  </supports>
  <requires>
    <display_length compare="ge">360</display_length>
  </requires>
  <screenshots>
    <screenshot type="default">
      <image>https://codeberg.org/kramo/cartridges/raw/branch/main/data/screenshots/1.png</image>
      <caption>Cartridges</caption>
    </screenshot>
    <screenshot>
      <image>https://codeberg.org/kramo/cartridges/raw/branch/main/data/screenshots/2.png</image>
      <caption>Game Details</caption>
    </screenshot>
    <screenshot>
      <image>https://codeberg.org/kramo/cartridges/raw/branch/main/data/screenshots/3.png</image>
      <caption>Edit Game Details</caption>
    </screenshot>
    <screenshot>
      <image>https://codeberg.org/kramo/cartridges/raw/branch/main/data/screenshots/4.png</image>
      <caption>Preferences</caption>
    </screenshot>
  </screenshots>
  <content_rating type="oars-1.1" />
  <releases>
    <release version="2.13.1" date="2025-09-24">
      <description translate="no">
        <p>Updated for GNOME 49, using the new keyboard shortcuts dialog.</p>
      </description>
    </release>
    <!-- … 20 older releases … -->
  </releases>
</component>
```

### E.3 `data/cartridges.gresource.xml.in`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<gresources>
  <gresource prefix="@PREFIX@">
    <file preprocess="xml-stripblanks">@APP_ID@.metainfo.xml</file>
    <file preprocess="xml-stripblanks">gtk/details-dialog.ui</file>
    <file preprocess="xml-stripblanks">gtk/game.ui</file>
    <file preprocess="xml-stripblanks">gtk/preferences.ui</file>
    <file preprocess="xml-stripblanks">gtk/window.ui</file>
    <file preprocess="xml-stripblanks" alias="shortcuts-dialog.ui">gtk/shortcuts-dialog.ui</file>
    <file alias="style.css">gtk/style.css</file>
    <file>library_placeholder.svg</file>
    <file>library_placeholder_small.svg</file>
  </gresource>
  <gresource prefix="@PREFIX@/icons/scalable/categories/">
    <file alias="steam-source-symbolic.svg">icons/sources/steam-source-symbolic.svg</file>
    <!-- … one per source … -->
  </gresource>
</gresources>
```

### E.4 `cartridges.doap`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
         xmlns:foaf="http://xmlns.com/foaf/0.1/"
         xmlns:gnome="http://api.gnome.org/doap-extensions#"
         xmlns="http://usefulinc.com/ns/doap#">
  <name>Cartridges</name>
  <shortdesc xml:lang="en">Launch all your games</shortdesc>
  <description xml:lang="en">Cartridges is a simple game launcher for all of your games. …</description>
  <homepage rdf:resource="https://git.kramo.page/cartridges" />
  <download-page rdf:resource="https://git.kramo.page/cartridges" />
  <bug-database rdf:resource="https://git.kramo.page/cartridges/issues" />
  <programming-language>Python</programming-language>
  <platform>GTK 4</platform>
  <platform>Libadwaita</platform>
  <maintainer>
    <foaf:Person>
      <foaf:name>kramo</foaf:name>
      <foaf:mbox rdf:resource="mailto:contact@kramo.page" />
      <foaf:account><foaf:OnlineAccount><foaf:accountServiceHomepage rdf:resource="https://github.com"/><foaf:accountName>kra-mo</foaf:accountName></foaf:OnlineAccount></foaf:account>
    </foaf:Person>
  </maintainer>
</Project>
```

## Appendix F — Code-style tooling (rewrite)

### F.1 `.pre-commit-config.yaml` (full)
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: check-added-large-files
      - id: trailing-whitespace
      - id: end-of-file-fixer
        exclude_types: [svg]
      - id: file-contents-sorter
        files: po/LINGUAS|po/POTFILES\.in

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.10
    hooks:
      - id: ruff-check
        args: [--select, I, --fix] # Only fix unsorted imports automatically
      - id: ruff-check
      - id: ruff-format

  - repo: local
    hooks:
      - id: pyright
        name: pyright
        language: node
        additional_dependencies: [pyright]
        types_or: [python, pyi]
        entry: pyright

      - id: blueprint-format # https://gitlab.gnome.org/GNOME/blueprint-compiler/-/merge_requests/258
        name: blueprint
        language: system
        files: \.blp$
        entry: blueprint-compiler format --fix --no-diff

      - id: meson-format
        name: meson
        language: python
        files: meson\.build|meson\.options
        entry: meson format --inplace

      - id: prettier
        name: prettier
        language: node
        additional_dependencies: [prettier]
        types_or: [css, json, yaml]
        entry: prettier --write

      - id: svgo
        name: svgo
        language: node
        additional_dependencies: [svgo]
        types: [svg]
        entry: svgo
```

### F.2 `pyproject.toml` (full)
```toml
[project]
requires-python = ">= 3.13"

[dependency-groups]
dev = [
  "blueprint-compiler @ git+https://gitlab.gnome.org/GNOME/blueprint-compiler.git",
  "pillow",
  "pre-commit",
  "pygobject-stubs @ git+https://github.com/jamiethecat/pygobject-stubs.git",
  "ruff",
]

[tool.pyright]
exclude = ["**/__pycache__", "**/.*", "_build/**"]
typeCheckingMode = "strict"

reportMatchNotExhaustive = "none"
reportMissingModuleSource = "none"
reportMissingParameterType = "none"
reportMissingTypeStubs = "none"
reportRedeclaration = "none"
reportUnknownArgumentType = "none"
reportUnknownLambdaType = "none"
reportUnknownMemberType = "none"
reportUnknownParameterType = "none"
reportUnknownVariableType = "none"
reportUntypedBaseClass = "none"
reportUntypedFunctionDecorator = "none"
reportUnusedImport = "none"
reportUnusedVariable = "none"

[tool.ruff]
builtins = ["_"]
format.preview = true

[tool.ruff.lint]
select = ["ALL"]
ignore = [
  "C901", "COM812", "COM819", "D100", "D104", "D105", "D107", "D203", "D206", "D213", "D300",
  "E111", "E114", "E117", "E402", "ERA001", "FA102", "FBT", "FIX", "FLY002", "PLC0415",
  "PLR0904", "PLR0911", "PLR0912", "PLR0913", "PLR0914", "PLR0915", "PLR0916", "PLR0917",
  "Q000", "Q001", "Q002", "Q003", "S310", "TC006", "TD", "TRY301", "W191",
]

[tool.ruff.lint.flake8-annotations]
allow-star-arg-any = true
suppress-dummy-args = true
suppress-none-returning = true

[tool.ruff.lint.pydocstyle]
property-decorators = ["gi.repository.GObject.Property"]
```

### F.3 `main` branch `.pylintrc`
```ini
[MAIN]
ignore=importers

[MESSAGES CONTROL]
disable=raw-checker-failed, bad-inline-option, locally-disabled, file-ignored, suppressed-message,
        useless-suppression, deprecated-pragma, use-symbolic-message-instead, too-few-public-methods,
        missing-function-docstring, missing-class-docstring, missing-module-docstring,
        relative-beyond-top-level, import-error, no-name-in-module

[TYPECHECK]
ignored-classes=Child

[VARIABLES]
additional-builtins=_
```

## Appendix G — Flatpak manifests

### G.1 `build-aux/flatpak/page.kramo.Cartridges.Devel.json` (main) — trimmed to structure (pip module list shortened)
```json
{
  "id": "page.kramo.Cartridges.Devel",
  "runtime": "org.gnome.Platform",
  "runtime-version": "49",
  "sdk": "org.gnome.Sdk",
  "command": "cartridges",
  "finish-args": [
    "--share=network",
    "--share=ipc",
    "--socket=fallback-x11",
    "--device=dri",
    "--socket=wayland",
    "--talk-name=org.freedesktop.Flatpak",
    "--filesystem=host",
    "--filesystem=~/.var/app/com.valvesoftware.Steam/data/Steam/:ro",
    "--filesystem=/var/lib/flatpak/app:ro",
    "--filesystem=xdg-data/flatpak/app:ro"
  ],
  "cleanup": ["/include", "/lib/pkgconfig", "/man", "/share/doc", "/share/gtk-doc", "/share/man", "/share/pkgconfig", "*.la", "*.a"],
  "modules": [
    {
      "name": "python3-modules",
      "buildsystem": "simple",
      "build-commands": [],
      "modules": [
        {
          "name": "python3-requests",
          "buildsystem": "simple",
          "build-commands": [
            "pip3 install --verbose --exists-action=i --no-index --find-links=\"file://${PWD}\" --prefix=${FLATPAK_DEST} \"requests\" --no-build-isolation"
          ],
          "sources": [
            { "type": "file", "url": "https://files.pythonhosted.org/packages/1e/db/4254e3eabe8020b458f1a747140d32277ec7a271daf1d235b70dc0b4e6e3/requests-2.32.5-py3-none-any.whl", "sha256": "2462f94637a34fd532264295e186976db0f5d453d1cdd31473c85a6a161affb6" },
            { "type": "file", "url": "https://files.pythonhosted.org/packages/a7/c2/fe1e52489ae3122415c51f387e221dd0773709bad6c6cdaa599e8a2c5185/urllib3-2.5.0-py3-none-any.whl", "sha256": "e6b01673c0fa6a13e374b50871808eb3bf7046c4b125b216f6bf1cc604cff0dc" },
            { "type": "file", "url": "https://files.pythonhosted.org/packages/76/c6/c88e154df9c4e1a2a66ccf0005a88dfb2650c1dffb6f5ce603dfbd452ce3/idna-3.10-py3-none-any.whl", "sha256": "946d195a0d259cbba61165e88e65941f16e9b36ea6ddb97f00452bae8b1287d3" },
            { "type": "file", "url": "https://files.pythonhosted.org/packages/e5/48/1549795ba7742c948d2ad169c1c8cdbae65bc450d6cd753d124b17c8cd32/certifi-2025.8.3-py3-none-any.whl", "sha256": "f6c12493cfb1b06ba2ff328595af9350c65d6644968e5d3a2ffd78699af217a5" },
            { "type": "file", "url": "https://files.pythonhosted.org/packages/83/2d/5fd176ceb9b2fc619e63405525573493ca23441330fcdaee6bef9460e924/charset_normalizer-3.4.3.tar.gz", "sha256": "6fce4b8500244f6fcb71465d4a4930d132ba9ab8e71a7859e6a5d59851068d14" }
          ]
        }
      ]
    },
    {
      "name": "cartridges",
      "builddir": true,
      "buildsystem": "meson",
      "run-tests": true,
      "config-opts": ["-Dprofile=development"],
      "sources": [{ "type": "dir", "path": "../.." }]
    }
  ]
}
```

### G.2 Flathub `page.kramo.Cartridges.json` — app module
```json
{
  "name": "cartridges",
  "builddir": true,
  "buildsystem": "meson",
  "sources": [
    { "type": "git", "url": "https://git.kramo.page/cartridges", "tag": "v2.13.1", "commit": "4c49baddbc49053b1b9c64b49aa032dffb2d79b9" }
  ]
}
```
`flathub.json`: `{ "end-of-life": "This application is no longer maintained." }`

## Appendix H — GitHub workflows (main, full)

### H.1 `.github/workflows/ci.yml`
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: release-${{ github.sha }}
jobs:
  flatpak:
    name: Flatpak
    runs-on: ubuntu-latest
    container:
      image: bilelmoussaoui/flatpak-github-actions:gnome-47
      options: --privileged
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Flatpak Builder
        uses: flatpak/flatpak-github-actions/flatpak-builder@v6.5
        with:
          bundle: page.kramo.Cartridges.Devel.flatpak
          manifest-path: build-aux/flatpak/page.kramo.Cartridges.Devel.json

  windows:
    name: Windows
    runs-on: windows-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup MSYS2
        uses: msys2/setup-msys2@v2
        with:
          msystem: UCRT64
          update: true
          install: mingw-w64-ucrt-x86_64-gtk4 mingw-w64-ucrt-x86_64-libadwaita mingw-w64-ucrt-x86_64-python-gobject mingw-w64-ucrt-x86_64-python-yaml mingw-w64-ucrt-x86_64-python-requests mingw-w64-ucrt-x86_64-python-pillow mingw-w64-ucrt-x86_64-desktop-file-utils mingw-w64-ucrt-x86_64-ca-certificates mingw-w64-ucrt-x86_64-meson git

      - name: Compile
        shell: msys2 {0}
        run: |
          meson setup _build
          ninja -C _build install
          pacman --noconfirm -Rs mingw-w64-ucrt-x86_64-desktop-file-utils mingw-w64-ucrt-x86_64-meson git

      - name: Test
        shell: msys2 {0}
        run: |
          set +e
          timeout 2 cartridges; [ "$?" -eq "124" ]

      - name: Inno Setup
        run: iscc ".\_build\build-aux\windows\Cartridges.iss"

      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          name: Windows Installer
          path: _build/build-aux/windows/Output/Cartridges Windows.exe

  macos:
    name: macOS
    runs-on: macos-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Homebrew
        id: set-up-homebrew
        uses: Homebrew/actions/setup-homebrew@master

      - name: Install Dependencies
        run: |
          brew install meson pygobject3 libadwaita adwaita-icon-theme desktop-file-utils pyinstaller pillow
          pip3 install --break-system-packages requests PyYAML

      - name: Meson Build
        run: |
          meson setup _build -Dtiff_compression=jpeg
          ninja install -C _build

      - name: PyInstaller
        env:
          PYTHONPATH: /opt/homebrew/opt/homebrew/lib/python3.12/site-packages
        run: |
          cd build-aux/macos
          pyinstaller ./cartridges.spec

      - name: Zip
        run: |
          cd build-aux/macos/dist
          zip -yr Cartridges\ macOS.zip Cartridges.app

      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          path: build-aux/macos/dist/Cartridges macOS.zip
          name: macOS Application
```

### H.2 `.github/workflows/publish-release.yml`
```yaml
name: Publish Release
on:
  push:
    tags: "*"

concurrency:
  group: release-${{ github.sha }}

jobs:
  publish-release:
    name: Publish Release
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download workflow artifact
        uses: dawidd6/action-download-artifact@v9
        with:
          workflow: ci.yml
          commit: ${{ github.sha }}

      - name: Get release notes
        shell: python
        run: |
          import re, textwrap
          open_file = open("./data/page.kramo.Cartridges.metainfo.xml.in", "r", encoding="utf-8")
          string = open_file.read()
          open_file.close()
          string = re.findall("<release.*>\s*<description.*>\n([\s\S]*?)\s*</description>\s*<\/release>", string)[0]
          string = textwrap.dedent(string)
          open_file = open("release_notes", "w", encoding="utf-8")
          open_file.write(string)
          open_file.close()

      - name: Get tag name
        id: get_tag_name
        run: echo tag_name=${GITHUB_REF#refs/tags/} >> $GITHUB_OUTPUT

      - name: Publish release
        uses: softprops/action-gh-release@v2.2.2
        with:
          files: |
            Windows Installer/Cartridges Windows.exe
            macOS Application/Cartridges macOS.zip
          fail_on_unmatched_files: true
          tag_name: ${{ steps.get_tag_name.outputs.tag_name }}
          body_path: release_notes
```

### H.3 Current upstream-recommended Flatpak CI snippet (from `flatpak/flatpak-github-actions` README, 2026) [V]
```yaml
on:
  push:
    branches: [main]
  pull_request:
name: CI
jobs:
  flatpak:
    name: "Flatpak"
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/flathub-infra/flatpak-github-actions:gnome-48
      options: --privileged
    steps:
    - uses: actions/checkout@v4
    - uses: flatpak/flatpak-github-actions/flatpak-builder@v6
      with:
        bundle: palette.flatpak
        manifest-path: org.gnome.zbrown.Palette.yml
```
Useful inputs: `run-tests`, `cache`, `arch`, `upload-artifact`, `artifact-name`, `build-bundle`, `repository-url`. A `flat-manager@v6` action exists for publishing to a self-hosted flat-manager repo (an alternative to Flathub for an own remote).

## Appendix I — Launcher script template (main, `cartridges/cartridges.in`)
```python
#!@PYTHON@
import gettext, locale, os, signal, sys
from pathlib import Path
from platform import system

VERSION = "@VERSION@"
if os.name == "nt":
    PKGDATADIR = os.path.join(os.path.dirname(__file__), "..", "share", "cartridges")
else:
    PKGDATADIR = "@pkgdatadir@"
    LOCALEDIR = "@localedir@"

sys.path.insert(1, PKGDATADIR)
signal.signal(signal.SIGINT, signal.SIG_DFL)

if system() == "Linux":
    locale.bindtextdomain("cartridges", LOCALEDIR)
    locale.textdomain("cartridges")
    gettext.install("cartridges", LOCALEDIR, names=['ngettext'])
else:
    gettext.install("cartridges", names=['ngettext'])

if __name__ == "__main__":
    from gi.repository import Gio, GLib
    try:   # For a macOS application bundle
        resource = Gio.Resource.load(str(Path(__file__).parent / "Resources" / "cartridges.gresource"))
    except GLib.GError:
        resource = Gio.Resource.load(os.path.join(PKGDATADIR, "cartridges.gresource"))
    resource._register()
    from cartridges import main
    sys.exit(main.main(VERSION))
```
