---
key: 55
title: release: cut v0.1.0
type: Task
labels: milestone::M1, type::task, priority::high, flatpak
parent: 3
blocked_by: 35, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 54
---
> **Size:** XS (if everything above is done) · **Who:** owner

## Steps

1. [ ] Make sure `meson.build` says `version: '0.1.0'` and the metainfo `<release version="0.1.0" date="…">` has today's date and real notes
2. [ ] Update the release manifest's git source to the `v0.1.0` tag + commit (as part of the release PR)
3. [ ] **Manual checklist** (`CONTRIBUTING.md` §Releasing), on the Devel bundle built from the release commit:
   - [ ] Open 3 games in-app, one of them an NYT game
   - [ ] Streak/progress persists across an app restart
   - [ ] "Open in Browser" and the "Default browser" mode both open the host browser
   - [ ] Dark style looks right
   - [ ] 360 px width: sidebar collapses, no horizontal scroll
   - [ ] Screen reader (Orca) announces tile names and the star toggle
   - [ ] Offline launch shows the bundled catalog
4. [ ] Push tag `v0.1.0` (per #12) and watch `release.yml` (#51)
5. [ ] Verify the release assets: `Dailies-x86_64.flatpak`, `Dailies-aarch64.flatpak`, `SHA256SUMS`; checksums verify; the x86_64 bundle installs on a clean user profile
6. [ ] `flatpak-builder-lint repo` was clean for the release ID in the `build` job log
7. [ ] Screenshot URLs in the metainfo (tag URLs) resolve now that the tag exists
8. [ ] WebKit memory was recorded in `docs/architecture.md` (#52)

## Acceptance criteria

- [ ] The GitHub Release `v0.1.0` exists with all three assets, and the README Download link points to it
- [ ] Every M1 exit criterion in #3 is ticked

## References

- [`mvp-first.md` §10, §12 (Manual before tagging), §16 (M1 exit)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
