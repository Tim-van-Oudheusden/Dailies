# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-04. #353 on `test/353-page-title-escaped-tag`.

- **Outcome:** `test_report_keeps_submitted_text_inside_its_table_cell` wrote a literal `<img src=x>` in the page
  title; CPython 3.12.12/3.13.6 made `html.parser` treat `<title>` as escapable raw text, so older patches dropped the
  tag and failed the test. The page now writes `&lt;img src=x&gt;`, which every release decodes to the same title;
  the assertion is unchanged. Passes on 3.12.11, 3.12.16, 3.13.5 and 3.13.6; removing the pipe escape still fails it.
- **Open follow-ups:** none. `_TitleParser` is left alone on purpose (production runs the newest 3.12).
- **Gotchas:**
  - CI's `python-version: "3.12"` only ever tests the newest patch; `uv python install 3.12.11 3.13.5` plus
    `uv run --no-project --python <v> --with-requirements scripts/requirements.txt --with pytest==9.1.1 pytest` checks
    older supported patches in seconds.
