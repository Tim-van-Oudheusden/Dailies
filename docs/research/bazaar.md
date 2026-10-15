# Research report: Bazaar (GNOME app store) — patterns reusable for Dailies

Research key: `bazaar` · Date: 2026-10-15 · Author: research subagent

Clone studied: `<scratch>/clones/bazaar` (GitHub mirror `bazaar-org/bazaar`, HEAD `3d347d5` 2026-08-18, tag `v0.9.4` + 14 commits; `version.sh` says 0.9.5). The GitHub repo is a **frozen mirror**: its README states the canonical repo moved to <https://gitlab.gnome.org/World/bazaar> on 2026-08-18. I cross-checked the live GitLab `main` (latest commit 2026-10-13 "Merge branch 'bump-version-to-0.9.9'", latest release **v0.9.8** 2026-10-13, `version.sh` VERSION=0.9.9). Where GitHub and GitLab differ I say so. Everything labelled **[verified]** was read from a file in the clone or fetched from a URL; **[inferred]** is my reading of the code.

---

## 1. Identity, status, licensing

| Item | Value | Source |
|---|---|---|
| App ID | `io.github.kolunmi.Bazaar` | `meson.build`, `data/*.metainfo.xml.in` [verified] |
| Summary / description | "Discover and install apps" — "A fast and modern app store for Linux with a focus on discovering and installing Flatpak apps and add-ons, particularly from Flathub." | metainfo [verified] |
| License | GPL-3.0-or-later (code), CC0-1.0 (metainfo) | `COPYING`, metainfo [verified] |
| Maintainers | Kolunmi (Adam Masciola), Alexander Vanhee | `bazaar.doap`, `.github/CODEOWNERS` [verified] |
| Canonical repo (2026-10) | <https://gitlab.gnome.org/World/bazaar> (GNOME World namespace; GNOME Circle badge in README) | GitLab README summary [verified] |
| Distribution | Flathub (`flathub/io.github.kolunmi.Bazaar`), GNOME nightly remote, distro packages (Fedora/Bazzite RPM, Debian, Arch) | README summary, Justfile `build-rpm`, bug template [verified] |
| Latest release | v0.9.8 (2026-10-13) on GitLab; v0.9.4 (2026-08-15) on frozen GitHub | GitLab API, `gh release list` [verified] |
| Code size | ~74k lines of C in `src/`, ~650 files, 32 translations (`po/LINGUAS`) | `wc`, `po/LINGUAS` [verified] |

Icon credit (README on GitLab): the market-stall app icon was designed by Tobias Bernard, Jakub Steiner and Sam Hewitt (GNOME design team). [verified via README summary]

---

## 2. Language & toolchain

**Language: C (GNU C11)**, GObject-based, no Rust/Python/Vala. [verified: `meson.build` `project('bazaar', 'c', ... 'c_std=gnu11')`]

**UI definition: Blueprint** (`.blp`) compiled to `.ui` with `blueprint-compiler >= 0.20.0` in `batch-compile` mode, then embedded with `gnome.compile_resources`. [verified: `src/meson.build`]

**Build system: Meson ≥ 1.0.0 + Ninja.** `meson_options.txt` options [verified]:

```
bge_only                       (bool, false)  restrict build to the libbge widget library
hardcoded_main_config_path     (string, '')   absolute path to main YAML config read at runtime
hardcoded_blocklist_path       (string, '')   absolute path to txt blocklist
hardcoded_content_config_path  (string, '')   absolute path to a YAML curated config
im_a_translator                (bool, false)  only set up po/ (no C build)
sandboxed_libflatpak           (bool, false)  treat libflatpak as sandboxed
development                    (bool, false)  dev build: uses .Devel icon, installs docs/example.yaml
```

**Versioning**: `version.sh` is the single source of truth (`VERSION=0.9.5`, `CACHE_VERSION=2`); meson calls `run_command('version.sh', 'get-vcs')` to produce `0.9.5 (vcs=v0.9.4-14-g3d347d5)`. `CACHE_VERSION` is written to `$XDG_CACHE_HOME/<appid>/cache-version` and the on-disk cache is wiped when it changes (`src/bz-application.c:1057-1114`). [verified]

**Dependencies (pkg-config name, min version, purpose)** — `CONTRIBUTING.md` table [verified]:

| pkg-config | min | purpose |
|---|---|---|
| `gtk4` | 4.22.1 | GUI |
| `libadwaita-1` | 1.8 | GNOME styling |
| `libdex-1` | 1.2.beta (GitLab main: 1.2.0) | async/futures/fibers |
| `flatpak` | 1.9 | install management |
| `appstream` | 1.0 | metadata |
| `xmlb` | 0.3.4 | binary XML (also used to parse the YAML *schema* XML) |
| `glycin-2`, `glycin-gtk4-2` | 2.0 | sandboxed image decoding → GdkTexture |
| `yaml-0.1` (libyaml) | 0.2.5 | YAML configs |
| `libsoup-3.0` | 3.6.0 | HTTP |
| `json-glib-1.0` | 1.10.0 | JSON replies |
| `md4c` | 0.5.1 | Markdown parsing (articles) |
| `gtksourceview-5` | 5.17 | code blocks in Markdown |
| `webkitgtk-6.0` | 2.50.2 | web views (only used for the Flathub OAuth login page) |
| `libsecret-1` | 0.20 | token storage |
| `libproxy-1.0` | 0.5 | proxy resolution |
| `malcontent-0` | 0.12.0 | parental controls |
| `libsystemd` | 245 | daemon helpers |

Of these, the subset relevant to Dailies is **gtk4, libadwaita, libdex, libsoup3, json-glib, glycin(+gtk4), libyaml, webkitgtk-6.0** (if an in-app browser is wanted).

**Code generation trick**: plain data-holder GObjects are not hand-written. `src/gen_gobject.sh` reads a tiny keyfile spec (`src/bz-curated-section.txt` etc., 50+ of them) and emits `.h/.c` at build time via a meson `generator()`. Example spec (verbatim, `src/bz-curated-section.txt`):

```
prefix=bz
name=curated_section
parent-prefix=g
parent-name=object
author=AUTOGEN

include=<gtk/gtk.h>

include="bz-entry-group.h"
include="bz-curated-appids-info.h"
include="bz-curated-markdown-info.h"

property=title char G_TYPE_STRING string
property=subtitle BzCuratedMarkdownInfo BZ_TYPE_CURATED_MARKDOWN_INFO object
property=appids BzCuratedAppidsInfo BZ_TYPE_CURATED_APPIDS_INFO object
property=list_type char G_TYPE_STRING string
property=enable_bulk_install gboolean G_TYPE_BOOLEAN boolean
property=overflow_count int G_TYPE_INT int
```

**Code style**: GNU C via `.clang-format` (`BasedOnStyle: GNU`, aligned declarations/assignments, `ColumnLimit: 0`); `CODESTYLE.md` mandates `g_autoptr`/`g_clear_*`, libdex over GTask, declare-then-init, fixed file section order. [verified]

**Dev tooling**: `Justfile` (`just run`, `just build-flatpak`, `just build-flatpak-bundle`, `just build-rpm`), `.devcontainer/` (Fedora rawhide Dockerfile with all `-devel` deps + `blueprint-compiler` + `clangd`), `.foundry/` (GNOME Foundry: `foundry run`), `scripts/install-deps/fedora-rawhide.sh`. [verified]

---

## 3. Project layout (GitHub mirror, v0.9.4+)

```
bazaar/
├── meson.build, meson_options.txt, version.sh, Justfile
├── README.md, CONTRIBUTING.md, CODESTYLE.md, COPYING (GPL-3)
├── bazaar.doap                  # GNOME DOAP project file (needed for gitlab.gnome.org/World)
├── funding.json, .well-known/   # FLOSS/fund + domain verification
├── .clang-format, .gitignore, .gitmodules (flatpak-builder-tools submodule)
├── .github/
│   ├── CODEOWNERS, FUNDING.yml
│   ├── ISSUE_TEMPLATE/bug_form.yml
│   └── workflows/build-flatpak.yml, flatpak-external-data-checker.yml
├── .devcontainer/{devcontainer.json,Dockerfile}
├── .foundry/.gitignore
├── build-aux/flatpak/
│   ├── io.github.kolunmi.Bazaar.json          # nightly/dev manifest
│   ├── fuse-*.patch, fusermount-wrapper.sh    # flatpak-in-flatpak hacks (not needed by Dailies)
│   └── flatpak-builder-tools/ (submodule)
├── data/
│   ├── io.github.kolunmi.Bazaar.desktop.in
│   ├── io.github.kolunmi.Bazaar.metainfo.xml.in     # 58 <release> entries, screenshots, branding
│   ├── io.github.kolunmi.Bazaar.gschema.xml
│   ├── io.github.kolunmi.Bazaar.service.in (systemd user), .search-provider.ini.in, dbus/
│   ├── icons/hicolor/scalable/apps/{AppID}.svg, {AppID}.Devel.svg
│   ├── icons/hicolor/symbolic/apps/{AppID}-symbolic.svg
│   ├── icons/{AppID}.Source.svg               # Inkscape master w/ GNOME icon template layer
│   └── meson.build
├── docs/overview.md (28 KB distributor docs), docs/example.yaml, docs/debugging.md
├── po/ (LINGUAS, POTFILES, meson.build: i18n.gettext('bazaar', preset: 'glib'))
├── screenshots/*.png
├── scripts/countries.py, install-deps/
├── bge/                          # "Bazaar GTK Extensions": libbge (carousel, markdown render, animations, wdgt DSL)
└── src/
    ├── main.c, bazaar-daemon.c, dl-worker.c, refresh-worker.c, update-worker.c
    ├── bz-*.c/.h/.blp            # one widget or model per file (bz-app-tile.{c,h,blp} etc.)
    ├── bz-*.txt                  # gen_gobject.sh specs
    ├── *-schema.xml              # YAML→GObject schemas (curated-config-schema.xml, ...)
    ├── internal-config.yaml      # built-in search biases
    ├── style.css, bazaar.gresource.xml, icons/scalable/actions/*.svg (91 symbolic icons)
    └── meson.build
```

Naming convention: `bz-<thing>.c`, `bz-<thing>.h`, `bz-<thing>.blp` for every widget; GType `BzThing`; CSS classes and `css-name` lower-kebab. [verified]

---

## 4. UI architecture

### 4.1 Window shell (`src/bz-window.blp`) [verified]

- `Adw.ApplicationWindow` 1220×900 default, `width-request: 360`, `height-request: 294`.
- `Adw.ToolbarView` → `Adw.BreakpointBin` → `Adw.ToastOverlay` → `Adw.NavigationView` (root page "main") → `Adw.ToolbarView` with `top-bar-style: flat`.
- Top-level **`Adw.ViewStack main_view_stack`** with pages `browse` ("Curated", `star-outline-rounded-symbolic`, only visible when curated config exists), `flathub` ("Explore", `explore-symbolic`), `installed` ("Library", `library-symbolic`, with `badge-number`), `search` ("Search", `system-search-symbolic`).
- Header bar `[title]` = `Adw.ViewSwitcher { policy: wide }`; `[bottom]` = `Adw.ViewSwitcherBar`; an `Adw.Breakpoint condition("max-width: 700px")` sets `top_header_bar.title-widget: null` and `toolbar_view.reveal-bottom-bars: true` (mobile layout). Breakpoint callbacks add a `narrow` CSS class to the window (used in `style.css` as `window.narrow ...`).
- Main `Stack main_stack` has a `"loading"` page (64 px `Adw.Spinner` + "Refreshing" `title-3` label) shown while the backend syncs; header shows a 16 px spinner in `[start]` while `busy`.
- Primary menu (`open-menu-symbolic`): Donate / Refresh / Login / Manage user data / Preferences / Keyboard Shortcuts / About / Quit — all `app.*` actions.
- Escape/Back/BackSpace/`<ctrl>g` → `action(escape)`.
- `Adw.Banner`s under the header for "new version", "offline, showing cached Flathub", "metered connection".

**No sidebar.** Navigation is purely view-switcher tabs plus `Adw.NavigationView` push for detail pages (`bz_window_push_page`).

### 4.2 Explore page (`src/bz-flathub-page.blp`, 25 KB) [verified]

Structure inside a `ScrolledWindow` → `Adw.ClampScrollable { maximum-size: 1500; tightening-threshold: 1400 }` → `Box content_box { margin 30/30/5/50, spacing 15 }`:

1. **Hero carousel** `$BzFeaturedCarousel` bound to `flathub.apps_of_the_week` (styles `card`, `featured-carousel`).
2. Optional Flathub curated "slot" sections (`after-hero`, `after-top-apps`, `after-first-category-block`) — gradient cards.
3. **Toggle group** `Adw.ToggleGroup section_toggles { styles ["round","huge"]; homogeneous }` with `Adw.Toggle`s *Trending / Popular / New / Updated*, each `enabled` bound to whether that category exists. An `Adw.ViewStack sections_stack { visible-child-name: bind section_toggles.active-name bidirectional }` swaps the 4 `$BzFlathubCategorySection`s (`min-items: 12; has-title: false`). **This is exactly the "Popular / Trending" weekly-changing section Dailies wants.**
4. Category sections (`office`, `graphics`, `audiovideo`, `education`, …) each a title-1 label + flow box of `BzAppTile` + pill "More …" button.
5. Big promo cards ("On the Go", "We ♥ Games") with 256 px symbolic hero icons, gradients (`.otg`, `.wlg`) and inner toggle groups.
6. "App of the Day" `title-1` + single-item carousel.

Three breakpoints: `max-width: 1250sp` (2 columns in promo lists, slice 6), `max-width: 970sp` (promo card goes vertical), `max-width: 700px` (margins 10, sections `compact: true`, toggles non-homogeneous).

State pages in the enclosing `Adw.ViewStack stack`: `"empty"` (`Adw.StatusPage` "Flathub Not Added"), `"offline"` (`Adw.StatusPage icon-name: "connected-squares-x"` "Can't Reach Flathub" + pill buttons "Search Apps"/"Reconnect"), `"content"`. `enable-transitions: true; transition-duration: 400`.

### 4.3 Tiles [verified]

**`BzAppTile`** (`src/bz-app-tile.blp`) — a `Button` with styles `card`, `app-tile`; child `Overlay > Box { margins 12, spacing 15 }` = 64 px `Image` (`icon-dropshadow`) + vertical box: title row (`Label heading ellipsize:end` + 14 px `verified-checkmark-symbolic`), description `Label { wrap, ellipsize end, lines 1–2 }`, and a small "Installed" pill (`small-pill installed-pill`, 12 px `app-installed-symbolic`). This is the standard grid tile seen in `screenshots/flathub.png`: 4 columns at 1220 px, white cards, big icon left, bold name + 1-line description.

**`BzRichAppTile`** (`src/bz-rich-app-tile.blp`) — used when a curated section sets `list-type: rich`: a 200 px tall `rich-screenshot-box` showing the first screenshot (`BzRoundedPicture radius: 6`) over a themed background (`BzThemedEntryGroupRect`, derived from the app's branding colour), then the icon/title/description row and an inline action `Stack` (Get / Open / Uninstall / Cancel) with `medium-pill` / `circular` buttons.

**`BzCategoryTile`** (`src/bz-category-tile.blp`) — `Button` styles `card`, `category-tile`; vertical box margins 16/24, 48 px icon (`icon-dropshadow`) + wrapped label. Per-category gradients in CSS (`.category-tile.category-trending { background: linear-gradient(135deg, #99c1f1, #3584e4) }`, `.category-popular { linear-gradient(135deg, #f7ef74, #ffbf6f); color: rgba(0,0,0,.8) }`, "All background gradients are at 135deg for consistency"). Comment in CSS: "Category buttons styling modified from GNOME Software". See `screenshots/categories.png`: a 4-column grid of colourful gradient tiles with a centred 48 px full-colour icon and bold label.

**`BzFeaturedTile`** (hero): 128 px icon + `title-1` + caption centered left, screenshot (`top-half: true`, rounded) on the right, "installed" check overlay top-right; `narrow` hides the screenshot.

**`BzFavoritesTile`** (list row): 48 px `BzTransactIcon`, title/description (`dim-label caption`), circular flat buttons (support ♥, install/remove, `bookmark-filled-symbolic` unfavorite with crossfade to spinner), trailing `go-next-symbolic` 14 px dimmed. Lives in a `ListView { styles ["navigation-sidebar", ...] }` inside `Adw.ClampScrollable { maximum-size: 650 }`.

**`BzArticleTile`**: `width-request: 275`, 16:9 `BzAspectPicture` + title/subtitle; article page = `Adw.NavigationPage` with `Adw.Clamp max 800` and `$BgeMarkdownRender`.

### 4.4 Generic grid/list host: `BzDynamicListView` [verified]

`src/bz-dynamic-list-view.{c,h}` is an `AdwBin` that takes a `GListModel` plus `child-type` (a GType name string like `"BzAppTile"`), `child-prop` (which property on the child to set from the item, e.g. `"group"`), optional `object-prop`, `scroll` (bool), `noscroll-kind` (`hbox|vbox|list-box|flow-box|carousel`), `max-children-per-line` (default 4), `row-spacing`, `column-spacing`. For `flow-box` it creates `gtk_flow_box_new()`, `set_homogeneous(TRUE)`, `set_selection_mode(GTK_SELECTION_NONE)` and `gtk_flow_box_bind_model()`. Sections use `SliceListModel { offset: 0; size: N }` for "show the first 12" with a pill "Show More"/"More X" button pushing an `Adw.NavigationPage` (`bz_apps_page_new(title, groups)`) with the full list.

Breakpoints change `max-children-per-line` and slice `size` (`game_list.max-children-per-line: 2; game_slice.size: 6` at ≤700 px).

### 4.5 Detail page (`src/bz-full-view.blp`) [verified]

`Adw.ToolbarView` + `Adw.HeaderBar` whose `[title]` is a `Revealer` that slides the app name in once scrolled (`reveal-child: bind $is_scrolled_down(main_scroll.vadjustment.value)`). Content: `Adw.ViewStack` (`empty`/`loading`/`content`) → nested `Adw.BreakpointBin`s (700 px and 525 px) → `ScrolledWindow` → `Adw.Clamp { maximum-size: 910; tightening-threshold: 576 }`. Header: 128 px icon (`icon-dropshadow`, 96 px when narrow), `title-1 app-title` label, developer badge, `Adw.WrapLayout` of `small-pill suggested-action` buttons (Support ♥ with custom pink accent `.support`, **`BzFavoriteButton`** with `bookmark-outline-symbolic` + count revealer + spinner stack), install controls (wide vs narrow variants). Then "context tiles" row (download size, license, safety, form factor, age rating, downloads/month — each a `circular-lozenge` with colour classes `green/yellow/orange/red/grey`), screenshot carousel, description. See `screenshots/fullview.png`.

### 4.6 Search (`src/bz-search-bar.blp`, `src/bz-search-page.blp`) [verified]

Custom `BzSearchBar: Widget` (accessible-role `search_box`, `BoxLayout`) = `system-search-symbolic` image + `Text` + 16 px `Adw.Spinner` while busy + end-widget bin (filters `MenuButton sliders-horizontal-symbolic`) + clear button; CSS `.search-box` pill: `border-radius: 9999px; background-color: var(--card-bg-color)` and an animated accent `outline` on `:focus-within`. Search page = `Adw.Clamp max 375` bar, quick-filter pills row (`Browser`, `Video`, …), "Browse Categories" grid of `BzCategoryTile`, results in a `GridView` with `min/max-columns` set by breakpoints (3 → 2 → 1).

### 4.7 Favorites [verified]

Favorites in Bazaar are **Flathub-account favorites** (requires login; `BzFavoriteButton.visible: bind entry.is-flathub`). Page `src/bz-favorites-page.blp` is an `Adw.NavigationPage` with `Adw.ViewStack` states `loading` (64 px spinner) / `empty` (`Adw.StatusPage icon-name: "starred-symbolic"; title: "No Favorites"; description: "Applications you mark as favorite will appear here"`) / `content` (ListView). Icons used: `bookmark-outline-symbolic` (not favorited), `bookmark-filled-symbolic` (favorited). For Dailies, the visual pattern is reusable but storage must be local (GSettings or a JSON file in `g_get_user_data_dir()`), since "no account creation" is a requirement.

### 4.8 Preferences [verified]

`Adw.PreferencesDialog { content-height: 500; search-enabled: true }` with `Adw.PreferencesPage` → `Adw.PreferencesGroup`s of `Adw.ActionRow` + `CheckButton` radio pairs and `Adw.SwitchRow`s, all backed by GSettings keys. An `Adw.Breakpoint condition("max-width: 625sp")`. A FlowBox of `accent-button` circular colour swatches picks the progress-bar theme.

---

## 5. Curated content: the YAML "curated config" [verified]

### 5.1 Where it comes from

- Compile-time `-Dhardcoded_content_config_path=/run/host/etc/bazaar/config.yaml` (Flathub build) plus any `curated-config-paths:` listed in the main config (`/run/host/etc/bazaar/bazaar.yaml`). Distributors (Bluefin, Aurora, Bazzite) ship these under `/etc/bazaar/` and grant `--filesystem=host-etc` via an override. The tab is hidden when no config exists (`visible: bind ... curated-provider.has-inputs`).
- `development=true` builds copy `docs/example.yaml` into `g_get_user_data_dir()/example.yaml` and load it.
- **Live reload**: `BzContentProvider` (`src/bz-content-provider.c`) takes a `GListModel` of `GFile`s, attaches a `GFileMonitor` to each (`g_file_monitor_file`) and re-parses on change; parse = `dex_file_load_contents_bytes` → `bz_parser_process_bytes`. Multiple files concatenate in order (docs/overview.md "Curated Section").

### 5.2 Format (full `docs/example.yaml` reproduced in Appendix A)

Top level: `rows:` — a vertical list rendered top-to-bottom. Each row is exactly one of:

| Row key | GObject (gen spec) | Fields |
|---|---|---|
| `section` | `BzCuratedSection` | `title` (str), `subtitle: {string: <markdown>}`, `appids: {list: [appid…]}`, `list-type: rich` (else default tile), `enable-bulk-install` (bool → "Install All" pill), `overflow-count` (int → "Show More" pill when list is longer; slice max 20) |
| `featured-carousel` | `BzCuratedFeaturedCarousel` | `appids: {list: […]}`, `disable-auto-rotate` |
| `banner` | `BzCuratedBanner` | `height` (int, default 250), `image: {uri | light-uri + dark-uri, alt, fit: contain|fill|cover|scale-down, can-shrink, halign}`, `light-color`, `dark-color` (any GTK CSS background value, incl. `linear-gradient(...)` or `url(...)`) |
| `articles` | `BzCuratedArticlesInfo` | `aspect-ratio` (float), `uri` (remote YAML feed, fetched with `bz_fetch_uri_contents`; falls back to) `list: [{title, subtitle, image, uri(.md)}]` |

### 5.3 Parsing mechanism (the clever part)

`BzYamlParser` (`src/bz-yaml-parser.c`, 1240 lines) is **generic**: it is constructed from a tiny XML *schema* resource and maps YAML mappings onto GObject properties by name, using `g_object_class_find_property` and `typehint`s for list element types. The curated schema is 6 lines (`src/curated-config-schema.xml`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<object class="BzRootCuratedConfig">
  <typehint name="rows" type="BzCuratedRow"/>
  <typehint name="rows.section.appids.list" type="GtkStringObject"/>
  <typehint name="rows.featured-carousel.appids.list" type="GtkStringObject"/>
  <typehint name="rows.articles.list" type="BzCuratedArticle"/>
</object>
```

`BzCuratedRow` has one object property per row kind (`section`, `featured_carousel`, `banner`, `articles`); `BzRowView::set_row` checks which one is non-NULL and instantiates `bz_section_view_new` / `bz_featured_carousel_view_new` / `bz_banner_view_new` / `bz_article_list_view_new`. The curated view itself is just a `BzDynamicListView { child-type: "BzDynamicListView"; object-prop: "rows"; child-prop: "model" }` inside `Adw.Clamp { maximum-size: 1500 }` with 30 px margins (10 px at ≤700 px).

App IDs are resolved to UI objects lazily through `BzApplicationMapFactory` (a `GtkMapListModel` wrapper + filter) so a YAML list of strings becomes a list of `BzEntryGroup`s that tiles bind to (`$convert_to_groups(...)` in `bz-section-view.blp`).

Also in the same mechanism: blocklists (`src/blocklist-schema.xml`, with `priority`, `conditions: [match-locale, match-envvar]`, `block/allow(-regex)`), main config (`src/main-config-schema.xml`), built-in `src/internal-config.yaml` with **search biases** (regex → `convert-to`, `boost-appids`, `linear-boost {slope, y-intercept}`), and `article-list-schema.xml` (`<list><object class="BzCuratedArticle"/></list>`) for the remote article feed.

---

## 6. Remote data: fetching and caching [verified unless noted]

### 6.1 HTTP layer (`src/global-net.{c,h}`)

- One global `SoupSession` (libsoup 3) with `GProxyResolver` from libproxy; `bz_send_with_global_http_session(SoupMessage*) → DexFuture*`.
- Helpers: `bz_https_query_json(uri)` (sets `User-Agent: Bazaar`, memory output stream, parses with json-glib, returns `JsonNode` boxed in a future), `bz_query_flathub_v2_json(request)` (`https://flathub.org/api/v2%s`), `bz_query_bazaar_json(request)` (`https://usebazaar.org%s` — the project's own domain hosts JSON/YAML, e.g. `https://usebazaar.org/curated/articles.yaml`), `bz_fetch_uri_contents(uri)`.
- Everything is **libdex**: fibers (`dex_scheduler_spawn`), `dex_await`, `dex_future_then/finally`, `dex_future_disown`. UI code never sees callbacks; `DexFuture`s are stored on objects (`self->initializing`) and property notifications flip `Adw.ViewStack` pages.

### 6.2 Flathub daily state (`src/bz-flathub-state.c`)

`bz_flathub_state_update_to_today()` computes `for_day = g_date_time_format(now_utc, "%F")` and spawns `initialize_fiber` on the IO scheduler, which issues (in parallel, awaited in sequence) requests such as:

```
/quality-moderation/passing-apps?page=1&page_size=N
/app-picks/app-of-the-day/<YYYY-MM-DD>
/app-picks/apps-of-the-week/<YYYY-MM-DD>
/app-picks/curated-app-selections/<YYYY-MM-DD>
/collection/category
/collection/recently-updated?page=0&per_page=N
/collection/recently-added?page=0&per_page=N
/collection/popular?page=0&per_page=N
/collection/trending?page=0&per_page=N
/collection/mobile?page=0&per_page=N
/collection/category/<cat>?page=0&per_page=N      (audiovideo, development, education, game, graphics, network, office, science, system, utility)
```

Each result becomes a `BzFlathubCategory { name, display-name, short-name, icon-name, applications (GListModel) }` appended to a `GListStore categories`; the UI looks categories up by name (`$get_category_by_name_cb(categories, "popular")`). "Trending" and "Popular" are therefore **just named collections computed server-side and re-fetched per day**; the client has no ranking logic. The whole `BzFlathubState` is **serializable to GVariant** (`for-day` key included, `bz-flathub-state.c:248`) so it is persisted to the on-disk cache and shown when offline (the window banner "You have a network connection but are viewing a cached version of Flathub").

### 6.3 Entry/metadata cache

`BzEntryCacheManager` writes serialized entries to `$XDG_CACHE_HOME/io.github.kolunmi.Bazaar/<module>/<sha-of-id>`; helpers `bz_dup_root_cache_dir()`, `bz_dup_cache_dir(submodule)`, `bz_dup_module_dir()` in `src/io.c`. A `cache-version` file stores `(PACKAGE_VERSION, CACHE_VERSION)`; mismatch → wipe. Daily refresh is scheduled by `refresh-worker.c` with GSettings keys `last-refresh-time`, `last-update-check`, `update-check-hour-offset` (randomised hour to avoid thundering herd), paused on metered connections (`GNetworkMonitor`).

### 6.4 Images (`src/bz-async-texture.c`, 1198 lines; `src/dl-worker.c`)

- `BzAsyncTexture` implements `GdkPaintable` and is created with `(GFile *source, GFile *cache_into)`; `_new_lazy` variants defer loading until first `snapshot`, so off-screen tiles cost nothing (`bz_async_texture_ensure`).
- Cache key: `g_compute_checksum_for_string(G_CHECKSUM_MD5, uri)` → file in the module cache dir, plus a sidecar `<path>.bz-async-texture-data` with the fetch timestamp; `CACHE_INVALID_AGE = G_TIME_SPAN_DAY * 1` → re-download after 24 h, corrupt files are deleted ("reaped") and refetched.
- Downloads are delegated to **separate `bazaar-dl-worker` subprocesses** (default 8, env `BAZAAR_N_DOWNLOAD_WORKERS`) that read `(ss)` GVariant lines `(src_uri, dest_path)` from stdin and stream with libsoup into the file; the main process then decodes with **glycin** (`gly_loader_new(file)` → `GdkTexture` via glycin-gtk4), which is sandboxed decoding. An in-memory `GHashTable texture_cache` dedups textures per URI with refcounting.
- Widgets bind `paintable:` to the `BzAsyncTexture` and use `try { … , fallback }` Blueprint expressions; `Image icon-name: "image-missing-symbolic"` placeholders are shown while `screenshot.visible` is false (`bz-rich-app-tile.blp`).
- App icons for the GNOME Shell search provider are downscaled to `<icon_size>` PNGs with cairo and cached (`bz_load_mini_icon_sync`).

### 6.5 Opening links

Bazaar opens external links with `g_app_info_launch_default_for_uri()` (most places) or `GtkUriLauncher` (`bz-appstream-description-render.c`, `bz-bundle-install-dialog.c`); inside the Flatpak sandbox both go through the portal. It embeds a `WebKitWebView` **only** for the Flathub OAuth login page (`src/bz-login-page.c`), i.e. WebKitGTK 6.0 (`webkitgtk-6.0 >= 2.50.2`) is already in the GNOME 50/51 SDK and works fine inside a Flatpak with `--share=network`. [verified: grep of `src/`]

---

## 7. Flatpak manifest & permissions [verified]

**Nightly/CI manifest** `build-aux/flatpak/io.github.kolunmi.Bazaar.json` (JSON; GitLab `main` now uses `org.gnome.Platform` **51**, GitHub mirror 50):

```json
{
  "id": "io.github.kolunmi.Bazaar",
  "runtime": "org.gnome.Platform", "runtime-version": "51",
  "sdk": "org.gnome.Sdk",
  "command": "bazaar-daemon",
  "sdk-extensions": ["org.freedesktop.Sdk.Extension.llvm20"],
  "tags": ["nightly"],
  "desktop-file-name-suffix": " (Nightly)",
  "finish-args": [
    "--share=network", "--share=ipc", "--socket=fallback-x11", "--socket=wayland", "--device=dri",
    "--filesystem=/var/lib/flatpak", "--filesystem=xdg-data/flatpak",
    "--talk-name=org.freedesktop.Flatpak", "--system-talk-name=org.freedesktop.Flatpak.SystemHelper",
    "--filesystem=/var/tmp", "--filesystem=~/.var/app",
    "--system-talk-name=org.freedesktop.Accounts", "--talk-name=org.freedesktop.impl.portal.PermissionStore"
  ],
  "cleanup": ["/share/zsh","/share/gettext","/include","/lib/pkgconfig","/lib/cmake",
              "/share/applications/mimeinfo.cache","/share/bash-completion","/share/zsh/site-functions",
              "/share/icons/hicolor/icon-theme.cache","/share/man","/share/pkgconfig","*.la","*.a"],
  "modules": [
    { "name": "bazaar", "buildsystem": "meson",
      "config-opts": ["-Ddevelopment=true","-Dsandboxed_libflatpak=true",
                      "-Dhardcoded_main_config_path=/run/host/etc/bazaar/bazaar.yaml",
                      "-Dhardcoded_content_config_path=/run/host/etc/bazaar/config.yaml",
                      "-Dhardcoded_blocklist_path=/run/host/etc/bazaar/blocklist.txt"],
      "sources": [{ "type": "dir", "path": "../.." }],
      "modules": [ libdex (git tag 1.2.beta), md4c (cmake, x-checker-data git tag-pattern), malcontent, flatpak(+polkit, ostree, libfuse, xdg-dbus-proxy, python3-pyparsing, python3-babel) ] },
    { "name": "bubblewrap", ... }
  ]
}
```

The `flatpak`/`ostree`/`polkit`/`libfuse` modules exist only because Bazaar bundles libflatpak; **Dailies needs none of them**. The minimal permission set for a network-reading GTK app is `--share=network --share=ipc --socket=fallback-x11 --socket=wayland --device=dri`.

**Flathub production manifest** (`flathub/io.github.kolunmi.Bazaar`, `io.github.kolunmi.Bazaar.yaml`, YAML not JSON) [verified via raw.githubusercontent.com]: same finish-args (with explanatory comments per line), `sources: {type: git, url: https://gitlab.gnome.org/World/bazaar.git, commit: <sha>}`, extra modules `libxmlb`, `libyaml`, `check`, `libfyaml`, `appstream`, each with `x-checker-data` (anitya `project-id` + `tag-template`, or git `tag-pattern`). Repo-level `flathub.json`: `{"require-important-update": true}`.

Both manifests carry `x-checker-data` so `flatpak-external-data-checker` can open update PRs.

---

## 8. CI/CD [verified]

### 8.1 GitHub Actions (frozen mirror, still a good template)

`.github/workflows/build-flatpak.yml` (reproduced in Appendix B): on push to `main`, PRs (ignoring `**.md`, `docs/*`, `screenshots/*`, issue templates) and `workflow_dispatch`; `permissions: {}`; matrix `x86_64` on `ubuntu-latest` and `aarch64` on `ubuntu-24.04-arm`; container `ghcr.io/flathub-infra/flatpak-github-actions:gnome-50` with `--privileged`; steps: `actions/checkout@<sha> # v7.0.0` (submodules recursive, `persist-credentials: false`), `actions/cache/restore` on `.flatpak-builder`, `flatpak/flatpak-github-actions/flatpak-builder@<sha> # v6.7` with `bundle: Bazaar.flatpak`, `manifest-path`, `cache: true`, `restore-cache: false`, `arch`, `verbose: true`, then `actions/cache/save`. All actions are **SHA-pinned with a version comment** (supply-chain hygiene worth copying). The job uploads `Bazaar.flatpak` as a workflow artifact (that action does so by default).

`.github/workflows/flatpak-external-data-checker.yml`: daily cron `0 0 * * *` + manual; `docker://ghcr.io/flathub/flatpak-external-data-checker:latest` with `args: --update --never-fork --require-important-update build-aux/flatpak/io.github.kolunmi.Bazaar.json`, committing as `github-actions[bot]` (`41898282+github-actions[bot]@users.noreply.github.com`).

Other GitHub plumbing: `CODEOWNERS` (workflows + flatpak dir owned by packagers), `FUNDING.yml` (`github: [kolunmi]`, `ko_fi`, `custom`), `ISSUE_TEMPLATE/bug_form.yml` (YAML issue form with required OS / version (`flatpak info <appid>`) / remotes / hardware fields).

### 8.2 GitLab CI (current canonical)

`.gitlab-ci.yml` on GitLab `main` (33 lines, reproduced in Appendix C): includes GNOME `citemplates` `flatpak/flatpak_ci_initiative.yml` and the `basic-release-with-dist@master` component (`dist-job-name: "flatpak@x86_64"`); `.flatpak_vars` sets `image: quay.io/gnome_infrastructure/gnome-runtime-images:gnome-51`, `FLATPAK_MODULE: bazaar`, `MANIFEST_PATH`, `APP_ID`, `RUNTIME_REPO: https://dl.flathub.org/repo/flathub.flatpakrepo`; jobs `flatpak@x86_64`, `flatpak@aarch64`, `nightly@x86_64`, `nightly@aarch64` (`.publish_nightly` → GNOME Nightly remote). The citemplates release component runs only `if: $CI_COMMIT_TAG`, takes the dist tarball artifact from the flatpak job and creates a GitLab Release with the tag message as notes (verified by reading `templates/basic-release-with-dist.yml`).

### 8.3 Release process (as practiced)

1. Bump `VERSION=` in `version.sh` (commit "bump version to X").
2. Add a `<release version="X" date="YYYY-MM-DD">` with `<url type="details">` and `<description translate="no">` to `data/*.metainfo.xml.in` (58 entries, newest first; `src/meson.build` extracts `//releases/release[1]` with `xmllint` into `release-notes.xml`, bundled as a GResource and shown in-app in the "See What's New" donations dialog).
3. Tag `vX` → GitHub Release (notes = same bullets + "What's Changed" PR list, **no binary assets attached**; `assets: []` for v0.9.4) / GitLab Release (dist tarball).
4. Open a PR on `flathub/io.github.kolunmi.Bazaar` bumping the git `commit:` (the external-data-checker bot does this automatically for `x-checker-data`-annotated sources; `require-important-update` limits noise).
5. Users get the build from Flathub; testers from GNOME Nightly. **Bazaar does not distribute `.flatpak` bundles on its release page** — the CI artifact and `just build-flatpak-bundle` (`flatpak build-export repo … && flatpak build-bundle repo <appid>.flatpak <appid>`) exist for local/testing use.

---

## 9. Metainfo, desktop file, GSettings [verified]

`data/io.github.kolunmi.Bazaar.metainfo.xml.in` highlights (full header in Appendix D): `<component type="desktop-application">`, `metadata_license CC0-1.0`, `project_license GPL-3.0-or-later`, `<supports><control>pointing|keyboard|touch`, `<requires><display_length compare="ge">360`, `<developer id="io.github.kolunmi"><name>The Bazaar Contributors`, URL types `homepage, vcs-browser, bugtracker, translate, faq, help, donation, contact, contribute`, `<translation type="gettext">bazaar`, `<launchable type="desktop-id">`, `<content_rating type="oars-1.1"/>`, **`<branding><color type="primary" scheme_preference="light">#ffbe6f</color><color … "dark">#c11c2b</color></branding>`** (powers Flathub/Software coloured headers), 5 `<screenshot>`s hosted as GitHub user-attachment URLs with captions, `<releases>`.

`data/meson.build` runs `desktop-file-validate`, `appstreamcli validate --no-net --explain` and `glib-compile-schemas --strict --dry-run` as meson **tests**, and installs the `.Devel.svg` icon renamed to the normal name when `development=true`.

Desktop file: `Categories=GTK;Utility;`, `Keywords=…`, `StartupNotify=true`, `X-Purism-FormFactor=Workstation;Mobile;`, `Actions=new-window`.

GSettings schema `io.github.kolunmi.Bazaar` path `/io/github/kolunmi/Bazaar/`: booleans for filters, `window-dimensions (ii)` default `(1220, 900)`, `force-adwaita-icons`, `auto-update`, timestamps as `x` (int64), enum-like string key with `<choices>`.

---

## 10. Icon design [verified]

- `data/icons/hicolor/scalable/apps/io.github.kolunmi.Bazaar.svg`: 128×128 canvas, no padding issues (content spans y≈12–117), flat GNOME-palette colours with subtle linear/radial gradients: red/white striped awning (`#f66151` + `#f6f5f4`), red bobbles (`#ed333b`, `#e01b24`), wooden stall in browns (`#b5835a`, `#986a44`, `#865e3c`, `#63452c`), produce = blue/green gradient box (`#1a5fb4`→`#8ff0a4`), purple ball (`#f0d7ff`→`#dc8add`→`#1a5fb4`), yellow highlight (`#f8e45c`). ≈4 KB optimised SVG, no text.
- `io.github.kolunmi.Bazaar.Devel.svg`: same art for the development build (installed under the normal name when `-Ddevelopment=true`), following the GNOME convention of a visually distinct nightly icon.
- `io.github.kolunmi.Bazaar-symbolic.svg`: 16×16 `viewBox 0 0 16 16`, pure black paths with `fill-opacity 0.5` mask for secondary detail — the HIG symbolic variant.
- `data/icons/io.github.kolunmi.Bazaar.Source.svg` (248 KB Inkscape file with layers "App Icon" and "template") — the GNOME app-icon template workflow (design in the 128 px grid with the template overlay, export only the "App Icon" layer).
- Extra artwork: 17 full-colour **category icons** `src/icons/io.github.kolumni.Bazaar.{Trending,Popular,New,Updated,Play,Create,…}.svg` (rocket, hot-air balloon, star, check, gamepad…) rendered at 48 px inside the gradient category tiles, and 91 symbolic action icons in `src/icons/scalable/actions/` (`bookmark-outline-symbolic`, `bookmark-filled-symbolic`, `explore-symbolic`, `library-symbolic`, `star-outline-rounded-symbolic`, `verified-checkmark-symbolic`, `app-installed-symbolic`, `connected-squares-x`, …) bundled through `bazaar.gresource.xml` and registered via `gtk_icon_theme_add_resource_path` [inferred for the registration call; the gresource listing is verified].
- GSettings `force-adwaita-icons` (default true) forces the Adwaita icon theme so custom symbolic icons always match.

---

## 11. Documented design decisions (from repo docs)

- `docs/overview.md` is written **for distributors**, not users: explains compile-time config, env vars, main config, blocklists (with YAML examples), curated sections, article Markdown subset ("rendered with GTK widgets (so its not a webview)"), and the `hooks` system (shell snippets run on `view-app`, `before-transaction`, …). The philosophy: *ship a generic client; content and policy come from YAML the vendor controls, hot-reloaded.*
- Curated sections: "Sections of 12 apps look nice at all window widths" (`docs/example.yaml` comment); `list-type: rich` "use when a section has little apps".
- CSS comments: all category gradients at 135°; category styling "modified from GNOME Software"; high-contrast (`@media (prefers-contrast: more)`) and light/dark (`@media (prefers-color-scheme: …)`) variants for every custom colour; use of libadwaita CSS variables (`var(--card-bg-color)`, `var(--accent-bg-color)`, `var(--window-fg-color)`, `color-mix(...)`).
- `CODESTYLE.md`: libdex-only async; GNU style; strict file layout.
- Accessibility: tiles declare `accessibility { described-by: description; labelled-by: title_label }`; search bar `accessible-role: search_box`; carousel buttons have `accessibility { label: _("Previous") }`.
- i18n: every user string `_("…")` in Blueprint; `// Translators:` comments; `translate="no"` on release notes; GNOME Damned Lies handles translations.

---

## 12. Recommendations for Dailies

### 12.1 Stack (adopt)
1. **GTK4 + libadwaita ≥ 1.8, Blueprint ≥ 0.20, Meson, GNOME Platform 51 runtime** — the exact combination Bazaar ships. Language choice is open (Bazaar's C is heavy for a small launcher; Python/PyGObject, Rust, or Vala work with the same Blueprint/Meson/Flatpak skeleton), but keep the *file layout and naming* (`src/<prefix>-<widget>.{blp,<lang>}`, `data/<AppID>.{desktop.in,metainfo.xml.in,gschema.xml}`, `data/icons/hicolor/{scalable,symbolic}/apps/`, `build-aux/flatpak/<AppID>.json`, `po/`, `docs/`).
2. Use **libsoup 3 + json-glib (+ libyaml if the catalogue is YAML)** for fetching, **glycin** for decoding remote favicons/thumbnails, and **GLib's async or libdex** for concurrency. For Python, `Gio.File.load_contents_async` / `Soup.Session.send_and_read_async` cover it.
3. **WebKitGTK 6.0** is in the GNOME SDK and Bazaar already embeds `WebKitWebView` in a Flatpak with only `--share=network`; the "built-in browser" tier of Dailies' open-link preference is therefore viable with no extra permissions. External tier: `Gtk.UriLauncher` (portal-aware). "Configured browser" tier: launch via `Gio.AppInfo` chosen from `Gio.AppInfo.get_all_for_type("x-scheme-handler/https")` — Bazaar does not do this, so it is an addition, not a copy.

### 12.2 Remote-config-driven sections (copy the model, simplify the schema)
- Mirror Bazaar's **two-layer split**: a *catalogue* (list of DLE entries: name, url, category, difficulty, icon) and a *curated/ranking layer* (which IDs go in "Popular" and "Trending" this week). In Bazaar the first is Flathub appstream and the second is Flathub's per-day collections + vendor YAML `rows:`; in Dailies both can be static files in the GitHub repo served from `raw.githubusercontent.com` or GitHub Pages, regenerated weekly by the GitHub Action + agent.
- Suggested `curated.yaml` shaped like Bazaar's: `rows: [{section: {title: "Popular", ids: {list: […]}, overflow-count: 12}}, {section: {title: "Trending", ids: {…}}}, …]`, plus `generated-at` and `week` keys. Keep "Favorites" as a **client-side** section always rendered first (Bazaar's Curated tab is config-driven; Dailies' Favorites must come from local storage — GSettings `as` array of IDs or a JSON file under `g_get_user_data_dir()`).
- Keep Bazaar's **`for_day` / date-stamped request** idea: request `…/popularity/<ISO-week>.json` (or `latest.json`) and persist the parsed result + date so the app opens instantly offline with a "viewing cached data" banner.

### 12.3 Async loading, placeholders, offline
- Per page: `Adw.ViewStack` with `loading` (64 px `Adw.Spinner` + title-3 label), `empty` / `offline` (`Adw.StatusPage` with pill action button), `content`; `enable-transitions: true; transition-duration: 400`. Bind `visible-child-name` to a state property.
- Per tile image: a lazy `GdkPaintable` wrapper keyed by URL hash in `$XDG_CACHE_HOME/<AppID>/`, 24 h TTL sidecar, `image-missing-symbolic` placeholder until loaded; dedupe in-memory per URL.
- Daily/weekly refresh with a randomised hour offset, skip on metered networks (`Gio.NetworkMonitor`), store `last-refresh-time` in GSettings (Bazaar keys: `last-refresh-time x`, `update-check-hour-offset i`).

### 12.4 Tile grid and category navigation
- **Grid tile** = Bazaar `BzAppTile`: `Button.card` with 64 px icon + heading + 1–2-line dimmed description + optional small pill (for Dailies: category/difficulty pill such as `small-pill` with `Easy/Medium/Hard`, plus a favourite toggle `bookmark-outline/filled-symbolic`). `GtkFlowBox` (homogeneous, selection none, `max-children-per-line` 4 → 2 → 1 via `Adw.Breakpoint` at 1250sp / 700px) inside `Adw.Clamp { maximum-size: 1500; tightening-threshold: 1400 }` with 30 px side margins (10 px narrow).
- **Weekly categories switcher** = Bazaar's `Adw.ToggleGroup { styles ["round","huge"] }` + `Adw.ViewStack` bound bidirectionally to `active-name` ("Favorites | Popular | Trending | All"), or a category tile grid (`category-tile` with 135° gradient per category and a 48 px coloured icon) for the full category list. Add the CSS snippet from Appendix E.
- **Detail page** (optional for Dailies): `Adw.NavigationPage` with 128 px icon, `title-1`, pill buttons (`small-pill suggested-action`), context lozenges (`circular-lozenge` for difficulty/category), and the header-title-on-scroll `Revealer` trick.
- Top-level nav: `Adw.ViewSwitcher` in the header bar collapsing to `Adw.ViewSwitcherBar` at ≤700 px — same as Bazaar, since Dailies has only a few top-level views (Home/Browse, Favorites could be a section instead of a tab, Search).

### 12.5 Repository / release hygiene to copy verbatim
- `.github/workflows/build-flatpak.yml` (Appendix B) adjusted to `gnome-51` image, `bundle: Dailies.flatpak`, manifest path; **add an upload step to GitHub Releases on tags** (Bazaar doesn't attach bundles; Dailies wants downloadable `.flatpak` until Flathub is set up — use `softprops/action-gh-release` or `gh release upload` with the artifact produced by `flatpak-github-actions`).
- `flatpak-external-data-checker.yml` (daily) once the manifest has `x-checker-data`.
- SHA-pin every action with a `# vX.Y.Z` comment; `permissions: {}` at top and minimal per-job.
- `version.sh`-style single version source consumed by `meson.build`, and `<release>` entries in metainfo validated by `appstreamcli validate --no-net --explain` + `desktop-file-validate` + `glib-compile-schemas --strict --dry-run` as meson tests.
- Metainfo `<branding>` colours, `<supports>/<requires display_length>`, `<developer id>`, `content_rating oars-1.1`, screenshots with captions — Flathub quality-moderation checks look for these.
- Ship `AppID.svg`, `AppID.Devel.svg`, `AppID-symbolic.svg`, plus `AppID.Source.svg` from the GNOME icon template; keep the icon a single centred object on the 128 px grid with GNOME palette colours (for Dailies: e.g. a calendar/day tile with a puzzle/grid motif).
- `Justfile` with `build-flatpak` / `build-flatpak-bundle` recipes; `.devcontainer` or `foundry` config; `CONTRIBUTING.md` with a dependency table; `docs/` for the data-format spec (Dailies: how to submit a DLE via the issue form — reuse Bazaar's YAML issue-form style for a "Add a DLE" template with required `name/url/category/difficulty` fields).

### 12.6 What *not* to copy
- The libflatpak/ostree/polkit/bubblewrap module stack and its permissions, the daemon/systemd service, search provider, `dl-worker` subprocess pool, hooks, blocklists, malcontent — all app-store specific.
- Account-backed favorites (Dailies must be local).
- The `gen_gobject.sh` generator and libbge are C-specific; only relevant if Dailies is written in C.

---

## 13. Open questions / unverified

- Whether GitLab `main` changed the curated YAML format after v0.9.4 (I read the format from the GitHub mirror at v0.9.4+14; GitLab deps/manifest/CI were checked, the YAML docs were not re-diffed).
- How `src/icons` resources are registered with `GtkIconTheme` (grep showed the gresource listing; the `gtk_icon_theme_add_resource_path` call was not located).
- Exact flatpak-github-actions artifact name/behaviour for release uploads (the action uploads the bundle as a workflow artifact; attaching it to a GitHub Release needs an extra step not present in Bazaar).
- Flathub's `/collection/trending` and `/collection/popular` ranking semantics are server-side and undocumented in the repo.

---

## Sources

Primary (clone + raw files):
- https://github.com/bazaar-org/bazaar (mirror; files: `meson.build`, `meson_options.txt`, `version.sh`, `Justfile`, `CONTRIBUTING.md`, `CODESTYLE.md`, `README.md`, `bazaar.doap`, `.clang-format`, `.github/workflows/build-flatpak.yml`, `.github/workflows/flatpak-external-data-checker.yml`, `.github/ISSUE_TEMPLATE/bug_form.yml`, `.github/CODEOWNERS`, `.github/FUNDING.yml`, `.devcontainer/*`, `build-aux/flatpak/io.github.kolunmi.Bazaar.json`, `data/*.in`, `data/*.gschema.xml`, `data/meson.build`, `data/icons/**`, `docs/overview.md`, `docs/example.yaml`, `docs/debugging.md`, `src/meson.build`, `src/bazaar.gresource.xml`, `src/style.css`, `src/*.blp`, `src/bz-yaml-parser.*`, `src/curated-config-schema.xml`, `src/bz-curated-*.txt`, `src/bz-content-provider.c`, `src/bz-flathub-state.c`, `src/global-net.*`, `src/bz-async-texture.*`, `src/dl-worker.c`, `src/io.c`, `src/bz-dynamic-list-view.*`, `src/bz-section-view.c`, `src/bz-row-view.c`, `src/bz-article-list-view.c`, `src/gen_gobject.sh`, `screenshots/*.png`)
- https://gitlab.gnome.org/World/bazaar (canonical) — `/-/raw/main/.gitlab-ci.yml`, `/-/raw/main/version.sh`, `/-/raw/main/src/meson.build`, `/-/raw/main/build-aux/flatpak/io.github.kolunmi.Bazaar.json`, `/-/raw/main/data/io.github.kolunmi.Bazaar.metainfo.xml.in`, `/-/raw/main/README.md`
- https://gitlab.gnome.org/api/v4/projects/World%2Fbazaar/releases and `/repository/commits` (release v0.9.8 2026-10-13; latest commit 2026-10-13)
- https://github.com/bazaar-org/bazaar/releases (via `gh release list/view`: v0.9.4 2026-08-15, no assets)
- https://github.com/flathub/io.github.kolunmi.Bazaar — `io.github.kolunmi.Bazaar.yaml`, `flathub.json` (raw.githubusercontent.com)
- https://gitlab.gnome.org/GNOME/citemplates/-/raw/master/templates/basic-release-with-dist.yml
- Flathub API base used by Bazaar: https://flathub.org/api/v2 (endpoints quoted from `src/bz-flathub-state.c`)
- Project site: https://usebazaar.org/ (hosts `curated/articles.yaml`, referenced in `docs/example.yaml`)

---

## Appendix A — `docs/example.yaml` (curated config, verbatim from the clone)

```yaml
rows:
  - banner:
      height: 250
      image:
        light-uri: https://www.mibatcontrol.com/wp-content/uploads/2026/04/Raccoon-Removal-Services-1.png # regular "uri" option is also available
        dark-uri: https://cdn.answeroverflow.com/1233140484017487952/image.png # you can also use file://
        fit: contain # contain, fill, cover or scale-down
        alt: "Raccoon"
        can-shrink: true
        halign: center
      dark-color: "#2b1f3d"
      light-color: "linear-gradient(135deg, #2b1f3d 0%, #778cf7 100%)" # Can also be a type of gradient
      # light-color: "url('file:///var/home/xander/Downloads/Conservation-Quest-at-Windsor-Great-Park-3.jpg') center / cover no-repeat" # Even an image should be possible
  - section:
      title: "Welcome to Bazaar"
      subtitle:
        string: | # Basic markdown is supported here.
          Discover apps you'll love. Here's one to get you started: [GNOME Calculator](appstream://org.gnome.Calculator).
      overflow-count: 8 # Will automatically create a "Show More" button, if there are more apps than the count (except if enable-bulk-install is true)
      appids:
        list:
          - org.gnome.Calendar
          - org.gnome.Contacts
          - org.gnome.Maps
          - org.gnome.Calculator
          - org.gnome.TextEditor
          - org.gnome.Loupe
          - org.mozilla.firefox
          - org.gnome.Boxes
          - org.gnome.Weather
          - org.gnome.clocks
          - org.gnome.Music
          - org.gnome.Showtime
          - org.gnome.Characters
          - org.gnome.Connections
          - org.gnome.Software
          - org.gnome.SimpleScan
          - org.gnome.font-viewer
          - org.gnome.Logs
  - articles:
      aspect-ratio: 1.777 # aspect ratio of the thumbnails, per articles section
      uri: https://usebazaar.org/curated/articles.yaml # Can be used as a feed.
      list: # Used only if URI fails, or is not given.
        - title: "Introducing GNOME 50, “Tokyo”" # Also used as the title on the article page
          subtitle: "First Half of 2026"
          image: https://release.gnome.org/50.webp # Always in 16:9
          uri: file:///var/home/xander/test-article.md
        - title: "#254 Commit Graph"
          subtitle: "This Week in GNOME"
          image: https://thisweek.gnome.org/posts/2026/06/twig-254/cover.webp
          uri: file:///var/home/xander/twig.md
        - title: "Introducing GNOME 50, “Tokyo”"
          subtitle: "First Half of 2026"
          image: https://release.gnome.org/50.webp
          uri: file:///var/home/xander/test-article.md
        - title: "HTTPS Test"
          subtitle: "This Week in GNOME"
          image: https://thisweek.gnome.org/posts/2026/06/twig-254/cover.webp
          uri: https://gist.githubusercontent.com/allysonsilva/85fff14a22bbdf55485be947566cc09e/raw/fa8048a906ebed3c445d08b20c9173afd1b4a1e5/Full-Markdown.md
  - featured-carousel: # A carousel, like the one seen at the top of the "Explore" page
      disable-auto-rotate: true
      appids:
        list:
          - io.github.kolunmi.Bazaar
          - be.alexandervanhee.gradia
  - section:
      title: "Web Browsers"
      list-type: rich # Directly features an install button on the card, use when a section has little apps.
      appids:
        list:
          - org.mozilla.firefox
          - com.google.Chrome
          - com.brave.Browser
          - org.chromium.Chromium
  - section:
      title: "Creative & Media"
      appids:
        list: # Sections of 12 apps look nice at all window widths
          - org.gnome.Music
          - org.gnome.Showtime
          - org.gnome.Loupe
          - org.gimp.GIMP
          - org.inkscape.Inkscape
          - org.blender.Blender
          - org.kde.krita
          - org.audacityteam.Audacity
          - org.kde.kdenlive
          - com.obsproject.Studio
          - org.shotcut.Shotcut
          - com.github.PintaProject.Pinta
  - section:
      title: "Developer Tools"
      subtitle:
        string: |
          Install these to become the *ultimate* developer
      list-type: rich
      appids:
        list:
          - me.iepure.devtoolbox
          - org.gnome.Builder
          - com.jetbrains.IntelliJ-IDEA-Community
          - re.sonny.Workbench
      enable-bulk-install: true
  - banner:
      image:
        uri: https://images.unsplash.com/photo-1612287230202-1ff1d85d1bdf?q=80&w=1471&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D
        fit: cover
        can-shrink: true
```

## Appendix B — `.github/workflows/build-flatpak.yml` (verbatim)

```yaml
on:
  push:
    branches: [main]
  pull_request:
    paths-ignore:
      - "**.md"
      - "docs/*"
      - "screenshots/*"
      - "translators.sh"
      - ".github/ISSUE_TEMPLATE/**"
  workflow_dispatch:

permissions: {}

name: CI Build Flatpak
jobs:

  flatpak:
    name: "Flatpak"
    container:
      image: ghcr.io/flathub-infra/flatpak-github-actions:gnome-50
      options: --privileged
    strategy:
      matrix:
        variant:
          - arch: x86_64
            runner: ubuntu-latest
          # no latest for ARM :(
          - arch: aarch64
            runner: ubuntu-24.04-arm

    runs-on: ${{ matrix.variant.runner }}
    steps:

    - name: Git Checkout
      uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
      with:
        submodules: recursive
        persist-credentials: false

    - name: Restore cache
      uses: actions/cache/restore@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0
      with:
        path: .flatpak-builder
        key: flatpak-builder-046f9ec-${{ matrix.variant.arch }}-${{ github.run_id }}
        restore-keys: |
          flatpak-builder-046f9ec-${{ matrix.variant.arch }}-

    - name: Build Flatpak
      uses: flatpak/flatpak-github-actions/flatpak-builder@401fe28a8384095fc1531b9d320b292f0ee45adb # v6.7
      with:
        bundle: Bazaar.flatpak
        manifest-path: build-aux/flatpak/io.github.kolunmi.Bazaar.json
        # caching is broken upstream
        # https://github.com/flatpak/flatpak-github-actions/issues/239
        # this is only true because there is no other way to call fb with --ccache
        cache: true
        restore-cache: false
        arch: ${{ matrix.variant.arch }}
        verbose: true

    - name: Write new cache
      uses: actions/cache/save@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0
      with:
        path: .flatpak-builder
        key: flatpak-builder-046f9ec-${{ matrix.variant.arch }}-${{ github.run_id }}
```

`.github/workflows/flatpak-external-data-checker.yml` (verbatim):

```yaml
name: Check for Flatpak dependency updates
on:
  schedule:
  - cron: "0 0 * * *" # every day
  workflow_dispatch:

jobs:
  flatpak-external-data-checker:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        branch: [ main ]

    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
        with:
          ref: ${{ matrix.branch }}

      - uses: docker://ghcr.io/flathub/flatpak-external-data-checker:latest
        env:
          GIT_AUTHOR_NAME: Flatpak External Data Checker
          GIT_COMMITTER_NAME: Flatpak External Data Checker
          # email sets "github-actions[bot]" as commit author, see https://github.community/t/github-actions-bot-email-address/17204/6
          GIT_AUTHOR_EMAIL: 41898282+github-actions[bot]@users.noreply.github.com
          GIT_COMMITTER_EMAIL: 41898282+github-actions[bot]@users.noreply.github.com
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          args: --update --never-fork --require-important-update build-aux/flatpak/io.github.kolunmi.Bazaar.json
```

## Appendix C — GitLab `.gitlab-ci.yml` (verbatim, fetched 2026-10-15)

```yaml
include:
  - project: "gnome/citemplates"
    file: "flatpak/flatpak_ci_initiative.yml"
  - component: gitlab.gnome.org/GNOME/citemplates/basic-release-with-dist@master
    inputs:
      dist-job-name: "flatpak@x86_64"

.flatpak_vars:
  image: "quay.io/gnome_infrastructure/gnome-runtime-images:gnome-51"
  variables:
    FLATPAK_MODULE: "bazaar"
    MANIFEST_PATH: "build-aux/flatpak/io.github.kolunmi.Bazaar.json"
    APP_ID: "io.github.kolunmi.Bazaar"
    RUNTIME_REPO: "https://dl.flathub.org/repo/flathub.flatpakrepo"

flatpak@x86_64:
  extends:
    - '.flatpak@x86_64'
    - '.flatpak_vars'

flatpak@aarch64:
  extends:
    - '.flatpak@aarch64'
    - '.flatpak_vars'

nightly@x86_64:
  extends: ".publish_nightly"
  needs: ["flatpak@x86_64"]

nightly@aarch64:
  extends: ".publish_nightly"
  needs: ["flatpak@aarch64"]
```

## Appendix D — metainfo header + one release entry (verbatim excerpt)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>io.github.kolunmi.Bazaar</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>

  <name>Bazaar</name>
  <summary>Discover and install apps</summary>
  <description>
    <p>
      A fast and modern app store for Linux with a focus on discovering
      and installing Flatpak apps and add-ons, particularly from Flathub.
    </p>
    <ul>
      <li>Queue multiple installs and keep browsing</li>
      <li>Easily view app permissions</li>
      <li>Sign in to Flathub to view and manage your favorites</li>
      <li>Search apps directly from GNOME Shell</li>
    </ul>
  </description>

  <supports>
    <control>pointing</control>
    <control>keyboard</control>
    <control>touch</control>
  </supports>
  <requires>
    <display_length compare="ge">360</display_length>
  </requires>

  <developer id="io.github.kolunmi">
    <name>The Bazaar Contributors</name>
  </developer>

  <url type="homepage">https://usebazaar.org/</url>
  <url type="vcs-browser">https://github.com/bazaar-org/bazaar</url>
  <url type="bugtracker">https://github.com/bazaar-org/bazaar/issues</url>
  <url type="translate">https://l10n.gnome.org/module/bazaar/</url>
  <url type="faq">https://github.com/bazaar-org/bazaar/blob/master/README.md</url>
  <url type="help">https://github.com/bazaar-org/bazaar/discussions</url>
  <url type="donation">https://github.com/sponsors/kolunmi</url>
  <url type="contact">https://github.com/kolunmi</url>
  <url type="contribute">https://github.com/bazaar-org/bazaar</url>

  <translation type="gettext">bazaar</translation>
  <launchable type="desktop-id">io.github.kolunmi.Bazaar.desktop</launchable>
  <content_rating type="oars-1.1" />

  <branding>
    <color type="primary" scheme_preference="light">#ffbe6f</color>
    <color type="primary" scheme_preference="dark">#c11c2b</color>
  </branding>

  <screenshots>
    <screenshot type="default">
      <image>https://github.com/user-attachments/assets/e67f35f0-9566-4068-93f5-cb814db0aedd</image>
      <caption>The home page displaying Flathub apps</caption>
    </screenshot>
    ...
  </screenshots>

  <releases>
    <release version="0.9.4" date="2026-08-14">
      <url type="details">https://github.com/bazaar-org/bazaar/releases/tag/v0.9.4</url>
      <description translate="no">
        <p>
          <em>Changes</em>
        </p>
        <ul>
          <li>Added shortcuts for zoom actions in the screenshot viewer</li>
          <li>Clicking other app tiles on an app page now creates a new page</li>
          <li>Fixed keyboard navigation on the "Curated" page</li>
        </ul>
        <p>
          Thanks for reading, and have a great day!
        </p>
      </description>
    </release>
    ...
  </releases>
</component>
```

`data/meson.build` validation tests (verbatim excerpt):

```meson
desktop_file = i18n.merge_file(
        input: 'io.github.kolunmi.Bazaar.desktop.in',
       output: 'io.github.kolunmi.Bazaar.desktop',
         type: 'desktop',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'applications'
)
desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

appstream_file = i18n.merge_file(
        input: 'io.github.kolunmi.Bazaar.metainfo.xml.in',
       output: 'io.github.kolunmi.Bazaar.metainfo.xml',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'metainfo'
)
appstreamcli = find_program('appstreamcli', required: false, disabler: true)
test('Validate appstream file', appstreamcli,
     args: ['validate', '--no-net', '--explain', appstream_file])

install_data('io.github.kolunmi.Bazaar.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
)
compile_schemas = find_program('glib-compile-schemas', required: false, disabler: true)
test('Validate schema file',
     compile_schemas,
     args: ['--strict', '--dry-run', meson.current_source_dir()])
```

`data/icons/meson.build` (verbatim):

```meson
application_id = 'io.github.kolunmi.Bazaar'

scalable_dir = 'hicolor' / 'scalable' / 'apps'
if get_option('development')
  icon_file = '@0@.Devel.svg'.format(application_id)
else
  icon_file = '@0@.svg'.format(application_id)
endif

install_data(
  scalable_dir / icon_file,
  install_dir: get_option('datadir') / 'icons' / scalable_dir,
  rename: '@0@.svg'.format(application_id)
)

symbolic_dir = 'hicolor' / 'symbolic' / 'apps'
install_data(
  symbolic_dir / ('@0@-symbolic.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / symbolic_dir
)
```

## Appendix E — Blueprint & CSS snippets worth copying

`src/bz-app-tile.blp` (verbatim, the standard grid tile):

```blueprint
using Gtk 4.0;

template $BzAppTile: Button {
  styles [
    "card",
    "app-tile",
  ]

  child: Overlay {
    Box {
      margin-start: 12;
      margin-end: 12;
      margin-top: 12;
      margin-bottom: 12;
      orientation: horizontal;
      spacing: 15;
      can-focus: false;

      Image {
        pixel-size: 64;
        paintable: bind try {template.group as <$BzEntryGroup>.ui-entry as <$BzResult>.object as <$BzEntry>.icon-paintable, template.icon-override};

        styles ["icon-dropshadow"]
      }

      Box {
        valign: center;
        hexpand: true;
        orientation: vertical;
        spacing: 4;

        Box {
          orientation: horizontal;
          spacing: 6;

          Label {
            css-name: "app-tile-title";
            styles [
              "heading",
            ]

            xalign: 0.0;
            ellipsize: end;
            label: bind template.group as <$BzEntryGroup>.title;
          }

          Image {
            css-name: "app-tile-verified-check";
            styles [
              "verified",
            ]
            visible: bind template.group as <$BzEntryGroup>.is-verified;
            icon-name: "verified-checkmark-symbolic";
            pixel-size: 14;
            accessibility {
              label: _("Verified");
            }
          }
        }

        Label {
          css-name: "app-tile-description";
          xalign: 0.0;
          yalign: 0.0;
          wrap: true;
          ellipsize: end;
          vexpand: true;
          lines: bind $description_line_amount($is_zero(template.group as <$BzEntryGroup>.removable) as <bool>) as <int>;
          single-line-mode: true;
          label: bind template.group as <$BzEntryGroup>.description;
        }

        Box {
          css-name: "app-tile-installed-pill";
          halign: start;
          spacing: 4;
          visible: bind $invert_boolean($is_zero(template.group as <$BzEntryGroup>.removable) as <bool>) as <bool>;
          styles ["small-pill", "installed-pill"]

          Image {
            icon-name: "app-installed-symbolic";
            pixel-size: 12;
          }

          Label {
            // Translators: As in 'The app is installed'.
            label: _("Installed");
          }
        }
      }
    }
  };
}
```

`src/bz-category-tile.blp` (verbatim):

```blueprint
using Gtk 4.0;

template $BzCategoryTile: Button {
  styles [
    "card",
    "category-tile",
  ]

  child: Box {
    margin-start: 16;
    margin-end: 16;
    margin-top: 24;
    margin-bottom: 24;
    orientation: vertical;
    spacing: 12;
    valign: center;
    halign: center;

    Image {
      pixel-size: 48;
      icon-name: bind template.category as <$BzFlathubCategory>.icon-name;
      visible: bind $invert_boolean($is_null(template.category as <$BzFlathubCategory>.icon-name) as <bool>) as <bool>;

      styles [
        "icon-dropshadow",
      ]
    }

    Label {
      css-name: "category-tile-label";
      halign: center;
      xalign: 0.5;
      label: bind template.category as <$BzFlathubCategory>.short-name;
      wrap: true;
      wrap-mode: word_char;
    }
  };
}
```

Toggle-group section switcher (excerpt of `src/bz-flathub-page.blp`):

```blueprint
Box section_toggles_box {
  halign: center;
  width-request: 800;

  Adw.ToggleGroup section_toggles {
    hexpand: true;
    halign: fill;
    homogeneous: true;
    styles [ "round", "huge" ]

    Adw.Toggle { label: _("Trending"); name: "trending"; }
    Adw.Toggle { label: _("Popular");  name: "popular"; }
    Adw.Toggle { label: _("New");      name: "recently-added"; }
    Adw.Toggle { label: _("Updated");  name: "recently-updated"; }
  }
}

Adw.ViewStack sections_stack {
  enable-transitions: true;
  transition-duration: 300;
  visible-child-name: bind section_toggles.active-name bidirectional;

  Adw.ViewStackPage { name: "trending"; child: $BzFlathubCategorySection { ... min-items: 12; has-title: false; }; }
  ...
}
```

Category section with "More" pill (`src/bz-flathub-category-section.blp`, verbatim):

```blueprint
using Gtk 4.0;

template $BzFlathubCategorySection : Box {
  orientation: vertical;
  spacing: 10;
  visible: bind $invert_boolean($is_null(template.category as <$BzFlathubCategory>) as <bool>) as <bool>;
  margin-bottom: 12;

  Label section_title {
    styles [ "title-1", ]
    visible: bind template.has-title as <bool>;
    xalign: 0.0;
    hexpand: true;
    margin-start: 3;
    margin-end: 3;
    margin-bottom: 5;
    ellipsize: end;
  }

  $BzDynamicListView section_list {
    styles [ "flathub-page-section", ]
    hexpand: true;
    scroll: false;
    noscroll-kind: flow-box;
    child-type: "BzAppTile";
    child-prop: "group";
    row-spacing: bind $get_spacing(template.compact) as <int>;
    column-spacing: bind $get_spacing(template.compact) as <int>;
  }

  Button more_button {
    styles [ "pill", ]
    can-shrink: true;
    halign: center;
    valign: center;
    margin-top: 5;
    clicked => $on_more_button_clicked();
  }
}
```

Loading / offline / empty pattern (`src/bz-curated-view.blp` + `bz-window.blp`, excerpts):

```blueprint
Adw.ViewStack stack {
  enable-transitions: true;
  transition-duration: 400;

  Adw.ViewStackPage { name: "empty";
    child: Adw.StatusPage {
      icon-name: "star-outline-rounded-symbolic";
      title: _("No Curation");
      description: _("There is no curation information provided on this system. You can still browse apps on Flathub");
      child: Button { label: _("Browse Flathub"); halign: center; styles [ "pill" ] };
    };
  }
  Adw.ViewStackPage { name: "offline";
    child: Adw.StatusPage { icon-name: "connected-squares-x"; title: _("Offline"); };
  }
  Adw.ViewStackPage { name: "content";
    child: ScrolledWindow {
      child: Adw.Clamp { maximum-size: 1500; tightening-threshold: 1400;
        child: $BzDynamicListView content_box { margin-start: 30; margin-end: 30; margin-bottom: 50; scroll: false; noscroll-kind: list-box; ... };
      };
    };
  }
}

/* window-level loading page */
StackPage { name: "loading";
  child: Box { halign: fill; valign: center; orientation: vertical; spacing: 6;
    Adw.Spinner { width-request: 64; height-request: 64; margin-bottom: 18; }
    Label { label: _("Refreshing"); wrap: true; justify: center; margin-bottom: 24; styles [ "title-3" ] }
  };
}
```

CSS (from `src/style.css`, verbatim excerpts):

```css
.search-box {
  outline: 0 solid transparent;
  outline-offset: 6px;
  transition-property: outline, outline-offset;
  transition-duration: 200ms;
  padding: 0px 12px;
  border-radius: 9999px;
  background-color: var(--card-bg-color);
}
.search-box:focus-within {
  outline-color: color-mix(in srgb, var(--accent-color), transparent);
  outline-offset: 0;
  outline-width: 2px;
}
@media (prefers-color-scheme: light) {
  .search-box { background-color: var(--shade-color); }
}

.small-pill { padding: 2px 12px; border-radius: 99999px; }
.medium-pill { border-radius: 99999px; }
.installed-pill {
  background-color: alpha(@success_bg_color, 0.15);
  color: @success_color;
  font-weight: 500;
  font-size: 0.9em;
  padding: 2px 7px 2px 4.5px;
}
.favorite {
  --accent-fg-color: @accent_bg_color;
  --accent-bg-color : alpha(@accent_bg_color, 0.25);
  --accent-color: @accent_color;
}
.support {
  --accent-fg-color : #f06292;
  --accent-bg-color : alpha(#f06292, 0.25);
  --accent-color : #f06292;
}
toggle-group.huge, toggle-group.huge * { border-radius: 9999px; }
.huge > toggle { padding: 3px 12px; }
.flathub-page-section { border-radius: 10px; }

/* Category buttons styling modified from GNOME Software*/
.category-tile {
  font-weight: 700;
  font-size: 13pt;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
  padding-left: 32px;
  padding-right: 32px;
  outline-offset: 2px;
}
window.narrow .category-tile { font-size: 14pt; padding-left: 24px; padding-right: 24px; }
/* All background gradients are at 135deg for consistency */
.category-tile.category-trending { background: linear-gradient(135deg, #99c1f1, #3584e4); }
.category-tile.category-trending:hover { background: linear-gradient(135deg, shade(#99c1f1, 1.1), shade(#3584e4, 1.1)); }
.category-tile.category-trending:active { background: linear-gradient(135deg, shade(#99c1f1, .95), shade(#3584e4, .95)); }
.category-tile.category-popular {
  background: linear-gradient(135deg, #f7ef74, #ffbf6f);
  color: rgba(0, 0, 0, 0.8);
  text-shadow: 0 1px rgba(255, 255, 255, 0.35);
}
.category-tile.category-game {
  background: linear-gradient(135deg, #f9e2a7 0%, #eb5ec3 50%, #6d53e0 100%);
  color: #393484;
  text-shadow: 0 1px rgba(255, 255, 255, 0.35);
}
@media (prefers-contrast: more) {
  .card.category-tile, .card.app-tile { box-shadow: inset 0 0 0 1px var(--hc-border); }
  .card.category-tile:focus-within, .card.app-tile :focus-within { box-shadow: none; outline-color: var(--accent-color); }
}
```

## Appendix F — Justfile Flatpak recipes (verbatim excerpt)

```just
build-flatpak $manifest=manifest $branch=branch:
    #!/usr/bin/env bash
    set -xeuo pipefail
    flatpak --user remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

    FLATPAK_BUILDER_DIR="$(realpath ".flatpak-builder")"
    BUILDER_ARGS+=(--default-branch="${branch}")
    BUILDER_ARGS+=(--state-dir="${FLATPAK_BUILDER_DIR}/flatpak-builder")
    BUILDER_ARGS+=("--user")
    BUILDER_ARGS+=("--ccache")
    BUILDER_ARGS+=("--force-clean")
    BUILDER_ARGS+=("--install")
    BUILDER_ARGS+=("--disable-updates")
    BUILDER_ARGS+=("--disable-rofiles-fuse")
    BUILDER_ARGS+=("${FLATPAK_BUILDER_DIR}/build-dir")
    BUILDER_ARGS+=("${manifest}")

    if which flatpak-builder &>/dev/null ; then
        flatpak-builder "${BUILDER_ARGS[@]}"
    else
        flatpak run org.flatpak.Builder "${BUILDER_ARGS[@]}"
    fi

build-flatpak-bundle $appid=appid: build-flatpak
    #!/usr/bin/env bash
    set -euo pipefail

    FLATPAK_BUILDER_DIR="$(realpath ".flatpak-builder")"

    flatpak build-export repo "${FLATPAK_BUILDER_DIR}/build-dir"
    flatpak build-bundle repo "${appid}".flatpak "${appid}"
```

## Appendix G — `version.sh` (verbatim, GitHub mirror)

```sh
#!/bin/sh

INSTR="$1"

VERSION=0.9.5
CACHE_VERSION=2

case "$INSTR" in
    get-version)
        echo "${VERSION}"
        ;;
    get-vcs)
        VCS_VERSION="$(git -C "$MESON_SOURCE_ROOT" describe --always --dirty)"
        if [ -n "$VCS_VERSION" ]; then
            echo "${VERSION} (vcs=${VCS_VERSION})"
        else
            echo "${VERSION}"
        fi
        ;;
    get-gh-release)
        TAG="v${VERSION}"
        echo "https://github.com/bazaar-org/bazaar/releases/tag/${TAG}"
        ;;
    get-cache)
        echo "${CACHE_VERSION}"
        ;;
    *)
        echo invalid arguments 1>&2
        exit 1
        ;;
esac
```
