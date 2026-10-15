# Dailies — GTK4 / Libadwaita UI building blocks and conventions

Research key: `libadwaita-ui-patterns`
Date of research: 2026-10-15
Author: research subagent (for the Dailies architecture/design document)

Legend used throughout:
- **[V]** verified against a primary source (URL or cloned file given)
- **[I]** inference / recommendation by the researcher, not stated verbatim by a source
- **[U]** could not be verified in this run

---

## 0. Executive summary

- **Current stable stack (Oct 2026)** [V]: GNOME 51 "A Coruña" shipped 2026-09-16 with **GTK 4.24.0** and **libadwaita 1.10.0**; the GNOME 51 Flatpak SDK/Platform (`org.gnome.Sdk//51`, `org.gnome.Platform//51`) is live on Flathub (remote build subject `51.0-14-ga554d8085`, dated 2026-10-14) and already installed on the owner's machine. libadwaita `main` is 1.11.alpha. The task brief mentioned "libadwaita 1.7/1.8, GNOME 48/49"; those are now two to three cycles old. Mapping: 1.7 ↔ GNOME 48, 1.8 ↔ GNOME 49, 1.9 ↔ GNOME 50, 1.10 ↔ GNOME 51.
- **Blueprint** [V]: blueprint-compiler is bundled in the GNOME SDK since 49 (`org.gnome.Sdk//49` → 0.18.0, `//50` → 0.20.4, `//51` → 0.22.2). Upstream latest tag is v0.22.2. Cartridges and Bazaar both build `.blp` → `.ui` with a Meson `custom_target` + `batch-compile`. Blueprint is production-ready for Dailies; a `subprojects/blueprint-compiler.wrap` fallback keeps non-Flatpak builds working.
- **In-app browser** [V]: `org.gnome.Platform//51` contains `libwebkitgtk-6.0.so.4` (WebKitGTK 2.54.1, GTK4 API "WebKit 6.0") plus the `WebKit-6.0.typelib`, so a built-in browser view costs zero extra Flatpak modules. It also contains **glycin 2.2.1** (`libglycin-gtk4-2`, `GlyGtk4-2.typelib`), the sandboxed image loader GTK's own docs recommend for untrusted images — ideal for remote game icons.
- **Recommended skeleton** [I]: `Adw.ApplicationWindow` → `Adw.ToastOverlay` → `Adw.NavigationView` (library page + browser page) → `Adw.NavigationSplitView` with an **`Adw.Sidebar`** (new in 1.9) for Favorites / Popular / Trending / categories, collapsing via an `Adw.Breakpoint` at `max-width: 500sp`; content is a `Gtk.GridView` of card tiles inside `Adw.ClampScrollable`, with `Adw.StatusPage` empty states and a `Gtk.SearchBar` driven by `key-capture-widget`. Preferences via `Adw.PreferencesDialog` (+ `Adw.ComboRow` for browser mode), `Adw.AboutDialog.new_from_appdata`, and `Adw.ShortcutsDialog` auto-wired by `AdwApplication` from `shortcuts-dialog.ui`.
- **Favorite icons** [V]: `starred-symbolic` and `non-starred-symbolic` exist in the Adwaita icon theme (`Adwaita/symbolic/status/`). Bundle copies in the GResource anyway (GNOME's own guidance; libadwaita itself bundles "all used icons not in GTK" since 1.9.rc).
- **Avoid (deprecated)** [V]: `AdwLeaflet`, `AdwFlap`, `AdwSqueezer`, `AdwViewSwitcherTitle` (1.4); `AdwAboutWindow`, `AdwMessageDialog`, `AdwPreferencesWindow`, `.opaque` (1.6); `.dim-label` → `.dimmed` (1.7); `style-dark.css`/`style-hc*.css` → media queries in `style.css` (1.9); `AdwEnumListModel` → `GtkEnumList` (1.10); GTK side: `GtkShortcutsWindow` (4.18), `GtkPicture:keep-aspect-ratio` → `content-fit` (4.8), `GdkTexture.new_for_pixbuf` (4.20), `GtkDialog`/`GtkComboBoxText` (4.10).

---

## 1. Version landscape and what it means for Dailies

| Component | GNOME 49 SDK | GNOME 50 SDK | GNOME 51 SDK (current) | Source |
|---|---|---|---|---|
| libadwaita | 1.8.x | 1.9.x | **1.10.0** | gnome-build-meta `gnome-51/elements/sdk/libadwaita.bst` → `libadwaita-1.10.0.tar.xz` [V]; release tags `1.8.8`, `1.9.4`, `1.10.0` in libadwaita git [V] |
| GTK | 4.20 [U, inferred from cadence] | 4.22 [U] | **4.24.0** | `gnome-51/elements/sdk/gtk.bst` → `gtk-4.24.0.tar.xz` [V]; Phoronix 2026-09-12 "GTK 4.24 Released" [V] |
| blueprint-compiler | **0.18.0** | **0.20.4** | **0.22.2** | `elements/sdk/blueprint-compiler.bst` on branches gnome-49 / gnome-50 / gnome-51 [V] |
| WebKitGTK (6.0 API) | [U] | [U] | **2.54.1** (`libwebkitgtk-6.0.so.4`) | `gnome-51/elements/sdk/webkitgtk.inc` [V]; `flatpak run --command=sh org.gnome.Platform//51` listing [V] |
| glycin (+ gtk4 bindings) | [U] | [U] | **2.2.1** | `gnome-51/elements/sdk/glycin.inc` [V]; Platform lib listing [V] |
| libsoup | — | — | 3.x (`libsoup-3.0.so.0`) | Platform lib listing [V] |

Other verified facts:
- libadwaita docs: `https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/` states "Library Version: 1.10.0" [V]; `/doc/main/` states 1.11.alpha [V]. Cite `1-latest` for stable behaviour.
- `AdwSidebar`/`AdwViewSwitcherSidebar` are **1.9+** (libadwaita NEWS 1.9.alpha) [V]; `AdwSidebar:prefix`/`:suffix` are 1.10 [V]. If Dailies wants `AdwSidebar`, require `libadwaita-1 >= 1.9` and runtime 50+.
- Flathub "GNOME runtime version 51 will drop gcr-3 and libhandy" [V, Flathub discourse] — irrelevant to a new GTK4 app but confirms 51 is the active target.
- Cartridges (reference app) targets `runtime-version: "49"`, requires `gtk4 >= 4.15.0`, `libadwaita-1 >= 1.6.beta` [V, `cartridges/meson.build`, `build-aux/flatpak/page.kramo.Cartridges.Devel.json`]. Bazaar targets `runtime-version: "50"` and `blueprint-compiler >= 0.20.0` [V, `bazaar/build-aux/flatpak/io.github.kolunmi.Bazaar.json`, `bazaar/src/meson.build:351`].

**Recommendation [I]:** Target `org.gnome.Platform//51` for the Flatpak, declare `dependency('gtk4', version: '>= 4.20')` and `dependency('libadwaita-1', version: '>= 1.9')` in Meson (1.9 floor because of `AdwSidebar`; drop to `>= 1.8` only if you replace `AdwSidebar` with a `GtkListBox.navigation-sidebar` as Cartridges does). Flatpak users are unaffected by distro versions; the floor matters only for Hive/native builds.

---

## 2. Window structure: `Adw.ApplicationWindow`, split views, sidebar

### 2.1 Containers [V]
- `AdwApplicationWindow` / `AdwWindow` have breakpoints built in (`AdwBreakpoint` children) and are required parents for `AdwDialog` (migrating-to-adaptive-dialogs page). Put the header bar inside an `AdwToolbarView` (`[top] Adw.HeaderBar`), never as the window titlebar.
- `AdwBreakpointBin` lets you add breakpoints to any subtree; most apps "shouldn't need it". With breakpoints the widget has **no minimum size**, so set `width-request`/`height-request` explicitly. Bazaar uses `Adw.BreakpointBin { width-request: 360; height-request: 450; ... }` around the whole content and per-page bins for grid column counts [V, `bz-window.blp`, `bz-all-apps-page.blp`].
- HIG adaptive guideline: phone-capable apps should scale down to **360×294 px**; desktop minimum display 1024×600 px [V, hig/guidelines/adaptive.html]. Bazaar's window uses `width-request: 360; height-request: 294;` exactly [V].

### 2.2 `Adw.NavigationSplitView` (since 1.4) [V]
URL: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/class.NavigationSplitView.html
- Sidebar and content must both be `AdwNavigationPage`. When `collapsed` it becomes an `AdwNavigationView` (sidebar = root page, content = subpage); `show-content` picks which is visible when collapsed. `AdwHeaderBar` inside the pages auto-provides back button and title.
- Sizing defaults: `min-sidebar-width` **180sp**, `max-sidebar-width` **280sp**, `sidebar-width-fraction` **0.25**; `sidebar-width-unit` selects px/pt/sp. `sidebar-position` since 1.7.
- CSS: node `navigation-split-view`; uncollapsed children get `.sidebar-pane` / `.content-pane`.
- Canonical breakpoint (docs):
  ```xml
  <object class="AdwBreakpoint">
    <condition>max-width: 400sp</condition>
    <setter object="split_view" property="collapsed">True</setter>
    <setter object="sidebar" property="mode">page</setter>
  </object>
  ```
  (The adaptive-layouts page adds: in the sidebar's `activated` handler call `adw_navigation_split_view_set_show_content(split_view, TRUE)` so tapping a category navigates to content when collapsed.)

### 2.3 `Adw.OverlaySplitView` (since 1.4) [V]
URL: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/class.OverlaySplitView.html
- Same sizing defaults (180sp/280sp/25%). When `collapsed`, the sidebar overlays content; `show-sidebar`, `pin-sidebar`, `enable-show-gesture`/`enable-hide-gesture` (touch only). Used for the **utility pane** pattern and for "overlay sidebar" (keep `AdwSidebar` in `sidebar` mode, put a menu button in each pane and toggle visibility from the breakpoint; hide the sidebar after activation when collapsed) [V, adaptive-layouts.html].
- Cartridges uses `Adw.OverlaySplitView overlay_split_view { sidebar-width-fraction: .2; }` with a `sidebar-show-symbolic` toggle button bound `visible: bind overlay_split_view.show-sidebar inverted;` and a breakpoint at `max-width: 564px` setting `overlay_split_view.collapsed: true` [V, `cartridges/data/gtk/window.blp`].

**Choice for Dailies [I]:** a category list that *navigates* (Favorites, Popular, Trending, categories) is the HIG "sidebar" pattern (hig/patterns/nav/sidebars.html: "a vertical panel listing locations, where selecting one navigates to it"; use when there are more views than a view switcher can hold and users switch often). That maps to `AdwNavigationSplitView` + `AdwSidebar` in `page` mode when collapsed. `AdwOverlaySplitView` is for *utility panes* (filters, details) — not the primary navigation.

### 2.4 `Adw.Sidebar` (since 1.9; prefix/suffix 1.10) [V]
URL: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/class.Sidebar.html
- Holds `AdwSidebarSection` → `AdwSidebarItem`. Properties: `mode` (`sidebar` | `page`), `selected`, `selected-item`, `items`, `sections`, `filter`, `placeholder`, `menu-model`, `drop-preload`, `prefix`/`suffix` (1.10). Signals: `activated`, `drop`, `drop-enter`, `drop-value-loaded`, `setup-menu`.
- `AdwSidebarItem`: `title`, `icon-name`, `drag-motion-activate`; `AdwSidebarSection`: `title`, `menu-model`.
- In `sidebar` mode it uses an internal `GtkListBox.navigation-sidebar`; in `page` mode an internal `AdwPreferencesPage` (boxed lists) — this is exactly the "collapsed phone layout" GNOME apps now use.
- Add/remove sections programmatically with `append/prepend/insert/remove/remove_all`; fixed sections can be declared in the UI file.
- Filtering (`filter`) and drag-and-drop onto items are built in → you could drop a game tile onto "Favorites" to favourite it [I].

**Favorites pinned at top [I]:** make the first `AdwSidebarSection` title-less with a single `AdwSidebarItem { title: _("Favorites"); icon-name: "starred-symbolic"; }`, a second section "This Week" (Popular, Trending), and a third section "Categories" populated from the data file. If you must support libadwaita 1.8, fall back to the Cartridges approach (`ScrolledWindow > ListBox.navigation-sidebar` with hand-built rows) [V, Cartridges window.blp].

### 2.5 `Adw.ViewStack` / view switcher alternatives [V]
- `AdwViewSwitcher` (+`AdwViewSwitcherBar` at the bottom via breakpoint `max-width: 550sp`, clearing `header_bar.title-widget`) — for 3–5 fixed views (HIG view-switchers.html: "three to five", nouns, header capitalization; move to bottom edge when narrow). Set `policy: wide` when paired with a bottom bar [V, class.ViewSwitcher.html]. Bazaar does exactly this (`[title] Adw.ViewSwitcher { stack: main_view_stack; policy: wide; }` + `[bottom] Adw.ViewSwitcherBar` + breakpoint `max-width: 700px` → `top_header_bar.title-widget: null; toolbar_view.reveal-bottom-bars: true;`) [V, `bz-window.blp`].
- `AdwInlineViewSwitcher` (1.7) — a view switcher built from `AdwToggleGroup`; `display-mode` icons/labels/both; style classes `.flat`, `.round` [V]. Good for a small inline "Grid / List" or "All / Easy / Medium / Hard" filter in the content header [I].
- `AdwToggleGroup` / `AdwToggle` (1.7) — exclusive toggles with `name`, `icon-name`, `tooltip`, `label`, `child`; `active`, `active-name`, `homogeneous`, `can-shrink` [V].
- `AdwViewSwitcherSidebar` (1.9) — sidebar driven by an `AdwViewStack` [V, NEWS]. Alternative to `AdwSidebar` if each category is a distinct stack page; for Dailies the categories are *data*, so `AdwSidebar` + one grid page re-filtered is simpler [I].
- Deprecated: `AdwViewSwitcherTitle` (1.4) → `AdwViewSwitcher` in `title-widget` + breakpoint [V, index].

---

## 3. The tile grid: `Gtk.GridView` vs `Gtk.FlowBox` vs `Adw.WrapBox`

| | `GtkGridView` | `GtkFlowBox` | `AdwWrapBox` (1.7) |
|---|---|---|---|
| Model | `GListModel` + `GtkListItemFactory` (recycled widgets) | widgets inserted directly, or `bind_model()` | widgets only |
| Columns | `min-columns` (no documented default), `max-columns` **default 7**; cells homogeneous; `single-click-activate`, `enable-rubberband`, `tab-behavior` (4.12), `scroll_to()` (4.12) | `min/max-children-per-line`, `homogeneous`, `column/row-spacing`, `selection-mode`, `activate-on-single-click`; `set_filter_func/set_sort_func/invalidate_filter` | `child-spacing`, `line-spacing`, `justify`, `pack-direction`, `wrap-policy`… children flow "like words", **not a grid** |
| Signals | `activate(position)` | `child-activated` | — |
| CSS | `gridview > child(.activatable)` | `flowbox > flowboxchild` | `wrap-box` |
| a11y role | GRID / GRID_CELL | — | GROUP |
| Who uses it | Bazaar (all tile pages) | Cartridges library | tags/chips |

Sources [V]: https://docs.gtk.org/gtk4/class.GridView.html , https://docs.gtk.org/gtk4/property.GridView.max-columns.html , https://docs.gtk.org/gtk4/class.FlowBox.html , https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/class.WrapBox.html ; HIG grid-views.html references only `GtkGridView`; says "set a maximum width so rows don't become uncomfortably long", minimal styling, outline cells only when thumbnails are irregular.

Bazaar pattern [V, `bz-all-apps-page.blp`]: `ScrolledWindow{hscrollbar-policy: never} > Adw.ClampScrollable{maximum-size: 1500; tightening-threshold: 1400} > GridView{min-columns: 4; max-columns: 4; single-click-activate: true; enable-rubberband: false; factory: BuilderListItemFactory { template ListItem { child: $BzAppTile { group: bind template.item as <$BzEntryGroup>; }; } }}` with `Adw.Breakpoint`s at 1300/900/700 px setting `grid_view.min-columns/max-columns` to 3/2/1.

Cartridges pattern [V, `window.blp`]: `FlowBox library { homogeneous: true; halign: center; valign: start; column-spacing: 12; row-spacing: 12; margin-*: 15; selection-mode: none; styles ["no-hover"] }` and in Python `set_filter_func`, `set_sort_func`, `set_max_children_per_line(10)`; empty/no-results `Adw.StatusPage`s are swapped in via a `Gtk.Overlay`.

**Recommendation [I]:** Dailies will have tens to low hundreds of games, so both work. Prefer **`GtkGridView`** backed by `Gio.ListStore` → `Gtk.FilterListModel` (search + category) → `Gtk.SortListModel` (popularity/name) → `Gtk.NoSelection`; bind the sidebar selection and search text to the filters. This gives you model-driven favourites/popularity updates for free and matches the HIG's named widget. Use `GtkFlowBox` only if you want trivially simple manual drag-reordering of favourites (FlowBox children are real widgets you can `insert()` at an index). Wrap the grid in `Adw.ClampScrollable` (maximum ~1400) and set `min-columns: 1; max-columns: 6`, letting breakpoints lower `max-columns` on narrow widths.

---

## 4. Empty states, loading, feedback

- **`Adw.StatusPage`** [V]: `icon-name`, `paintable`, `title`, `description` (markup), `child`; `.compact` style class for small spaces; setting an `AdwSpinnerPaintable` as `paintable` adds `.spinner` for a compact loading look; `focus()`/`grab_focus()` added in 1.9 (NEWS). HIG placeholders.html: every placeholder needs a heading ("Empty Folder"), optional description, optional action; symbolic icon for frequently-empty spaces (search results), illustration only for first-run main view. Cartridges' pattern: `Adw.StatusPage notice_empty { title; description; Button { label: _("Import"); styles ["pill","suggested-action"]; action-name: "app.import"; } }` [V].
- **`Adw.Spinner`** (1.6) [V]: scales 16–64 px; set `width-request/height-request` + `halign/valign` for a fixed size; CSS `image.spinner`; a11y role progress bar. Prefer it over `GtkSpinner`; libadwaita 1.10 stylesheet "Adapt to GtkSpinner changes in newer GTK" [V, NEWS]. Bazaar's loading page: `Adw.Spinner { width-request: 64; height-request: 64; }` + `Label.title-3` [V].
- **`Adw.Toast` / `Adw.ToastOverlay`** [V]: `title` (markup unless `use-markup: false`), `button-label`, `action-name`/`action-target`, `priority` (`ADW_TOAST_PRIORITY_HIGH` jumps the queue), `timeout` **default 5 s, 0 = indefinite**, signals `dismissed`, `button-clicked`; `adw_toast_overlay_dismiss_all()` since 1.7. HIG toasts.html: short title, informal style, no button by default (Undo is the main exception), bottom-centre of window. Dailies use: "Added to Favorites — Undo" [I].

---

## 5. Preferences: `Adw.PreferencesDialog` and rows

- **`Adw.PreferencesDialog`** (1.5) [V]: `AdwDialog` subclass; `add(page)`, `remove`, `search-enabled` (**defaults to FALSE since the dialog API** — set `true`; Cartridges and Bazaar both do), `add_toast`, `push_subpage`/`pop_subpage` (+ `navigation.pop` action); CSS `dialog.preferences`. Pages: `AdwPreferencesPage { name; title; icon-name; banner (1.7); }` containing `AdwPreferencesGroup { title; description; separate-rows; }`; 1.8 added `AdwPreferencesGroup.bind_model()/get_row()` and `AdwPreferencesPage.insert()/get_group()` [V, NEWS].
- **`Adw.ComboRow`** [V]: mirrors `GtkDropDown` — `model` (e.g. `GtkStringList`), `selected`, `selected-item`, `expression`, `factory`, `list-factory`, `header-factory` (1.6), `use-subtitle`, `enable-search` (1.4), `search-match-mode` (1.6). Watch `notify::selected`. `AdwEnumListModel` is deprecated in 1.10 → `GtkEnumList` (GTK 4.24) [V, NEWS 1.10.alpha].
- **`Adw.SwitchRow`** (1.4) [V]: `active`; a11y role switch; `notify::active`.
- **`Adw.EntryRow`** (1.2) [V]: `GtkEditable` (`text`), `show-apply-button` (use when applying is expensive), `input-purpose`, `input-hints`, `activates-default`, `text-length` (1.5), `max-length` (1.6); signals `apply`, `entry-activated`; `[prefix]`/`[suffix]` children; `.monospace` affects only the editable part. Ideal for "Browser command" [I].
- Boxed-list reference [V, libadwaita boxed-lists.html]: `GtkListBox { selection-mode: none; styles ["boxed-list"] }` or `AdwPreferencesGroup`; rows: ActionRow, SwitchRow, ExpanderRow, ComboRow, EntryRow, PasswordEntryRow, SpinRow, ButtonRow; `.property` for read-only values; `.boxed-list-separate` for one card per row. HIG boxed-lists.html: at most two controls per row; navigation rows end with `go-next-symbolic`; for reorderable lists provide drag handles **and/or** a "Move up/Move down/Remove" menu (menu required for accessibility).

Browser-mode setting design [I]: an `Adw.ComboRow` "Open Games With" (`StringList { strings [_("Configured Browser"), _("Built-in Browser"), _("Default Browser")] }`) + an `Adw.EntryRow` "Browser Command" visible only for the first choice, + an `Adw.SwitchRow` "Always Try Built-in Browser First". Store as a GSettings enum (see §10).

---

## 6. About, shortcuts, dialogs

### 6.1 `Adw.AboutDialog` (1.5) [V]
URL: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/ctor.AboutDialog.new_from_appdata.html
```c
AdwDialog* adw_about_dialog_new_from_appdata (const char* resource_path, const char* release_notes_version /* nullable */)
```
Reads from the AppStream metainfo in your GResource: icon ← `<id>`, name ← `<name>`, developer name ← `<developer><name>`, version ← latest `<release>`, website ← `<url type="homepage">`, support ← `<url type="help">`, issues ← `<url type="bugtracker">`, license ← `<project_license>` (unknown → `GTK_LICENSE_CUSTOM`), release notes ← the `<release version=…>` matching `release_notes_version`. Also `appdata-resource-path` property (1.9) to do the same from UI files; `other-apps-title` (1.10). Cartridges: `Adw.AboutDialog.new_from_appdata(shared.PREFIX + "/" + shared.APP_ID + ".metainfo.xml", shared.VERSION)` then `set_developers([...])`, with the metainfo compiled into the gresource (`<file preprocess="xml-stripblanks">@APP_ID@.metainfo.xml</file>`) [V, `cartridges/main.py`, `cartridges.gresource.xml.in`]. Bazaar extracts only the latest release via `xmllint --xpath "//releases/release[1]"` into `release-notes.xml` at build time to keep the resource small [V, `bazaar/src/meson.build`].

### 6.2 `Adw.ShortcutsDialog` (1.8) [V]
URL: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/class.ShortcutsDialog.html
- `AdwShortcutsSection { title }` → `AdwShortcutsItem { title; accelerator | action-name; direction (ltr/rtl) }`. If `action-name` is given and the app has an accelerator for it (`set_accels_for_action`), the dialog shows it — no duplication.
- **Automatic resource** [V, class.Application.html]: if your gresource contains `shortcuts-dialog.ui` defining an `AdwShortcutsDialog` with id **`shortcuts_dialog`**, `AdwApplication` creates the `app.shortcuts` action, presents the dialog, and installs the standard accelerator (Ctrl+?). Cartridges therefore aliases `gtk/shortcuts-dialog.ui` to `shortcuts-dialog.ui` in the gresource and lists `item (_("Keyboard Shortcuts"), "app.shortcuts")` in its primary menu [V].
- `GtkShortcutsWindow` is **deprecated since GTK 4.18** ("will be removed in GTK 5") [V, docs.gtk.org/gtk4/class.ShortcutsWindow.html]; `AdwShortcutLabel` (1.8) replaces `GtkShortcutLabel`.
- Both reference apps' `shortcuts-dialog.blp` files are reproduced in Appendix B.

### 6.3 `Adw.Dialog` (1.5) adaptive dialogs [V]
URL: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/class.Dialog.html and migrating-to-adaptive-dialogs.html
- Floating window or bottom sheet automatically (`presentation-mode`: auto/floating/bottom-sheet); never larger than the parent; not resizable → size via `content-width`/`content-height` (or `follows-content-size`); `can-close` + `close-attempt` for confirmations; `force_close()`; Esc closes; `present(parent)` accepts *any* widget inside the window; always modal; requires `AdwWindow`/`AdwApplicationWindow` parent; use `AdwHeaderBar` inside (it adds the close button).
- `AdwAlertDialog` replaces `AdwMessageDialog`; Blueprint has a `responses [ cancel: _("Cancel"), delete: _("Delete") destructive, ... ]` extension for it [V, blueprint extensions.rst].

---

## 7. Search and type-to-search [V]
- `GtkSearchBar`: set `key-capture-widget` (window or a parent container) so typing anywhere starts a search; `connect_entry()` (Blueprint: the entry inside the bar is auto-connected only when it is the direct child—Cartridges still calls `search_bar.connect_entry(search_entry)` in Python because it wraps the entry in an `Adw.Clamp`); `search-mode-enabled` bound bidirectionally to a header `ToggleButton` (`system-search-symbolic`, tooltip "Search"); Esc hides; Ctrl+F must be an **app action**, not handled by the bar. Source: https://docs.gtk.org/gtk4/class.SearchBar.html .
- `GtkSearchEntry`: `search-changed` fires after `search-delay` ms (4.8; default not stated on the page), `stop-search`, `activate`, `next-match`/`previous-match`, `placeholder-text` (4.10), `input-purpose`/`input-hints` (4.14), `key-capture-widget` property (4.22); a11y role SEARCH_BOX. Source: https://docs.gtk.org/gtk4/class.SearchEntry.html .
- HIG search.html: live results, "No results" placeholder in the content area, search global across views, fuzzy matching, most relevant first.
- Cartridges snippet [V]:
  ```blp
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
  ```

---

## 8. Favorite toggle, buttons, icons

### 8.1 Icon names [V]
Host check (`find /usr/share/icons/Adwaita -iname '*star*'`): `Adwaita/symbolic/status/starred-symbolic.svg`, `non-starred-symbolic.svg`, `semi-starred-symbolic.svg` (+ `-rtl`), and `Adwaita/symbolic/actions/star-new-symbolic.svg`. So `starred-symbolic` (filled) / `non-starred-symbolic` (outline) are the canonical pair in the adwaita-icon-theme that ships inside the GNOME runtime [I: the runtime contains adwaita-icon-theme; not separately listed in this run]. Bazaar instead bundles icon-development-kit icons (`star-outline-rounded-symbolic`, `bookmark-outline-symbolic`, `heart-filled-symbolic`) [V, `bz-window.blp`, `bz-favorite-button.blp`, `bz-favorites-tile.blp`]. GNOME HIG ui-icons.html: reuse GTK/Icon Library icons; libadwaita 1.9.rc itself started to "bundle all used icons not in GTK" [V, NEWS] — **bundle your two star SVGs** under `/<prefix>/icons/scalable/actions/` in the gresource exactly as Cartridges does for its source icons (`<gresource prefix="@PREFIX@/icons/scalable/categories/">`) so they render identically on every icon theme [I].

### 8.2 Toggle pattern [I, built from verified APIs]
`Gtk.ToggleButton favorite_button { styles ["circular", "osd"]; }` overlaid at the tile's top-end corner (Cartridges overlays `Button.circular.osd` via `Gtk.Overlay` + `Gtk.Revealer{transition-type: crossfade}` shown on hover [V, `game.blp`]). Bind `icon-name` through a closure: `icon-name: bind $favorite_icon(template.favorite) as <string>;` returning `"starred-symbolic"`/`"non-starred-symbolic"`; bind `tooltip-text` the same way ("Remove from Favorites"/"Add to Favorites") and give an `accessibility { label: _("Favorite"); }` block (Blueprint `accessibility {}` extension [V]). Do not nest the toggle **inside** the card `Gtk.Button` (button-in-button); put both in a `Gtk.Overlay` as Cartridges/Bazaar do. Alternatively a `Gtk.Button` whose `clicked` flips a model property — the model is the source of truth so the sidebar count and the Favorites grid update through list-model filtering.

### 8.3 `Adw.ButtonContent` [V]
Child of `GtkButton`/`GtkMenuButton`/`AdwSplitButton` with `icon-name`, `label`, `use-underline`, `can-shrink` (1.4); adds `.image-text-button` to the button automatically; HIG header-bars.html: label-only buttons are not auto-flattened in header bars — add an icon with `ButtonContent`. Dailies: "Open in Browser" button on the browser page → `Button { child: Adw.ButtonContent { icon-name: "external-link-symbolic"; label: _("Open Externally"); } }` [I].

### 8.4 Style classes to know [V, style-classes.html]
Buttons `.suggested-action`, `.destructive-action`, `.flat`, `.raised`, `.circular`, `.pill`, `.osd` (`.opaque` deprecated 1.6); `.card` (+ `.activatable`; automatic on a `GtkButton`), `.boxed-list`, `.boxed-list-separate`, `.navigation-sidebar`, `.toolbar`, `.spacer`, `.linked`; typography `.title-1…4`, `.heading`, `.body`, `.caption`, `.caption-heading`, `.monospace`, `.numeric`, `.document` (1.8), `.dimmed` (1.7; `.dim-label` deprecated), colours `.accent/.success/.warning/.error`; `.icon-dropshadow` (icons > 32px), `.lowres-icon`; `.compact` (StatusPage); `.devel` (striped header bar for nightly builds); toggle groups `.flat`, `.round`. **There is no `.badge` class** — Bazaar's "Installed" pill is custom CSS (`small-pill`) [V]; Dailies' difficulty badge therefore needs ~6 lines of CSS using libadwaita colour variables (Appendix A.6).

---

## 9. Remote icons: `Gtk.Picture`, textures, async loading, caching

- `GtkPicture` [V, docs.gtk.org/gtk4/class.Picture.html]: `paintable`, `file`, `alternative-text` (a11y, role IMG), `can-shrink`, `content-fit` (4.8: `GtkContentFit` — `fill`, `contain`, `cover`, `scale-down`), `keep-aspect-ratio` **deprecated 4.8**; `new_for_resource()` for bundled placeholders. For fixed-size icons GTK recommends `GtkImage` (Bazaar's tile uses `Image { pixel-size: 64; paintable: bind …; styles ["icon-dropshadow"] }`) [V].
- `GdkTexture` [V, docs.gtk.org/gdk4/class.Texture.html]: `new_from_bytes` (4.6), `new_from_filename` (4.6), `new_from_file`, `new_from_resource`; `new_for_pixbuf` **deprecated 4.20**; immutable and threadsafe; **"for untrusted image data … use a dedicated image loading framework, e.g. glycin"**.
- **glycin** is in `org.gnome.Platform//51` (`libglycin-gtk4-2.so`, `GlyGtk4-2.typelib`, version 2.2.1) [V]. Bazaar's `BzAsyncTexture` (a `GdkPaintable` GObject) loads via `glycin-gtk4-2`, keeps a process-wide `GHashTable` texture cache keyed by URI with a mutex, and writes a cache file (`cache_into` `GFile`) [V, `bz-async-texture.c/.h`]. Cartridges downloads covers once into its data dir and loads them with `Gdk.Texture.new_from_filename`, with `Gdk.Texture.new_from_resource(... "/library_placeholder.svg")` placeholders and an `Adw.Spinner` overlay while loading [V, `game_cover.py`, `game.blp`].
- Networking: `libsoup-3.0` is in the runtime [V]; Python can use `Gio.File.new_for_uri(url).load_bytes_async()` (GIO HTTP backend) or Soup 3; cache under `GLib.get_user_cache_dir()` (inside Flatpak → `~/.var/app/<APPID>/cache`).

**Recommendation [I]:** a small `DailiesIconCache` GObject: `(url) → Gdk.Paintable`, first returning a bundled placeholder, then: disk cache hit → `Gly.Loader` (glycin, sandboxed decode) → `GdkTexture`; miss → `Gio.File.load_bytes_async` → write to cache → glycin decode → `notify::paintable`. Bind `Gtk.Picture.paintable` to it. Keep icons small (64–96 px) and expose `alternative-text` = game name.

---

## 10. Drag-to-reorder favorites

- `GtkDragSource` [V, docs.gtk.org/gtk4/class.DragSource.html]: event controller; `prepare` returns a `GdkContentProvider` (`gdk_content_provider_new_typed()` / `new_union()`; in PyGObject `Gdk.ContentProvider.new_for_value(GObject.Value(...))`), `drag-begin` → `set_icon(gtk_widget_paintable_new(widget), hot_x, hot_y)`, `drag-end` (delete source for `GDK_ACTION_MOVE`), `drag-cancel`; `actions`, `content`.
- `GtkDropTarget` [V, docs.gtk.org/gtk4/class.DropTarget.html]: `gtk_drop_target_new(GType, GdkDragAction)`, `set_gtypes()`, `preload`, `value`, `current-drop` (4.4), signals `accept`, `enter`, `motion`, `leave`, `drop(value, x, y) → bool`, `reject()`; widget gets `GTK_STATE_FLAG_DROP_ACTIVE` (`:drop(active)` in CSS) while hovered. Bazaar attaches `DropTarget drop_target { actions: copy; accept => $drop_accept_cb(template); drop => $drop_cb(template); }` directly in Blueprint on the window [V, `bz-window.blp`].
- Pattern [I]: in each favourite tile add a `DragSource { actions: move; prepare => $on_drag_prepare(); }` providing the `DailiesGame` GObject (`GType` of your class), and a `DropTarget` with that `GType` + `move` whose `drop` handler computes the target index from the hovered tile and does `store.remove(old); store.insert(new, game)` then persists the ordered list of IDs to GSettings (`as` key). HIG boxed-lists.html requires an accessible alternative: context menu "Move Up / Move Down" (the tile menu is where Cartridges puts Edit/Hide/Remove via `menu game_options` [V]). `AdwSidebar` also accepts drops on items (`drop`, `drop-enter`, `drop-value-loaded`, `drag-motion-activate`) — dropping a tile on "Favorites" is a nice extra [I].

---

## 11. GSettings schema, Meson, bindings

### 11.1 Schema syntax [V, docs.gtk.org/gio/class.Settings.html]
```xml
<schemalist gettext-domain="dailies">
  <enum id="io.github.tim_van_oudheusden.Dailies.BrowserMode">
    <value nick="configured" value="0"/>
    <value nick="builtin" value="1"/>
    <value nick="external" value="2"/>
  </enum>
  <schema id="io.github.tim_van_oudheusden.Dailies" path="/io/github/tim_van_oudheusden/Dailies/">
    <key name="browser-mode" enum="io.github.tim_van_oudheusden.Dailies.BrowserMode">
      <default>'builtin'</default>
      <summary>How game links are opened</summary>
    </key>
    <key name="browser-command" type="s"><default>''</default></key>
    <key name="favorites" type="as"><default>[]</default></key>
    <key name="refresh-interval-hours" type="u"><range min="1" max="168"/><default>24</default></key>
  </schema>
  <schema id="io.github.tim_van_oudheusden.Dailies.State" path="/io/github/tim_van_oudheusden/Dailies/State/">
    <key name="width" type="i"><default>1100</default></key>
    <key name="height" type="i"><default>760</default></key>
    <key name="is-maximized" type="b"><default>false</default></key>
  </schema>
</schemalist>
```
(Enum/flags keys are stored as strings; `g_settings_get_enum()/set_enum()` convert. `<choices>` is the string-key alternative Cartridges uses for `sort-mode` [V]. App-ID form `io.github.<user>.<Project>` with `-` → `_` follows Flathub's GitHub-ID rule [U: not re-fetched in this run — verify against docs.flathub.org before committing].)

### 11.2 Meson [V]
Cartridges `data/meson.build` (reproduced in Appendix C) does: `install_data(configure_file(... '@APP_ID@.gschema.xml'), install_dir: datadir/'glib-2.0/schemas')`, a `test('Validate schema file', glib-compile-schemas, args: ['--strict', '--dry-run', meson.current_source_dir()])`, and at the root `gnome.post_install(glib_compile_schemas: true, gtk_update_icon_cache: true, update_desktop_database: true)`. Meson gnome module docs [V, mesonbuild.com/Gnome-module.html]: `gnome.post_install()` (0.57.0) runs once, skipped when `DESTDIR` is set (Flatpak builder handles it); `gnome.compile_schemas(build_by_default, depend_files)` compiles into the build dir for tests; `gnome.compile_resources(id, xml, gresource_bundle:, dependencies: [blueprints], source_dir:, c_name:, install:, install_dir:)`.

### 11.3 Bindings [V, docs.gtk.org/gio/method.Settings.bind.html]
`g_settings_bind(settings, key, object, property, flags)`; flags `DEFAULT`, `GET`, `SET`, `NO_SENSITIVITY` (otherwise key writability is bound to `sensitive`), `GET_NO_CHANGES`, `INVERT_BOOLEAN`; one binding per property; lifecycle tied to the object; `bind_with_mapping()` for custom conversions. Cartridges binds window geometry: `state_schema.bind("width", win, "default-width", Gio.SettingsBindFlags.DEFAULT)` etc. [V, `main.py`]. For `AdwComboRow:selected` (uint) ↔ an enum key use `bind_with_mapping` in C/Vala; in Python (no closure-mapping binding) either store a `u` key and bind `selected` directly, or connect `notify::selected` ↔ `changed::browser-mode` manually [I].

---

## 12. GNOME HIG rules that bind Dailies [V unless marked]

- **Typography** (hig/guidelines/typography.html): default font Adwaita Sans (Inter build); use style classes not hard-coded sizes; no all-caps, avoid italics; typographic characters: “ ” ’ … × – • and narrow no-break space in "32 GB". Header capitalization for menu items, view titles, buttons; sentence case for descriptions [V menus.html for header caps; sentence-case rule is in writing-style.html — not fetched, [U]].
- **UI icons** (ui-icons.html): 16 px symbolic SVGs, usable at 32/64/128; control has either icon or label (sidebars/view switchers may combine); icon-only buttons must be recognisable (search, menu, back, forward, share), otherwise use text; take icons from GTK/Icon Library; Symbolic Preview for custom ones (2 px strokes, pixel grid).
- **App icon / logo** (app-icons.html): 128×128 canvas with template grid, baseline-aligned, slight top+front perspective (front ≤ 2 detail units), flat colours on flat surfaces, gradients only on curved, no shadows outside the silhouette, palette colours, no text/mascots, unique metaphor tied to the name; mandatory **symbolic variant** in the same SVG; **nightly/Devel variant** (App Icon Preview `org.gnome.design.AppIconPreview` generates it); template `template.svg` in GNOME/HIG-app-icons. Install paths used by Cartridges [V, `data/icons/meson.build`]: `hicolor/scalable/apps/<APPID>.svg` and `hicolor/symbolic/apps/<APPID>-symbolic.svg` (with `.Devel` variants). Metaphor ideas for "Dailies" [I]: a tear-off desk calendar page showing a letter-tile grid (Wordle-like 5-square row) — calendar = daily, tiles = guessing games.
- **Menus** (patterns/controls/menus.html): primary menu button `open-menu-symbolic`, tooltip and accessible label "Main Menu", at the end of the header bar (with a sidebar: above the sidebar list); standard final group **Preferences, Keyboard Shortcuts, Help, About App**; **no Close/Quit** items; header capitalization. Set `MenuButton { primary: true; }` so F10 opens it (Bazaar does) [V, `bz-window.blp`].
- **Keyboard** (reference/keyboard.html): Ctrl+Q quit, Ctrl+W close, F1 help, F9 side pane, F10 menu, Ctrl+? shortcuts, Ctrl+, preferences, Ctrl+F find, Ctrl+R reload, Alt+← / Alt+→ back/forward, Ctrl+L enter location, Ctrl+D add bookmark (→ favourite [I]), Ctrl+N new; avoid reserved system shortcuts (Alt+Tab, Alt+F4…).
- **Header bars** (patterns/containers/header-bars.html): start = main actions (new/add/open/back), centre = title or view switcher, end = menus; few controls; leave drag space; **all primary header-bar controls need tooltips**; buttons flat (auto for icon buttons); use `.spacer` separators rather than linked buttons.
- **Sidebars / view switchers / grids / boxed lists / search / toasts / placeholders**: see §2–§7.
- **Accessibility** (guidelines/accessibility.html): every element needs a short descriptive accessible name; test with high contrast, large text, keyboard only, screen reader, on-screen keyboard. GTK: `accessible-role`, `update_property(LABEL/DESCRIPTION)`, `update_relation(LABELLED_BY/DESCRIBED_BY)` [V iface.Accessible.html lists these methods]; Blueprint `accessibility { label: …; labelled-by: id; described-by: id; }` [V]; Bazaar labels tiles `accessibility { labelled-by: title_label; described-by: description_label; }` and marks decorative images `accessible-role: presentation;` [V].
- **UI styling** (guidelines/ui-styling.html): minimal custom CSS; use libadwaita classes and CSS variables (auto light/dark/HC); default to light + follow system; offer Light/Dark/Follow System if you add a style preference (`AdwStyleManager`); never colour-only information.
- **Adaptive** (guidelines/adaptive.html): 360×294 px minimum for phone-capable; cap content width at large sizes (clamps); breakpoints switch layouts; smooth resizing.

---

## 13. Blueprint: status and syntax essentials

- **Status** [V]: upstream repo `https://gitlab.gnome.org/GNOME/blueprint-compiler`, latest tag `v0.22.2` (meson.build on main says 0.22.1 → 0.22.2 released); NEWS v0.22.0: extern enum types, GList in expressions, Python ≥ 3.9 check; v0.20.0: `--minify`, linter, `Gtk.TryExpression` (`try { a, b }`), `null`, type-checked closures/bindings, libgirepository-based typelib loading, extern class names with ".". Bundled in GNOME SDK 49/50/51 (0.18.0/0.20.4/0.22.2) — so **no Flatpak module needed**; keep the Meson wrap for distro builds.
- **Build integration** [V, setup.rst]:
  ```meson
  blueprints = custom_target('blueprints',
    input: files('gtk/window.blp', ...),
    output: '.',
    command: [find_program('blueprint-compiler'), 'batch-compile', '--minify', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
  )
  gnome.compile_resources(..., dependencies: blueprints)
  ```
  `subprojects/blueprint-compiler.wrap`: `[wrap-git] directory = blueprint-compiler, url = https://gitlab.gnome.org/GNOME/blueprint-compiler.git, revision = main, depth = 1, [provide] program_names = blueprint-compiler`; add `/subprojects/blueprint-compiler` to `.gitignore`. Bazaar pins `find_program('blueprint-compiler', version: '>= 0.20.0')`. Typelibs for every `using` namespace must be present at build time (packaging.rst) — `WebKit-6.0.typelib` is in the SDK [V].
- **Syntax cheatsheet** [V, docs/reference/*.rst + reference apps]: header `using Gtk 4.0; using Adw 1;`; `template $DailiesWindow: Adw.ApplicationWindow { … }`; child types `[top]`, `[start]`, `[end]`, `[title]`, `[overlay]`, `[prefix]`, `[suffix]`, `[sidebar]`; properties `name: value;`, object-valued `content: Adw.ToolbarView { … };`; bindings `prop: bind obj.prop [inverted|bidirectional|sync-create];`, expressions `bind template.item as <$Type>.prop`, closures `bind $fn(args) as <type>`, `try { expr, fallback }`; signals `clicked => $handler(template);` / `… swapped`; `styles ["card"]`; `accessibility { label: _("…"); labelled-by: id; }`; `Adw.Breakpoint { condition ("max-width: 500sp") setters { obj.prop: value; } apply => $cb(); }`; `menu primary_menu { section { item (_("Preferences"), "app.preferences") } }`; `BuilderListItemFactory { template ListItem { child: …bind template.item…; } }`; `StringList { strings [ … ] }`; `Adw.AlertDialog { responses [ cancel: _("Cancel"), ok: _("OK") suggested ] }`; translator comments `// Translators: …`; `C_("context", "str")`.
- Tooling: `blueprint-compiler format`, `lint` (0.20+), `port` (XML → blp), language server (VS Code/GNOME Builder/Kate/Zed) [V NEWS/setup].

---

## 14. Deprecated items to avoid (with versions) [V]

| Deprecated | Since | Use instead |
|---|---|---|
| `AdwLeaflet`, `AdwLeafletPage`, `AdwFlap`, `AdwSqueezer`, `AdwSqueezerPage`, `AdwViewSwitcherTitle` | libadwaita 1.4 | `AdwNavigationSplitView`/`AdwOverlaySplitView`/`AdwNavigationView`, `AdwBreakpoint`, `AdwViewSwitcher` + `AdwViewSwitcherBar` |
| `AdwAboutWindow`, `AdwMessageDialog`, `AdwPreferencesWindow`; `button.opaque` | 1.6 | `AdwAboutDialog`, `AdwAlertDialog`, `AdwPreferencesDialog`; `.suggested-action` with accent override |
| `.dim-label` | 1.7 | `.dimmed` (Cartridges/Bazaar still use `.dim-label`; don't copy that) |
| `style-dark.css`, `style-hc.css`, `style-hc-dark.css` | 1.9 | one `style.css` with `@media (prefers-color-scheme: dark)` / `(prefers-contrast: more)` (Cartridges' `style.css` already does this [V]) |
| `AdwEnumListModel`, `AdwEnumListItem` | 1.10 | `GtkEnumList` (GTK 4.24) |
| `.content`, `.sidebar`, `.app-notification`, `.large-title`, `headerbar.flat` | ≤1.4 | `.boxed-list`, `.navigation-sidebar`, `AdwToastOverlay`, `.title-1`, `AdwToolbarView` |
| `GtkShortcutsWindow`/`GtkShortcutLabel` | GTK 4.18 | `AdwShortcutsDialog`/`AdwShortcutLabel` (1.8) |
| `GtkPicture:keep-aspect-ratio` | GTK 4.8 | `content-fit` |
| `GdkTexture.new_for_pixbuf`, `GtkPicture.new_for_pixbuf` | GTK 4.20 / 4.12 | textures from bytes/file, glycin |
| `GtkDialog`, `GtkInfoBar`, `GtkComboBoxText`, (and GtkTreeView family) | GTK 4.10 | `AdwDialog`/`AdwAlertDialog`, `AdwBanner`, `GtkDropDown`/`AdwComboRow`, `GtkListView`/`GtkGridView` |
| `GtkSpinner` (not deprecated, but) | — | `AdwSpinner` (1.6) for libadwaita look |

---

## 15. In-app browser view (WebKitGTK 6.0)

- API [V, webkitgtk.org/reference/webkitgtk/stable/class.WebView.html, 2.54.1]: `webkit_web_view_new()`, `load_uri()`, `go_back/go_forward/can_go_back/can_go_forward/reload/reload_bypass_cache`, properties `uri`, `title`, `estimated-load-progress` (0–1), `is-loading`, `favicon` (**deprecated 2.54 → `page-icons`**), signals `load-changed` (started/redirected/committed/finished), `decide-policy` (navigation, new-window, response), `create` (popups → return a new view or `NULL`), `settings` (`WebKitSettings`), `network-session` (`WebKitNetworkSession`, 2.40). Namespace in GI/Blueprint: `WebKit 6.0`; pkg-config `webkitgtk-6.0` [I: directory `webkitgtk-6.0` seen in the runtime; `.pc` not checked].
- Sandbox notes [I]: WebKit runs its own web processes; inside Flatpak this works out of the box (Epiphany is a Flatpak). Use a persistent `WebKitNetworkSession` (data dir under `GLib.get_user_data_dir()`) so game sites keep cookies/local storage (streaks!). Handle `decide-policy` to open `NEW_WINDOW_ACTION` in the same view or externally; handle `create` to avoid unexpected popups.
- UI [I]: a dedicated `Adw.NavigationPage` ("browser") pushed onto the main `Adw.NavigationView` (the header bar then shows the back button automatically); header: `[start]` back/forward (`go-previous-symbolic`/`go-next-symbolic`, `sensitive` updated on `load-changed`), reload/stop (`view-refresh-symbolic` / `process-stop-symbolic`), `[title] Adw.WindowTitle { title: bind web_view.title; subtitle: bind web_view.uri; }`, `[end]` "Open Externally" (`Gtk.UriLauncher` — GTK 4.10 [U: not re-fetched]) and a secondary menu (Copy Link, Zoom In/Out, Clear Site Data). A thin `Gtk.ProgressBar.osd` overlaid at the top bound to `estimated-load-progress`, hidden when not loading. Shortcuts: Alt+←/→, Ctrl+R, Ctrl+L (HIG). The skeleton is in Appendix A.4.
- Browser-mode fallbacks [I]: "Default browser" → `Gtk.UriLauncher.launch()` (OpenURI portal, works in sandbox). "Configured browser" (a *specific* host browser) is **not reachable from inside the sandbox** without `--talk-name=org.freedesktop.Flatpak` + `flatpak-spawn --host <cmd> <url>` (Cartridges requests that permission to launch games) — this is a design/permission decision for the architecture doc.

---

## 16. Recommendations for Dailies (consolidated)

1. **Toolchain**: Flatpak on `org.gnome.Platform//51`; Meson + Blueprint (`batch-compile --minify`); Python/PyGObject (like Cartridges) or C (like Bazaar) — either way the UI files are identical. Pin `libadwaita-1 >= 1.9`, `gtk4 >= 4.20`, `blueprint-compiler >= 0.20`.
2. **Window**: `Adw.ApplicationWindow` (360×294 min) → `Adw.ToastOverlay` → `Adw.NavigationView` {library page, browser page} ; library page = `Adw.NavigationSplitView` (sidebar `Adw.Sidebar`: Favorites | This Week: Popular, Trending | Categories…) ; breakpoint `max-width: 500sp` → `collapsed: true; sidebar.mode: page`. Primary menu above the sidebar list (HIG rule with sidebars); search toggle + sort menu on the content header bar.
3. **Content**: `Gtk.GridView` in `Adw.ClampScrollable`; tiles are `Gtk.Button.card` inside a `Gtk.Overlay` with a `Gtk.ToggleButton.circular.osd` star; `Gio.ListStore` + `FilterListModel` + `SortListModel`; `Adw.StatusPage`s for "No Favorites Yet" (`non-starred-symbolic`, description "Tap the star on a game to add it here"), "No Games Found" (`system-search-symbolic`), and offline/no data (`network-offline-symbolic`?) [U icon]. Loading: `Adw.Spinner` 48–64 px.
4. **Settings**: `Adw.PreferencesDialog` with `search-enabled: true`; browser mode `Adw.ComboRow`, command `Adw.EntryRow { show-apply-button: true }`, toggles `Adw.SwitchRow`; bind via `Gio.Settings.bind`; window state in a separate `.State` schema.
5. **About/Shortcuts**: `Adw.AboutDialog.new_from_appdata(resource, VERSION)` with metainfo in the gresource and `<release>` notes; `shortcuts-dialog.ui` with id `shortcuts_dialog` so `app.shortcuts` is automatic; standard accelerators via `set_accels_for_action` (`app.quit` Ctrl+Q, `app.preferences` Ctrl+comma, `win.search` Ctrl+F, `win.toggle-favorite` Ctrl+D, browser Alt+Left/Right, Ctrl+R, Ctrl+L).
6. **Icons**: bundle `starred-symbolic`/`non-starred-symbolic` (and any Icon Library icons you use) under `/io/github/…/icons/scalable/actions/`; app icon per HIG template incl. symbolic + Devel variant; add `.devel` style class to the window in development profile (Cartridges' `profile` option pattern).
7. **Remote icons**: glycin + disk cache + placeholder; never `GdkPixbuf` for untrusted downloads.
8. **Favorites reorder**: `GtkDragSource`/`GtkDropTarget` with a `move` action over the favourites grid, plus "Move Up/Down" menu items for accessibility; persist as an ordered `as` GSettings key (or in the JSON user store).
9. **Styling**: single `style.css` with CSS variables and `@media (prefers-color-scheme: dark)`; no `.dim-label`; custom `.difficulty-badge` using `--accent-bg-color`/`--warning-bg-color`/`--error-bg-color`.
10. **Open design decisions to settle**: (a) whether "configured browser" needs host-spawn permission; (b) `GtkGridView` vs `GtkFlowBox` if manual drag reorder of favourites is a must-have on day one; (c) libadwaita floor 1.9 (AdwSidebar) vs 1.8 (ListBox sidebar) for Hive/native packaging.

---

## Appendix A — Skeleton Blueprint snippets for Dailies

> These are the researcher's compositions **[I]**, written against the Blueprint reference grammar (docs/reference/*.rst, v0.22) and modelled on the verified Cartridges/Bazaar files. They were **not compiled** in this run (no `blueprint-compiler` on the host and the GNOME 51 SDK is not installed locally); run `blueprint-compiler compile` in the SDK before relying on them. App ID placeholder: `io.github.tim_van_oudheusden.Dailies`.

### A.1 `data/gtk/window.blp` — main window with sidebar + grid

```blp
using Gtk 4.0;
using Adw 1;

template $DailiesWindow: Adw.ApplicationWindow {
  title: _("Dailies");
  default-width: 1100;
  default-height: 760;
  width-request: 360;
  height-request: 294;

  Adw.Breakpoint {
    condition ("max-width: 500sp")

    setters {
      split_view.collapsed: true;
      sidebar.mode: page;
      grid_view.max-columns: 2;
    }
  }

  Adw.Breakpoint {
    condition ("max-width: 900sp")

    setters {
      grid_view.max-columns: 3;
    }
  }

  content: Adw.ToastOverlay toast_overlay {
    Adw.NavigationView navigation_view {
      Adw.NavigationPage {
        tag: "library";
        title: _("Dailies");

        Adw.NavigationSplitView split_view {
          min-sidebar-width: 200;
          max-sidebar-width: 280;
          sidebar-width-fraction: 0.22;

          sidebar: Adw.NavigationPage {
            title: _("Dailies");

            Adw.ToolbarView {
              [top]
              Adw.HeaderBar {
                [end]
                MenuButton {
                  primary: true;
                  icon-name: "open-menu-symbolic";
                  tooltip-text: _("Main Menu");
                  menu-model: primary_menu;
                }
              }

              content: Adw.Sidebar sidebar {
                // Handler calls split_view.set_show_content(True) and
                // switches the grid's category filter.
                activated => $on_sidebar_activated(template);

                Adw.SidebarSection {
                  Adw.SidebarItem favorites_item {
                    title: _("Favorites");
                    icon-name: "starred-symbolic";
                  }
                }

                Adw.SidebarSection {
                  title: _("This Week");

                  Adw.SidebarItem {
                    title: _("Popular");
                    icon-name: "emblem-favorite-symbolic";
                  }

                  Adw.SidebarItem {
                    title: _("Trending");
                    icon-name: "view-refresh-symbolic";
                  }
                }

                // Category items are appended at runtime from the data file.
                Adw.SidebarSection categories_section {
                  title: _("Categories");
                }
              };
            }
          };

          content: Adw.NavigationPage content_page {
            title: _("Favorites");

            Adw.ToolbarView {
              [top]
              Adw.HeaderBar header_bar {
                [end]
                MenuButton {
                  icon-name: "view-sort-descending-symbolic";
                  tooltip-text: _("Sort");
                  menu-model: sort_menu;
                }

                [end]
                ToggleButton search_button {
                  icon-name: "system-search-symbolic";
                  tooltip-text: _("Search");
                  action-name: "win.search";
                }
              }

              [top]
              SearchBar search_bar {
                search-mode-enabled: bind search_button.active bidirectional;
                key-capture-widget: split_view;

                Adw.Clamp {
                  maximum-size: 500;
                  tightening-threshold: 500;

                  SearchEntry search_entry {
                    placeholder-text: _("Search games");
                    hexpand: true;
                    search-changed => $on_search_changed(template);
                  }
                }
              }

              content: Stack content_stack {
                transition-type: crossfade;

                StackPage {
                  name: "loading";

                  child: Adw.Spinner {
                    halign: center;
                    valign: center;
                    width-request: 48;
                    height-request: 48;
                  };
                }

                StackPage {
                  name: "grid";

                  child: ScrolledWindow {
                    hscrollbar-policy: never;

                    child: Adw.ClampScrollable {
                      maximum-size: 1400;
                      tightening-threshold: 1200;

                      child: GridView grid_view {
                        min-columns: 1;
                        max-columns: 5;
                        single-click-activate: true;
                        enable-rubberband: false;
                        margin-top: 12;
                        margin-bottom: 12;
                        margin-start: 12;
                        margin-end: 12;
                        activate => $on_game_activated(template);

                        factory: BuilderListItemFactory {
                          template ListItem {
                            activatable: true;
                            child: $DailiesGameTile {
                              game: bind template.item as <$DailiesGame>;
                            };
                          }
                        };
                      };
                    };
                  };
                }

                StackPage {
                  name: "empty-favorites";

                  child: Adw.StatusPage {
                    icon-name: "non-starred-symbolic";
                    title: _("No Favorites Yet");
                    description: _("Press the star on any game to pin it here");

                    Button {
                      label: _("Browse Popular Games");
                      halign: center;
                      action-name: "win.show-popular";

                      styles [
                        "pill",
                        "suggested-action",
                      ]
                    }
                  };
                }

                StackPage {
                  name: "no-results";

                  child: Adw.StatusPage {
                    icon-name: "system-search-symbolic";
                    title: _("No Games Found");
                    description: _("Try a different search");
                  };
                }
              };
            }
          };
        }
      }

      // The in-app browser page is pushed at runtime (see browser-view.blp).
    }
  };
}

menu primary_menu {
  section {
    item {
      label: _("_Refresh Game List");
      action: "app.refresh";
    }
  }

  section {
    item (_("_Preferences"), "app.preferences")
    item (_("_Keyboard Shortcuts"), "app.shortcuts")
    item (_("_About Dailies"), "app.about")
  }
}

menu sort_menu {
  section {
    item {
      label: _("Popularity");
      action: "win.sort-by";
      target: "popularity";
    }

    item {
      label: _("Name");
      action: "win.sort-by";
      target: "name";
    }

    item {
      label: _("Difficulty");
      action: "win.sort-by";
      target: "difficulty";
    }
  }
}
```

### A.2 `data/gtk/game-tile.blp` — tile card (icon, name, favorite star, difficulty badge)

```blp
using Gtk 4.0;
using Adw 1;

template $DailiesGameTile: Overlay {
  // The whole card is the "open" button; the star is an overlay so we never
  // nest a button inside a button.
  child: Button open_button {
    clicked => $on_open_clicked(template);

    accessibility {
      labelled-by: title_label;
      described-by: category_label;
    }

    styles [
      "card",
      "game-tile",
    ]

    child: Box {
      orientation: vertical;
      spacing: 6;
      margin-top: 12;
      margin-bottom: 12;
      margin-start: 12;
      margin-end: 12;

      Picture icon {
        width-request: 64;
        height-request: 64;
        halign: center;
        can-shrink: true;
        content-fit: contain;
        paintable: bind template.game as <$DailiesGame>.icon-paintable;
        alternative-text: bind template.game as <$DailiesGame>.name;

        styles [
          "icon-dropshadow",
        ]
      }

      Label title_label {
        label: bind template.game as <$DailiesGame>.name;
        ellipsize: end;
        xalign: 0;
        margin-top: 6;

        styles [
          "heading",
        ]
      }

      Box {
        spacing: 6;

        Label category_label {
          label: bind template.game as <$DailiesGame>.category;
          ellipsize: end;
          xalign: 0;
          hexpand: true;

          styles [
            "caption",
            "dimmed",
          ]
        }

        Label difficulty_label {
          label: bind template.game as <$DailiesGame>.difficulty-label;
          // CSS classes "difficulty-easy|medium|hard" are toggled from code
          // (Adw.CssClassBinding, libadwaita 1.10, can do this declaratively).
          styles [
            "caption-heading",
            "difficulty-badge",
          ]
        }
      }
    };
  };

  [overlay]
  ToggleButton favorite_button {
    halign: end;
    valign: start;
    margin-top: 6;
    margin-end: 6;
    active: bind template.game as <$DailiesGame>.favorite bidirectional;
    icon-name: bind $favorite_icon_name(favorite_button.active) as <string>;
    tooltip-text: bind $favorite_tooltip(favorite_button.active) as <string>;

    accessibility {
      label: _("Favorite");
    }

    styles [
      "circular",
      "osd",
    ]
  }
}
```

### A.3 `data/gtk/preferences.blp` — preferences dialog (browser mode)

```blp
using Gtk 4.0;
using Adw 1;

template $DailiesPreferencesDialog: Adw.PreferencesDialog {
  search-enabled: true;
  content-width: 640;
  content-height: 560;

  Adw.PreferencesPage {
    name: "general";
    title: _("General");
    icon-name: "preferences-system-symbolic";

    Adw.PreferencesGroup {
      title: _("Opening Games");
      description: _("Dailies tries the options in order: configured browser, built-in browser, then the system browser");

      Adw.ComboRow browser_mode_row {
        title: _("Open Games With");

        model: StringList {
          strings [
            _("Configured Browser"),
            _("Built-in Browser"),
            _("System Browser"),
          ]
        };
      }

      Adw.EntryRow browser_command_row {
        title: _("Browser Command");
        show-apply-button: true;
        input-purpose: terminal;
        apply => $on_browser_command_apply(template);
      }

      Adw.SwitchRow fallback_row {
        title: _("Fall Back to Built-in Browser");
        subtitle: _("Use the built-in browser when the configured browser cannot be started");
      }
    }

    Adw.PreferencesGroup {
      title: _("Library");

      Adw.SwitchRow show_difficulty_row {
        title: _("Show Difficulty Badges");
      }

      Adw.ComboRow refresh_row {
        title: _("Refresh Popularity Data");
        subtitle: _("How often the weekly report is downloaded");

        model: StringList {
          strings [
            _("Daily"),
            _("Weekly"),
            _("Manually"),
          ]
        };
      }
    }

    Adw.PreferencesGroup {
      title: _("Danger Zone");
      separate-rows: true;

      Adw.ButtonRow clear_favorites_row {
        title: _("Clear All Favorites");
        activated => $on_clear_favorites(template);

        styles [
          "destructive-action",
        ]
      }
    }
  }
}
```

Binding (Python) [I, from verified `Gio.Settings.bind` semantics]:
```python
settings.bind("show-difficulty", self.show_difficulty_row, "active", Gio.SettingsBindFlags.DEFAULT)
settings.bind("browser-command", self.browser_command_row, "text", Gio.SettingsBindFlags.DEFAULT)
# enum key <-> ComboRow.selected: map manually (no closure mapping in PyGObject)
MODES = ["configured", "builtin", "external"]
self.browser_mode_row.set_selected(MODES.index(settings.get_string("browser-mode")))
self.browser_mode_row.connect("notify::selected", lambda r, _p: settings.set_string("browser-mode", MODES[r.get_selected()]))
self.browser_command_row.set_visible(self.browser_mode_row.get_selected() == 0)  # and update on notify::selected
```

### A.4 `data/gtk/browser-view.blp` — in-app browser page

```blp
using Gtk 4.0;
using Adw 1;
using WebKit 6.0;

template $DailiesBrowserPage: Adw.NavigationPage {
  tag: "browser";
  title: bind web_view.title;

  Adw.ToolbarView {
    [top]
    Adw.HeaderBar {
      [start]
      Box {
        spacing: 6;

        Button back_button {
          icon-name: "go-previous-symbolic";
          tooltip-text: _("Back");
          action-name: "browser.back";
        }

        Button forward_button {
          icon-name: "go-next-symbolic";
          tooltip-text: _("Forward");
          action-name: "browser.forward";
        }

        Button reload_button {
          icon-name: "view-refresh-symbolic";
          tooltip-text: _("Reload");
          action-name: "browser.reload";
          visible: bind web_view.is-loading inverted;
        }

        Button stop_button {
          icon-name: "process-stop-symbolic";
          tooltip-text: _("Stop");
          action-name: "browser.stop";
          visible: bind web_view.is-loading;
        }
      }

      title-widget: Adw.WindowTitle {
        title: bind web_view.title;
        subtitle: bind web_view.uri;
      };

      [end]
      MenuButton {
        icon-name: "view-more-symbolic";
        tooltip-text: _("Browser Menu");
        menu-model: browser_menu;
      }

      [end]
      Button {
        tooltip-text: _("Open in System Browser");
        action-name: "browser.open-externally";

        child: Adw.ButtonContent {
          icon-name: "external-link-symbolic";
          label: _("Open Externally");
          can-shrink: true;
        };
      }
    }

    content: Overlay {
      [overlay]
      ProgressBar progress_bar {
        valign: start;
        fraction: bind web_view.estimated-load-progress;
        visible: bind web_view.is-loading;

        styles [
          "osd",
        ]
      }

      WebKit.WebView web_view {
        vexpand: true;
        hexpand: true;
        load-changed => $on_load_changed(template);
        decide-policy => $on_decide_policy(template);
        create => $on_create(template);
      }
    };
  }
}

menu browser_menu {
  section {
    item (_("_Copy Link"), "browser.copy-link")
    item (_("Add to _Favorites"), "browser.favorite")
  }

  section {
    item (_("Zoom _In"), "browser.zoom-in")
    item (_("Zoom _Out"), "browser.zoom-out")
    item (_("_Normal Size"), "browser.zoom-reset")
  }
}
```
Notes: back/forward `sensitive` is set in `on_load_changed` via `web_view.can_go_back()`; `external-link-symbolic` must be bundled (Icon Library); `WebKit.WebView` requires `WebKit-6.0.typelib` at Blueprint compile time (present in the GNOME 51 SDK). If you prefer a `WebKitNetworkSession` with persistent storage, construct the view in code with `WebKit.WebView(network_session=...)` and place it into an `Adw.Bin` instead of declaring it in Blueprint.

### A.5 `data/gtk/shortcuts-dialog.blp` (auto-wired by `AdwApplication`)

```blp
using Gtk 4.0;
using Adw 1;

Adw.ShortcutsDialog shortcuts_dialog {
  Adw.ShortcutsSection {
    title: C_("shortcut window", "General");

    Adw.ShortcutsItem { title: C_("shortcut window", "Search"); action-name: "win.search"; }
    Adw.ShortcutsItem { title: C_("shortcut window", "Toggle Favorite"); action-name: "win.toggle-favorite"; }
    Adw.ShortcutsItem { title: C_("shortcut window", "Refresh Game List"); action-name: "app.refresh"; }
    Adw.ShortcutsItem { title: C_("shortcut window", "Preferences"); action-name: "app.preferences"; }
    Adw.ShortcutsItem { title: C_("shortcut window", "Keyboard Shortcuts"); action-name: "app.shortcuts"; }
    Adw.ShortcutsItem { title: C_("shortcut window", "Quit"); action-name: "app.quit"; }
  }

  Adw.ShortcutsSection {
    title: C_("shortcut window", "Browser");

    Adw.ShortcutsItem { title: C_("shortcut window", "Back"); accelerator: "<Alt>Left"; }
    Adw.ShortcutsItem { title: C_("shortcut window", "Forward"); accelerator: "<Alt>Right"; }
    Adw.ShortcutsItem { title: C_("shortcut window", "Reload"); accelerator: "<Control>r"; }
    Adw.ShortcutsItem { title: C_("shortcut window", "Open in System Browser"); accelerator: "<Control><Shift>o"; }
  }
}
```
Gresource: `<file preprocess="xml-stripblanks" alias="shortcuts-dialog.ui">gtk/shortcuts-dialog.ui</file>` (Cartridges' alias trick) [V].

### A.6 `data/gtk/style.css` — minimal custom CSS

```css
/* Difficulty badge (no built-in .badge class in libadwaita) */
.difficulty-badge {
  padding: 1px 8px;
  border-radius: 9999px;
  background-color: var(--accent-bg-color);
  color: var(--accent-fg-color);
}
.difficulty-badge.difficulty-easy   { background-color: var(--success-bg-color); color: var(--success-fg-color); }
.difficulty-badge.difficulty-medium { background-color: var(--warning-bg-color); color: var(--warning-fg-color); }
.difficulty-badge.difficulty-hard   { background-color: var(--error-bg-color);   color: var(--error-fg-color); }

/* Drop highlight while reordering favorites */
.game-tile:drop(active) {
  outline: 2px solid var(--accent-bg-color);
  outline-offset: -2px;
}

@media (prefers-color-scheme: dark) {
  /* overrides if needed; prefer variables so nothing is required here */
}
```
(Variable names `--accent-bg-color`, `--success-bg-color`, `--warning-bg-color`, `--error-bg-color` and their `-fg-` partners are libadwaita named colours — see `named-colors.html` [U: page not re-fetched in this run; Cartridges' `style.css` confirms `--accent-color`/`--accent-bg-color` usage].)

---

## Appendix B — Reproduced reference files (verbatim, for copying)

### B.1 Cartridges `data/gtk/shortcuts-dialog.blp` [V]
```blp
using Gtk 4.0;
using Adw 1;

Adw.ShortcutsDialog shortcuts_dialog {
  Adw.ShortcutsSection {
    title: _("General");

    Adw.ShortcutsItem {
      title: _("Search");
      action-name: "win.toggle_search";
    }

    Adw.ShortcutsItem {
      title: _("Preferences");
      action-name: "app.preferences";
    }

    Adw.ShortcutsItem {
      title: _("Keyboard Shortcuts");
      action-name: "app.shortcuts";
    }

    Adw.ShortcutsItem {
      title: _("Undo");
      action-name: "win.undo";
    }

    Adw.ShortcutsItem {
      title: _("Quit");
      action-name: "app.quit";
    }

    Adw.ShortcutsItem {
      title: _("Toggle Sidebar");
      action-name: "win.show_sidebar";
    }

    Adw.ShortcutsItem {
      title: _("Main Menu");
      action-name: "win.open_menu";
    }
  }

  Adw.ShortcutsSection {
    title: _("Games");

    Adw.ShortcutsItem {
      title: _("Add Game");
      action-name: "app.add_game";
    }

    Adw.ShortcutsItem {
      title: _("Import");
      action-name: "app.import";
    }

    Adw.ShortcutsItem {
      title: _("Show Hidden Games");
      action-name: "win.show_hidden";
    }

    Adw.ShortcutsItem {
      title: _("Remove Game");
      action-name: "app.remove_game_details_view";
    }
  }
}
```

### B.2 Cartridges `data/gtk/game.blp` (tile card) [V]
```blp
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
          margin-start: 6;
          margin-end: 3;
          margin-top: 6;
          margin-bottom: 3;

          styles [
            "circular",
            "osd",
          ]
        }
      }

      [overlay]
      Revealer menu_revealer {
        transition-type: crossfade;
        valign: start;
        halign: end;

        MenuButton menu_button {
          icon-name: "view-more-symbolic";
          margin-start: 3;
          margin-end: 6;
          margin-top: 6;
          margin-bottom: 3;

          styles [
            "circular",
            "osd",
          ]
        }
      }

      Button cover_button {
        name: "cover_button";
        overflow: hidden;

        accessibility {
          labelled-by: title;
        }

        Box {
          orientation: vertical;

          Overlay {
            [overlay]
            Adw.Spinner spinner {
              visible: false;
            }

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
            margin-top: 15;
            margin-bottom: 15;
            margin-start: 12;
            margin-end: 12;
          }
        }

        styles [
          "card",
        ]
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

### B.3 Bazaar `src/bz-all-apps-page.blp` (GridView + breakpoints) [V]
```blp
using Gtk 4.0;
using Adw 1;

template $BzAllAppsPage: Adw.NavigationPage {
  Adw.ToolbarView {
    [top]
    Adw.HeaderBar {}

    content: Adw.BreakpointBin {
      width-request: 360;
      height-request: 100;

      child: ScrolledWindow {
        hexpand: true;
        vexpand: true;
        hscrollbar-policy: never;

        child: Adw.ClampScrollable clamp_scrollable {
          maximum-size: 1500;
          tightening-threshold: 1400;

          child: GridView grid_view {
            styles [
              "search-grid",
            ]

            min-columns: 4;
            max-columns: 4;
            margin-start: 30;
            margin-end: 30;
            enable-rubberband: false;
            single-click-activate: true;

            factory: BuilderListItemFactory {
              template ListItem {
                child: $BzAppTile {
                  group: bind template.item as <$BzEntryGroup>;
                };
              }
            };
          };
        };
      };

      Adw.Breakpoint {
        condition ("max-width: 1300px")

        setters {
          grid_view.min-columns: 3;
          grid_view.max-columns: 3;
        }
      }

      Adw.Breakpoint {
        condition ("max-width: 900px")

        setters {
          grid_view.min-columns: 2;
          grid_view.max-columns: 2;
        }
      }

      Adw.Breakpoint {
        condition ("max-width: 700px")

        setters {
          grid_view.margin-start: 3;
          grid_view.margin-end: 3;
          grid_view.min-columns: 1;
          grid_view.max-columns: 1;
        }
      }
    };
  }
}
```

### B.4 Bazaar `src/bz-favorite-button.blp` [V]
```blp
using Gtk 4.0;
using Adw 1;

template $BzFavoriteButton: Button {
  styles [
    "small-pill",
    "suggested-action",
    "favorite",
  ]
  margin-top: 8;
  valign: start;
  halign: start;
  has-tooltip: true;
  tooltip-text: _("Favorite Count");
  visible: bind template.entry as <$BzEntry>.is-flathub;
  clicked => $button_clicked_cb() swapped;

  child: Stack stack {
    transition-type: crossfade;

    StackPage {
      name: "content";
      child: Box box {
        Image icon {
          icon-name: "bookmark-outline-symbolic";
        }

        Revealer count_revealer {
          reveal-child: bind $is_positive(template.entry as <$BzEntry>.favorites-count) as <bool>;
          transition-type: slide_left;

          child: Label count_label {
            margin-start: 4;
            label: bind $format_favorites_count(template.entry as <$BzEntry>.favorites-count) as <string>;
          };
        }
      };
    }

    StackPage {
      name: "spinner";
      child: Adw.Spinner {
        halign: center;
        width-request: 16;
      };
    }
  };
}
```

### B.5 Cartridges `data/gtk/style.css` [V]
```css
:root {
  --accent-color: var(--purple-5);
  --accent-bg-color: var(--purple-3);
}

.no-hover > flowboxchild:hover {
  background-color: transparent;
}

#details_view {
  background-color: white;
}

#details_view_play_button {
  color: white;
  background-color: rgba(0, 0, 0, 0.8);
}

@media (prefers-color-scheme: dark) {
  :root {
    --accent-color: var(--purple-1);
    --accent-bg-color: var(--purple-4);
  }

  #details_view {
    background-color: black;
  }

  #details_view_play_button {
    color: rgba(0, 0, 0, 0.8);
    background-color: white;
  }
}
```

---

## Appendix C — Cartridges Meson/GResource/schema scaffolding (verbatim) [V]

### C.1 `data/meson.build`
```meson
blueprints = custom_target(
  'blueprints',
  input: files(
    'gtk/details-dialog.blp',
    'gtk/game.blp',
    'gtk/preferences.blp',
    'gtk/shortcuts-dialog.blp',
    'gtk/window.blp',
  ),
  output: '.',
  command: [
    find_program('blueprint-compiler'),
    'batch-compile',
    '@OUTPUT@',
    '@CURRENT_SOURCE_DIR@',
    '@INPUT@',
  ],
)

if host_machine.system() == 'windows'
  desktop_file = configure_file(
    input: 'page.kramo.Cartridges.desktop.in',
    output: app_id + '.desktop.in',
    configuration: conf,
    install: true,
    install_dir: join_paths(get_option('datadir'), 'applications'),
  )
else
  desktop_file = i18n.merge_file(
    input: configure_file(
      input: 'page.kramo.Cartridges.desktop.in',
      output: app_id + '.desktop.in',
      configuration: conf,
    ),
    output: app_id + '.desktop',
    type: 'desktop',
    po_dir: '../po',
    install: true,
    install_dir: join_paths(get_option('datadir'), 'applications'),
  )
endif

if host_machine.system() != 'windows'
  desktop_utils = find_program('desktop-file-validate', required: false)
  if desktop_utils.found()
    test('Validate desktop file', desktop_utils, args: [desktop_file])
  endif
endif

if host_machine.system() == 'windows'
  appstream_file = configure_file(
    input: 'page.kramo.Cartridges.metainfo.xml.in',
    output: app_id + '.metainfo.xml',
    configuration: conf,
    install: true,
    install_dir: join_paths(get_option('datadir'), 'metainfo'),
  )
else
  appstream_file = i18n.merge_file(
    input: configure_file(
      input: 'page.kramo.Cartridges.metainfo.xml.in',
      output: app_id + '.metainfo.xml.in',
      configuration: conf,
    ),
    output: app_id + '.metainfo.xml',
    po_dir: '../po',
    install: true,
    install_dir: join_paths(get_option('datadir'), 'metainfo'),
  )
endif

gnome.compile_resources(
  'cartridges',
  configure_file(
    input: 'cartridges.gresource.xml.in',
    output: 'cartridges.gresource.xml',
    configuration: conf,
  ),
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: [blueprints, appstream_file],
)

if host_machine.system() != 'windows'
  appstreamcli = find_program('appstreamcli', required: false)
  if appstreamcli.found()
    test(
      'Validate appstream file',
      appstreamcli,
      args: ['validate', '--no-net', '--explain', appstream_file],
      workdir: meson.current_build_dir(),
    )
  endif
endif

install_data(
  configure_file(
    input: 'page.kramo.Cartridges.gschema.xml.in',
    output: app_id + '.gschema.xml',
    configuration: conf,
  ),
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas'),
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test(
    'Validate schema file',
    compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()],
  )
endif

subdir('icons')
```

### C.2 Root `meson.build` (profile/app-id/post_install excerpt)
```meson
project('cartridges', version: '2.13.1', meson_version: '>= 0.59.0',
  default_options: ['warning_level=2', 'werror=false'])

dependency('gtk4', version: '>= 4.15.0')
dependency('libadwaita-1', version: '>= 1.6.beta')

profile = get_option('profile')
if profile == 'development'
  app_id = 'page.kramo.Cartridges.Devel'
  prefix = '/page/kramo/Cartridges/Devel'
elif profile == 'release'
  app_id = 'page.kramo.Cartridges'
  prefix = '/page/kramo/Cartridges'
endif

conf = configuration_data()
conf.set('APP_ID', app_id)
conf.set('PREFIX', prefix)
conf.set('VERSION', meson.project_version())
conf.set('PROFILE', profile)
# ...
gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
```

### C.3 `data/cartridges.gresource.xml.in`
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
  <file alias="bottles-source-symbolic.svg">icons/sources/bottles-source-symbolic.svg</file>
  <!-- ... more bundled symbolic icons ... -->
  </gresource>
</gresources>
```

### C.4 `data/icons/meson.build`
```meson
scalable_dir = join_paths('hicolor', 'scalable', 'apps')
install_data(
  join_paths(scalable_dir, ('@0@.svg').format(app_id)),
  install_dir: join_paths(get_option('datadir'), 'icons', scalable_dir),
)

symbolic_dir = join_paths('hicolor', 'symbolic', 'apps')
install_data(
  join_paths(symbolic_dir, ('@0@-symbolic.svg').format(app_id)),
  install_dir: join_paths(get_option('datadir'), 'icons', symbolic_dir),
)
```

### C.5 gnome-build-meta `gnome-51/elements/sdk/blueprint-compiler.bst` [V]
```yaml
kind: meson

sources:
- kind: tar
  url: gnome_downloads:blueprint-compiler/0.22/blueprint-compiler-0.22.2.tar.xz
  ref: 231d72efbac931c235ac3e022fe94982095c20d88721d9a8dcf60152f2017e07

build-depends:
- (@): include/gcc-for-recc.yml
- buildsystems/meson.bst

depends:
- sdk/pygobject.bst
- freedesktop-sdk.bst:components/python3.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
```
(gnome-49 pins `blueprint-compiler-0.18.0.tar.xz`; gnome-50 pins `0.20.4`.)

---

## Sources

Libadwaita documentation (gnome.pages.gitlab.gnome.org/libadwaita/doc/):
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/ (index, 1.11.alpha; deprecated class list)
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/ (1.10.0)
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.NavigationSplitView.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.OverlaySplitView.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Sidebar.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.BreakpointBin.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Breakpoint.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/adaptive-layouts.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ViewSwitcher.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.InlineViewSwitcher.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ToggleGroup.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.StatusPage.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Spinner.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Toast.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/property.Toast.timeout.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.PreferencesDialog.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ComboRow.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.SwitchRow.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.EntryRow.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ButtonContent.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Clamp.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.WrapBox.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.AboutDialog.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/ctor.AboutDialog.new_from_appdata.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ShortcutsDialog.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Dialog.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/migrating-to-adaptive-dialogs.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Application.html (automatic resources)
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/style-classes.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/boxed-lists.html
- libadwaita NEWS (git clone `https://gitlab.gnome.org/GNOME/libadwaita.git`, commit 0531b4c, 2026-10-12; tags 1.8.8, 1.9.4, 1.10.0)

GTK / GLib documentation:
- https://docs.gtk.org/gtk4/class.GridView.html , https://docs.gtk.org/gtk4/property.GridView.max-columns.html
- https://docs.gtk.org/gtk4/class.FlowBox.html
- https://docs.gtk.org/gtk4/class.SearchBar.html , https://docs.gtk.org/gtk4/class.SearchEntry.html
- https://docs.gtk.org/gtk4/class.ShortcutsWindow.html (deprecated 4.18)
- https://docs.gtk.org/gtk4/drag-and-drop.html , https://docs.gtk.org/gtk4/class.DragSource.html , https://docs.gtk.org/gtk4/class.DropTarget.html
- https://docs.gtk.org/gtk4/class.Picture.html , https://docs.gtk.org/gdk4/class.Texture.html
- https://docs.gtk.org/gtk4/iface.Accessible.html , https://docs.gtk.org/gtk4/class.Builder.html
- https://docs.gtk.org/gio/class.Settings.html , https://docs.gtk.org/gio/method.Settings.bind.html
- https://mesonbuild.com/Gnome-module.html

GNOME HIG (developer.gnome.org/hig/):
- https://developer.gnome.org/hig/ (index)
- https://developer.gnome.org/hig/guidelines/typography.html
- https://developer.gnome.org/hig/guidelines/ui-icons.html
- https://developer.gnome.org/hig/guidelines/app-icons.html
- https://developer.gnome.org/hig/guidelines/accessibility.html
- https://developer.gnome.org/hig/guidelines/adaptive.html
- https://developer.gnome.org/hig/guidelines/ui-styling.html
- https://developer.gnome.org/hig/patterns/controls/menus.html
- https://developer.gnome.org/hig/patterns/containers/header-bars.html
- https://developer.gnome.org/hig/patterns/containers/grid-views.html
- https://developer.gnome.org/hig/patterns/containers/boxed-lists.html
- https://developer.gnome.org/hig/patterns/nav/sidebars.html
- https://developer.gnome.org/hig/patterns/nav/view-switchers.html
- https://developer.gnome.org/hig/patterns/nav/search.html
- https://developer.gnome.org/hig/patterns/feedback/toasts.html
- https://developer.gnome.org/hig/patterns/feedback/placeholders.html
- https://developer.gnome.org/hig/reference/keyboard.html

Blueprint:
- git clone `https://gitlab.gnome.org/GNOME/blueprint-compiler.git` (commit 8eca521, 2026-09-03; meson version 0.22.1; tags up to v0.22.2): `NEWS.md`, `docs/setup.rst`, `docs/packaging.rst`, `docs/reference/extensions.rst`, `docs/reference/expressions.rst`
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-49/elements/sdk/blueprint-compiler.bst (0.18.0)
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-50/elements/sdk/blueprint-compiler.bst (0.20.4)
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/blueprint-compiler.bst (0.22.2)
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/issues/806 (SDK inclusion request)

Runtime contents / versions:
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/gtk.bst (gtk-4.24.0)
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/libadwaita.bst (libadwaita-1.10.0)
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/webkitgtk-6.0.bst and webkitgtk.inc (webkitgtk-2.54.1)
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/glycin.inc (glycin-2.2.1)
- Local: `flatpak run --user --command=sh org.gnome.Platform//51 -c 'ls /usr/lib/x86_64-linux-gnu …'` (libwebkitgtk-6.0.so.4, libglycin-gtk4-2.so, WebKit-6.0.typelib, GlyGtk4-2.typelib, Adw-1.typelib)
- Local: `flatpak remote-info --user flathub org.gnome.Sdk//51` (Subject "Build of the GNOME Runtime from: 51.0-14-ga554d8085", Date 2026-10-14)
- Local: `find /usr/share/icons/Adwaita -iname '*star*'` (starred-symbolic.svg, non-starred-symbolic.svg, semi-starred-symbolic.svg, star-new-symbolic.svg)
- https://webkitgtk.org/reference/webkitgtk/stable/class.WebView.html (WebKit 6.0 API, 2.54.1)

Release news (secondary):
- https://www.phoronix.com/news/libadwaita-1.8-Released (2025-09-13) ; https://www.phoronix.com/news/GTK-4.24-Released (2026-09-12)
- https://discourse.gnome.org/t/gnome-51-released/38820 ; https://discourse.flathub.org/t/gnome-runtime-version-51-will-drop-gcr-3-and-libhandy-modules/12240
- https://nyaa.place/blog/libadwaita-1-8 (maintainer blog on AdwShortcutsDialog)

Reference applications (git clones, read-only):
- https://github.com/kra-mo/cartridges (commit d56323e, 2026-09-03; v2.13.1): `meson.build`, `data/meson.build`, `data/cartridges.gresource.xml.in`, `data/page.kramo.Cartridges.gschema.xml.in`, `data/gtk/window.blp`, `data/gtk/game.blp`, `data/gtk/preferences.blp`, `data/gtk/shortcuts-dialog.blp`, `data/gtk/style.css`, `data/icons/meson.build`, `cartridges/main.py`, `cartridges/window.py`, `cartridges/game_cover.py`, `build-aux/flatpak/page.kramo.Cartridges.Devel.json`
- https://github.com/bazaar-org/bazaar (commit 3d347d5, 2026-08-18): `src/bz-window.blp`, `src/bz-app-tile.blp`, `src/bz-all-apps-page.blp`, `src/bz-favorite-button.blp`, `src/bz-favorites-tile.blp`, `src/bz-search-bar.blp`, `src/bz-preferences-dialog.blp`, `src/shortcuts-dialog.blp`, `src/bz-async-texture.[ch]`, `src/meson.build`, `build-aux/flatpak/io.github.kolunmi.Bazaar.json`

## Open questions / not verified
1. Flathub app-ID form for a GitHub project (`io.github.tim_van_oudheusden.Dailies`) — re-check docs.flathub.org requirements before scaffolding.
2. `GtkUriLauncher` (GTK 4.10) and libadwaita `named-colors.html` variable names were used from memory, not re-fetched.
3. Whether a "configured (specific) browser" can be launched from the sandbox without `--talk-name=org.freedesktop.Flatpak` / `flatpak-spawn --host` — design decision required.
4. The Blueprint skeletons were not compiled (no blueprint-compiler on host; SDK 51 not installed). Compile inside `org.gnome.Sdk//51` before adoption.
5. Exact GTK versions bundled in GNOME 49/50 runtimes (4.20/4.22) are inferred from release cadence, not fetched.
6. `GtkSearchEntry:search-delay` default and `GtkGridView:min-columns` default are not stated on the docs pages fetched.
7. HIG writing-style page (sentence-case rules) and the libadwaita `AdwSpinnerPaintable` page were not fetched.
