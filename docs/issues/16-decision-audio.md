---
key: 16
title: Decision: request audio (`--socket=pulseaudio`) and when
type: Task
labels: decision, milestone::M3, priority::low, flatpak
parent: 5
---
## Question

Music games (Bandle, Heardle Decades, Songless) need audio in the built-in browser. v0.1 deliberately ships **five** finish-args (`--share=network --share=ipc --socket=fallback-x11 --socket=wayland --device=dri`). Should `--socket=pulseaudio` be added, and when?

- **Wait for user demand (proposed):** add it in the first release after a user asks, and say so in that release's metainfo note. Until then, music games work through "Open in Browser".
- **Add it now:** music games work in-app from v0.1. It adds one permission to justify on Flathub; `embedded-browser.md` lists pulseaudio as part of the minimal WebKit finish-args.

## Proposed default

**Wait.** Decide by the M3 cut at the latest; #69 implements whichever answer is chosen, including the "no" case (document it).

## References

- [`mvp-first.md` §9, §18.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`embedded-browser.md` §1.4, §9.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)
