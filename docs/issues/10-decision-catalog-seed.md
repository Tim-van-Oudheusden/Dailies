---
key: 10
title: Decision: catalog seed scope and fan-made IP games
type: Task
labels: decision, milestone::M0, priority::high, data
parent: 2
---
## Questions

1. **Breadth:** seed `data/v1/games.json` with the curated, liveness-checked list (~110 entries after pruning), or import aukspot/dles' 785 active entries wholesale (GPL-3.0, compatible)?
2. **Fan-made IP games** (Pokédle, LoLdle, Smashdle, Narutodle, …): include them by default with a `fan-made` tag, or hide them behind a filter?

## Options and evidence

- **Curated seed (proposed):** the 116 entries in [`dle-catalog.md` Appendix A](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md), every URL curl-checked on 2026-10-15. Drop `food-le` and `birdle` (low-confidence provenance) and anything the first link-check run flags. Credit aukspot in the README: "Catalog seeded with help from The Dles by aukspot, GPL-3.0".
- **Wholesale import:** 785 active entries and a 19-category scheme, which "would swamp a desktop launcher" ([`dle-catalog.md` §5.10](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)). Records would need re-mapping to the 10-category enum and a hand-set difficulty for each one; no aggregator publishes difficulty.
- **Fan-made:** high takedown and churn risk ([`mvp-first.md` §17 risk 14](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)). The link checker flips the status and favourites degrade gracefully, so including them is low-impact.

## Proposed defaults

1. **Curated seed**, minus `food-le` and `birdle`. Use the graveyard (`moviedle.app`, `absurdle.online`, `posterdle.com`, `cladder.io`, `cloudle.app`, `foodle.io`) as link-checker test fixtures, never as entries.
2. **Include fan-made games by default**, tagged `fan-made`.

## Also confirm while deciding

- Spot-check by hand: whether NYT Spelling Bee and The Mini are free without an account, whether LinkedIn games are playable logged out, and whether WaPo Keyword is live. All three are **[U]** in [`dle-catalog.md` §6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md). Set `free_no_account` accordingly.

## How to close

Comment with the choices and close. #26 builds the seed.

## References

- [`mvp-first.md` §6.1, §18.5, §18.6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`dle-catalog.md` §1.4 graveyard, §2.2 taxonomy, §5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)
