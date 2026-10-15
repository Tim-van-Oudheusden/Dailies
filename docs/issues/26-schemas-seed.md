---
key: 26
title: data: catalog and popularity JSON Schemas, seed games.json, first popularity.json, data tests
type: Task
labels: milestone::M0, type::task, priority::high, data
parent: 2
blocked_by: 10, 20
---
> **Risk tier:** high (`data/v1/schema/**`), medium (`data/v1/*.json`) · **Size:** M

## Why

The catalog is the product. The schema is the contract between the app (#37), the submission pipeline (#57–#59), the popularity pipeline (#61) and CI. The decision is **one catalog file**, `data/v1/games.json`, rather than one YAML per game: at ~100–300 entries a single file stays under 100 KB with one ETag and needs no concatenation step. Per-entry history lives in a `history` array instead.

## Tasks

### `data/v1/schema/catalog.schema.json` (JSON Schema 2020-12)

Start from [`data-pipeline.md` §2.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md) and apply three changes from [`dle-catalog.md` Appendix C](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md): add `free_no_account` (boolean), add `history` (array of `{date, event, note}`), and replace the category enum with the **ten-value taxonomy, with no `other`**.

| Field | Rule |
|---|---|
| `schema_version` | const `1` |
| `generated_at` | RFC 3339 date-time |
| `games[].id` | `^[a-z0-9][a-z0-9-]{1,48}$`; immutable; never reused |
| `games[].url` | `^https://` |
| `games[].category` | enum `words, geography, music, movies-tv, video-games, numbers-logic, trivia, visual, food, sports` |
| `games[].difficulty` | enum `easy, medium, hard` |
| `games[].status` | enum `active, broken, retired` (soft delete; never delete records) |
| required | `id, name, url, category, difficulty, description, added, status, domain` |
| optional | `tags[]`, `language` (default `en`), `free_no_account`, `wikipedia`, `source_issue`, `aliases[]`, `history[]` |
| unknown fields | allowed (`additionalProperties: true`), because apps ignore them; breaking changes go to `data/v2/` |

### `data/v1/schema/popularity.schema.json`

Use exactly [`data-pipeline.md` §7.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md): `schema_version`, `method_version`, `week` (`^\d{4}-W\d{2}$`), `generated_at`, `valid_until` (+10 days), `stale`, `popular[]` / `trending[]` of `{id, rank, score, delta?, reason}`, per-game `scores`, per-source `sources` health, `attribution[]`, `report`.

### Seed `data/v1/games.json`

- [ ] Build it from [`dle-catalog.md` Appendix A](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md) (116 entries) using the scope decided in #10. Default: drop `food-le`, `birdle` and anything flagged during a one-off run of the link-check rules
- [ ] Never seed graveyard domains (`moviedle.app`, `absurdle.online`, `posterdle.com`, `cladder.io`, `cloudle.app`, `foodle.io`). Use the live replacements where they exist (e.g. moviedle.xyz, qntm.org/absurdle)
- [ ] Every entry gets `added: "2026-…"`, `status: "active"`, `domain` (registrable domain), `history: [{date, event: "added", note: "seed"}]`
- [ ] Difficulty is maintainer-curated following the rubric in [`dle-catalog.md` §2.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)
- [ ] Entries sorted by `id`

### First `data/v1/popularity.json`

- [ ] Hand-written for the current ISO week: `method_version: 0`, a `popular` list of the obvious staples (Wordle, Connections, Worldle, …), and `trending` filled with recently added games, each with `reason: "new"`. Set `valid_until` +10 days and `attribution: []`
- [ ] Must validate against the schema

### `tests/data/test_catalog_file.py`
- [ ] Both files validate against their schemas
- [ ] `id`s are unique and sorted
- [ ] Normalised URLs are unique (lower-case host, strip `www.`, trailing slash and `utm_*`)
- [ ] Every `domain` is the registrable domain of its `url`
- [ ] Every enum value is valid
- [ ] Every id in `popularity.json` exists in `games.json`

### Also
- [ ] `docs/data-format.md` is written in #53. Here, add a short `data/v1/README.md` pointing to it

## Acceptance criteria

- [ ] `check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json` passes, and the same for popularity
- [ ] `pytest tests/data` passes
- [ ] `games.json` is under 100 KB
- [ ] The ten categories each have at least one active game (categories with zero active games are hidden in the UI, but the seed should cover all ten)

## References

- [`mvp-first.md` §6.1, §6.2, §12 (Data row)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §2, §7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
- [`dle-catalog.md` §1.3, §1.4, §2, Appendix A, Appendix C](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)
