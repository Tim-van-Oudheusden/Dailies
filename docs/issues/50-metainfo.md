---
key: 50
title: data(metainfo): complete metainfo — branding, OARS, release 0.1.0, screenshots
type: Task
labels: milestone::M1, type::task, priority::high, flatpak
parent: 3
blocked_by: 34, 42, 43, 44, 46, 47
---
> **Risk tier:** high (`data/*.metainfo.xml.in`) · **Size:** M (screenshots need the finished UI)

## Why

The metainfo feeds the About dialog, GNOME Software, the future Flathub page and `release.yml`, whose `verify` job compares the newest `<release>` with the tag. Flathub's MetaInfo and quality rules apply even before submission because the linter enforces them.

## Content (`data/io.github.tim_van_oudheusden.Dailies.metainfo.xml.in`)

- [ ] `<id>@APP_ID@</id>`, `<name>Dailies</name>` (under 20 characters), `<summary>Play your daily guessing games in one place</summary>` (≤ 35 characters per Flathub guidance; shorten if needed, e.g. "Play your daily guessing games")
- [ ] `<description>`: five feature sentences matching the README "About" section: categories, weekly Popular/Trending, Favorites, the built-in browser, no account and nothing leaving the device
- [ ] `<developer id="io.github.tim_van_oudheusden"><name>Tim van Oudheusden</name></developer>`
- [ ] `<launchable type="desktop-id">@APP_ID@.desktop</launchable>`
- [ ] `<url type="homepage|bugtracker|vcs-browser|contribute">` pointing at the GitHub repo, its issues, and `CONTRIBUTING.md`
- [ ] `<branding>`: light `#99c1f1` (Blue 1), dark `#1a5fb4` (Blue 5) ([`logo-icon.md` §8, Appendix G](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/logo-icon.md))
- [ ] `<supports><control>pointing</control><control>keyboard</control><control>touch</control></supports>`, `<requires><display_length compare="ge">360</display_length></requires>`
- [ ] `<content_rating type="oars-1.1">`: consider that users can reach arbitrary third-party web content through normal navigation in the built-in browser, and rate accordingly (e.g. `social-info` / `money-purchasing` per what games expose). Document the reasoning in the PR
- [ ] `<releases><release version="0.1.0" date="YYYY-MM-DD"><description translate="no">…</description></release></releases>`; the date is the actual tag date
- [ ] `<screenshots>`: **4** shots, ~960×640, window only with its native shadow and rounded corners, default GNOME session, light first, one dark, each with a one-sentence `<caption>`. Files go in `data/screenshots/1.png … 4.png` and are referenced by **tag URL** (`https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/v0.1.0/data/screenshots/1.png`), never `main`
  1. Library with Favorites
  2. Popular shelf
  3. A game open in the built-in browser
  4. Dark style, a category

## Acceptance criteria

- [ ] `appstreamcli validate --no-net --explain` passes (the Meson test)
- [ ] `flatpak-builder-lint appstream` and `flatpak-builder-lint repo repo` are clean for the **release** ID
- [ ] The About dialog shows the 0.1.0 release notes
- [ ] Screenshots meet the Flathub quality rules ([`logo-icon.md` §9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/logo-icon.md))

## References

- [`mvp-first.md` §10 (changelog), §13 (screenshots)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`flatpak-release-pipeline.md` §4.3, Appendix C.1, C.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
- [`cartridges.md` §12, Appendix E.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)
