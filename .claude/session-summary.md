# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-01. #311 on `ci/311-ai-audit-trail`.

- **Outcome:** `ai-audit.yml` (Mon 06:17 UTC, past 7 days; manual with `days`) runs `scripts/ai-audit-report.sh` over
  the PRs merged into `main` and attributes each to Hive (`— hive:` signature, agent and model from it, or the
  `hive-forge-app` author), Claude Code (CI) (`claude/*`), Dependabot (`dependabot/*`) or Other, with author and
  merger. Job summary plus a 90-day `ai-audit` artifact with the raw PR JSON. Ported from MinimalUI (#256); the rules
  match Dailies' real PRs (maintainer's local agent signs `— hive: backend=omp`). Tests:
  `tests/scripts/test_ai_audit_report.py`, a `JOB_PERMISSIONS` row. Satisfies `aef:audit-trail`.
- **Open follow-ups:** none. The PR touches `.github/workflows/`, so the maintainer merges it.
- **Gotchas:**
  - A host jq older than 1.7 (or `jaq`) fails the jq-based script tests; CI's jq passes them.
  - `gh pr list` names a GitHub App author `app/<slug>`, the REST API `<slug>[bot]`; the script accepts both.
