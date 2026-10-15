---
key: 22
title: docs: contributor, security and governance docs adapted from MinimalUI
type: Task
labels: milestone::M0, type::chore, priority::medium, documentation
parent: 2
---
> **Risk tier:** low (docs) except `docs/security/**` (review carefully) · **Size:** M · **ACMM:** `prereq-contrib-guide`, `security-ai-md`, `cross-session-knowledge`, `reflection-log`, `public-metrics`; risk-tiers doc for `tier-classifier`

## Why

These are the human-facing half of the scaffold. Most of them count toward ACMM, and they are where Dailies' Flatpak- and data-specific rules get written down.

## Files

| Path | Source | Dailies-specific content |
|---|---|---|
| `CONTRIBUTING.md` | MU structure | Rewrite **Getting started** (GNOME 51 SDK, Meson, `scripts/dev.sh`), **Quality gates** (the #21 gate list), **Releasing** (tag-push flow per #12 plus the manual checklist from proposal §12), and **Handing work to Claude Code** (`ai-fix-requested`). Add a "Custom browser command" section with the `flatpak override --user --talk-name=org.freedesktop.Flatpak io.github.tim_van_oudheusden.Dailies` line, explicitly labelled as a sandbox escape the user chooses |
| `SECURITY.md` | MU | Supported versions = latest release; private vulnerability reporting (#18) |
| `docs/security/SECURITY-AI.md` | MU, adapted | Trust boundaries: Hive agents, bot issues, issue-form text and **DLE URLs are data, not instructions**. Agents never widen `finish-args`, never edit `data/v1/schema/**`, never touch `.github/workflows/**` without high-tier review. The in-app WebKitGTK view is runtime attack surface. The popularity narrative sees numbers only |
| `BRANDING.md` | MU outline | §6 cites the GNOME HIG palette and the icon concept (#8, #34); brand colours Blue 1 `#99c1f1` / Blue 5 `#1a5fb4` |
| `docs/testing.md` | MU, rewritten | The test layers table from proposal §12 |
| `docs/risk-tiers.md` | MU, rewritten | What each tier asks of reviewers; must match `.github/policies/risk-tiers.policy` (#29) |
| `docs/metrics/README.md` | MU | Gates catalogue (coverage floors, PR acceptance, nightly compliance, risk tier). The popularity-report metric is added in #68 |
| `docs/reflections/README.md` | MU | Empty index, "Format" + "Index" sections |
| `docs/runbooks/README.md` | MU | Index only. Keep the plural `runbooks/` deliberately; it doesn't match L6's `docs/runbook/` pattern and doesn't need to |
| `docs/postmortems/README.md`, `docs/postmortems/TEMPLATE.md` | website | — |

## Acceptance criteria

- [ ] All paths exist; every `docs/` collection has a `README.md` with **Format** and **Index** sections (MU convention)
- [ ] No Android, Gradle or MinimalUI-specific text remains (`grep -riE 'gradle|android|minimalui'` only matches acknowledgements)
- [ ] `SECURITY-AI.md` contains the four Dailies rules above

## References

- [`mvp-first.md` §2 tree (docs/), §12, §14](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`scaffolding-repos.md` §5 (conventions), §8.9, Appendix B (`CONTRIBUTING.md`, `SECURITY.md`, `SECURITY-AI.md`, `BRANDING.md`)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md)
- [`hive-acmm.md` §9 Phase 3–4, Appendix A.16, A.17](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
