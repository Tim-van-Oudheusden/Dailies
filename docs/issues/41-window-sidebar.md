---
key: 41
title: feat(ui): main window shell and sidebar (Favorites, This Week, Categories)
type: Feature
labels: milestone::M1, type::feature, priority::high, app
parent: 3
blocked_by: 19, 24, 38
---
> **Risk tier:** medium · **Size:** M · **Brief:** "Categorised DLEs. Weekly changing categories: Popular, Trending." and "Top-level category is always Favorites."

## Structure (`data/ui/window.blp`, `dailies/window.py`, `dailies/ui/library.py`)

Start from the window skeleton that #19 compiled (`libadwaita-ui-patterns.md` Appendix A.1).

```text
Adw.ApplicationWindow  (default 1100×760, width-request 360, height-request 294)
└─ Adw.ToastOverlay
   └─ Adw.NavigationView
      ├─ page "library": Adw.NavigationSplitView
      │     min-sidebar-width 200, max-sidebar-width 280, sidebar-width-fraction 0.22
      │     sidebar → Adw.ToolbarView { header: Adw.HeaderBar [end: primary MenuButton]; content: Adw.Sidebar }
      │     content → (grid page, #42)
      └─ page "browser": pushed at runtime (#46)
Adw.Breakpoint max-width: 500sp → split_view.collapsed = true, sidebar.mode = page, grid_view.max-columns = 2
Adw.Breakpoint max-width: 900sp → grid_view.max-columns = 3
```

## Sidebar (`Adw.Sidebar`, libadwaita ≥ 1.9)

1. **Title-less section:** **Favorites** (`starred-symbolic`). It is always first and is the default selection.
2. **"This Week":** **Popular** (`emblem-favorite-symbolic`) and **Trending** (`dailies-trending-symbolic` from #40). The section shows a subtitle widget "Week 2026-W42" from `popularity.json`. When `now > valid_until` it reads "Week 2026-W42 (as of 12 Oct)"; the shelves are still shown.
3. **"Categories":** the ten categories, appended at startup from `Category`, each with its glyph. **Categories with zero active games are hidden** and reappear after a refresh adds one.

- `activated` → set the `SectionFilter` section (#42), update the content page title, then call `split_view.set_show_content(True)` so a tap navigates when collapsed
- Restore the selection from `State.last-section` and save it on change
- If #19 found `Adw.Sidebar` unusable from Python, use the documented fallback: `Gtk.ListBox` with the `.navigation-sidebar` style (Cartridges `main`)

## Primary menu

`Gtk.MenuButton` with `icon-name: open-menu-symbolic`, `primary: true`, tooltip "Main Menu", placed **in the sidebar header bar** per the HIG. Menu:

- Refresh Game List (`app.refresh`)
- *(separator)*
- Preferences (`app.preferences`)
- Keyboard Shortcuts (`app.shortcuts`)
- About Dailies (`app.about`)

There is **no Quit** item; the actions themselves come from #48.

## Window state

Bind `width`, `height` and `is-maximized` (`State` schema) to `default-width`, `default-height` and `maximized` with `Gio.Settings.bind`, as Cartridges does.

## Never use (deprecated)

`AdwLeaflet`, `AdwFlap`, `AdwViewSwitcherTitle`, the `.dim-label` class (use `.dimmed`), `style-dark.css`, `GtkShortcutsWindow`.

## Acceptance criteria

- [ ] On first launch, Favorites is selected and appears above everything else
- [ ] At 360 px width the split view collapses; tapping a section navigates to the content, and the back button returns to the sidebar
- [ ] The "This Week" subtitle shows the ISO week from `popularity.json`, and the "(as of …)" variant shows when stale. Test the stale case with a fixture whose `valid_until` has passed
- [ ] Window size and the last section persist across restarts
- [ ] F10 opens the primary menu

## References

- [`mvp-first.md` §4.1, §4.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`libadwaita-ui-patterns.md` §2, §12, §14, Appendix A.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
- [`cartridges.md` §5.1, §5.3, Appendix C.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)
