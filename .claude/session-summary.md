# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-15. #467 on `ci/467-overlay-redirect-dir` (EXDEV on AWS runners; #456 step 2).

- **Outcome:** `ci.yml`'s `Show container filesystem` step also prints every overlay module parameter
  (`/sys/module/overlay/parameters/*`, as `path:value`), so `redirect_dir` and `index` show up next to the mount
  options. Diagnostics only; the job still fails on EXDEV.
- **Open follow-ups:** #467 stays open. On the next AWS-hosted `Flatpak (x86_64)` job, compare those lines with an
  Azure job; if `redirect_dir` is `N` on AWS only, move the runtime installation onto the bind-mounted workspace as
  #456 describes, otherwise re-triage. #399's other rows.
- **Gotchas:**
  - The runner's cloud is in the `Set up job` log group (`Cloud: AWS`/`Azure`); the kernel suffix (`-aws`/`-azure`)
    in `uname -r` says the same.
  - A full `/tmp` (tmpfs quota) makes `pytest` fail by the hundreds with `Disk quota exceeded`; point `TMPDIR` at disk.
