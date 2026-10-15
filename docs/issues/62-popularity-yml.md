---
key: 62
title: ci(popularity): weekly popularity.yml (numbers-only PR)
type: Task
labels: milestone::M2, type::task, priority::high, ci, data
parent: 4
blocked_by: 18, 61
---
> **Risk tier:** high · **Size:** S · **Brief:** "A GitHub Action plus agentic work composes a popularity report on a set cadence (start with weekly)."

## Workflow `.github/workflows/popularity.yml`

Use the skeleton in [`data-pipeline.md` Appendix A4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md). M2 ships the **numbers only**; #66 adds the Claude step.

- **Triggers:** `schedule: cron: '17 4 * * 1'` (Monday 04:17 UTC, deliberately not minute 0), and `workflow_dispatch` with a boolean input `narrate` (default false; unused until #66)
- **Job `compute`** (`contents: read`):
  1. checkout
  2. setup-python and `pip install --require-hashes -r scripts/requirements.txt`
  3. `collect.py`, then `compute.py` (#61)
  4. `check-jsonschema` on the result
  5. upload the **raw signals as an artifact with 90-day retention**, plus the new `popularity.json` and `summary.json`
- **Job `publish`** (`contents: write`, `pull-requests: write`):
  1. download the artifacts
  2. **guard**: a `git status --porcelain` check fails if anything except `data/v1/popularity.json` (and, from #66, `docs/popularity/*`) changed
  3. `peter-evans/create-pull-request@5f6978fa… # v8.1.1` with `branch: data/popularity`, title `data(popularity): week 2026-W43`, labels `data, automated`, and a body containing the top-5 table and source health
- **Review gate:** a PR plus a human merge; `main` is protected. Auto-merge after a month of clean runs is #79
- Concurrency: one run at a time

## Runbook

- [ ] `docs/runbooks/re-enable-cron.md`: public-repo scheduled workflows are **disabled after 60 days without repository activity**. The runbook explains how to notice (no Monday PR, and the app shows "as of <date>") and how to re-enable the workflow from the Actions tab. `valid_until` (+10 days) keeps the shelves looking current in the app in the meantime

## Acceptance criteria

- [ ] A `workflow_dispatch` run opens a PR that changes only `data/v1/popularity.json`
- [ ] A forced Tranco failure (bad API URL on a scratch branch) makes `compute` fail and opens **no** PR
- [ ] **Milestone exit:** one *scheduled* Monday run's PR merged (record the PR in #65)

## References

- [`mvp-first.md` §8 (Workflow, Review gate), §17 risk 6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §5, Appendix A4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
