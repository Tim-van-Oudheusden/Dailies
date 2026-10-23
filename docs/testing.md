# Testing

How Dailies' tests and quality checks run, and where each one can run.

## Test layers

| Layer | What | Where it runs | Gate |
| --- | --- | --- | --- |
| Unit (pure Python) | `tests/core/`: catalog parsing, including tolerance of an unknown category or status; popularity parsing and staleness; search (`test_search.py`: accent and case folding, typo tolerance and its length thresholds, word starts, the rank order prefix > word start > name substring > other fields > typo, no typo flood and no fuzzy short queries over the real catalog, whether a new query narrows or widens the matches, checked against the catalog while typing, and a best-of-five micro-benchmark: under 5 ms per keystroke over 300 games); the cache decisions (`test_cache.py`: maximum age, `If-None-Match`, URL fall-through order, `Retry-After`, validation before any write, atomic cache files, the stale-banner rule); the sidebar sections (`test_sections.py`: categories without an active game hidden, the restored section, the "as of" date of stale shelves, what each section holds (Favorites keep unavailable games, categories only active ones), the default and overriding sort orders, which empty-state page shows); the favourites export file (`test_favorites_file.py`: 2-space UTF-8 output read back in order, malformed JSON, wrong top-level type or `schema_version`, non-string, empty or duplicate ids rejected, Merge and Replace). `tests/scripts/`: the submission validator (with fixtures for dead and hijacked domains), adding an approved submission (`test_add_game.py`: insertion sorted by id, a diff against the real `games.json` of only the new entry and `generated_at`, refusal of an existing id or a failed validation, the PR body and step outputs), the popularity computation on synthetic ranking data, the full domain score and the two-per-domain shelf cap, the committed `domain_weights.json`, the fail-closed threshold, the weekly report guard (only the week's report and byte-identical shelves may change; a tampered `games.json` fails it), the optional Wikipedia, HN and Radar collectors against a fake session and the composite score with its renormalisation over missing sources, output byte-identical to `method_version: 2` without them (`tests/scripts/fixtures/popularity/`), the link checker; the CI scripts (coverage gate, quality report, floor tuner, PR metrics, review-suggestion applier, nightly compliance) run against fixtures and stub tools; the shell suites `scripts/pr-review-check.test.sh` (PR title and issue-link rubric) and `scripts/tier-classify.test.sh` (risk-tier engine, `-z` and git C-quoted paths, and the shipped policy, whose rules `docs/risk-tiers.md` must list) | `ubuntu-latest`, plain pytest, seconds | `Build, lint, test`; coverage floors on `dailies/core` and `scripts` |
| Data | `tests/data/test_catalog_file.py`: schema, sorted unique ids, unique normalised URLs, every `domain` matches its `url`, enum membership, every id in `popularity.json` exists in the catalog | same | `Build, lint, test` |
| Tooling | `tests/tooling/test_workflows.py` (`ruamel.yaml`, from the scripts' lock), over every file in `.github/workflows/`: top-level permissions exactly `contents: read`, job permissions equal to the reviewed `JOB_PERMISSIONS` map, `timeout-minutes` on every job, actions pinned to 40-hex SHAs with a `# vX.Y.Z` comment (`docker://` images by digest, or listed in `DOCKER_TAG_ALLOWLIST` with a reason), job `container:` images by digest (or listed in `CONTAINER_TAG_ALLOWLIST` with a reason), no `${{ github.event.* }}` in `run:`, `pull_request_target` only in `labeler.yml` and without a checkout, no `cron` at minute 0, `.github/labeler.yml` labels equal to the path labels documented in #18, labeler and risk-tier policy parity (each glob's sample path is covered by the other file, exemptions listed with reasons), every `data/v1/*.json` copied into the `pages.yml`; `tests/tooling/test_potfiles.py`: every Python, Blueprint and data template file with translatable strings is listed in `po/POTFILES.in`, every listed file exists, the list is sorted without duplicates, and every language in `po/LINGUAS` has its `.po` artifact. Each check also has a test that feeds it a broken inline YAML fixture | same | `Build, lint, test` |
| Build validation | Meson tests: `desktop-file-validate`, `appstreamcli validate --no-net --explain`, `glib-compile-schemas --strict --dry-run`, the Blueprint compile of every `.blp` (a syntax error fails the build), and `tests/tooling/check_pot.py` (`Template is up to date`: `po/dailies.pot` has exactly the messages xgettext extracts from `po/POTFILES.in`, compared with `msgcmp` in both directions) | inside `flatpak-builder --run-tests` | `Flatpak (x86_64)` |
| GI integration | `tests/gi/`: the `dailies/data` and `dailies/ui` classes that need GLib, against the real schema. Stdlib `unittest` scripts (the SDK has no pytest), registered in `tests/meson.build` (suite `gi`) with `GSETTINGS_BACKEND=memory` and `GSETTINGS_SCHEMA_DIR` at the schema compiled into `_build/data`. `tests/gi/test_favorites.py`: toggle on and off, insertion order, undo restoring the index, one `changed` per toggle, a move writing the key once with one `changed` (and nothing for a move that changes nothing), external changes to the key, `set_order` and `import_ids`; the export file written and read back through Gio's asynchronous I/O (export, reset, import gives the same order), malformed, missing and unwritable files reported. `test_done_today.py`, with an injected local clock: earlier days ignored and pruned at startup, toggle and mark, one `changed` per change, a refresh after midnight clearing the marks, the midnight timer firing on its own, external changes to the key. `test_store.py`: cold start from the bundled snapshot, a corrupt or older cache replaced by the bundle, ranks, favourites and done-today marks applied, diff by id on reload, stale popularity, lookup by id. `test_filters.py`: the grid's pipeline (section filter, search filter, search and section sorters) over `GameObject`s: shelf rank order, categories by name, favourite order with an unavailable favourite kept, the sort mode overriding it, "not done first" moving the done games last, accent-folded search narrowing the current section, the best matches first while searching and the section order back once the query is cleared, a query long enough for a typo re-testing hidden games; the `GameObject` texts that follow its game. `test_tile.py`: the game tile from the built resources on a private Broadway display (`gtk4-broadwayd`): its labels and colour classes following the game, the accessible name and description, opening through `win.open-game`, the star as a separate labelled button that follows the favourite state (icon, tooltip) and toggles it through `win.toggle-game-favorite`, the "Unavailable" pill on a broken game, the "Done today" badge and dimmed card, the game menu's done item and its pop-up; the menu's Open With choices and Isolated Session item following the built-in browser and host access, an Open With item writing the game's `open-mode-override` (choosing what a hidden override shows as keeps it), Isolated Session toggling `isolated-session` and disabled while `session-isolation` is per-game; in Favorites, the menu's Move Up, Move Down, Move to Top (disabled when impossible, else `win.move-favorite`) and Remove from Favorites after the done and Open With sections, the drag source offering the game id, a drop on either half activating `win.drop-favorite` and the drop indicator on that side. `test_window.py`, on its own `gtk4-broadwayd` display with animations on: the main window over the bundled snapshot, a game opened in-app while the previous browser page is still sliding out after Back is shown, without a `Duplicate page tag` critical from `Adw.NavigationView`. `test_favorites_transfer.py`, on its own Broadway display, after a file is chosen (the portal's file dialogs are not driven): export, reset, import gives the same order with an "Imported N favorites" toast; with favourites set, the Merge (default) / Replace / Cancel `Adw.AlertDialog`; a malformed file shows an error toast and changes nothing. `test_dialogs.py`, on its own `gtk4-broadwayd` display: `Adw.Application` wiring the bundled Shortcuts dialog to Ctrl+?, every accelerator listed in its section, and the About dialog's version, licence and release notes read from the bundled metainfo. `test_fetcher.py`: the fetcher against a local `http.server` with ETags: unconditional first fetch, no request while fresh, 304 changing only `.fetched`, a truncated body leaving the cache untouched, fall-through on 503 and on a refused connection, the User-Agent. `test_opening.py` also covers a game's relocatable `Game` settings and its `open-mode-override`, and the Preferences "Privacy and compatibility" rows reading and writing the browser keys. `test_browser.py` (only when WebKitGTK is found), on its own display with temporary XDG directories: the shared session by default, per-game sessions with their own directories and `cookies.sqlite` holding separate cookies, `isolated-session`, the cookie policy and ITP following the settings live, "Clear website data" reaching a per-game session not opened in the run, and the WebKit settings (hardware acceleration, user agent, developer extras) with their v0.1 defaults. `test_translations.py`, with `LANGUAGE=nl` and the catalogs built from `po/`: Dutch category names, tile captions and plural forms. Plain `pytest` skips the directory (`--ignore=tests/gi` in `pyproject.toml`) | `meson test` inside the SDK, so also `flatpak-builder --run-tests` | `Flatpak (x86_64)` |
| E2E smoke | `tests/e2e/test_smoke.py`: starts the installed app with the hidden `--smoke` flag, which skips the network refresh and quits half a second after the window has mapped, under `dbus-run-session` on a private `gtk4-broadwayd` display (`GDK_BACKEND=broadway`; the SDK has no Xvfb, and broadway needs no host display) with `GSETTINGS_BACKEND=memory`; asserts exit status 0 within 30 s and no `CRITICAL` or `Traceback` on stderr. A stdlib `unittest` script registered as a Meson test (suite `e2e`); it reports SKIP when the app is not installed, and plain `pytest` deselects it by its `e2e` marker | inside `flatpak-builder --run-tests` | `Flatpak (x86_64)` |
| Windows (experimental) | `.github/workflows/windows.yml` (#84): the MSYS2 UCRT64 build and the Meson tests that can run there (build validation, `favorites`, `done_today`, `store`, `filters`, `translations`; not `icons` and `fetcher`, which need glycin, nor `dialogs` and `smoke`, which need `gtk4-broadwayd`). Then `build-aux/windows/smoke.ps1` on the bundled tree, moved to another directory and with only Windows on `PATH`: `dailies --smoke` exits 0 with no `CRITICAL` or `Traceback`, `Dailies.cmd` starts the app, and two screenshots, Popular and Popular under `LANGUAGE=nl` (artifact `windows-screenshots`) | `windows-2025` runner | none: the job is `continue-on-error` and not required |
| Manual before tagging | The checklist in [`CONTRIBUTING.md`](../CONTRIBUTING.md#manual-checklist-before-tagging): three games in-app (one from the New York Times), login and streak kept across a restart, external open, dark style, 360 px width, screen reader names on tiles | the maintainer | — |

Not tested: pixel or UI snapshots, the content of game websites inside WebKit, the Windows build on real hardware, and
macOS.

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

## Agent sandbox: what runs where

**Decision (#182):** an unprivileged container can run every gate except the Flatpak build. `Dockerfile.sandbox` is
that container, for agents and contributors without Flatpak or the GNOME 51 libraries; the Flatpak build runs on a
host with Flatpak and in CI's `Flatpak (x86_64)` job, which runs on every pull request.

| Gate | In the sandbox |
| --- | --- |
| `ruff check`, `ruff format --check`, `pytest` with the coverage floors, `check-jsonschema` | Yes, at the versions CI installs |
| `shellcheck -x`, `actionlint` | Yes, the binaries CI's `Static checks` job pins |
| Meson build, install and `meson test`: build validation, gi tests, e2e smoke test | Yes, against the GNOME 51 SDK's libraries |
| `flatpak-builder` on the Devel manifest, `flatpak-builder-lint` | No: CI, or a host with Flatpak |

Why the Flatpak build cannot: `flatpak-builder` runs every build and test command through `flatpak build`, which
starts bubblewrap with a fresh `/proc` and `/dev/pts`. Inside an unprivileged container, bubblewrap can create its
user namespace but may not mount those: the runtime masks parts of the container's `/proc` and SELinux confines it,
so the kernel refuses the mounts. In a rootless podman container, `bwrap --unshare-user --dev-bind / / true` works,
while `bwrap --unshare-all --ro-bind / / --proc /proc --dev /dev true` fails with
`Can't mount proc on /newroot/proc: Permission denied` (and `--dev /dev` alone with
`Can't mount devpts on /newroot/dev/pts`). CI's Flatpak job runs its container with `--privileged` for this reason.
The only fix is to start the outer container with `--privileged`, or with an unmasked `/proc` and SELinux labelling
off, which widens the sandbox it exists to keep narrow, and an agent inside a container cannot change how it was
started.

Why the rest can: the image's root filesystem is GNOME's OCI mirror of `org.gnome.Sdk//51`, the SDK `flatpak-builder`
builds in, so Meson finds GTK, libadwaita, WebKitGTK and Python with PyGObject directly, with no sandbox to start.
`scripts/sandbox-gates.sh` installs the build into a throwaway prefix before `meson test`, as `--run-tests` does, so
the e2e smoke test runs instead of skipping. One difference: WebKit starts its web processes in a bubblewrap sandbox
of its own, which fails the same way, so the image sets `WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1`. Inside the
Flatpak, WebKit's sandbox stays on.

What only the Flatpak build checks: the manifests (`finish-args`, modules, `cleanup`), the app's layout under `/app`,
and the `flatpak-builder-lint` rules. A change to `build-aux/flatpak/` or to what Meson installs needs CI's Flatpak job
(or a local Flatpak build) to pass. The sandbox's Python is the SDK's (3.14 for GNOME 51), while CI's `Build, lint,
test` job runs `pytest` on 3.12.

On a host with rootless podman, `scripts/sandbox.sh` builds the image (a no-op when nothing changed; the first build
downloads the SDK, about 1.5 GB) and runs a command in it with the checkout at `/workspace`:

```sh
scripts/sandbox.sh                    # every gate above except the Flatpak build
scripts/sandbox.sh pytest tests/core  # any command
scripts/sandbox.sh bash               # a shell
```

An agent whose container is built from `Dockerfile.sandbox` runs `scripts/sandbox-gates.sh` directly. It runs every
gate even when one fails, prints a `PASS`/`FAIL` line per gate at the end and exits 1 if any failed. It builds in a
temporary directory, so it leaves no `_build/` behind. In a git worktree, `.git` points outside the mount and git sees
no repository inside the container; the gates do not need one.

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
A module that no test imports still counts, at 0 %: the folders under `scripts/` are not packages, and
`include_namespace_packages` in `pyproject.toml` makes coverage.py list their modules anyway.
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
| External data checker image | `scripts/check_checker_digest.py` finds that the `flatpak-external-data-checker` digest pinned in `.github/workflows/external-data-checker.yml` is no longer the image's `:latest` on ghcr.io, or cannot read ghcr.io. To bump the pin, see CONTRIBUTING.md, "Dependencies" |
| Catalog links (weekly) | Sundays (UTC) only, or with `--force-links` / `DAILIES_FORCE_LINKS=1` (the manual run's `force_links` input): `scripts/check_links.py` finds an active catalog entry that is `redirected-cross-domain`, `blocked-title`, `hijacked`, `http-<code>`, `timeout` or `unreachable`. A `bot-walled` entry (a Cloudflare challenge, or a 403 or timeout on an entry tagged `bot-walled`) is a warning, not a failure |

The alerts come from `gh api repos/$GITHUB_REPOSITORY/dependabot/alerts?state=open`, read with the job's `GITHUB_TOKEN`
through the `vulnerability-alerts: read` permission, so no secret is needed.

### Broken game links

`scripts/check_links.py --catalog data/v1/games.json --out links.md` checks every `status: active` entry with the
submission validator's rules, shared in `scripts/lib/urlcheck.py`: a public https URL, a 2xx answer, a final registrable
domain equal to the entry's `domain`, and no gambling keyword in the page title. It sends one request at a time,
grouped by host, at most two a second, with the validator's User-Agent. The report lists each failing or bot-walled
game with its reason and a suggested `status`; the script exits 0 when nothing failed, 1 when an entry did and 2 on an
error. In the workflow (`--open-issue`) a failure also opens one issue `data: N broken links (week W)` labelled `data`,
or updates the open one (found by the report marker or that title), using the job's `issues: write` permission.

### Automatic status changes

On `main` the workflow also flips `status` itself, through a pull request (issue #81). With `LINKS_STATUS_DIR` set,
`scripts/nightly-compliance.sh` passes `--previous-state`, `--state-out` and `--status-out` to the link checker, which
then also checks the `broken` entries (left out of the report and the exit code) and keeps a streak per game in a
small state file (`scripts/lib/linkstatus.py`):

| Situation | Change |
| --- | --- |
| An active game fails the **same** check (e.g. `http-404`) in two consecutive ISO weeks | `status: broken`, history event `broken` with the check and reason |
| A broken game passes in two consecutive ISO weeks | `status: active`, history event `restored` |
| The link leads to another site whose page title holds a blocklisted keyword (`hijacked`) | `status: retired` at once, history event `retired`; the pull request gets `priority::high` |
| A single failure, another check, a skipped week, a pass or a bot wall in between | nothing; the issue row only |

A second run in the same week (a manual run) is not a second week. When a status should change, the checker writes
`changes.json` and `pr-body.md`; the `link-status` job checks out the newest `main`, applies the changes with
`scripts/apply_link_status.py` (sets `status`, appends the `history` event, updates `generated_at`, writes the file
in its committed format, never removes an entry), and opens or updates the pull request on branch `data/link-status`
with `peter-evans/create-pull-request`, labelled `data` and `automated`. A maintainer reviews and merges it; a game
that only moved needs its `url` and `domain` changed by hand instead. Pull requests opened with `GITHUB_TOKEN` start no
CI, as with the popularity pull request.

The streaks live in the `link-check-state` workflow artifact (90-day retention; each weekly run on `main` downloads the
newest one with the job's `actions: read` permission and uploads a fresh one), not in a committed file: `main` is
protected, so a committed state would need a merged pull request every week. Losing the artifact (it expired after
the workflow was disabled, or a download failed) only restarts the streaks, so it can delay a change by a week but
never make a wrong one. Runs on other branches start from no state and open no pull request.

### Accepting an advisory

Add its GHSA or PYSEC id to the ignore list in `scripts/nightly-compliance.sh`, with a comment on the line above that
gives the reason and the date to revisit. Remove the entry once a fixed version is pinned. Dismissing the alert on
GitHub also removes it from the open alerts, but leaves no reviewed record in the repository.

### Running it locally

```sh
scripts/nightly-compliance.sh [--force-links] > nightly-compliance.md
```

This reads the alerts with your `gh` login (needs `jq`). Set `ALERTS_JSON=<file>` to read an alerts JSON array from a
file instead, `CHECK_LINKS=<script>` to replace the link checker and `CHECKER_DIGEST=<script>` to replace the image
digest check; the tests in `tests/scripts/` use them. Outside GitHub Actions the link check only writes its report and
never touches issues.
