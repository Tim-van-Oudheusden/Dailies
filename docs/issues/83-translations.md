---
key: 83
title: i18n: translations via Weblate
type: Task
labels: milestone::M5, type::task, priority::low, app
parent: 7
blocked_by: 24
---
> **Risk tier:** low (po/) / medium (code) · **Size:** S (setup) + ongoing

## Why

gettext has been wired since #24 (English only). Cartridges ran translations through Weblate; Dailies can follow the same pattern.

## Tasks

- [ ] Audit for untranslated strings: every user-facing string in `.py` and `.blp` goes through `_()` / `_("…")`, and `po/POTFILES.in` is complete (CI check: `meson compile dailies-pot` / `xgettext` produces no warnings about missing files)
- [ ] Generate `po/dailies.pot` and commit it
- [ ] Set up a Hosted Weblate project (libre plan) or Codeberg Translate; connect it to GitHub through the Weblate GitHub app, with PRs opened by Weblate, never direct pushes
- [ ] `translator-credits` in About (#48)
- [ ] Category display names are translated in the UI layer, never in `games.json`
- [ ] Revisit the `show-other-languages` default (#15) once a translation exists
- [ ] Document the process in `CONTRIBUTING.md`

## Acceptance criteria

- [ ] With `LANGUAGE=nl`, a test translation (Dutch, given the owner) shows translated UI

## References

- [`mvp-first.md` §2 tree (po/), §16 (M5)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`cartridges.md` §4.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)
