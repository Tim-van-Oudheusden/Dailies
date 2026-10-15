---
key: 13
title: Decision: shared-domain popularity weighting
type: Task
labels: decision, milestone::M2, priority::medium, data
parent: 4
---
## Question

Tranco ranks **registrable domains**, not pages, so every `nytimes.com` game (Wordle, Connections, Spelling Bee, Strands, The Mini) gets the same rank. How should one domain's signal be split across its games?

## Options

- **Equal split, plus an optional override file (proposed):** each game on a shared domain gets `domain_score / n`, unless `data/v1/domain_weights.json` (`{"nytimes.com": {"wordle": 0.4, "connections": 0.3, ...}}`) overrides it. The file is optional and maintainer-edited.
- **Hand-maintained `domain_weights.json` from day one:** more accurate, but it is a recurring chore with no objective source behind it.

## Proposed default

**Equal split; add `domain_weights.json` only when a shelf looks obviously wrong.** Validate the override file in CI: weights per domain sum to 1 and every id exists.

## How to close

Comment and close. #61 implements the split.

## References

- [`mvp-first.md` §8 (Score), §18.7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §4.2, §8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
