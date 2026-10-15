---
key: 72
title: release(flathub): submit Dailies to Flathub (owner-authored)
type: Task
labels: milestone::M4, type::task, priority::medium, flatpak
parent: 6
blocked_by: 71
---
> **Who:** the owner, personally. **An AI agent must not write the Flathub manifest or open the submission PR.**

> [!IMPORTANT]
> Flathub requirements: "Flathub manifests must not contain AI-generated or AI-assisted content; AI tools must not open submission PRs." This issue is a checklist for the owner. Agents may help only with the in-repo prerequisites (metainfo, screenshots, lint fixes), never with the Flathub-side manifest or PR.

## Readiness checklist

- [ ] ≥ 3 tagged releases and visible users (#71)
- [ ] **Substantial native value**, to clear the "thin wrappers or launchers" / "simple web wrapper" rejection reasons: Favorites, categories, weekly Popular/Trending shelves, search, offline catalog, HIG UI. Write a paragraph for the PR explaining this
- [ ] App ID `io.github.tim_van_oudheusden.Dailies`. Verification requires logging in to Flathub with the GitHub account that owns the repo
- [ ] Runtime is the **latest** GNOME at submission time (bump from 51 if 52 has shipped; GNOME 52 is due 2027-03-17)
- [ ] Metainfo: developer id, launchable, OARS, branding light/dark, screenshots on **tag** URLs (≤ 1000×700 window), releases with dates; `appstreamcli validate` and `flatpak-builder-lint appstream` clean
- [ ] Finish-args justified one line each (table in #25)
- [ ] `flathub.json`: `{"require-important-update": true}`

## Submission flow

1. [ ] Fork `flathub/flathub` and branch from **`new-pr`**
2. [ ] Add the manifest (**written by hand by the owner**) and `flathub.json`
3. [ ] Open the PR "Add io.github.tim_van_oudheusden.Dailies"; comment `bot, build` to trigger a test build
4. [ ] Respond to review

## If rejected as a "launcher"

Proceed with #73 (self-hosted remote). Record the reviewer's reasoning in `docs/architecture.md`.

## Acceptance criteria

- [ ] Dailies is on Flathub, **or** the PR was rejected and #73 is scheduled
- [ ] Add the Flathub badge and "Flathub" link to the README (#54) on acceptance

## References

- [`mvp-first.md` §10 (Flathub), §16 (M4), §17 risk 1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`flatpak-release-pipeline.md` §4, §9 item 7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
