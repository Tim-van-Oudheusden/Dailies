---
key: 9
title: Decision: default open mode (built-in browser vs default browser)
type: Task
labels: decision, milestone::M1, priority::high
parent: 3
---
## Question

When a user clicks a game for the first time, does it open in the **built-in WebKitGTK page** (`open-mode = 'in-app'`) or in the **system default browser** (`'external'`)?

The brief's order is "configured browser → built-in browser → external browser" and must be configurable. Inside the Flatpak a *specific* host browser is unreachable without a sandbox escape, so the realistic choice for the default is between in-app and external ([`embedded-browser.md` §4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)).

## Options

| Option | For | Against |
|---|---|---|
| **in-app (proposed)** | The differentiator over a bookmark folder; Obsidian-style "web viewer" is what the brief describes; one shared persistent session keeps streaks and logins across sibling games (NYT) ([`embedded-browser.md` §9.5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)) | NYT ToS (effective 2026-01-20) restricts "display (including framing and inline linking)". A top-level WebView is a browser, not a frame, but that is a legal judgement **[U]** ([`embedded-browser.md` §7.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md), [`dle-catalog.md` §3.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)) |
| external | Zero ToS exposure; [`dle-catalog.md` §5.7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md) recommends it | Dailies becomes a bookmark list; game state lives in whatever browser the user has |

## Proposed default

**in-app**, with these mitigations:

- a first-run `Adw.Banner`: "Games open inside Dailies. You can change this in Preferences."
- "Open in Browser" (Ctrl+Shift+O) on every game page
- "Default browser" one setting away
- no injection, no ad blocking, no UA spoofing

Revisit if a publisher objects.

## How to close

Comment with the choice and close. #45 sets the GSettings default (`open-mode`) and the first-run banner accordingly. This only changes a default value, so #45 can start before this closes and adjust the value at the end.

## References

- [`mvp-first.md` §5.1, §14, §17 risk 2, §18.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
