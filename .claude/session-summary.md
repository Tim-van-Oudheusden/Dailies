# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-01. #293 on `test/293-docs-claims`.

- **Outcome:** `tests/tooling/test_docs_claims.py` checks four repeated doc claims against their code: release assets
  (the `release.yml` publish step) in both release diagrams and `bad-release.md`; who merges (`AUTO_MERGE_JOBS`) in
  diagram edges and prose; the data files `fetcher.py` requests in the README privacy bullet and `data/v1/README.md`;
  every workflow with an issue or pull request write scope or the `bot` environment in the "Work the workflows
  generate" table. Drift fixed: four "human merge" sentences (README, `docs/architecture.md`) and three missing table
  rows (`auto-review.yml`, `claude.yml`, `labeler.yml`). `docs/testing.md` has a "Docs claims" row.
- **Open follow-ups:** a new workflow that opens issues or pull requests now fails the suite until it has a row in
  `docs/multi-agent.md`; the metainfo download list stays a manual check.
- **Gotchas:**
  - Host Python 3.11 cannot import `dailies/core` (PEP 695 generics); run `pytest` under 3.12+ (`uv venv -p 3.13`
    plus `scripts/requirements.txt` and `pytest==9.1.1`).
  - A host jq older than 1.7 (or `jaq`) fails the `pr-metrics.sh`, `auto-qa-tuner.sh` and `quality-report.sh` tests
    (`$label`/`$module` are keywords there); CI's jq passes them.
  - Without the GNOME 51 SDK on the host, `scripts/sandbox.sh` runs every gate but the Flatpak build.
