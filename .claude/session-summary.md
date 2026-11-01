# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-01. #309 on `docs/309-agent-task-traceability` (ACMM L6 `aef:task-traceability`).

- **Outcome:** `docs/agent-tasks/README.md` describes the issue → claim → branch → commit → PR → merge → close chain
  for Dailies (what the `PR review rubric` check enforces, what is convention, how to follow it either way, how
  `session-summary.md`, `corrections.tsv` and `docs/reflections/` sit beside it). Linked from README, CONTRIBUTING,
  `docs/README.md` and `docs/multi-agent.md`. Docs only; `scripts/acmm-self-check.py` accepts `docs/agent-tasks/`.
- **Open follow-ups:** none.
- **Gotchas:** Hive's topic branches (`quality/test-…`) and `claude/*` branches carry no issue number, so the PR body's
  `Fixes #N` is the authoritative link, not the branch name.
