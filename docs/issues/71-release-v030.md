---
key: 71
title: release: cut v0.3.0 (third release, Flathub-ready release manifest)
type: Task
labels: milestone::M3, type::task, priority::medium, flatpak
parent: 5
blocked_by: 65, 66, 67, 68, 69, 70
---
> **Size:** S · **Who:** owner

## Why

A third tagged release gives Dailies the development history Flathub's inclusion policy asks about ("insufficient development history" is a rejection reason). It is also the point where the release manifest must be good enough to hand to Flathub (#72) or to the Pages remote (#73).

## Steps

1. [ ] **Flathub-ready release manifest** (`build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json`):
   - `git` source with `tag` + `commit` for `v0.3.0`
   - `x-checker-data` working (#67 produced at least one bump PR or confirmed no-op)
   - `flatpak-builder-lint manifest` and `repo` clean with **no exceptions**
   - finish-args unchanged from #25 (plus pulseaudio only if #16/#69 added it)
   - prepare `flathub.json` content with `{"require-important-update": true}` for the Flathub copy (not committed here)
2. [ ] Metainfo `<release version="0.3.0">` with notes (weekly reports, polish, audio decision)
3. [ ] Manual checklist (#55) plus: the weekly report link renders on Pages
4. [ ] Push tag `v0.3.0`; verify the assets
5. [ ] **Milestone exit evidence:** `nightly-compliance` green for 2 consecutive weeks (link the runs); three releases exist

## Acceptance criteria

- [ ] GitHub Release `v0.3.0` with both bundles and `SHA256SUMS`
- [ ] Every M3 exit criterion in #5 is ticked

## References

- [`mvp-first.md` §10 (Flathub), §16 (M3 exit, "`.flatpakref`-ready release manifest")](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`flatpak-release-pipeline.md` §4, §9 item 7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
