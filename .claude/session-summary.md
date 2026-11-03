# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-03. #337 on `test/337-manifest-sandbox-parity`.

- **Outcome:** `tests/tooling/test_manifest_parity.py` requires the Devel manifest to equal the release manifest once
  the keys that differ on purpose are removed (top-level `id`, `tags`, `desktop-file-name-suffix`; the `dailies`
  module's `run-tests`, `config-opts`, `sources`). Review on PR #338 turned the first allow-list (`finish-args`,
  `cleanup`) into this deny-list. Checked against 16 one-manifest mutants (permissions, cleanup, `command`, `sdk`,
  `runtime`, SDK extensions, build options, an extra module, app-module keys): all fail; a release tag bump, an extra
  release `config-opts` entry and dropping Devel `run-tests` still pass. Documented in CONTRIBUTING's quality-gates
  paragraph.
- **Open follow-ups:** none.
- **Gotchas:**
  - Host Python 3.11 cannot import `dailies/core` (use a 3.13 venv); the host `jq` is jaq, which fails the
    `pr-metrics`/`auto-qa-tuner`/`quality-report` tests on `main` too.
