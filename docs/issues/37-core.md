---
key: 37
title: feat(core): pure-Python domain core — models, catalog, popularity, search
type: Feature
labels: milestone::M1, type::feature, priority::high, app
parent: 3
blocked_by: 20, 26
---
> **Risk tier:** medium · **Size:** M · **Rule:** nothing under `dailies/core/` imports `gi`

## Why

"Core is pure Python; ui/data touch gi" is called the single most important maintenance decision in the proposal. Catalog parsing, popularity maths and search can then be unit-tested on a plain `ubuntu-latest` runner in seconds, without the GNOME SDK, and coverage floors apply here.

## Modules

### `dailies/core/models.py`
- `@dataclass(frozen=True) Game` with fields `id, name, url, category, difficulty, description, tags, language, added, status, domain, free_no_account, wikipedia, source_issue` (later fields optional, with defaults)
- `class Category(Enum)` with the ten ids. Each one has a display name (translatable with `_()` at the UI layer, not here) and a glyph icon name:

| id | Display | Glyph |
|---|---|---|
| `words` | Words | `dailies-category-words-symbolic` |
| `geography` | Geography | `dailies-category-geography-symbolic` |
| `music` | Music | `dailies-category-music-symbolic` |
| `movies-tv` | Movies & TV | `dailies-category-movies-tv-symbolic` |
| `video-games` | Video Games | `dailies-category-video-games-symbolic` |
| `numbers-logic` | Numbers & Logic | `dailies-category-numbers-logic-symbolic` |
| `trivia` | Trivia | `dailies-category-trivia-symbolic` |
| `visual` | Pictures & Colors | `dailies-category-visual-symbolic` |
| `food` | Food | `dailies-category-food-symbolic` |
| `sports` | Sports | `dailies-category-sports-symbolic` |

  The glyph files come from #40.
- `class Difficulty(Enum)`: `easy | medium | hard`, with a sort order
- **Tolerance:** an unknown category maps to `trivia` and an unknown status maps to `broken` **at runtime**, so a newer catalog never crashes an older app. CI's schema check (#26) keeps unknown values out of the repo

### `dailies/core/catalog.py`
- `parse(data: bytes) -> Catalog`: structural validation only (`schema_version == 1`, required keys, enum membership with the tolerant fallback). This is **not** full JSON Schema, to stay dependency-free. Raises `CatalogError` on anything structurally wrong, so the caller keeps the last good copy
- `Catalog.games` keeps **every** record, including `broken`/`retired`, so favourites still resolve. `Catalog.active()` returns only `status == "active"`
- `is_newer(a, b)` compares `generated_at`

### `dailies/core/popularity.py`
- `parse(data: bytes) -> Popularity(week, generated_at, valid_until, popular: list[str], trending: list[str], scores)`. The app reads only `week`, `valid_until`, `popular` and `trending`
- `rank_of(id) -> int | None` per shelf; `is_stale(now) -> bool` (`now > valid_until`)
- Ids missing from the catalog are dropped silently

### `dailies/core/search.py`
- Case- and accent-folded substring match (`unicodedata.normalize("NFKD")`, strip combining marks, `casefold()`) over name, description, tags and the category label
- `matches(game, query, category_label) -> bool`; an empty query matches everything

## Tests (`tests/core/`)

- [ ] `test_catalog.py`: valid seed parses; an unknown category maps to `trivia`; an unknown status maps to `broken`; a missing required key raises; `schema_version: 2` raises; broken/retired records are kept but excluded from `active()`; `is_newer`
- [ ] `test_popularity.py`: parse, `rank_of`, `is_stale` on both sides of `valid_until`, unknown ids dropped
- [ ] `test_search.py`: "pokedle" matches "Pokédle"; "GEO" matches the Geography label; tags match; empty query matches all

## Acceptance criteria

- [ ] `pytest tests/core` passes with only `pytest` installed
- [ ] Line coverage of `dailies/core` ≥ the floor in `.github/auto-qa-tuning.json` (#28)
- [ ] `grep -rE "^(from|import) gi" dailies/core` is empty

## References

- [`mvp-first.md` §3.1 (module table), §6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §2.3 (soft delete, versioning)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
