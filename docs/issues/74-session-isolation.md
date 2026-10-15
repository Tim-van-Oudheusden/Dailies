---
key: 74
title: feat(browser): per-game session isolation and cookie-policy settings
type: Feature
labels: milestone::M5, type::feature, priority::low, app
parent: 7
blocked_by: 46, 47
---
> **Risk tier:** medium · **Size:** M

## Why

The MVP uses one shared persistent session, so sibling NYT games share a login. Some users want games isolated from each other (privacy, or separate accounts). These were deferred keys from the browser research. They are additive, so nothing needs migrating.

## Tasks

- [ ] GSettings keys (`@APP_ID@` schema):
  - `session-isolation` enum `{shared, per-game}`, default `shared`
  - `cookie-policy` enum `{always, no-third-party, never}`, default `always`
  - `itp-enabled` `b` (Intelligent Tracking Prevention)
  - `hardware-acceleration` enum `{always, never}`. WebKit 6.0 only offers ALWAYS or NEVER
  - `user-agent` `s` (empty = default)
  - `developer-extras` `b`
- [ ] Relocatable per-game schema `@APP_ID@.Game` at `/…/games/<id>/` with `open-mode-override` and `isolated-session` ([`embedded-browser.md` §9.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md))
- [ ] Per-game mode: `WebKit.NetworkSession.new(data_dir/<id>, cache_dir/<id>)`, each with its own `cookies.sqlite`
- [ ] Preferences → Built-in browser: an expander row with these options. "Clear website data…" must clear every session
- [ ] Moving between shared and per-game doesn't migrate data. Say so in the row subtitle ("Games will need to sign in again")
- [ ] The `user-agent` key is for compatibility fixes only and must never be used to spoof another browser by default (ToS rule, #46)

## Acceptance criteria

- [ ] In per-game mode, logging into NYT in Wordle doesn't log Connections in
- [ ] The default (shared) behaves exactly like v0.1

## References

- [`mvp-first.md` §3.3 (deferred keys), §5.2, §16 (M5)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`embedded-browser.md` §2.1, §2.3, §9.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)
