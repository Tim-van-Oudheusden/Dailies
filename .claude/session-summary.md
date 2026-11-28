# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-28. #561 on `test/561-game-id-parity` (the catalog game-id pattern is restated in `dailies/core/web.py`
`_GAME_ID` and nothing compared it with `catalog.schema.json`).

- **Outcome:** `tests/tooling/test_shared_values.py` has a "catalog game id pattern" row with two new extractor kinds:
  `json_anchored_pattern` (the schema's `$defs/game/properties/id/pattern`, `^`/`$` stripped, failing if the anchors
  go) and `compiled_pattern` (`web._GAME_ID.pattern`, failing if the name is gone or no longer a compiled regex).
  `json_list` now walks the JSON through a shared `json_node`. The docs/testing.md "Tooling" row names the new row.
- **Open follow-ups:** none from #561.
- **Gotchas:**
  - Mutation proof: widening `_GAME_ID` to `{1,63}`, renaming it, or dropping the schema anchors each fails only the new
    row, naming the place.
  - `_GAME_ID` stays private on purpose (hive decision in #561); the test reads it with `getattr`.
