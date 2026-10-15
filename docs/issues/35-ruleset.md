---
key: 35
title: chore(repo): commit and apply the branch ruleset for main
type: Task
labels: milestone::M0, type::chore, priority::high, ci
parent: 2
blocked_by: 27, 28, 29
---
> **Risk tier:** high · **Size:** XS · **Who:** owner (admin API call)

## Why

`main` has to be protected by the same four required checks MinimalUI uses. GitHub only accepts a required-check context that **has already run once on `main`**, so this ticket waits for #27, #28 and #29 to merge.

## Tasks

- [ ] `.github/rulesets/main.json`: copy MU's file ([`hive-acmm.md` Appendix A.15](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md); it matches MU's live ruleset 24941495). Settings: target `~DEFAULT_BRANCH`; pull request required with **0 approvals**; merge method **merge commit only**; no force pushes; no deletion; required status checks:
  - `PR review rubric` (#29)
  - `Build, lint, test` (#27)
  - `Unit-test coverage floors` (#28)
  - `Static checks` (#27)
- [ ] Keep the repository-admin **bypass**. Bot data PRs opened with `GITHUB_TOKEN` run no checks, so the maintainer merges them with the bypass until #79 adds `DATA_BOT_TOKEN`
- [ ] Apply it: `gh api -X POST repos/Tim-van-Oudheusden/Dailies/rulesets --input .github/rulesets/main.json`. If it already exists, use `-X PUT …/rulesets/<id>`

## Acceptance criteria

- [ ] `gh api repos/Tim-van-Oudheusden/Dailies/rulesets` lists the ruleset, active
- [ ] A test PR with a failing `Build, lint, test` cannot be merged by a non-admin
- [ ] The committed JSON and the live ruleset agree (record the ruleset id in the PR)

## References

- [`mvp-first.md` §2 tree (rulesets), §7.4 (bypass), §11 (Repository settings)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`scaffolding-repos.md` §1, §8.7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md)
