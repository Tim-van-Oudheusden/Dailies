---
key: 38
title: feat(settings): GSettings schemas and favourites store
type: Feature
labels: milestone::M1, type::feature, priority::high, app
parent: 3
blocked_by: 24
---
> **Risk tier:** high (`*.gschema.xml.in`) and medium (`dailies/data/favorites.py`) · **Size:** S

## Why

Favourites, preferences and window state all live in GSettings. The favourites list is small, needs no schema versioning, survives reinstalls through `~/.var/app/<id>/config/glib-2.0/settings/keyfile`, and Cartridges' `rewrite` proves that `as`/`aa{sv}` collections work in GSettings. Nothing leaves the device and no account is needed (brief: "No account creation required").

## Schema `data/io.github.tim_van_oudheusden.Dailies.gschema.xml.in`

Copy it **exactly** from [`mvp-first.md` §3.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md). The id and path are `@APP_ID@`-templated so the Devel build gets its own settings.

| Schema | Key | Type | Default | Notes |
|---|---|---|---|---|
| `@APP_ID@` | `favorites` | `as` | `[]` | Favourite game ids in display order (insertion order, newest last) |
| | `open-mode` | enum `OpenMode {in-app=0, external=1, custom=2}` | `'in-app'` (per #9) | |
| | `external-browser-command` | `s` | `''` | Used by #63; the description explains the `flatpak override` requirement |
| | `clear-web-data-on-exit` | `b` | `false` | Used by #46/#47 |
| | `sort-mode` | enum `SortMode {default=0, name=1, difficulty=2}` | `'default'` | `default` = shelf rank / favourite order / name |
| | `show-other-languages` | `b` | `true` (per #15) | **Key added now**; the UI comes in #64 |
| `@APP_ID@.State` | `width` / `height` | `i` | `1100` / `760` | |
| | `is-maximized` | `b` | `false` | |
| | `last-section` | `s` | `'favorites'` | |

Enum keys are stored as strings. Python reads them with `get_string` (or `get_enum`).

Deferred keys are **not** added now: `session-isolation`, `cookie-policy`, `itp-enabled`, `hardware-acceleration`, `user-agent`, `developer-extras`. They are additive (#74).

## `dailies/data/favorites.py`

- `class Favorites(GObject.Object)` wrapping the `favorites` key
- `is_favorite(id) -> bool`, `toggle(id) -> bool` (returns the new state; appends on add, removes on remove), `add(id, index=None)` (used by undo to restore the original position), `order() -> list[str]`
- Emits `changed(id: str)`
- Reacts to external changes (`changed::favorites` on the `Gio.Settings`) so `gsettings set` from a terminal updates the UI

## Tests

- [ ] `glib-compile-schemas --strict --dry-run` (the Meson test from #24) passes
- [ ] A Meson-registered Python test using `GSETTINGS_BACKEND=memory`: toggle on/off, order preserved, undo restores the index, `changed` emitted once per toggle

## Acceptance criteria

- [ ] `gsettings --schemadir _build/data list-recursively io.github.tim_van_oudheusden.Dailies.Devel` lists every key above with its default
- [ ] The tests pass inside `flatpak-builder --run-tests` (CI job `Flatpak (x86_64)`)

## References

- [`mvp-first.md` §3.3, §4.5, §6.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`libadwaita-ui-patterns.md` §11](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
- [`cartridges.md` §6.2, §7, Appendix E.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)
