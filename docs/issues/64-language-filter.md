---
key: 64
title: feat(ui): "Show games in other languages" filter
type: Feature
labels: milestone::M2, type::feature, priority::low, app
parent: 4
blocked_by: 15, 42, 47
---
> **Risk tier:** medium · **Size:** XS

## Tasks

- [ ] `LanguageFilter(Gtk.Filter)` in `dailies/ui/filters.py`, added to the `Gtk.EveryFilter` (#42). When `show-other-languages` is **false**, hide games whose `language` doesn't match the system locale's language (`GLib.get_language_names()`; compare the primary subtag, e.g. `nl` from `nl_NL.UTF-8`). A game without a `language` counts as `en`
- [ ] The **Favorites** section is exempt; a favourite is never hidden by this filter
- [ ] **Preferences** (#47) → Catalog group: `Adw.SwitchRow` "Show games in other languages", bound with `Gio.Settings.bind`. Subtitle: "Games in languages other than your system language"
- [ ] Default comes from #15 (proposed `true`). The key already exists from #38; change the default there if #15 decides otherwise
- [ ] Hide sidebar categories that become empty under the filter (the same rule as #41)

## Acceptance criteria

- [ ] With `LANG=en_US.UTF-8` and the switch off, Woordle (`nl`) disappears from Words but stays in Favorites if starred
- [ ] With `LANG=nl_NL.UTF-8` and the switch off, English games disappear
- [ ] Toggling takes effect immediately, with no restart

## References

- [`mvp-first.md` §3.3, §4.6, §18.11](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`dle-catalog.md` §5.9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)
