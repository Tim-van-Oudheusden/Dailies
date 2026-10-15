---
key: 82
title: feat(search): fuzzy matching
type: Feature
labels: milestone::M5, type::feature, priority::low, app
parent: 7
blocked_by: 44
---
> **Risk tier:** medium · **Size:** S

## Tasks

- [ ] Extend `core/search.py` (#37) with ranked fuzzy matching using only the stdlib (`difflib`, or a small subsequence scorer), keeping the zero-dependency rule: tolerate a typo ("wordel" → Wordle) and match word starts ("n l" → Numbers & Logic)
- [ ] Rank results: exact prefix > word prefix > substring > fuzzy. In search mode, use a `Gtk.SortListModel` sorter by score, which overrides the section sort while a query is active
- [ ] Performance: under 5 ms per keystroke for 300 games on a modest machine (add a micro-benchmark test)

## Acceptance criteria

- [ ] Unit tests for typos, accents and ranking order
- [ ] Clearing the query restores the section's normal sort

## References

- [`mvp-first.md` §4.4 (fuzzy matching is roadmap)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
