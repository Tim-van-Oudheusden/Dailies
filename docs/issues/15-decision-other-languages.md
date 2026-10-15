---
key: 15
title: Decision: default for "Show games in other languages"
type: Task
labels: decision, milestone::M2, priority::low, app
parent: 4
---
## Question

The GSettings key `show-other-languages` (`b`) hides games whose `language` doesn't match the system locale. What should it default to?

- **true, show everything (proposed):** nothing is hidden by surprise, and the catalog is mostly `en` anyway. The owner is Dutch, and Woordle-style games stay visible.
- **false for non-matching locales:** [`dle-catalog.md` §5.9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md) suggests hiding non-matching languages by default.

## Proposed default

**true**, until translations exist (#83).

## How to close

Comment and close. #64 uses the chosen default in the schema.

## References

- [`mvp-first.md` §3.3, §18.11](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
