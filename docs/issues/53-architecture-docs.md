---
key: 53
title: docs: docs/architecture.md and docs/data-format.md
type: Task
labels: milestone::M1, type::task, priority::medium, documentation
parent: 3
blocked_by: 26
---
> **Risk tier:** low · **Size:** M

## Why

The proposal names two living docs. `docs/architecture.md` is "this proposal, trimmed; Mermaid diagrams", where decisions are written as "**Decision:** … Why: …" paragraphs (no ADRs, per the MinimalUI convention). `docs/data-format.md` is the reference for contributors and for anyone consuming the JSON.

## `docs/architecture.md`

- [ ] Trim `docs/proposals/mvp-first.md` down to what was actually built. Drop the research citations and the "[I]/[V]/[U]" markers, but keep a link back to the proposal
- [ ] Two Mermaid diagrams: (1) the runtime data flow (bundled → cache → fetcher → store → filter/sort → grid → opener; proposal §3.1); (2) the data and release pipelines (issue form → stage A/B → PR → Pages; Monday cron → PR; tag → release.yml → bundles)
- [ ] Module table (proposal §3.1), the startup sequence (§3.2), the caching/offline table (§3.4) and the link-opening strategy (§5)
- [ ] **Decision:** paragraphs for at least: Python over Rust/C; zero pip deps; one JSON catalog over per-game YAML; GSettings for favourites; in-app default (#9); tag-push releases (#12); no `--talk-name=org.freedesktop.Flatpak` in the manifest
- [ ] A **Measurements** section, filled in by #52
- [ ] If `docs/ARCHITECTURE.md` is produced by the design/judge process, merge the two into one file; don't keep both

## `docs/data-format.md`

- [ ] Field-by-field description of `games.json` and `popularity.json`, with links to the schemas (#26)
- [ ] The ten categories with their ids and display names, and the curated tag vocabulary (mechanics, media, subject, publisher, language, flags such as `fan-made`, `account-required`, `subscription-limited`, `weekdays-only`, `bot-walled`), from [`dle-catalog.md` §2.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)
- [ ] The difficulty rubric ([`dle-catalog.md` §2.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md))
- [ ] Submission rules: https only; the final registrable domain must match the submitted one; daily puzzle; no account for `free_no_account: true`; ids are immutable and never reused; `status` instead of deletion; `data/v2/` for breaking changes
- [ ] Data licences: catalog CC0; popularity data with attribution as listed in `popularity.json` `attribution[]`

## Acceptance criteria

- [ ] Both docs are linked from the README documentation table (#54) and from `docs/README.md`
- [ ] The Mermaid diagrams render on GitHub

## References

- [`mvp-first.md` §2 tree (docs/), §2 conventions ("No ADRs"), §3, §6, §7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`scaffolding-repos.md` §5, §8.9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md)
