---
key: 81
title: ci(data): automate the status flip for broken links
type: Task
labels: milestone::M5, type::task, priority::low, ci, data
parent: 7
blocked_by: 60
---
> **Risk tier:** high · **Size:** S

## Why

In M2 the weekly link checker (#60) opens an issue and the maintainer flips `status` by hand. Once its results have proven reliable, it can open the PR itself.

## Tasks

- [ ] When an active game fails the **same** check on **two consecutive** weekly runs (track this with an artifact or a small state file), open a PR on branch `data/link-status` that sets `status: broken` and appends `history: {date, event: "broken", note: "<reason>"}`. Never delete entries
- [ ] Games that recover (`broken` → passing twice) get a PR back to `active` with a history entry
- [ ] Cross-domain redirects to blocklisted titles → `retired` immediately, with the PR labelled `priority::high`
- [ ] PRs are human-merged (or auto-merged under #79 rules, if the owner extends them)

## Acceptance criteria

- [ ] A fixture game that fails twice gets a correct status PR; a single failure produces only the issue row

## References

- [`mvp-first.md` §7.6, §16 (M5)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`dle-catalog.md` §5.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)
