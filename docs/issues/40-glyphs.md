---
key: 40
title: design: category glyphs and bundled symbolic icons
type: Task
labels: milestone::M1, type::task, priority::medium, app
parent: 3
blocked_by: 24
---
> **Risk tier:** low · **Size:** S

## Why

The MVP shows no third-party icons: no favicons and no game logos, to avoid trademark and redistribution issues (decision #17). Each tile shows a **category glyph** in a tinted rounded square instead, and the sidebar uses the same glyphs.

## Deliverables (bundled in the gresource, under the app's icon resource path)

| Icon | Use |
|---|---|
| `dailies-category-words-symbolic.svg` | Words |
| `dailies-category-geography-symbolic.svg` | Geography |
| `dailies-category-music-symbolic.svg` | Music |
| `dailies-category-movies-tv-symbolic.svg` | Movies & TV |
| `dailies-category-video-games-symbolic.svg` | Video Games |
| `dailies-category-numbers-logic-symbolic.svg` | Numbers & Logic |
| `dailies-category-trivia-symbolic.svg` | Trivia |
| `dailies-category-visual-symbolic.svg` | Pictures & Colors |
| `dailies-category-food-symbolic.svg` | Food |
| `dailies-category-sports-symbolic.svg` | Sports |
| `starred-symbolic.svg`, `non-starred-symbolic.svg` | Favourite toggle and the Favorites sidebar item. They exist in Adwaita (`symbolic/status`); bundle copies so the look doesn't depend on the icon theme |
| `dailies-trending-symbolic.svg` | Sidebar "Trending". Replaces the `view-refresh-symbolic` placeholder |

## Tasks

- [ ] Take each glyph from the **Icon Development Kit (CC0)** where a suitable one exists. Otherwise draw it at 16 px with 2 px strokes on the pixel grid
- [ ] Register the resource path so `Gtk.IconTheme` finds the icons (`<gresource prefix="@PREFIX@/icons/scalable/actions">`, or `Gtk.IconTheme.add_resource_path`)
- [ ] Record each icon's source and licence in `data/icons/categories/README.md`

## Acceptance criteria

- [ ] Every `Category` glyph name in `core/models.py` (#37) resolves, checked by a Meson test that looks up each name with `Gtk.IconTheme.has_icon`
- [ ] The icons recolour correctly in light, dark and high-contrast modes (they are symbolic)

## References

- [`mvp-first.md` §1 (Images), §2 tree (`icons/categories`), §4.2, §4.3, §13 (Category glyphs)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`libadwaita-ui-patterns.md` §8.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
