# Issue backlog (drafts)

These files are the implementation backlog for Dailies: 84 GitHub issues derived from
[`../proposals/mvp-first.md`](../proposals/mvp-first.md), with detail from [`../research/`](../research/README.md).
They live here because the session that wrote them could not create issues (the GitHub integration returned
`403 Resource not accessible by integration`). Once they exist on GitHub, this directory can be deleted.

## Format

One file per issue, `NN-slug.md`, where `NN` is the issue number the drafts expect on an empty repository.

```text
---
key: 42                         # expected issue number
title: feat(ui): game grid, ...
type: Feature                   # GitHub issue type (Task | Feature)
labels: milestone::M1, type::feature, priority::high, app
parent: 3                       # epic: becomes a GitHub sub-issue link
blocked_by: 39, 40, 41          # becomes "Blocked by" / "Blocks" sections and native dependencies
---
body (Markdown; #N refers to draft N)
```

The **Dependencies** section of each issue (Blocked by / Blocks, with titles) is generated from `blocked_by`, and
so are the roadmap table (`{{TABLE}}`) and the epic checklists (`{{CHILDREN}}`). Edit `blocked_by`, not the prose.

## Index

| Range | What |
|---|---|
| 01 | Roadmap: master tracking issue with milestone table, critical path and every blocker |
| 02–07 | Epics M0–M5 |
| 08–17 | Owner decisions from proposal §18, each with a proposed default |
| 18–36 | M0 Scaffold (Hive ACMM L5, Meson/Flatpak skeleton, CI) |
| 37–55 | M1 Usable launcher → v0.1.0 |
| 56–65 | M2 Data pipeline → v0.2.0 |
| 66–71 | M3 Agentic report and hygiene → v0.3.0 |
| 72–73 | M4 Distribution (Flathub or Pages remote) |
| 74–84 | M5 Growth backlog |

## Creating the issues

Requires `gh` authenticated with issues write access on the repository.

```sh
python3 docs/issues/create_issues.py --repo Tim-van-Oudheusden/Dailies --dry-run | less   # preview
python3 docs/issues/create_issues.py --repo Tim-van-Oudheusden/Dailies
```

The script creates the labels (`gh label create --force`), creates all issues in key order, then fills in every body
with references remapped to the real numbers, so it stays correct even if the repository already has issues. It
then sets the issue type, links each issue to its epic as a sub-issue, and records native "blocked by"
dependencies. Progress is saved in `.created.json` (git-ignored), so an interrupted run resumes where it stopped.
