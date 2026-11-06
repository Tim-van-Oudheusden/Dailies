# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-06. #392 on `ci/392-land-dispatch-retry`.

- **Outcome:** `scripts/merge-queue.sh` starts every workflow through `start_workflow`: three tries, 10 s apart, then
  an `::error` with the hand command. `land` starts the rest and the next run after a failure and then exits 1.
  Ported from Tim-van-Oudheusden/website#1199. Three tests and three shell-mutant rows cover it.
- **Open follow-ups:** none.
- **Gotchas:**
  - A row's `old` must occur exactly once. The second `for attempt in 1 2 3; do` loop made the merge-state row
    match twice, so that row now includes the next line too.
  - `Queue.run` now stubs `sleep` for every run, not only the UNKNOWN-merge-state tests.
