---
key: 70
title: feat(ui): toast polish — "Opened in your browser" and consistent undo
type: Feature
labels: milestone::M3, type::feature, priority::low, app
parent: 5
blocked_by: 43, 45
---
> **Risk tier:** medium · **Size:** XS

## Tasks

- [ ] When a game opens **externally** (mode `external`, a WebKit fallback, or a popup handed off), show the toast "Opened in your browser". When `HAVE_WEBKIT` is true, add the action "Open Here", which pushes the built-in page for the same URL ([`embedded-browser.md` §9.5 item 8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md))
- [ ] Audit every toast for consistency:
  - sentence case, no trailing period
  - every destructive or reversible action has Undo: removing a favourite, and clearing site data shows "Website data cleared" with no undo, since it can't be undone
  - default timeout of 5 s
- [ ] Use `Adw.ToastOverlay.dismiss_all()` (libadwaita ≥ 1.7) when navigating away from the library, so stale toasts don't linger

## Acceptance criteria

- [ ] Every toast in the app is listed in the PR description with its text and action
- [ ] "Open Here" works from the external-open toast

## References

- [`mvp-first.md` §4.3, §16 (M3 "undo toasts polish")](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`libadwaita-ui-patterns.md` §4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
