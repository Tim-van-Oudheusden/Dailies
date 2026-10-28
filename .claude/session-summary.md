# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-10-28. Dead `catalog.is_newer` (#262) on `refactor/262-drop-is-newer`.

- **Outcome:** deleted `catalog.is_newer` and its only caller, `test_a_later_generated_at_is_newer`. The
  `core/catalog.py` row of `docs/architecture.md` no longer names it; the `data/store.py` row now says where the
  bundle-vs-cache rule lives (`Store._load`: the cache wins unless the bundled copy has a later `generated_at`, so a
  tie keeps the cache). No behaviour change: nothing in `dailies/` called it.
- **Open follow-ups:** none. Moving that rule into `dailies/core` as a pure function is a separate change the issue
  does not ask for.
- **Gotchas:**
  - No gate finds unused public functions (ruff `ALL` has no such rule, no vulture); grep `dailies/` before trusting
    `docs/architecture.md` about where a rule lives.
  - `docs/proposals/mvp-first.md` still mentions `is_newer`: it is the historical proposal, not the current layout.
