# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-01. #308 on `docs/308-ai-ops-runbook`.

- **Outcome:** `docs/ai-ops-runbook.md` answers the on-call questions: the automations and what runs as what, where
  to look (`gh` command per question), Monday routine checks, playbooks (Claude Code skipped or failed, a PR that
  does not merge, `hold` from the merge queue, no CI after a queued merge, the PR review rubric, a permissions-policy
  failure, two agents on one issue, an agent acting outside its instructions) and a stop/undo table per automation
  (workflows, `hold`, revoking the Claude token, Hive, the bot App key). Ported from MinimalUI (#253, #261) and the
  website, adapted to Dailies' workflows, labels and checks. Linked from `README.md`, `CONTRIBUTING.md`,
  `docs/README.md`, `docs/multi-agent.md` and `docs/runbooks/README.md`. Satisfies `acmm:observability-runbook`.
- **Open follow-ups:** none. Docs only; no test, since the siblings added none.
- **Gotchas:**
  - Every command, label, workflow and job name in the runbook was checked against `gh label list`,
    `gh workflow list` and the tree. `merge-queue.yml`, `strategy-report.yml` and `ai-audit.yml` are not on `main`
    yet, so `gh workflow list` omits them until their PRs merge; `gh workflow disable` works once they do.
  - Relative paths in the read and edit tools resolve against the main checkout; pass absolute worktree paths.
