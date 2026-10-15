---
key: 20
title: chore(repo): editor/git hygiene, pyproject.toml (ruff, pytest, coverage) and tests/ skeleton
type: Task
labels: milestone::M0, type::chore, priority::high, ci
parent: 2
---
> **Risk tier:** medium · **Size:** S · **ACMM:** `prereq-test-suite`, `prereq-code-style`, `editor-config`, `prereq-e2e` (by directory name)

## Why

This is the base layer every other ticket formats, lints and tests against. Ruff config lives in `pyproject.toml`; there is **no `ruff.toml`**, because `pyproject.toml` + `.editorconfig` already satisfy ACMM `prereq-code-style`.

## Tasks

- [ ] `.editorconfig`: start from MinimalUI's base and add sections `[*.py] indent_size = 4`, `[meson.build] indent_size = 2`, `[*.blp] indent_size = 2`, `[*.json] indent_size = 2`. Flatpak manifests are 2-space JSON, as in Cartridges and Bazaar; Flathub's "4-tab" wording is ambiguous ([`flatpak-release-pipeline.md` §10](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md))
- [ ] `.gitattributes` and `.git-blame-ignore-revs` from MinimalUI
- [ ] `.gitignore`: keep MinimalUI's secrets/agent blocks and add `_build/`, `.flatpak-builder/`, `repo/`, `*.flatpak`, `subprojects/blueprint-compiler/`, `.coverage`, `coverage.xml`, `__pycache__/`
- [ ] `pyproject.toml` with:
  - `[tool.ruff]`: target `py312`, line length 120. Base on Cartridges `rewrite` (`select = ["ALL"]` plus its ignore list, [`cartridges.md` Appendix F.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)), trimmed to what this codebase needs
  - `[tool.ruff.format]`
  - `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `markers = ["e2e: needs a display and the installed app"]`, and e2e excluded by default (`-m "not e2e"`)
  - `[tool.coverage.run]` / `[tool.coverage.report]`: `source = ["dailies/core", "scripts"]`, Cobertura via `pytest --cov-report=xml`
- [ ] `.pre-commit-config.yaml` (from Cartridges `rewrite`, [`cartridges.md` Appendix F.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)): `ruff`, `ruff-format`, `blueprint-compiler format`, `meson format`. Hooks pinned by tag
- [ ] `tests/` skeleton, with **one passing test per directory** so CI is green from day one: `tests/core/`, `tests/scripts/`, `tests/tooling/`, `tests/data/`, `tests/e2e/` (the e2e placeholder is marked `e2e` and skipped until #49)
- [ ] Code targets **Python ≥ 3.12** (runtime 49 ships 3.13.15; 51 is probably 3.14, confirmed by #19)

## Acceptance criteria

- [ ] `ruff check . && ruff format --check .` passes on the empty tree
- [ ] `pytest` passes locally with only `pip install pytest pytest-cov`, and no GNOME SDK needed
- [ ] `pre-commit run --all-files` passes
- [ ] The paths `pyproject.toml`, `tests/`, `tests/e2e/` and `.editorconfig` all exist, matching ACMM L0 file-existence checks ([`hive-acmm.md` §4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md))

## References

- [`mvp-first.md` §1 (Code style, Tests), §2 tree](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`scaffolding-repos.md` §8.3, Appendix B (`.editorconfig`)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md)
