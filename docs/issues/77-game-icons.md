---
key: 77
title: feat(data): game icons (implements decision #17)
type: Feature
labels: milestone::M5, type::feature, priority::low, data, app
parent: 7
blocked_by: 17, 56
---
> **Risk tier:** high (scripts and pipeline) / medium (app) · **Size:** M

## Tasks (depend on the option chosen in #17)

### Option (b): build-time favicons served from Pages
- [ ] `scripts/icons/fetch_icon.py`: try, in order, the web-app manifest icon, `apple-touch-icon`, `link rel=icon`, `/favicon.ico`, then the (unofficial) Google faviconV2 and DuckDuckGo ip3 endpoints. Normalise to a 64×64 PNG with Pillow (add it to `scripts/requirements.txt` with hashes). Write to `data/v1/icons/<id>.png`, or to an orphan branch if #17 says so
- [ ] Stage B (#59) calls it for new games; a one-off backfill for existing ones
- [ ] `pages.yml` publishes `/v1/icons/`; icons stay **out of the Flatpak payload**
- [ ] A takedown note in the README and `docs/data-format.md`

### Option (c): runtime favicons
- [ ] Fetch the favicon from the game's own domain on first display; cache it in `$XDG_CACHE_HOME/dailies/icons/<sha256(url)>` with a 24 h-style TTL sidecar (Bazaar's `BzAsyncTexture` pattern); never redistributed
- [ ] Say in Preferences that this contacts each game's site; add a switch to turn it off

### Both
- [ ] Decode remote images with **glycin** (`GlyGtk4-2`, 2.2.1 in Platform 51), never directly with GdkPixbuf
- [ ] Fall back to the category glyph (#40) on any failure
- [ ] Keep the glyph visible somewhere (e.g. a small corner badge) so the category stays scannable

## Acceptance criteria

- [ ] Tiles show icons where available and glyphs otherwise, with no layout shift
- [ ] Network behaviour matches what the chosen option promises

## References

- [`mvp-first.md` §8 (Icons), §18.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
- [`bazaar.md` §6.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/bazaar.md)
- [`libadwaita-ui-patterns.md` §9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
