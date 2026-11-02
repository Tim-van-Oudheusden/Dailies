# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-02. #331 on `test/331-shell-mutants`.

- **Outcome:** the owner accepted the shell-mutant gate. `tests/scripts/test_shell_mutants.py` copies the files git
  sees to `tmp_path`, applies one `(script, old, new, node)` row and requires the node to exit 1; a control requires
  each killing node to pass on an unmutated copy. Rows: the four #198 mutants of `scripts/popularity-report.sh` plus
  its `--weeks` guard, and two mutants of the exit-2-with-a-report branch of `scripts/nightly-compliance.sh`, killed
  by the new `test_a_links_check_error_with_a_report_puts_the_report_under_failures` (both survived the 22 nightly
  tests before it). Documented in `docs/testing.md#shell-mutants`.
- **Open follow-ups:** none filed; new rows go in with the test that kills them.
- **Gotchas:**
  - The inner pytest drops the outer `PYTEST_*`, `COV_CORE_*` and `COVERAGE_*` variables and gets its own
    `--basetemp`, so `pytest --cov` and the outer `tmp_path` are not disturbed.
  - Host Python 3.11 cannot import `dailies/core` (use a 3.13 venv); the host `jq` is jaq, which fails the
    `pr-metrics`/`auto-qa-tuner`/`quality-report` tests on `main` too.
