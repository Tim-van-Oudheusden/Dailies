---
key: 28
title: ci: unit-test coverage gate on Cobertura XML (coverage-gate.yml)
type: Task
labels: milestone::M0, type::task, priority::high, ci
parent: 2
blocked_by: 20
---
> **Risk tier:** high · **Size:** S · **ACMM:** `prereq-coverage-gate`, `auto-qa-tuning`, `auto-qa-self-tuning`

## Why

**`Unit-test coverage floors`** is a required check. MinimalUI's `scripts/lib/coverage.sh` parses Kover/JaCoCo output, so it has to be rewritten for Cobertura XML (what `pytest-cov --cov-report=xml` writes). The `{margin, floors}` JSON contract and the exit codes must stay the same so `auto-qa-tuner.sh` and `quality-report.sh` (#30) keep working unchanged.

## Tasks

- [ ] `.github/workflows/coverage-gate.yml`: on `pull_request` and `push: main`; job name **`Unit-test coverage floors`**; runs `pytest --cov=dailies/core --cov=scripts --cov-report=xml` and then `scripts/coverage-check.sh coverage.xml .github/auto-qa-tuning.json`
- [ ] `scripts/lib/coverage.sh`: read `coverage.xml` (`<coverage line-rate=… branch-rate=…>` and per-`<package>` rates) and emit percentages per floor group (`core` = `dailies/core`, `scripts` = `scripts`)
- [ ] `scripts/coverage-check.sh`: MU's script, keeping exit codes **0** (pass), **1** (below floor) and **2** (usage or parse error)
- [ ] `.github/auto-qa-tuning.json`: `{"margin": 2, "floors": {"core": {"lines": 70, "branches": 50}, "scripts": {"lines": 70, "branches": 50}}}`. Start at 70 % lines and let the tuner ratchet it
- [ ] Coverage applies to `dailies/core` and `scripts/` **only**. gi-dependent code (`dailies/data`, `dailies/ui`) is tested by the e2e smoke test, not by unit-coverage floors
- [ ] Add a small Cobertura fixture plus a shell test (`scripts/coverage-check.test.sh`) covering pass, fail and malformed input

## Acceptance criteria

- [ ] The job passes on the scaffold (placeholder tests count; adjust the initial floors if the empty tree can't meet 70 %, and say so in the PR)
- [ ] Deliberately lowering coverage in a test PR makes the job fail with a message naming the group and the floor
- [ ] shellcheck passes on both scripts

## References

- [`mvp-first.md` §11 (coverage-gate row), §12 (Unit row)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`scaffolding-repos.md` §8.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md)
- [`hive-acmm.md` Appendix A.7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
