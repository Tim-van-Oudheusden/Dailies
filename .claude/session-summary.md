# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-14. #454 on `test/454-gi-mutant-gate` (GI-only mutant gate).

- **Outcome:** `tests/gi/mutants.py` holds hand mutants of `dailies/` outside `dailies/core`, and
  `tests/gi/test_mutants.py` (Meson test `mutants`, suite `gi`, broadwayd only) runs each row's GI test on a mutated
  copy of `dailies/` with a control run. First rows: #449's `fetcher.py` error (new
  `test_a_network_error_names_its_cause_in_the_warning`), #422's two `browser_page.py` dialog mutants, #431's
  `tile.py` description and `game_object.py` handler-order mutants.
- **Open follow-ups:** none filed. The `.blp` halves of #431 stay with hand sweeps (a rebuild per row).
- **Gotchas:**
  - No GI on the agent host: the harness was smoke-tested on a fake tree only; the rows themselves are verified by
    CI's `Flatpak (x86_64)`.
  - The runner exits 2 when the test module does not import and 3 when the test skips; only 1 counts as a kill.
