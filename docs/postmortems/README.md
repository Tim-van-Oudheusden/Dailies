# Postmortems

A record of what actually happened during a production incident, written up after the fact: a broken release, bad
catalog or popularity data that reached users, a game link that turned malicious while in the catalog, a scheduled
workflow that stopped without anyone noticing. Distinct from [`docs/reflections/`](../reflections/README.md), which is
cross-session knowledge for **agent work** (a tooling surprise, an environment quirk); a postmortem is about what
happened to **users**.

There is no alerting backend here (see [`docs/metrics/README.md`](../metrics/README.md)): the app sends no telemetry
and no incident is paged, so writing one up is always a deliberate, after-the-fact choice, not a process triggered
automatically. What to do while an incident is still going on is in [`docs/runbooks/`](../runbooks/README.md).

## When to write one

- A published release had to be replaced by a fix-forward release.
- A data change (`data/v1/games.json` or `popularity.json`) reached users and had to be reverted or corrected.
- A catalog entry led users to a site it should not have (a hijacked or redirected domain), whether the link checker
  caught it or a user did.
- Any other user-visible failure: the app failing to start for some users, website data lost, a scheduled workflow
  disabled long enough for the shelves to go stale.

Writing one is optional for a near-miss that was caught before it reached users — use judgement; the bar is "would the
next person investigating a similar symptom want this."

## Blameless

This is a single-maintainer project, so "blameless" mostly means: write down what the system did and why, not who
pushed the bad commit. The point is a better root cause and a follow-up, not an audit trail.

## Format

Copy [`TEMPLATE.md`](TEMPLATE.md) to `YYYY-MM-DD-short-slug.md` and fill it in. Evidence over recollection: link the
actual workflow runs, commits, releases and issues, and quote the log lines you had at the time, rather than
reconstructing them from memory afterward.

If a postmortem's lesson becomes a standing rule, encode it where it will actually be read again (`AGENTS.md`, a
runbook, a test) and link that from the postmortem's **Follow-up** section.

## Index

- No postmortems yet.
