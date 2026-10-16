# Weekly popularity reports

One short report per ISO week about the Popular and Trending shelves in
[`data/v1/popularity.json`](../../data/v1/popularity.json). The numbers come from deterministic Python
(`scripts/popularity/compute.py`, described in [`data-format.md`](../data-format.md#how-method_version-2-is-computed));
Claude only writes the prose around them. The reports are published on GitHub Pages at
`https://tim-van-oudheusden.github.io/Dailies/popularity/<week>.md`, and `popularity.json`'s `report` field points at
the week's report (`../popularity/<week>.md`, relative to the JSON file).

## Format

Each report is `docs/popularity/<week>.md`, named after the ISO week, e.g. `2026-W43.md`. It is English Markdown of
about 400 words, without emoji, and starts with `# Popularity report <week>`, followed by:

- **Overview**: three to five sentences about the week.
- **Popular**: the Popular shelf as a table.
- **Trending**: the Trending shelf as a table.
- **Movers**: the biggest rises and falls in popularity.
- **Data quality**: each source's health and the domains whose score was carried forward from last week.

Every number in a report comes from that week's `summary.json` or `popularity.json`; nothing is rounded, computed or
guessed.

## How a report is made

The `publish` job of [`.github/workflows/popularity.yml`](../../.github/workflows/popularity.yml) runs
`anthropics/claude-code-action` every Monday, and on a manual run with **narrate** ticked. The model reads
`summary.json` and `popularity.json` and may write exactly one file, this week's report. It sees only numbers and
maintainer-approved game names, never issue text or fetched web pages
([`SECURITY-AI.md`](../security/SECURITY-AI.md#the-popularity-report)).

After the model, `scripts/popularity/report_guard.py` fails the job unless the only changes are
`data/v1/popularity.json`, byte-identical to the `compute` job's artifact, and the week's report. Only then does it set
`report` in `popularity.json`. A failed or skipped report never blocks the numbers: the pull request then carries the
shelves alone. A maintainer reviews and merges the pull request, report included.

## Index

The directory is the index: each merged data pull request adds one `<week>.md` file here, and the file names sort by
week. This page lists no reports, because the guard lets the model write only the week's own report. No report has
been merged yet.
