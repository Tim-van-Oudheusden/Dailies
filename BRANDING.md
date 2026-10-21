# Branding: Dailies

## 1. Name

- **Name:** Dailies (one word, capital D)
- **Application ID:** `io.github.tim_van_oudheusden.Dailies`; development builds use
  `io.github.tim_van_oudheusden.Dailies.Devel`
- **Command:** `dailies`

## 2. Tagline

> Play your daily guessing games in one place

## 3. Positioning

Dailies is a GNOME app that gathers the daily "-dle" guessing games (Wordle and the many games it inspired) into one
library: favourites first, this week's popular and trending games, and ten categories. It opens each game's own website,
in a built-in browser or in the user's browser. It takes its cue from [Cartridges](https://github.com/kra-mo/cartridges)
and [Bazaar](https://github.com/bazaar-org/bazaar): a native launcher that gets out of the way. It is not a game, not a
clone of any game, and not affiliated with any game's publisher.

## 4. Principles

- **Native.** Looks and behaves like a GNOME app: libadwaita widgets, the GNOME HIG, the user's accent colour, light
  and dark style, keyboard and screen reader support.
- **The publisher's game, as published.** Dailies links to games and shows their pages unchanged: no injected scripts,
  no ad blocking, no disguised user agent, and the real address always visible.
- **Private.** No account, no telemetry. Nothing leaves the computer except the catalog download and the games the user
  opens.
- **Works offline.** The catalog ships with the app; an update is a bonus, never a requirement.

## 5. Voice

- **Honest.** Describe a game only by what its catalog entry says; never claim a publisher's endorsement.
- **Plain words.** Short labels in the UI, short sentences in the docs. UI text follows the HIG writing style: header
  capitalization for titles and buttons ("Add to Favorites"), sentence capitalization for descriptions, US English as
  GNOME does.

## 6. Visual identity

- **Toolkit first:** the app uses libadwaita's styles and colour variables instead of a custom theme, so light, dark and
  high-contrast styles and the user's accent colour follow automatically. There is no app-specific accent colour in the
  UI.
- **Palette:** icons and illustrations use only the
  [GNOME HIG palette](https://developer.gnome.org/hig/reference/palette.html), with the HIG's
  [app icon guidelines](https://developer.gnome.org/hig/guidelines/app-icons.html) for shape, perspective and detail.
- **Icon ("Torn Page"):** today's page torn off a pad, filled by a guessing game's feedback grid, so it shows the name
  (a daily page) and the purpose (guessing games) in one object. It has no binder rings and no coloured header band,
  the two marks of a calendar, so it is not mistaken for one. Square base shape on the HIG grid with a torn top edge:
  the page in Light 2 `#f6f5f4` over a Light 4 `#c0bfbc` chin that follows the same torn outline. On the page, a 3×3
  grid of tiles that tells a game from first guess to solved: a miss, a near miss (Orange 3 `#ff7800`) and a miss; a
  near miss, a hit (Blue 4 `#1c71d8`) and a miss; then three hits. Misses are Light 4. Blue and orange rather than
  green and yellow keep the icon clear of Wordle's trade dress; the grid stays 3×3 and is never drawn as 5×6. No
  letters, no outer shadow, no clip paths, masks or filters.
- **Symbolic icon:** the torn page at 16 px with the 3×3 grid cut out of it: 2 px tiles with 2 px gaps on the pixel
  grid.
- **Devel icon and window:** the Devel build uses App Icon Preview's stripes overlay (Yellow 1 to Yellow 4 with dark
  stripes, baked to the icon's outline instead of masked) and libadwaita's striped `.devel` header bar.
- **Brand colours:** Blue 1 `#99c1f1` (light) and Blue 5 `#1a5fb4` (dark), set in the metainfo's `<branding>`; they are
  lighter and darker versions of the icon's Blue 4 tiles.
- **Tiles:** each game is a card with the game's own icon in a rounded square tinted per category, the game's name,
  and its category and difficulty as text. The category's symbolic glyph (from the GNOME Icon Development Kit where one
  exists, otherwise drawn at 16 px with 2 px strokes) sits in a badge on the square's corner, which **Preferences**
  can hide; a game without an icon shows the glyph in the icon's place. Difficulty also has a small pill, because
  colour never carries information alone.
- **Game icons:** Dailies publishes third-party logos: each game's icon is its site's own icon, or the one a favicon
  service shows for it, as a 64×64 PNG in `data/v1/icons/`. They go out with the catalog on GitHub Pages, not in the
  app, and remain the marks of their owners, shown only to identify each game. An owner who asks gets the icon taken
  down for good ([Game icons](README.md#game-icons), [runbook](docs/runbooks/game-icon.md)).
- **Type:** the system interface font, in libadwaita's type styles (`title-1`, `heading`, `caption`); no bundled fonts.
- **Screenshots:** a window of about 960×640 on a default GNOME session, light style first and one in dark style,
  real content rather than empty states, no edits; Flathub's screenshot rules apply.

## 7. Assets

The App Icon Preview project [`data/icons/<id>.Source.svg`](data/icons/io.github.tim_van_oudheusden.Dailies.Source.svg)
holds the icon and its symbolic variant; it is not installed. The exported icons are
[`<id>.svg`](data/icons/hicolor/scalable/apps/io.github.tim_van_oudheusden.Dailies.svg) and
[`<id>.Devel.svg`](data/icons/hicolor/scalable/apps/io.github.tim_van_oudheusden.Dailies.Devel.svg) in
`data/icons/hicolor/scalable/apps/`, and
[`<id>-symbolic.svg`](data/icons/hicolor/symbolic/apps/io.github.tim_van_oudheusden.Dailies-symbolic.svg) in
`data/icons/hicolor/symbolic/apps/`. [`data/icons/meson.build`](data/icons/meson.build) installs the profile's icon
under the profile's app ID: the plain icon for release builds, the striped one as `<id>.Devel.svg` for development
builds. Category glyphs and the other bundled symbolic icons live in `data/icons/categories/`, with each icon's
source and licence in [its README](data/icons/categories/README.md); screenshots in `data/screenshots/`, linked from
the metainfo by tag URL.
