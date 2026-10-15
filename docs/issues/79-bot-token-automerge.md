---
key: 79
title: ci(data): DATA_BOT_TOKEN so data PRs run CI; auto-merge after probation
type: Task
labels: milestone::M5, type::task, priority::low, ci, data
parent: 7
blocked_by: 35, 59, 62
---
> **Risk tier:** high · **Size:** S · **When:** after a month of clean popularity runs, or when submission volume makes manual merging a chore

## Why

PRs opened with `GITHUB_TOKEN` don't trigger `pull_request` workflows, so bot data PRs show no checks and need the admin bypass (#35, #59). A dedicated token fixes that and makes auto-merge safe.

## Tasks

- [ ] Create a **fine-grained PAT** (or a GitHub App token) `DATA_BOT_TOKEN`, scoped to this repo only, with `contents: write` and `pull-requests: write`, and an expiry plus a rotation reminder in `docs/runbooks/`
- [ ] Use it as `token:` in `create-pull-request` in `game-submission-approve.yml` (#59) and `popularity.yml` (#62)
- [ ] Turn on Settings → General → "Allow auto-merge"
- [ ] For `popularity.yml` PRs only, after probation: `gh pr merge --auto --merge "$PR_URL"` (merge commits only, matching the ruleset). The required checks (#35) must pass first
- [ ] Game-submission PRs stay **human-merged** (new URLs are higher risk)
- [ ] Update `SECURITY-AI.md` with the token's scope and the rule that it is never available to `claude.yml`

## Acceptance criteria

- [ ] A bot PR shows all four required checks
- [ ] A popularity PR auto-merges once green; a submission PR does not

## References

- [`mvp-first.md` §7.4, §8 (Review gate), §16 (M5), §17 risk 12](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §1.4 (token facts, auto-merge)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
