---
key: 75
title: feat(ui): reorder favourites (drag-and-drop + Move up/down)
type: Feature
labels: milestone::M5, type::feature, priority::low, app
parent: 7
blocked_by: 43
---
> **Risk tier:** medium · **Size:** M

## Why

Favorites show insertion order in the MVP. The HIG requires drag-reorder **and** an accessible alternative (Move Up/Down) together, so both ship in one change.

## Tasks

- [ ] Tile context menu (right-click, long-press, Menu key) in the Favorites section: **Move Up**, **Move Down**, **Move to Top**, *separator*, **Remove from Favorites**
- [ ] Drag-and-drop in the Favorites section: a `Gtk.DragSource` on the tile (`prepare` → `Gdk.ContentProvider` with the game id) and a `Gtk.DropTarget` (`GType str`, `Gdk.DragAction.MOVE`) on the tiles. Show a drop indicator
- [ ] `Favorites.move(id, new_index)` (#38) rewrites the `favorites` `as` key once per drop
- [ ] `GridView` vs `FlowBox`: reordering in a model-driven `GridView` is harder than in a `FlowBox` ([`libadwaita-ui-patterns.md` §3, §10](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)). Prototype in the GridView first; if it's unworkable, document the alternative before switching the Favorites section to a FlowBox
- [ ] Keyboard: Ctrl+Up / Ctrl+Down on a focused favourite. Add them to the Shortcuts dialog

## Acceptance criteria

- [ ] Order changes persist across restarts
- [ ] The whole flow is possible with the keyboard alone and with a screen reader

## References

- [`mvp-first.md` §4.5, §16 (M5)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`libadwaita-ui-patterns.md` §10](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
