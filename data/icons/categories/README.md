# Bundled symbolic icons

These 16×16 symbolic icons are compiled into `dailies.gresource` under `<resource base path>/icons/scalable/actions/`
(see `data/dailies.gresource.xml.in`). `Adw.Application` adds `<resource base path>/icons` to the icon theme, so the UI
looks them up by name. The names of the category glyphs come from `Category.icon_name` in `dailies/core/models.py`;
the Meson test `Bundled icons resolve` (`tests/icons/check_icons.py`) checks that every one of them, and the four
other icons below, resolves from the gresource alone.

All of them come from the GNOME [Icon Development Kit](https://gitlab.gnome.org/Teams/Design/icon-development-kit)
(commit `e5857f6d796a96571a61030db40f35bfb8815a94`, 2026-09-23), drawn by Jakub Steiner and released under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). The kit ships them in GTK's stateful symbolic format
(`gpa:` attributes); the copies here are the shapes of one state, unchanged, as plain SVG paths with GTK's
`foreground-fill` / `transparent-fill foreground-stroke` classes, so GTK recolours them and librsvg still renders them.
They keep the kit's 2 px strokes on the 16 px grid.

| Icon | Used for | Kit icon (state) | Licence |
|---|---|---|---|
| `dailies-category-words-symbolic.svg` | Words | `text` (outline) | CC0-1.0 |
| `dailies-category-geography-symbolic.svg` | Geography | `globe` (outline) | CC0-1.0 |
| `dailies-category-music-symbolic.svg` | Music | `music-note` (outline) | CC0-1.0 |
| `dailies-category-movies-tv-symbolic.svg` | Movies & TV | `clapper` (outline) | CC0-1.0 |
| `dailies-category-video-games-symbolic.svg` | Video Games | `games` (outline) | CC0-1.0 |
| `dailies-category-numbers-logic-symbolic.svg` | Numbers & Logic | `calculator` (outline) | CC0-1.0 |
| `dailies-category-trivia-symbolic.svg` | Trivia | `questionmark` (outline) | CC0-1.0 |
| `dailies-category-visual-symbolic.svg` | Pictures & Colors | `graphics` (outline) | CC0-1.0 |
| `dailies-category-food-symbolic.svg` | Food | `cutlery` (outline) | CC0-1.0 |
| `dailies-category-sports-symbolic.svg` | Sports | `trophy` (outline) | CC0-1.0 |
| `dailies-trending-symbolic.svg` | Sidebar "Trending" | `fire` (outline) | CC0-1.0 |
| `dailies-popular-symbolic.svg` | Sidebar "Popular" | `heart` (outline) | CC0-1.0 |
| `dailies-starred-symbolic.svg` | Favourite toggle (on), sidebar "Favorites" | `star` (filled) | CC0-1.0 |
| `dailies-non-starred-symbolic.svg` | Favourite toggle (off) | `star` (outline) | CC0-1.0 |

The stars carry the `dailies-` prefix on purpose: Adwaita has its own `starred-symbolic` and `non-starred-symbolic`,
and GTK searches the current theme before the application's resource path, so under those names Adwaita's copies
would be drawn instead of these.
