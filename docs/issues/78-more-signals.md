---
key: 78
title: feat(popularity): optional Wikipedia, HN and Cloudflare Radar signals
type: Feature
labels: milestone::M5, type::feature, priority::low, data
parent: 7
blocked_by: 61, 62
---
> **Risk tier:** high · **Size:** M

## Sources (from [`data-pipeline.md` §4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md))

| Source | Access | Licence | Coverage | Proposed weight |
|---|---|---|---|---|
| Tranco (existing) | keyless, 1 req/s | unstated **[U]** | all domains | 0.80 |
| Wikipedia pageviews | keyless, strict User-Agent, 200 req/min for compliant bots | CC0 | only famous games (Connections, Framed and Scrandle have no article) | 0.15 |
| HN Algolia | keyless, 10k/h | — | buzz only | 0.05 |
| Cloudflare Radar | token (Account → Radar Read), 1,200 req / 5 min | **CC BY-NC 4.0** | per-domain rank/bucket + `TRENDING_RISE` | optional |

## Tasks

- [ ] Collectors in `scripts/popularity/collect.py` behind flags, **off by default** (`--wikipedia`, `--hn`, `--radar`). Wikipedia uses each entry's `wikipedia` field
- [ ] Composite score in `compute.py`, **bumping `method_version` to 2**. The app can then show "methodology changed", and `compute.py` skips trend comparison across versions
- [ ] Per-source health in `sources`, and attribution entries in `attribution[]` (Radar requires CC BY-NC attribution, so state the non-commercial nature in the README)
- [ ] Radar: create `CLOUDFLARE_RADAR_TOKEN` (#18). The per-domain endpoint's query parameters (date, `rankingType`, limit) were **unverified** in the research; verify them against the live API first
- [ ] Tests with synthetic data for the composite score, including a missing source being renormalised

## Acceptance criteria

- [ ] With all flags off, output is byte-identical to `method_version: 1` behaviour
- [ ] With flags on, the shelves change in explainable ways (show the diff in the PR)

## References

- [`mvp-first.md` §8 (Sources), §16 (M5), §17 risk 9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §4.1, §4.2, §8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
