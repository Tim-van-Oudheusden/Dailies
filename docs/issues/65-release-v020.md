---
key: 65
title: release: cut v0.2.0
type: Task
labels: milestone::M2, type::task, priority::medium, flatpak
parent: 4
blocked_by: 55, 56, 58, 59, 60, 62, 63, 64
---
> **Size:** XS · **Who:** owner

## Steps

1. [ ] **Milestone exit evidence** (link it here):
   - [ ] Game 1 added through the form end-to-end: issue #… → PR #…
   - [ ] Game 2 added through the form end-to-end: issue #… → PR #…
   - [ ] One scheduled Monday `popularity.yml` run merged: PR #…
2. [ ] Bump `meson.build` to `0.2.0` and add `<release version="0.2.0">` to the metainfo. The notes mention the Pages data source, the custom-command mode and the language filter
3. [ ] Update the release manifest git source
4. [ ] Repeat the manual checklist from #55, plus: custom-command mode with the override granted; the language switch
5. [ ] Push tag `v0.2.0`, verify the assets and checksums, and install on a clean profile

## Acceptance criteria

- [ ] GitHub Release `v0.2.0` with both bundles and `SHA256SUMS`
- [ ] Every M2 exit criterion in #4 is ticked

## References

- [`mvp-first.md` §16 (M2 exit)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
