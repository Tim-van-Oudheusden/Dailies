---
key: 8
title: Decision: app icon solved-row colours (Blue/Orange vs Green/Yellow)
type: Task
labels: decision, milestone::M0, priority::high
parent: 2
---
## Question

The app icon is Concept A "Daily Grid": a tear-off desk-calendar card whose page shows a 3×2 guess-feedback tile grid. Which colours should the **solved row** use?

## Options

| Option | Solved row | Unsolved row | For | Against |
|---|---|---|---|---|
| **A (proposed)** | Blue 4 `#1c71d8` / Orange 3 `#ff7800` / Blue 4 | Light 3 `#deddda` | Avoids the Wordle trade-dress association: NYT's 2024 DMCA campaign asserted trade dress over the green/yellow/grey grid ([`dle-catalog.md` §4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)); the launcher gains nothing from the association | Reads less obviously as "guessing game" |
| B (draft) | Green 4 / Yellow 4 | Light 3 | Closest to the genre's visual language; the research draft SVGs already use it ([`logo-icon.md` §10, Appendix F](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/logo-icon.md)) | GNOME-palette hues, but the same green/yellow/grey semantics NYT has asserted |

Either way, keep the **3×2 grid** (never 5×6).

## Proposed default

**Option A (Blue/Orange).** The owner can switch to B later in one commit.

## How to close

Comment with the choice and close as completed. #34 then draws the icon in the chosen colours.

## References

- [`mvp-first.md` §13, §18.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`logo-icon.md` §3 (palette), §10, §12](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/logo-icon.md)
- [`dle-catalog.md` §4 (trademark)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)
