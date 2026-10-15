---
key: 3
title: [Epic] M1 Usable launcher → v0.1.0
type: Task
labels: epic, milestone::M1, priority::high
parent: 1
---
**Target:** weeks 2–3 · **Source:** [`mvp-first.md` §3–§5, §9, §10, §12, §13, §16 (M1)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)

## Goal

A launcher you can use every day, released as **v0.1.0** Flatpak bundles. It includes:

- the sidebar with Favorites (always first), Popular, Trending and the ten categories
- a `Gtk.GridView` of tiles with a star toggle
- search
- favourites stored in GSettings
- the bundled snapshot plus a raw.githubusercontent fetch with ETags
- the in-app WebKit page with a persistent session, and external open through the portal
- Preferences, About and Shortcuts
- an e2e smoke test
- a hand-written first `popularity.json`
- `release.yml`
- a complete metainfo
- the README

## Exit criteria

- [ ] Tag `v0.1.0` pushed; GitHub Release has `Dailies-x86_64.flatpak`, `Dailies-aarch64.flatpak` and `SHA256SUMS` (#51, #55)
- [ ] `flatpak-builder-lint repo repo` clean for the **release** ID, with no exceptions (#51)
- [ ] WebKit memory measured with `smem` on a NYT game and recorded in `docs/architecture.md` (#52)
- [ ] Manual release checklist passed (#55)

## Sub-issues

Decisions that gate this milestone: #9 (default open mode), #12 (release trigger).

{{CHILDREN}}

## Suggested order

1. #37, #38 and #40 can run in parallel once M0's #24/#26 have landed.
2. Then #39 and #41.
3. Then #42, followed by #43/#44 and #45 → #46 → #47 in parallel.
4. Then #48 and #49.
5. Then #50 (screenshots need the finished UI), #51 → #54 → #55.
