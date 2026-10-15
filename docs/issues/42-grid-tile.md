---
key: 42
title: feat(ui): game grid, tile card, section filter/sorter and empty states
type: Feature
labels: milestone::M1, type::feature, priority::high, app
parent: 3
blocked_by: 39, 40, 41
---
> **Risk tier:** medium · **Size:** L (split into two PRs if needed: model+filters, then tile+CSS)

## Model pipeline

```text
Gio.ListStore(GameObject)  (#39)
  → Gtk.FilterListModel(Gtk.EveryFilter[SectionFilter, SearchFilter, (LanguageFilter #64)])
  → Gtk.SortListModel(SectionSorter)
  → Gtk.NoSelection
  → Gtk.GridView
```

### `dailies/ui/game_object.py`
`GameObject(GObject.Object)` with the properties `game` (the frozen `Game` dataclass, held as a Python object property), `name`, `category-label`, `difficulty-label`, `favorite: bool`, `popular-rank: int`, `trending-rank: int` (0 = not on the shelf) and `available: bool` (`status == active`). These are what Blueprint bindings and filters use.

### `dailies/ui/filters.py`
- `SectionFilter(Gtk.Filter)` takes a `section` of `favorites`, `popular`, `trending` or a category id:
  - Favorites: `favorite` is true; broken/retired favourites are **kept**
  - Popular/Trending: rank > 0
  - Categories: category matches and the game is available
- `SearchFilter(Gtk.Filter)`: `text` property, delegates to `core.search.matches` (#44 wires the UI)
- On a change, call `filter.changed(Gtk.FilterChange.DIFFERENT)` (or `LESS_STRICT`/`MORE_STRICT` when the direction is known)
- `SectionSorter(Gtk.Sorter)`:
  - Popular/Trending: by shelf rank
  - Favorites: by favourite order
  - Categories: by name
  - When `sort-mode` (GSettings) is `name` or `difficulty`, that overrides the section default

Pattern from Cartridges `rewrite` ([`cartridges.md` §5.3, §7, Appendix C.6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)).

## Grid (content page)

`Adw.ToolbarView`:

- Header bar with `[end]` a sort `Gtk.MenuButton` (Default / Name / Difficulty, a stateful `win.sort-mode` action bound to GSettings) and `[end]` a search `Gtk.ToggleButton` (#44)
- Body is a `Gtk.Stack` (crossfade) with pages `grid`, `empty-favorites`, `no-results`, `empty-section`
- `grid`: `Gtk.ScrolledWindow` → `Adw.ClampScrollable` (`maximum-size 1400`, `tightening-threshold 1200`) → `Gtk.GridView` (`min-columns 1`, `max-columns 5`, `single-click-activate true`, `enable-rubberband false`)
- `Gtk.BuilderListItemFactory` whose child is `$DailiesGameTile { game: bind template.item as <$DailiesGameObject>; }`
- CSS reset from Cartridges: `#grid > child { padding: 0; background: none; outline: none; box-shadow: none; }`

## Tile (`data/ui/game-tile.blp`, `dailies/ui/tile.py`)

`GameTile(Gtk.Overlay)`. **Never put a button inside a button.**

- **Child:** a `Gtk.Button` with styles `["card", "game-tile"]` containing:
  - a 64 px category glyph in a rounded square tinted per category (CSS classes `cat-words` … `cat-sports`, built from libadwaita colour variables so light, dark and high-contrast follow automatically)
  - the game name (`heading`, ellipsised)
  - a caption "Geography · Medium" (`caption`, `dimmed`)
  - a **difficulty pill** `.difficulty-badge`: about 6 lines of CSS using `--success-bg-color` / `--warning-bg-color` / `--error-bg-color`. It must carry **text**, not just colour, because the HIG forbids colour-only information
  - for unavailable favourites: an "Unavailable" pill (#43)
- **`[overlay]` top-end:** a `Gtk.ToggleButton` with styles `["circular", "osd"]`. It is wired up in #43, but placed here
- **Accessibility:** `accessibility { labelled-by: title; described-by: caption; }` on the card

Activating a tile (click or Enter) calls `opener.open(game)` (#45). Until #45 lands, log the URL.

## Empty states (`Adw.StatusPage`)

| Page | Icon | Title | Description | Action |
|---|---|---|---|---|
| `empty-favorites` | `non-starred-symbolic` | No Favorites Yet | Press the star on any game to pin it here | Pill button "Browse Popular Games" → `win.show-section('popular')` |
| `no-results` | `system-search-symbolic` | No Games Found | Try a different search | — |
| `empty-section` | category glyph | Nothing Here Yet | — | Pill "Suggest a game on GitHub" → opens the new-game issue form **externally** (always `Gtk.UriLauncher`, never in-app) |

## Acceptance criteria

- [ ] Each sidebar section shows the right games in the right order (Popular in `popular[]` order)
- [ ] Changing the sort menu re-sorts immediately and persists
- [ ] Each empty-state page appears in its case
- [ ] Orca reads "Worldle, Geography · Easy" (name plus caption) on a focused tile
- [ ] No horizontal scrolling at 360 px; columns follow the breakpoints (2 at ≤ 500sp, 3 at ≤ 900sp, up to 5)
- [ ] The tile looks right in light, dark and high-contrast (screenshots in the PR)

## References

- [`mvp-first.md` §3.1 (game_object, filters, tile rows), §4.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`libadwaita-ui-patterns.md` §3, §4, §8.2, §8.4, Appendix A.2, A.6, B.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
- [`bazaar.md` §4.3, §12.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/bazaar.md)
