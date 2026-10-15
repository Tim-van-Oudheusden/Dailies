---
key: 44
title: feat(ui): search bar and folded search across the current section
type: Feature
labels: milestone::M1, type::feature, priority::medium, app
parent: 3
blocked_by: 37, 42
---
> **Risk tier:** medium · **Size:** S

## Behaviour

- `Gtk.SearchBar` under the content header bar. Its `Gtk.SearchEntry` sits inside an `Adw.Clamp` (`maximum-size 500`)
- `key-capture-widget: split_view`, so typing anywhere in the library starts a search. Call `connect_entry` as well
- Search `Gtk.ToggleButton` in the header (`[end]`), bidirectionally bound to `search-mode-enabled`
- **Ctrl+F** is an app/window action (`win.search`); **Escape** closes the bar and clears the query
- `search-changed` sets `SearchFilter.text` (#42). Matching is `core.search.matches` (#37): case- and accent-folded substring over name, description, tags and the category label
- **The query persists when switching sections** (the HIG says search is global across views), and the result set is filtered by the current section
- When nothing matches, the stack shows the `no-results` page (#42)
- Fuzzy matching is out of scope (#82)

## Acceptance criteria

- [ ] Typing "pokedle" with the library focused opens the search bar and finds "Pokédle"
- [ ] Switching from Words to Geography keeps the query and re-filters
- [ ] Escape closes the bar and restores the full section
- [ ] Ctrl+F appears in the Shortcuts dialog (#48)

## References

- [`mvp-first.md` §4.3 (header), §4.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`libadwaita-ui-patterns.md` §7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
