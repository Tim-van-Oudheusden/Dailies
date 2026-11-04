# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-04. #345 on `fix/345-hive-worker-bee-login`.

- **Outcome:** the Hive GitHub App was renamed `hive-forge-app` → `hive-worker-bee` (same id 335687290), and GitHub
  reports the new login for old PRs too. `scripts/pr-metrics.sh` and `scripts/ai-audit-report.sh` now accept
  `app/hive-worker-bee` and `hive-worker-bee[bot]` alongside the old pair; fixtures with the new login fail on the old
  scripts. Prose naming the App (CONTRIBUTING, `docs/`, the `pr-metrics.yml` header) now names `hive-worker-bee`.
- **Open follow-ups:** none. `docs/research/` and `docs/proposals/` keep the old name as historical record; the quoted
  `claude-code-action` error in `claude.yml`/`docs/multi-agent.md` is left verbatim.
- **Gotchas:**
  - Host `jq` is jaq and host Python is 3.11: fetch jq 1.7.1 into `PATH` and use a 3.12 venv with
    `scripts/requirements.txt`; run `python -m pytest` (the venv's `pytest` entry point did not see `ruamel`).
