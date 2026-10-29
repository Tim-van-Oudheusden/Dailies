# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-10-29. ACMM L6 gaps #274 (PR #276, merged) and #277 on `docs/277-multi-agent`.

- **Outcome:** #274: `auto-issues.yml` + `scripts/compliance_issue.py` open, update and close one
  `ci: nightly compliance: N failing checks` issue after each Nightly compliance run on `main`. #277:
  `docs/multi-agent.md` maps how Hive's agents, Claude Code, CLI agents and the workflows share the issue queue.
  The owner wants real artifacts for ACMM gaps, not waivers (`.claude/memory/corrections.tsv`).
- **Open follow-ups:** #278 (owner decision: skip or allow Hive's bot-applied `ai-fix-requested` in `claude.yml`).
  The `v0.3.0` tag is pushed; #206 (after the release) is still open.
- **Gotchas:**
  - Renaming a PR's head branch (`gh api …/branches/<b>/rename`) closes the PR; GitHub only retargets PRs that use the
    branch as their base. Pick the branch type before pushing.
  - Hive's ACMM gap issues carry `ai-fix-requested`, but `claude.yml` fails on bot-applied labels; nobody else picks
    them up automatically.
  - Without the GNOME 51 SDK on the host, `scripts/sandbox.sh` runs every gate but the Flatpak build.
