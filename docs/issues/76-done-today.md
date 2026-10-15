---
key: 76
title: feat(ui): "Done today" marker
type: Feature
labels: milestone::M5, type::feature, priority::low, app
parent: 7
blocked_by: 42
---
> **Risk tier:** medium · **Size:** S

## Why

This is aukspot's "done today" idea ([`dle-catalog.md` §3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)): you see at a glance which of today's puzzles you've already played. It is local only and never leaves the device.

## Tasks

- [ ] Decide the trigger: (a) automatic, when a game page has been open for ≥ N seconds in-app, or (b) manual, via a "Mark as Done Today" toggle in the tile menu and the browser page menu. Proposed: **manual, plus an optional automatic mode** behind a preference
- [ ] Storage: GSettings `done-today` `a{ss}` mapping game id → local date (`YYYY-MM-DD`); entries from earlier days are ignored and pruned on startup. "Today" is the **local** day
- [ ] Tile: a small check badge (with text for accessibility, e.g. "Done today") and a dimmed style. A sort option "Not done first"
- [ ] Favorites empty-state copy stays the same

## Acceptance criteria

- [ ] Marking a game as done shows the badge; it disappears after local midnight
- [ ] No network traffic is involved

## References

- [`mvp-first.md` §16 (M5)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
