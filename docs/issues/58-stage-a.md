---
key: 58
title: ci(data): stage A — validate game submissions (game-submission-check.yml)
type: Task
labels: milestone::M2, type::task, priority::high, ci, data
parent: 4
blocked_by: 18, 23, 57
---
> **Risk tier:** high · **Size:** S · **Security:** untrusted input, read-only contents token

## Workflow `.github/workflows/game-submission-check.yml`

Use the skeleton in [`data-pipeline.md` Appendix A2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md).

- **Trigger:** `issues: [opened, edited]`, with a job-level `if: contains(github.event.issue.labels.*.name, 'game-submission')`
- **Permissions:** `contents: read`, `issues: write`. Nothing else
- **Steps:**
  1. `actions/checkout@3d3c42e5… # v7.0.1`, sparse checkout of `data/`, `scripts/` and `.github/ISSUE_TEMPLATE/`
  2. `stefanbuck/github-issue-parser@cb6e9715… # v3.2.5` with `template-path: .github/ISSUE_TEMPLATE/new-game.yml`
  3. `actions/setup-python@5fda3b95… # v7.0.0`; `pip install --require-hashes -r scripts/requirements.txt`
  4. `python -I scripts/validate_submission.py …` (#57). Every value reaches the shell **only through `env:`**, never as inline `${{ }}` in `run:`
  5. `peter-evans/create-or-update-comment@e8674b07… # v5.0.0`: **one** comment, found by its `<!-- dailies-submission-check -->` marker and updated on every edit. Resolve and pin the SHA for `peter-evans/find-comment` too; it is still unresolved in the research ([`data-pipeline.md` open questions](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md))
  6. Toggle labels with `gh issue edit`: add `validated` and remove `needs-changes` on success, the reverse on failure
- `timeout-minutes: 5`; concurrency group per issue number with `cancel-in-progress: true`

(Full SHAs are in [`data-pipeline.md` §1.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md).)

## Acceptance criteria

- [ ] Submitting a valid game through the form produces one comment with a ✅ table and the label `validated`
- [ ] Editing the issue to a hijacked URL updates **the same** comment to ❌, swaps the label to `needs-changes`, and states the reason
- [ ] An issue without the `game-submission` label doesn't trigger the job
- [ ] A form value containing `$(id)` / `` `id` `` / `"; rm -rf /` is echoed safely in the comment and never executed
- [ ] The workflow passes `tests/tooling/test_workflows.py` (#33)

## References

- [`mvp-first.md` §7.2, §14 (IssueOps)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §1.2, §1.4, Appendix A2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
