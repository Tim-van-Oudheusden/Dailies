# Testing

How Dailies' tests and quality checks run, and where each one can run.

## Test layers

| Layer | What | Where it runs | Gate |
| --- | --- | --- | --- |
| Unit (pure Python) | `tests/core/`: catalog parsing, including tolerance of an unknown category or status; popularity parsing and staleness; search folding and whether a new query narrows or widens the matches; the cache decisions (`test_cache.py`: maximum age, `If-None-Match`, URL fall-through order, `Retry-After`, validation before any write, atomic cache files, the stale-banner rule); the sidebar sections (`test_sections.py`: categories without an active game hidden, the restored section, the "as of" date of stale shelves, what each section holds (Favorites keep unavailable games, categories only active ones), the default and overriding sort orders, which empty-state page shows). `tests/scripts/`: the submission validator (with fixtures for dead and hijacked domains), the popularity computation on synthetic ranking data, the shared-domain split, the fail-closed threshold, the link checker; the CI scripts (coverage gate, quality report, floor tuner, PR metrics, review-suggestion applier, nightly compliance) run against fixtures and stub tools | `ubuntu-latest`, plain pytest, seconds | `Build, lint, test`; coverage floors on `dailies/core` and `scripts` |
| Data | `tests/data/test_catalog_file.py`: schema, sorted unique ids, unique normalised URLs, every `domain` matches its `url`, enum membership, every id in `popularity.json` exists in the catalog | same | `Build, lint, test` |
| Tooling | `tests/tooling/test_workflows.py` (PyYAML): top-level and per-job permissions, `timeout-minutes` on every job, actions pinned to 40-hex SHAs with version comments, no `${{ github.event.* }}` in `run:`, `pull_request_target` only in `labeler.yml` and without a checkout, labeler and risk-tier policy parity, every `data/v1/*.json` published by `pages.yml` | same | `Build, lint, test` |
| Build validation | Meson tests: `desktop-file-validate`, `appstreamcli validate --no-net --explain`, `glib-compile-schemas --strict --dry-run`, and the Blueprint compile of every `.blp` (a syntax error fails the build) | inside `flatpak-builder --run-tests` | `Flatpak (x86_64)` |
| E2E smoke | `tests/e2e/test_smoke.py`: starts the installed app with the hidden `--smoke` flag, which skips the network refresh and quits half a second after the window has mapped, under `dbus-run-session` on a private `gtk4-broadwayd` display (`GDK_BACKEND=broadway`; the SDK has no Xvfb, and broadway needs no host display) with `GSETTINGS_BACKEND=memory`; asserts exit status 0 within 30 s and no `CRITICAL` or `Traceback` on stderr. A stdlib `unittest` script registered as a Meson test (suite `e2e`); it reports SKIP when the app is not installed, and plain `pytest` deselects it by its `e2e` marker | inside `flatpak-builder --run-tests` | `Flatpak (x86_64)` |
| GI integration | `tests/gi/`: the `dailies/data` and `dailies/ui` classes that need GLib, against the real schema. Stdlib `unittest` scripts (the SDK has no pytest), registered in `tests/meson.build` (suite `gi`) with `GSETTINGS_BACKEND=memory` and `GSETTINGS_SCHEMA_DIR` at the schema compiled into `_build/data`. `tests/gi/test_favorites.py`: toggle on and off, insertion order, undo restoring the index, one `changed` per toggle, external changes to the key. `test_store.py`: cold start from the bundled snapshot, a corrupt or older cache replaced by the bundle, ranks and favourites applied, diff by id on reload, stale popularity, lookup by id. `test_filters.py`: the grid's pipeline (section filter, search filter, section sorter) over `GameObject`s: shelf rank order, categories by name, favourite order with an unavailable favourite kept, the sort mode overriding it, accent-folded search narrowing the current section; the `GameObject` texts that follow its game. `test_tile.py`: the game tile from the built resources on a private Broadway display (`gtk4-broadwayd`): its labels and colour classes following the game, the accessible name and description, opening through `win.open-game`, the star as a separate labelled button. `test_fetcher.py`: the fetcher against a local `http.server` with ETags: unconditional first fetch, no request while fresh, 304 changing only `.fetched`, a truncated body leaving the cache untouched, fall-through on 503 and on a refused connection, the User-Agent. Plain `pytest` skips the directory (`--ignore=tests/gi` in `pyproject.toml`) | `meson test` inside the SDK, so also `flatpak-builder --run-tests` | `Flatpak (x86_64)` |
| Manual before tagging | The checklist in [`CONTRIBUTING.md`](../CONTRIBUTING.md#manual-checklist-before-tagging): three games in-app (one from the New York Times), login and streak kept across a restart, external open, dark style, 360 px width, screen reader names on tiles | the maintainer | — |

Not tested: pixel or UI snapshots, the content of game websites inside WebKit, and platforms other than Linux.

## Running the gates

```sh
ruff check . && ruff format --check .
pytest
meson setup _build -Dprofile=development && meson test -C _build
flatpak-builder --user --install --force-clean _flatpak build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json
```

`pytest` runs the unit, data and tooling layers (the `testpaths` in `pyproject.toml`); it needs no GNOME libraries,
because `dailies/core` and `scripts/` never import `gi`. The native Meson build needs the GNOME 51 libraries on the
host (see [Getting started](../CONTRIBUTING.md#getting-started)). The Flatpak gate needs only Flatpak and the GNOME 51
SDK: the Devel manifest sets `run-tests`, so `flatpak-builder` runs `meson test`, the build validation, the gi tests
and the e2e smoke test inside the sandbox, exactly as CI's `Flatpak (x86_64)` job does in the `gnome-51` image.

To try the app against a local copy of the data, a development build reads `DAILIES_DATA_URLS` (space-separated base
URLs ending in `/`, e.g. `http://127.0.0.1:8000/v1/`) instead of the published URLs; release builds ignore it. Start it
with `G_MESSAGES_DEBUG=all` to see each refresh decision logged.

Validate the data files the way CI does:

```sh
check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json
check-jsonschema --schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json
```

## Coverage floors

Unit-test coverage is measured with [pytest-cov](https://pytest-cov.readthedocs.io/) on two modules: `core`
(`dailies/core`) and `scripts` (`scripts/`). `dailies/data`, `dailies/ui` and the tests themselves are not measured;
the UI is covered by the build validation and the smoke test instead.

```sh
pytest --cov=dailies/core --cov=scripts --cov-report=xml
```

writes a Cobertura-format report to `coverage.xml`. The floors live in `.github/auto-qa-tuning.json`, per group, as
line and branch coverage in percent:

```json
{ "margin": 2, "floors": { "core": { "lines": 70, "branches": 50 }, "scripts": { "lines": 70, "branches": 50 } } }
```

`scripts/coverage-check.sh coverage.xml .github/auto-qa-tuning.json` sums the covered and valid lines and branches of
every file in each group (`core` = `dailies/core`, `scripts` = `scripts`) from the Cobertura report, through
`scripts/lib/coverage.sh`, and compares them with the floors. It prints the observed coverage next to each floor and
exits 1 if a group is below a floor (`::error::<group> <lines|branches> coverage X% is below its floor of Y%`), 2 for a
usage error, an unreadable or malformed report, or a malformed floors file. A group with no measured lines yet is
reported as "no code yet" and passes; so does a missing report, but only while neither group folder holds any Python.
The comparison uses the exact ratio, so 69.999 % does not pass a 70 % floor. `scripts/coverage-check.test.sh` covers
these cases against the fixtures in `tests/scripts/fixtures/coverage/`, and `pytest` runs it.

`.github/workflows/coverage-gate.yml` (job **Unit-test coverage floors**, every PR and push to `main`) runs the check
for every group in the floors file and is a required status check in the `main` ruleset. Adding a group to the gate
means adding it to `.github/auto-qa-tuning.json`, to the `--cov` list and to `scripts/lib/coverage.sh`. Apply the
ruleset entry to the live ruleset only after the workflow has run on `main` once; a required check that never reports
blocks every PR.

Raise a floor when coverage rises; never lower one to make a PR pass. Add tests instead. The floors start at 70 % lines
and 50 % branches and are ratcheted up by the self-tuning below. Run the check locally:

```sh
pytest --cov=dailies/core --cov=scripts --cov-report=xml
scripts/coverage-check.sh coverage.xml .github/auto-qa-tuning.json
```

`pytest --cov=dailies/core --cov=scripts --cov-report=html` writes a browsable report to `htmlcov/`.

## Quality report

`.github/workflows/quality-report.yml` (job **Quality report**: every push to `main`, weekly on Monday at 06:17 UTC,
and on demand) runs `scripts/quality-report.sh > quality-report.md`. The script runs each gate of `Build, lint, test`
separately (`ruff check`, `ruff format --check`, `pytest`, `check-jsonschema` on each data file), then one coverage run
(`pytest --cov=dailies/core --cov=scripts --cov-report=xml`) whose Cobertura report, read through
`scripts/lib/coverage.sh`, gives every module in `.github/auto-qa-tuning.json`, and prints a Markdown report: pass/fail
per gate and line and branch coverage per group. Every gate and the coverage run happen even when an earlier one fails.
If the coverage run fails, or leaves no report, every module shows `❌ n/a`; a report left by an earlier run is deleted
first, so it never stands in for the current run. A module with no measured lines shows `no code yet`, and one with
lines but no branches shows `no branches` for them; neither fails the report. Tool output goes to stderr. The script
exits 1 if anything failed, 2 if the floors file lists no module.

The workflow appends the floor tuning below (even when a gate failed), publishes the result to the job summary and
uploads it as the `quality-report` artifact. Run it locally:

```sh
scripts/quality-report.sh > quality-report.md
```

## Coverage floor self-tuning

`scripts/auto-qa-tuner.sh --report quality-report.md [--config .github/auto-qa-tuning.json] [--write]` reads the
coverage rows of a quality report and proposes, per module and metric (lines, branches), the floor raised to the
observed coverage minus the config's `margin` (in percentage points), rounded down to a whole percent; coverage of
exactly floor + margin proposes no change. Floors only ratchet up: a proposal below the current floor keeps the floor
(a fractional floor is never rounded down), and a metric reported without a percentage (`n/a`, `no code yet`,
`no branches`) keeps its floor. It prints the proposals as a Markdown table (`⬆️` marks a raise); `--write` saves them
to the config, keeping every other key. It exits 2 for a missing report or a malformed config (a floor outside 0–100, a
negative or missing margin, no modules) and then leaves the config untouched.

The quality report workflow runs it with `--write` and uploads the tuned file as the `auto-qa-tuning` artifact. Nothing
is committed automatically: to adopt the proposal, download the artifact, review the diff and commit it in a PR.

## Nightly compliance

`.github/workflows/nightly-compliance.yml` runs nightly (`23 3 * * *` UTC) and on manual dispatch, for checks that can
go stale without a code change. It runs `scripts/nightly-compliance.sh > nightly-compliance.md` and publishes the report
as the job summary and the `nightly-compliance` artifact. The script reports one pass/fail row per check, runs every
check even when an earlier one fails, and exits non-zero if any failed:

| Check | Fails when |
| --- | --- |
| Dependabot alerts (high+) | an open Dependabot alert has severity `high` or `critical` and its GHSA id is not on the ignore list, or the alerts API cannot be read |
| CI tool advisories | `pip-audit` finds a known vulnerability in `scripts/requirements.txt` that is not on the ignore list |
| GNOME runtime | `flatpak remote-info flathub org.gnome.Platform//51` reports the runtime as end-of-life |
| ACMM self-check | `scripts/acmm-self-check.py` finds that a file a Hive ACMM criterion looks for has gone missing |
| Game links (Sundays) | `scripts/check_links.py` finds an active catalog entry that fails, or whose final domain differs from its `domain`; the run also opens one `data` issue listing them |

The alerts come from `gh api repos/$GITHUB_REPOSITORY/dependabot/alerts?state=open`, read with the job's `GITHUB_TOKEN`
through the `vulnerability-alerts: read` permission, so no secret is needed.

### Accepting an advisory

Add its GHSA or PYSEC id to the ignore list in `scripts/nightly-compliance.sh`, with a comment on the line above that
gives the reason and the date to revisit. Remove the entry once a fixed version is pinned. Dismissing the alert on
GitHub also removes it from the open alerts, but leaves no reviewed record in the repository.

### Running it locally

```sh
scripts/nightly-compliance.sh > nightly-compliance.md
```

This reads the alerts with your `gh` login (needs `jq`). Set `ALERTS_JSON=<file>` to read an alerts JSON array from a
file instead; the tests in `tests/scripts/` use it.
