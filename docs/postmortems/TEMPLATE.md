<!--
Copy this file to docs/postmortems/YYYY-MM-DD-short-slug.md and fill it in.
See docs/postmortems/README.md for when to write one and the blameless framing.
Delete this comment block once copied.
-->

# <Short, specific title: what broke, not just "incident">

**Date:** <YYYY-MM-DD> &nbsp;&nbsp; **Author:** <who wrote this up>

## Summary

One or two sentences: what broke, for how long, and who/what was affected (if known).

## Impact

What a user would have seen, and for how long. Say which path it reached them by: a release bundle (only users who
installed that version) or the catalog and popularity data (every installed app that refreshed in the window). Be
explicit about what you *don't* know: the app sends no telemetry, so the number of affected users is usually
unknowable. Note which sources you actually had (issue reports, release download counts, workflow runs, a manual
check) rather than estimating without saying so.

## Timeline

All times in UTC. Pull exact timestamps from workflow runs, commits, release pages and issue comments where possible
rather than reconstructing them from memory.

| Time | Event |
| --- | --- |
| | Detected — how, and by whom/what (nightly compliance, the link checker, a user's issue, a manual check) |
| | Mitigated — what stopped the user-visible impact |
| | Resolved — what fixed the underlying cause |

## Detection

How this was noticed. If a scheduled check caught it (nightly compliance, the weekly link check), link the run. If it
was noticed some other way (a user's issue, a manual check), say what the gap was between the problem starting and it
being noticed — that gap is itself a finding worth a follow-up if it's long, since there's no alerting backend to
shorten it automatically.

## Root cause

What actually caused it — not just the proximate trigger. "A game URL redirected to another site" is the trigger; the
root cause is *why* it got into, or stayed in, the catalog.

## Resolution

What fixed it. A reverted data commit or a fix-forward release stops the impact; say so, and then focus on the change
that keeps it from happening again. If users had to act themselves (install a new bundle, clear website data), say how
they were told.

## Follow-up

- [ ] Link any filed GitHub issue(s) for the underlying fix
- [ ] If a lesson here should become a standing rule, say where it was encoded (a test, `AGENTS.md`, a runbook)
      or file a follow-up issue if it hasn't been yet
- [ ] Add this postmortem to the index in `docs/postmortems/README.md`
