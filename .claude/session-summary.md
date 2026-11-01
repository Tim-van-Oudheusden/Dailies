# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-01. #305 on `ci/305-merge-queue`.

- **Outcome:** `.github/workflows/merge-queue.yml` and `scripts/merge-queue.sh` (ported from MinimalUI #249/#260 and
  website #967/#983/#986/#994) merge ready PRs one at a time after re-running CI's `Build, lint, test` commands on the
  PR merged onto main. Keep-out labels: `hold`, `blocked`, `sentinel-alert`, `automated` (the last keeps catalog and
  link-status PRs human-merged, #79); high-risk PRs are left for the maintainer. `coverage-gate.yml` gained
  `workflow_dispatch` so the queue can start it on main. `test_workflows.py` counts `merge-queue.sh land` as a merging
  job (row in `AUTO_MERGE_JOBS`) and has `JOB_PERMISSIONS` rows for pick, land and reject. Docs that said "the
  maintainer merges" now describe the queue.
- **Open follow-ups:** none. No repository setting is needed (merge commits are on, the jobs declare their own token
  scopes). The queue only runs once this PR is merged, since `workflow_run` workflows start from main.
- **Gotchas:**
  - The `write` and `edit` tools resolve relative paths against the main checkout, not the worktree; use absolute paths.
  - `GITHUB_TOKEN` merges start no push workflows and close no issues, so `land` dispatches every push-to-main workflow
    (each needs `workflow_dispatch`; `tests/scripts/test_merge_queue.py` checks it) and closes the linked issues.
  - `test_nightly_compliance.py`'s ACMM-gap test scored the real repo and named `acmm:merge-queue`; it now runs a copy
    of the two scripts in an empty checkout, so it holds as the other L6 files land.
