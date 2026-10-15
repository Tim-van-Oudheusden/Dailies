# Testing

How Dailies' tests and quality checks run, and where each one can run.

## Test layers

| Layer | What | Where it runs | Gate |
| --- | --- | --- | --- |
| Unit (pure Python) | `tests/core/`: catalog parsing, including tolerance of an unknown category or status; popularity parsing and staleness; search folding. `tests/scripts/`: the submission validator (with fixtures for dead and hijacked domains), the popularity computation on synthetic ranking data, the shared-domain split, the fail-closed threshold, the link checker | `ubuntu-latest`, plain pytest, seconds | `Build, lint, test`; coverage floors on `dailies/core` and `scripts` |
| Data | `tests/data/test_catalog_file.py`: schema, sorted unique ids, unique normalised URLs, every `domain` matches its `url`, enum membership, every id in `popularity.json` exists in the catalog | same | `Build, lint, test` |
| Tooling | `tests/tooling/test_workflows.py` (PyYAML): top-level and per-job permissions, `timeout-minutes` on every job, actions pinned to 40-hex SHAs with version comments, no `${{ github.event.* }}` in `run:`, `pull_request_target` only in `labeler.yml` and without a checkout, labeler and risk-tier policy parity, every `data/v1/*.json` published by `pages.yml` | same | `Build, lint, test` |
| Build validation | Meson tests: `desktop-file-validate`, `appstreamcli validate --no-net --explain`, `glib-compile-schemas --strict --dry-run`, and the Blueprint compile of every `.blp` (a syntax error fails the build) | inside `flatpak-builder --run-tests` | `Flatpak (x86_64)` |
| E2E smoke | `tests/e2e/test_smoke.py`: starts the installed app under `dbus-run-session` and `xvfb-run` with the hidden `--smoke` flag, which quits once the window has mapped; asserts exit status 0 and no `CRITICAL` on stderr. A Meson test with `GSETTINGS_BACKEND=memory` | inside `flatpak-builder --run-tests` (the action provides xvfb) | `Flatpak (x86_64)` |
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
SDK: the Devel manifest sets `run-tests`, so `flatpak-builder` runs `meson test`, the build validation and the e2e smoke
test inside the sandbox, exactly as CI's `Flatpak (x86_64)` job does in the `gnome-51` image.

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

writes a Cobertura-format report to `coverage.xml`. The floors live in `.github/auto-qa-tuning.json`, per module, as
line coverage in percent:

```json
{ "margin": 2, "floors": { "core": { "lines": 70 }, "scripts": { "lines": 70 } } }
```

`scripts/coverage-check.sh <module> <lines>` reads the module's line coverage from `coverage.xml` (through
`scripts/lib/coverage.sh`) and compares it with the floor. It prints the observed coverage next to the floor and exits 1
if it is below, 2 if the report is missing or the floor is not a percentage between 0 and 100. The comparison uses the
exact ratio, so 69.999 % does not pass a 70 % floor.

`.github/workflows/coverage-gate.yml` (job **Unit-test coverage floors**, every PR and push to `main`) runs the check
for every module listed in the floors file and is a required status check in the `main` ruleset. Adding a module to the
gate means adding it to `.github/auto-qa-tuning.json` and to the `--cov` list. Apply the ruleset entry to the live
ruleset only after the workflow has run on `main` once; a required check that never reports blocks every PR.

Raise a floor when coverage rises; never lower one to make a PR pass. Add tests instead. Both floors start at 70 %
lines and are ratcheted up by the self-tuning below. Run the check locally:

```sh
pytest --cov=dailies/core --cov=scripts --cov-report=xml
scripts/coverage-check.sh core 70
scripts/coverage-check.sh scripts 70
```

`pytest --cov=dailies/core --cov=scripts --cov-report=html` writes a browsable report to `htmlcov/`.

## Quality report

`.github/workflows/quality-report.yml` (job **Quality report**: every push to `main`, weekly on Monday at 06:17 UTC,
and on demand) runs `scripts/quality-report.sh > quality-report.md`. The script runs each gate of `Build, lint, test`
separately (`ruff check`, `ruff format --check`, `pytest`, `check-jsonschema`), then the coverage run for every module
in `.github/auto-qa-tuning.json`, and prints a Markdown report: pass/fail per gate and line coverage per module. Every gate
and coverage run happens even when an earlier one fails. A module whose coverage run fails, or leaves no report, shows
`❌ n/a`; a report left by an earlier run is deleted first, so it never stands in for the current run. Tool output goes
to stderr. The script exits 1 if anything failed, 2 if the floors file lists no module.

The workflow appends the floor tuning below (even when a gate failed), publishes the result to the job summary and
uploads it as the `quality-report` artifact. Run it locally:

```sh
scripts/quality-report.sh > quality-report.md
```

## Coverage floor self-tuning

`scripts/auto-qa-tuner.sh --report quality-report.md [--config .github/auto-qa-tuning.json] [--write]` reads the
coverage rows of a quality report and proposes, per module, the floor raised to the observed coverage minus the
config's `margin` (in percentage points), rounded down to a whole percent. Floors only ratchet up: a proposal below the
current floor keeps the floor, and a module reported as `n/a` keeps its floor. It prints the proposals as a Markdown
table (`⬆️` marks a raise); `--write` saves them to the config, keeping every other key. It exits 2 for a missing report
or a malformed config (a floor outside 0–100, a negative or missing margin, no modules) and then leaves the config
untouched.

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
