---
key: 27
title: ci: ci.yml — "Build, lint, test", "Static checks", "Flatpak (x86_64)"
type: Task
labels: milestone::M0, type::task, priority::high, ci, flatpak
parent: 2
blocked_by: 20, 24, 25, 26
---
> **Risk tier:** high (`.github/workflows/**`) · **Size:** M · **ACMM:** `prereq-cicd`, `ci-matrix`

## Why

This is the main gate. Two of its job names are **required status checks** in the ruleset (#35), so they must be spelled exactly as below.

## Workflow `.github/workflows/ci.yml`

Triggers: `push: branches: [main]`, `pull_request`, `workflow_dispatch`. Top level `permissions: contents: read`. Every job has `timeout-minutes`. Every `uses:` is pinned to a 40-hex SHA with a `# vX.Y.Z` comment. There is no `${{ github.event.* }}` inside `run:`.

| Job (exact name) | Runs on | Steps |
|---|---|---|
| **`Build, lint, test`** | `ubuntu-latest` | `actions/setup-python`; `pip install ruff pytest pytest-cov pyyaml check-jsonschema`; `ruff check . && ruff format --check .`; `pytest tests/core tests/scripts tests/tooling tests/data`; `check-jsonschema` on `games.json` and `popularity.json` against their schemas |
| **`Static checks`** | `ubuntu-latest` | MU verbatim: **shellcheck 0.11.0** + **actionlint 1.7.12** from SHA-256-pinned release archives. Recompute the hashes if the versions move |
| **`Flatpak (x86_64)`** | `ubuntu-latest`, `container: image: ghcr.io/flathub-infra/flatpak-github-actions:gnome-51, options: --privileged` | `flatpak-builder-lint --gha-format --user-exceptions build-aux/flatpak/lint-exceptions.json manifest build-aux/flatpak/<id>.Devel.json`; `flatpak/flatpak-github-actions/flatpak-builder@v6.8` (SHA `79327416…`, full SHA in [`flatpak-release-pipeline.md` Appendix A.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)) with `bundle: io.github.tim_van_oudheusden.Dailies.Devel-x86_64.flatpak`, `manifest-path: build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json` and `cache-key: flatpak-builder-${{ github.sha }}`. Meson tests run because the Devel manifest's `dailies` module sets `run-tests: true`; that includes the e2e smoke test once #49 lands, and the container provides xvfb; then `flatpak-builder-lint --gha-format repo repo`. The action uploads the Devel bundle as an artifact |

- aarch64 runs **only on release** (#51) to keep PR CI short **[I]**
- Bazaar wraps the builder step with a manual `actions/cache` restore/save and cites upstream issue 239 ("caching is broken upstream"). Read that issue and pick one approach; the research left it open ([`flatpak-release-pipeline.md` §1.4, §10](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md))

## Acceptance criteria

- [ ] All three jobs are green on the PR and on `main`
- [ ] The Devel bundle artifact downloads and installs with `flatpak install --user ./io.github.tim_van_oudheusden.Dailies.Devel-x86_64.flatpak` and opens the M0 window
- [ ] Any Devel-ID linter exceptions found on this first run are recorded in `lint-exceptions.json` (#25), with a comment in the PR
- [ ] `tests/tooling/test_workflows.py` (#33) passes against this file

## References

- [`mvp-first.md` §11 (ci.yml row, shared properties, Devel builds)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`flatpak-release-pipeline.md` §1, §4.5, Appendix A.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
- [`bazaar.md` §8.1, Appendix B](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/bazaar.md)
- [`hive-acmm.md` §9 Phase 2 (`ci-matrix`)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
