---
key: 4
title: [Epic] M2 Data pipeline → v0.2.0
type: Task
labels: epic, milestone::M2, priority::medium
parent: 1
---
**Target:** weeks 4–5 · **Source:** [`mvp-first.md` §5.1, §7, §8, §16 (M2)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)

## Goal

Automate the two data loops the brief asks for:

1. **Contributions:** issue form → stage A validation → maintainer `approved` label → stage B PR → human merge → Pages publish.
2. **Popularity:** a Monday cron pulls Tranco ranks, computes the Popular/Trending shelves deterministically and opens a numbers-only PR.

The milestone also adds the opt-in custom-command open mode and the "Show games in other languages" filter.

## Exit criteria

- [ ] Two real games added through the form end-to-end (issue → validated → approved → PR merged → visible in the app after refresh) (#58, #59)
- [ ] One scheduled Monday `popularity.yml` run produced a PR that was merged (#62)
- [ ] `pages.yml` deploys `data/v1/` and the app uses Pages first, raw second (#56)
- [ ] `v0.2.0` tagged and released (#65)

## Sub-issues

Decisions that gate this milestone: #13 (shared-domain weighting), #15 (other-languages default).

{{CHILDREN}}
