# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-01. #312 on `ci/312-workflow-permissions-policy`.

- **Outcome:** the reviewed `GITHUB_TOKEN` grants moved from `JOB_PERMISSIONS`/`TOP_LEVEL_PERMISSIONS` in
  `tests/tooling/test_workflows.py` to `.github/policies/workflow-permissions.yml` (port of website#990, Dailies
  shape: one `default` top-level block, per-job blocks under `jobs:`). Every workflow needs a rule; a rule for a
  missing workflow or job, or an unknown rule key, fails `pytest`. Keeps `acmm:policy-as-code` met once #307 moves
  `risk-tiers.policy` out of `.github/policies/` (checked with `acmm-self-check.py --root` on a copy without it).
- **Open follow-ups:** none. #307 moves `risk-tiers.policy` and so changes `POLICY` in `test_workflows.py`; the
  permissions policy stays in `.github/policies/`.
- **Gotchas:**
  - Host Python 3.11 cannot import `dailies/core` (PEP 695 generics); run `pytest` under 3.12+
    (`~/.local/bin/python3.13 -m venv`, then `scripts/requirements.txt` and `pytest==9.1.1`).
  - The host `jq` is `jaq`, which fails the `pr-metrics.sh`, `auto-qa-tuner.sh` and `quality-report.sh` tests (13
    failures, `$label`/`$module` are keywords there); CI's jq passes them.
  - Without the GNOME 51 SDK on the host, `scripts/sandbox.sh` runs every gate but the Flatpak build.
