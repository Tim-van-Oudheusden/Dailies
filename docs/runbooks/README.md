# Runbooks

What to do when something goes wrong in production. For Dailies that means what users already have or are about to
receive, not a running server: the published Flatpak bundles, the catalog and popularity files every installed app
fetches from GitHub, and the scheduled workflows that keep those files current. The app has no backend and collects no
telemetry (see [`docs/metrics/README.md`](../metrics/README.md)). Every runbook here starts from a user-visible symptom
and ends with the concrete commands that resolve it.

## Format

One Markdown file per scenario, with:

- **Symptom** — what a user or the maintainer observes.
- **Why this app is different** — the Dailies-specific risk, if any (see below).
- **Response** — ordered steps, maintainer-side and user-side.
- **Prevention** — what already guards against this, and what does not.

## Why runbooks matter here

Dailies ships two things on separate paths, and neither can simply be pulled back:

- **Release bundles do not update themselves.** A user who installed `Dailies-x86_64.flatpak` keeps that version until
  they install the next bundle by hand, so a bad release is fixed forward with a new one, and the fix has to reach
  users through the release notes and the issue tracker.
- **Data reaches every user without a release.** Each installed app revalidates `games.json` and `popularity.json`
  from GitHub every few hours. The app checks a download before replacing its cached copy and keeps the last good one,
  but a valid file with wrong content (a dead or hijacked game URL, a broken shelf) reaches every user within hours.

Every runbook here should say which of the two paths it concerns.

## Index

- [Re-enable a scheduled workflow](re-enable-cron.md): no Monday popularity pull request; the app shows "as of".
