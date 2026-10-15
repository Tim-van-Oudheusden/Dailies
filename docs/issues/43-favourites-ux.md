---
key: 43
title: feat(ui): favourite star toggle, Favorites section and undo
type: Feature
labels: milestone::M1, type::feature, priority::high, app
parent: 3
blocked_by: 38, 42
---
> **Risk tier:** medium · **Size:** S · **Brief:** "Favorite button." / "Top-level category is always Favorites."

## Behaviour

- **Star toggle** (the overlay `Gtk.ToggleButton` on each tile, from #42):
  - `icon-name` bound to `favorite`: `starred-symbolic` when on, `non-starred-symbolic` when off
  - tooltip "Add to Favorites" / "Remove from Favorites"
  - `accessibility { label: _("Favorite"); }`
  - **always visible**, not hover-only, so touch and keyboard users can reach it
- Toggling calls `Favorites.toggle(id)` (#38), which emits `changed(id)`. Then `GameObject.favorite` flips and `SectionFilter` + `SectionSorter` are notified
- **Undo:** on removal **only**, show the toast "Removed from Favorites" with an "Undo" button. Undo restores the original position with `Favorites.add(id, index)`. Adding shows no toast (pattern from [`cartridges.md` §7, Appendix C.7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md))
- **Ctrl+D** toggles the favourite on the focused tile. Register it as `win.toggle-favorite` and list it in the Shortcuts dialog (#48)
- **Order:** Favorites shows insertion order, newest last. Move up/down and drag-reorder are #75 (the HIG requires both together)
- **Unavailable favourites:** if the catalog entry's `status` becomes `broken` or `retired`, the tile **stays** in Favorites with an "Unavailable" pill. Activating it opens a toast "This game is no longer available" with the action "Remove from Favorites" instead of opening the URL
- **Privacy:** no account, no sync; nothing leaves the device

## Acceptance criteria

- [ ] Starring a game in any section makes it appear in Favorites immediately; un-starring from Favorites removes it, and Undo puts it back in the same place
- [ ] Favourites survive an app restart and an app update (GSettings keyfile)
- [ ] With a fixture that marks a favourited game `broken`, the tile shows "Unavailable" and the remove action works
- [ ] Keyboard only: Tab to a tile, then Ctrl+D toggles it; the star button is reachable with Tab and activates with Space

## References

- [`mvp-first.md` §4.3 (star, undo), §4.5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`libadwaita-ui-patterns.md` §8, §10](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
- [`data-pipeline.md` §2.3 (soft delete)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
