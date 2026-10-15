---
key: 34
title: design: app icon "Daily Grid" (full-colour, symbolic, Devel, source)
type: Task
labels: milestone::M0, type::task, priority::medium, app, flatpak
parent: 2
blocked_by: 8, 24
---
> **Risk tier:** low (SVG), high (icon Meson rules) · **Size:** M (design work) · **Brief:** "Must follow Libadwaita/GNOME HIG icon guidelines and represent the name and purpose."

## Concept

**Concept A "Daily Grid"** ([`logo-icon.md` §10](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/logo-icon.md)): a tear-off desk-calendar card whose page is a guess-feedback tile grid (**3×2**, never 5×6). It ties the *name* (a daily page) to the *purpose* (guessing games), survives 32 px, and has a trivial symbolic version.

Colours depend on #8. Default: solved row Blue 4 `#1c71d8` / Orange 3 `#ff7800` / Blue 4; unsolved row Light 3 `#deddda`.

## Construction (from the draft SVG in [`logo-icon.md` Appendix F](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/logo-icon.md))

- Square base shape 104×104 at 12..116, `rx 8`
- Header Blue 3, header edge Blue 4, page Light 2, an 8 px "chin" in Light 4, rings Dark 2, baseline y 116
- Flat colours on straight surfaces and gradients only on curves; shadows inside the silhouette only, light from above
- **No** `clipPath`, `mask`, filters or `mix-blend-mode` (KDE's Qt SVG renderer breaks on them; see Bazaar's fix)
- Symbolic: header bar + 2×3 tiles, 16 px, 2 px strokes, 1 px margin, pixel-aligned

## Deliverables

| File | Notes |
|---|---|
| `data/icons/hicolor/scalable/apps/io.github.tim_van_oudheusden.Dailies.svg` | 128×128 full-colour |
| `data/icons/hicolor/scalable/apps/io.github.tim_van_oudheusden.Dailies.Devel.svg` | App Icon Preview's striped Devel variant |
| `data/icons/hicolor/symbolic/apps/io.github.tim_van_oudheusden.Dailies-symbolic.svg` | 16×16 monochrome |
| `data/icons/io.github.tim_van_oudheusden.Dailies.Source.svg` | App Icon Preview project (Bazaar pattern), **not installed** |
| `data/icons/meson.build` | Install the profile-appropriate icon under the profile's app ID ([`logo-icon.md` §5.2, Appendix C](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/logo-icon.md)) |

## Tasks

- [ ] Draw it in **App Icon Preview 3.5.1** + Inkscape from the official HIG template. Compare it against GNOME Calendar, Cartridges and Bazaar for visual weight
- [ ] Export, run `svgo`, and check legibility at 32 px and 16 px
- [ ] Optional: ask for feedback on GNOME Discourse (design category)
- [ ] Wire the install rules into `data/meson.build` (#24); make `Icon=` in the desktop file equal the app ID

## Acceptance criteria

- [ ] `appstreamcli compose` on the build tree produces a 128 px icon (the Flathub linter requirement)
- [ ] `grep -E 'clipPath|<mask|filter=|mix-blend' data/icons -r` is empty
- [ ] The Devel build shows the striped icon and the release build the plain one
- [ ] `BRANDING.md` (#22) references the final files

## References

- [`mvp-first.md` §13, §18.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`logo-icon.md` §2 (HIG rules), §3 (palette), §5, §6, §11, Appendix F](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/logo-icon.md)
