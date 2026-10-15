---
key: 61
title: feat(popularity): Tranco collector and deterministic shelf computation
type: Feature
labels: milestone::M2, type::feature, priority::high, data
parent: 4
blocked_by: 13, 26, 31
---
> **Risk tier:** high (`scripts/**`) · **Size:** M · **Principle:** numbers are deterministic Python; Claude only ever writes prose (#66)

## Sources (MVP)

- **Tranco only:** `GET https://tranco-list.eu/api/ranks/domain/{domain}`. No key; **1 request per second**; returns 30 daily ranks; covers even tiny DLE domains (observed ranks 21k–1.49M for eight sample games)
- Wikipedia pageviews (CC0) and HN Algolia exist as optional collectors behind flags, **off by default** (#78). Cloudflare Radar is roadmap
- Tranco's licence isn't stated on its site **[U]**. Name it in `attribution[]` and have the owner email the Tranco maintainers once

## `scripts/popularity/collect.py`
- [ ] For each **distinct registrable domain** of active games, fetch Tranco ranks (1 req/s, retry once on 5xx), and write `raw/tranco.json` with per-domain `{ranks: [...], fetched_at, ok}`
- [ ] Record per-source health (`ok`, `failed`, `count`) for `popularity.json.sources`

## `scripts/popularity/compute.py` (`method_version: 1`)
- [ ] `tranco_score = clamp(1 − (log10(rank) − 2) / 4.5, 0, 1)`, computed on the **mean of the last 7 daily ranks**. A domain with no rank gets 0 and `carried_forward: false`
- [ ] `popularity = tranco_score` while the other sources are off
- [ ] **Shared domains** (per #13): equal split of a domain's contribution across its games, unless `data/v1/domain_weights.json` overrides it. If that file exists, validate that weights sum to 1 and every id exists
- [ ] `trend = popularity − mean(previous 4 weeks)`, read from the previous `popularity.json` history (up to 8 weeks per game). It is **null** until two prior weeks exist
- [ ] **Shelves:**
  - `N = max(5, min(12, 10 % of active games))`
  - `popular`: top N by popularity; stable sort by score desc, then `id`
  - `trending`: games with `trend > 0.02` that aren't in the **top 5** popular, sorted by trend desc, top N. If fewer than 3 qualify, backfill with the newest `added` games flagged `reason: "new"`, so the shelf is never empty
- [ ] **Fail closed:** if Tranco failed for **> 20 %** of domains, exit non-zero and leave the old file untouched
- [ ] Output `data/v1/popularity.json` per the schema (#26): `week` (ISO 8601, e.g. `2026-W43`), `generated_at`, `valid_until` = +10 days, `stale: false`, `popular[]` / `trending[]` of `{id, rank, score, delta, reason}`, `scores`, `sources`, `attribution` (Tranco), `report` (path of the weekly report, null in M2). Also write `summary.json` (top movers, source health), which #66 feeds to Claude

## Tests (`tests/scripts/test_compute.py`, synthetic data)
- [ ] The score formula at rank 100 → 1.0, rank 10^6.5 → 0.0, and clamping
- [ ] Equal split across 4 NYT games; override file respected; invalid override rejected
- [ ] Trend is null with fewer than 2 prior weeks
- [ ] Trending excludes the top 5 popular, and backfill with `reason: "new"` works
- [ ] The fail-closed threshold at 20 % vs 21 %
- [ ] Output validates against the schema; same input gives byte-identical output (determinism)

## Acceptance criteria

- [ ] A local run against the live seed produces a valid `popularity.json` in under ~3 minutes (about 100 domains at 1 req/s)
- [ ] Tests pass offline; `scripts/` coverage stays above its floor

## References

- [`mvp-first.md` §8 (Sources, Score, Shelves)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §4, §5.2, §7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
