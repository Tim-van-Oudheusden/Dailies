---
key: 54
title: docs: README following the MinimalUI skeleton
type: Task
labels: milestone::M1, type::task, priority::medium, documentation
parent: 3
blocked_by: 34, 50, 51
---
> **Risk tier:** low · **Size:** S · **Brief:** "README with the useful features of the owner's other repositories and/or Flatpak repositories."

## Structure (MinimalUI skeleton, [`scaffolding-repos.md` §6, Appendix B `README.md`](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md))

1. **Centred banner:** the app icon (`data/icons/hicolor/scalable/apps/io.github.tim_van_oudheusden.Dailies.svg`) at 128 px, H1 "Dailies", the tagline "Play your daily guessing games in one place"
2. **Link row**, `·`-separated: Download (latest release) · Add a game (new-game issue form) · Flathub (later; leave it out until #72) · buildwithtim.dev
3. **Badges:** `ci.yml`, `coverage-gate.yml`, `v/release?include_prereleases`, `license`, `last-commit`
4. **Two screenshots** from #50, with full-sentence alt text
5. **Status:** an honest one-liner (e.g. "Early: v0.1, Linux Flatpak only.")
6. **About:** five bold-led feature sentences
7. **Installing**, "Pick one":
   - Release bundle: the Flathub runtime prerequisite spelled out, then `flatpak install --user ./Dailies-x86_64.flatpak`, plus a note that bundles don't self-update
   - CI artifact (Devel build)
   - Build from source (`scripts/dev.sh build-devel`)
8. **Adding a game:** link to the issue form and to `docs/data-format.md` for the rules
9. **Tech stack:** Python, PyGObject, GTK 4.24, libadwaita 1.10, Blueprint, Meson, WebKitGTK 6.0, GNOME 51 runtime
10. **Architecture:** the two Mermaid diagrams from #53
11. **Documentation** table
12. **Contributing:** "AI agents follow AGENTS.md"
13. **Acknowledgments:** Cartridges, Bazaar, The Dles by aukspot (seed help, GPL-3.0), Tranco
14. **Non-affiliation disclaimer**, the same text as in About (#48)
15. **Custom browser command:** the `flatpak override --user --talk-name=org.freedesktop.Flatpak io.github.tim_van_oudheusden.Dailies` line, with the sandbox-escape warning. It can live under Installing, or wait until #63 ships
16. **Contact:** including links to the owner's other repositories (MinimalUI, website)
17. **Licence table:** code GPL-3.0-or-later; metainfo CC0-1.0; catalog data CC0; popularity data with attribution

Tone: terse and honest, as in MinimalUI.

## Acceptance criteria

- [ ] Every link resolves; the badges render
- [ ] The install commands were tested against the v0.1.0 release assets before tagging (#55); otherwise the Download link points to the releases page with a "coming soon" note

## References

- [`mvp-first.md` §2.1, §10 (install instructions), §14 (Trademarks)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`flatpak-release-pipeline.md` §2.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
