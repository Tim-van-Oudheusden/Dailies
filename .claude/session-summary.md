# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-01. #312 on `ci/312-workflow-permissions-policy`.

- **Outcome:** the reviewed workflow token grants moved from `JOB_PERMISSIONS` in `tests/tooling/test_workflows.py` into
  `.github/policies/workflow-permissions.yml` (`default` top-level token plus a `jobs` rule per workflow, review
  comments kept). The test loads it and now also fails for a workflow with no rule, a rule for a missing workflow, or a
  rule for a missing job (the first two are new; every workflow now needs a rule, `{}` for read-only ones). Website#990's
  per-workflow top-level `permissions:` override is not ported: every Dailies workflow keeps exactly `contents: read`.
  Restores `acmm:policy-as-code` once #307 empties `.github/policies/` of `risk-tiers.policy`.
- **Open follow-ups:** none.
- **Gotchas:**
  - `bash` tool cwd is the main checkout; `write`/`edit` with a relative path land there, not in the worktree. Use
    absolute worktree paths.
  - Run `pytest` inside the distrobox with a login shell (`bash -lc`).
