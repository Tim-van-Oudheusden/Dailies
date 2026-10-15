---
key: 6
title: [Epic] M4 Distribution — Flathub or self-hosted remote
type: Task
labels: epic, milestone::M4, priority::medium
parent: 1
---
**Target:** weeks 9–12 · **Source:** [`mvp-first.md` §10, §16 (M4), §17 risk 1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md), [`flatpak-release-pipeline.md` §3, §4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)

## Goal

Make Dailies installable with automatic updates. Path A is Flathub. Path B is the fallback: a GPG-signed OSTree remote on GitHub Pages plus a `.flatpakref` on Releases, used if Flathub rejects Dailies as a "thin wrapper or launcher" or if users ask for updates first.

> [!IMPORTANT]
> Flathub's Generative-AI policy says that **Flathub manifests must not contain AI-generated or AI-assisted content and AI tools must not open submission PRs**. The owner must write #72 personally. Agents may prepare checklists only.

## Exit criteria

- [ ] App installable from Flathub (#72) **or** with `flatpak install --user https://tim-van-oudheusden.github.io/Dailies/io.github.tim_van_oudheusden.Dailies.flatpakref` (#73)

## Sub-issues

{{CHILDREN}}
