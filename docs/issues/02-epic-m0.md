---
key: 2
title: [Epic] M0 Scaffold — Hive ACMM L5 repository and an empty Devel Flatpak
type: Task
labels: epic, milestone::M0, priority::high
parent: 1
---
**Target:** week 1 · **Source:** [`mvp-first.md` §2, §11, §16 (M0)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)

## Goal

Copy the owner's MinimalUI scaffolding wholesale and swap the Gradle gates for Meson/ruff/pytest/flatpak-builder. The repository should reach Hive **Codebase Level L5** from its first scaffold. Alongside that, ship a Meson/Blueprint skeleton that builds an empty `Adw.ApplicationWindow` in the `.Devel` Flatpak.

The ACMM result this tree is designed to hit, checked against the 50 criteria in [`hive-acmm.md` §4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md): L0 8/8, L2 8/8, L3 8/8, L4 9/9, L5 5/5, L6 3/12 → **Codebase L5**. That matches MinimalUI and website. L6 is deliberately not pursued.

## Exit criteria

- [ ] Hive ACMM Eval shows **Codebase L5** for `Tim-van-Oudheusden/Dailies` (#36)
- [ ] `Flatpak (x86_64)` job is green on `main` (#27)
- [ ] `flatpak run io.github.tim_van_oudheusden.Dailies.Devel` opens a window (#24, #25)
- [ ] The four required checks (`PR review rubric`, `Build, lint, test`, `Unit-test coverage floors`, `Static checks`) are enforced by the committed ruleset (#35)
- [ ] `games.json` seed + schema + data tests are in place and green (#26)
- [ ] Icon draft committed (#34)

## Sub-issues

Decisions that gate this milestone: #8 (icon colours), #10 (seed scope), #11 (Hive details).

{{CHILDREN}}

## Notes

- Copy files from MinimalUI at HEAD `510282a`. [`scaffolding-repos.md` Appendix B](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md) has them verbatim, and [`hive-acmm.md` Appendix A](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md) has the language-agnostic workflows. Take `docs/postmortems/` from `website`.
- Copy **patterns, not code**, from Cartridges: it is unmaintained and its `rewrite` branch is partly non-functional ([`cartridges.md` §0](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)).
- Do **not** copy MinimalUI's `.beads/` (it carries MinimalUI's `project_id`). See #11.
