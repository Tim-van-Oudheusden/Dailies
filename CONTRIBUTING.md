# Contributing

Thanks for helping out. This guide covers how to get set up, find work, and ship changes through review.

Stack: Python 3 with PyGObject, GTK 4 and libadwaita, Blueprint for the UI, Meson for the build, Flatpak on the GNOME 51
runtime for packaging, ruff and pytest for lint and tests. The app has no third-party Python dependencies at runtime:
everything it imports comes from the GNOME Platform or the standard library.

## Getting started

You need:

- Flatpak with the Flathub remote, and `flatpak-builder` (your distribution's package, or `org.flatpak.Builder` from
  Flathub)
- The GNOME 51 SDK and Platform from Flathub; the Devel manifest builds against them
- Python ≥ 3.12 with `ruff`, `pytest`, `pytest-cov`, `pyyaml` and `check-jsonschema`, for the gates that run outside
  Flatpak
- For a native Meson build: Meson ≥ 1.4, Ninja, GTK ≥ 4.24, libadwaita ≥ 1.10, PyGObject, `desktop-file-utils`,
  `appstream` and the GLib schema tools. `blueprint-compiler` comes from `subprojects/blueprint-compiler.wrap` (pinned
  to v0.22.2) when the system has none

```sh
flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Sdk//51 org.gnome.Platform//51
python3 -m pip install --user ruff pytest pytest-cov pyyaml check-jsonschema
```

If your distribution does not ship the GNOME 51 libraries, skip the native build: the Flatpak gate runs the same Meson
tests inside the SDK.

`scripts/dev.sh` wraps the everyday Flatpak commands, so you rarely type a manifest path. It uses `flatpak-builder` and
`flatpak-builder-lint` from your `PATH`, or the `org.flatpak.Builder` Flatpak when they are not installed:

```sh
scripts/dev.sh build-devel   # build the Devel manifest into repo/ and install it for your user
scripts/dev.sh run           # run the installed Devel build
scripts/dev.sh bundle        # export the Devel build as Dailies-Devel-x86_64.flatpak
scripts/dev.sh lint          # flatpak-builder-lint on both manifests and on repo/
```

The Devel build has its own app ID, `io.github.tim_van_oudheusden.Dailies.Devel`, so it installs next to a release
build with separate settings and website data. It shows the striped header bar and the striped icon, so the two are
never confused.

Every CI run uploads the Devel bundle (`io.github.tim_van_oudheusden.Dailies.Devel-x86_64.flatpak`) as an artifact, so
a build can be tried without a local toolchain: download it from the run, then
`flatpak install --user ./io.github.tim_van_oudheusden.Dailies.Devel-x86_64.flatpak`.

## Project layout

```text
dailies/                    the application package
  core/                     pure Python (no gi): models, catalog and popularity parsing, search
  data/                     fetcher (libsoup), favourites and the list store (GSettings, GLib)
  ui/                       widgets, filters, the in-app browser page, the link opener, preferences
data/                       desktop file, metainfo, GSettings schema, Blueprint files, icons, screenshots
  v1/                       games.json (the catalog), popularity.json (weekly shelves), schema/
build-aux/flatpak/          Devel manifest (CI and local), release manifest, linter exceptions
scripts/                    CI and data scripts: gates, coverage, submission validator, link checker, popularity
tests/                      core/, scripts/, data/, tooling/ (pytest) and e2e/ (smoke test inside Flatpak)
po/                         gettext setup
prompts/                    reusable agent prompts (code review, PR body)
docs/                       testing, risk tiers, metrics, runbooks, reflections, postmortems, security
```

**Where code goes.** Anything that can be expressed without GTK or GLib (parsing, validation, ranking, search) goes in
`dailies/core`, so it is tested with plain pytest on any machine. `dailies/data` and `dailies/ui` stay thin layers that
read from GLib APIs and render with GTK. UI layout lives in Blueprint files under `data/ui/`, never in hand-written
`.ui` XML.

**Where a test goes.** In the `tests/` directory that mirrors the code it covers: a test for `dailies/core/catalog.py`
goes in `tests/core/test_catalog.py`, one for `scripts/validate_submission.py` in `tests/scripts/`. Checks on the
committed data files go in `tests/data/`; checks on `.github/` (workflow invariants, label and policy parity) go in
`tests/tooling/`. Adding a workflow means adding its reviewed token scopes to `tests/tooling/test_workflows.py`.

## Finding and claiming work

- GitHub issues are the **source of truth**. Browse open issues and assign one to yourself before starting.
- To suggest a game, use the **New game** issue form; you do not need to edit `data/v1/games.json` yourself.

We favour small, focused changes tied to a tracked issue.

## Development workflow

1. Create a branch off `main`: `<type>/<number>-<slug>`.
2. Work the issue **test-first** (see below).
3. Commit with [Conventional Commits][conventional-commits] messages, one commit per issue:
   `type(scope): summary (#<number>)`, e.g. `feat(library): add search (#41)`, `fix(fetcher): honour Retry-After (#57)`.
4. Open a pull request and fill in the template (link the issue with `Fixes #<number>`, paste evidence).

`main` is protected by the ruleset in [`.github/rulesets/main.json`](.github/rulesets/main.json): no direct pushes,
force-pushes or deletion; changes land only through pull requests whose `PR review rubric`, `Build, lint, test`,
`Unit-test coverage floors` and `Static checks` checks pass. Pull requests merge with a merge commit only (no squash or
rebase), so each issue's single commit lands on `main` unchanged, and the head branch is deleted on merge. The file is
the source of truth: a change to it lands by PR, then a maintainer applies it with
`gh api -X PUT repos/Tim-van-Oudheusden/Dailies/rulesets/<id> --input .github/rulesets/main.json`.

[conventional-commits]: https://www.conventionalcommits.org/

Every pull request is classified into a low, medium or high risk tier from the paths it changes (the informational
`Risk tier` check); [`docs/risk-tiers.md`](docs/risk-tiers.md) lists the paths in each tier and the review each expects.

### Test-driven development

We require TDD. One test at a time:

1. Write a failing test for the behaviour you're adding or fixing.
2. Confirm it fails for the expected reason.
3. Make it pass with the smallest change.
4. Refactor only as needed.

Assert on observable outputs, return values, and side effects — never on internal state or private methods. Never
weaken or skip a failing test to make it pass; fix the implementation.

## Quality gates

Run these before opening a PR (CI runs the same on every PR):

```sh
ruff check . && ruff format --check .
pytest
meson setup _build -Dprofile=development && meson test -C _build
flatpak-builder --user --install --force-clean _flatpak build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json
```

| Command | What it runs |
| --- | --- |
| `ruff check . && ruff format --check .` | Lint and formatting of every Python file |
| `pytest` | `tests/core`, `tests/scripts`, `tests/data` and `tests/tooling` (the `testpaths` in `pyproject.toml`) |
| `meson setup … && meson test -C _build` | Native build, then `desktop-file-validate`, `appstreamcli validate`, `glib-compile-schemas --strict` and the Blueprint compile |
| `flatpak-builder … Devel.json` | The Devel Flatpak in the GNOME 51 SDK with `run-tests`, so the Meson tests and the e2e smoke test run inside the sandbox |

`meson setup` refuses an existing `_build`; use `meson setup --reconfigure _build -Dprofile=development` after the
first time. In CI, `Build, lint, test` runs ruff, pytest and `check-jsonschema` on both data files on a plain runner;
the `Flatpak (x86_64)` job runs the Flatpak gate in the `gnome-51` image with `flatpak-builder-lint` on the manifest and
the exported repo. [`docs/testing.md`](docs/testing.md) says which test runs where.

The `main` ruleset also requires the **Unit-test coverage floors** check (`.github/workflows/coverage-gate.yml`): it
runs `pytest --cov=dailies/core --cov=scripts --cov-report=xml` and fails the PR if the line or branch coverage of
`core` or `scripts` drops below its floor in `.github/auto-qa-tuning.json`. See
[`docs/testing.md`](docs/testing.md#coverage-floors) to run it locally.

### Shell scripts and workflows

The `main` ruleset also requires the **Static checks** job in `.github/workflows/ci.yml`. It downloads pinned
[shellcheck](https://www.shellcheck.net/) and [actionlint](https://github.com/rhysd/actionlint) releases (versions and
SHA-256 checksums in the job's `env:`) and runs `shellcheck -x` on every tracked `*.sh` file, then `actionlint` on
`.github/workflows/`. actionlint reads `.github/actionlint.yaml` and runs shellcheck on each `run:` block too. Run the
same locally, with both tools at the versions in `ci.yml` on your `PATH`:

```sh
shellcheck -x scripts/*.sh scripts/lib/*.sh
actionlint
```

Fix a finding rather than silencing it. A check that cannot apply to this repository is turned off in
`.github/actionlint.yaml` with a comment saying why.

### Formatting

[ruff](https://docs.astral.sh/ruff/) formats and lints the Python, with its settings in `pyproject.toml`.
`ruff format --check .` fails on a deviation; `ruff format .` fixes it, and `ruff check --fix .` fixes what it safely
can. `.editorconfig` sets the indent per file type (Python 4 spaces; Meson, Blueprint and JSON 2), which most editors
read. `.pre-commit-config.yaml` runs ruff, `blueprint-compiler format` and `meson format`; install it with
`pre-commit install` to format on commit.

A rule that misfires is turned off for the whole project in `pyproject.toml`, with a comment saying why. Never silence
one finding with a `# noqa` comment.

The commit that first formatted the code base is listed in `.git-blame-ignore-revs`. Run
`git config blame.ignoreRevsFile .git-blame-ignore-revs` once so local `git blame` skips it; GitHub does so on its own.

### Applying review suggestions

Comment `/apply-suggestions` on a pull request to commit every ```` ```suggestion ```` block that reviewers with write
access (human or Claude) left on its current diff. `.github/workflows/auto-review.yml` commits them to the PR branch as
`chore(review): apply review suggestions (#N)` and posts a report comment listing what was applied and what was skipped:
outdated suggestions, ones on the base side of the diff, ranges past the end of the file or overlapping an already
applied range, comments holding more than one suggestion block, paths outside the checkout, and files under
`.github/workflows/` (the workflow token cannot push those, and one such edit would sink the whole push). A suggestion
block ends only at a fence that starts a line. Only `OWNER`/`MEMBER`/`COLLABORATOR` comments trigger it and only their
suggestions count; fork pull requests are refused, and so is a head committed after the command comment (comment again
once you have looked at it). Resolved or declined review threads are not detected (the REST API does not expose thread
state): delete or edit a suggestion you do not want before commenting. The apply script
(`scripts/apply-review-suggestions.sh`) runs from the default branch, never from the PR. Pushes made with the workflow
token start no CI run, so push again or re-run CI before merging.

### Handing work to Claude Code

`.github/workflows/claude.yml` runs [Claude Code](https://github.com/anthropics/claude-code-action) in CI. Label an
issue `ai-fix-requested`, or mention `@claude` in an issue comment, PR review, or review comment, and Claude works the
request on a `claude/*` branch and opens a pull request; it never pushes to `main`. On a pull request, `@claude review
this` asks for a review. Mentions only count from `OWNER`/`MEMBER`/`COLLABORATOR`, the label can only be applied by
triagers, and fork pull requests are refused, so outside contributors cannot start or steer a run. Claude may run only
the quality-gate tools (`meson`, `ninja`, `pytest`, `ruff`, `flatpak-builder`, `blueprint-compiler`); the full Flatpak
build is left to CI. Its PRs go through the same checks and human review as any other. The workflow needs the
`CLAUDE_CODE_OAUTH_TOKEN` repo secret and the Claude GitHub App.

For reviews, point Claude at the shared rubric in [`prompts/code-review.md`](prompts/code-review.md), e.g.
`@claude review this PR using prompts/code-review.md against issue #12`; [`prompts/`](prompts/README.md) also holds the
PR-body template.

## Releasing

A release is a pushed tag `vX.Y.Z`. Three places name the version and must agree: `version:` in `project()` in
`meson.build` (the single source of truth), the newest `<release>` entry in
`data/io.github.tim_van_oudheusden.Dailies.metainfo.xml.in` (the human changelog, shown in the About dialog and on
Flathub), and the tag.

Pushing the tag runs `.github/workflows/release.yml`:

1. **Verify** checks that the tag, the Meson version and the newest metainfo release are the same version, and that
   the release date is not in the future. On a mismatch it stops before anything is built.
2. **Build** builds the release manifest, `build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json`, for x86_64
   (`ubuntu-latest`) and aarch64 (`ubuntu-24.04-arm`) in the `gnome-51` image, and runs `flatpak-builder-lint` on the
   manifest before and the repo after, with Flathub's rules and no exceptions.
3. **Publish** creates the GitHub Release with `Dailies-x86_64.flatpak`, `Dailies-aarch64.flatpak` and `SHA256SUMS`.
   The body is the newest metainfo release's description, followed by notes generated from the merged PRs
   (`.github/release.yml` sorts them into categories).

A tag with a `-` suffix (`v0.2.0-beta.1`) publishes a pre-release. Bundles do not update themselves: users install the
next bundle over the old one, and their favourites and settings stay.

### Cutting a release

1. Open a pull request (`chore(release): X.Y.Z (#N)`) that raises `version:` in `meson.build` and adds a
   `<release version="X.Y.Z" date="YYYY-MM-DD">` entry at the top of `<releases>` in the metainfo, describing what
   changed for users. The Meson `appstreamcli validate` test checks the entry.
2. Merge it, then run the manual checklist below on the Devel bundle that CI built from the merge commit.
3. Tag the merge commit and push the tag:

   ```sh
   git switch main && git pull
   git tag -a vX.Y.Z -m "Dailies X.Y.Z"
   git push origin vX.Y.Z
   ```

4. The `Release` workflow under **Actions** publishes the release, which then appears under **Releases**.

To retry a failed run, re-run its failed jobs from the Actions tab. If the tag points at the wrong commit, delete the
tag (`git push origin :refs/tags/vX.Y.Z`) and any release it created, fix the cause, and tag again. A published release
that turns out to be broken is fixed forward with a new patch release; see [`docs/runbooks/`](docs/runbooks/README.md).

### Manual checklist before tagging

The automated tests do not drive WebKit content or a real desktop session, so check these by hand:

- [ ] Open three games in the built-in browser, one of them a New York Times game
- [ ] Sign in or play a turn, restart Dailies, and check that the login and streak are still there
- [ ] Switch **Open games** to **Default browser** and check that a game opens in the system browser
- [ ] Dark style: the window, tiles and empty states read correctly
- [ ] Narrow the window to 360 px: the sidebar collapses and the grid stays usable
- [ ] With a screen reader (Orca), a tile reads as the game's name, then its category and difficulty

## Custom browser command

Games open in the built-in browser by default, or in the system's default browser through the OpenURI portal. Neither
needs any extra permission. A third mode, **Custom command**, runs a command of your choice on the host (for example a
particular browser or browser profile) with the game's URL appended.

From inside the Flatpak sandbox that needs host access, which the Dailies manifest never requests. To turn the mode on,
grant it yourself:

```sh
flatpak override --user --talk-name=org.freedesktop.Flatpak io.github.tim_van_oudheusden.Dailies
```

**This is a sandbox escape that you choose.** Access to `org.freedesktop.Flatpak` lets Dailies run any command on your
host as your user, outside the sandbox; Flatpak documents it as a sandbox escape allowing arbitrary code execution. Only
grant it if you accept that. Once granted, **Custom command** appears under **Preferences → Opening games**; until
then it is hidden and inert. To take the access back:

```sh
flatpak override --user --no-talk-name=org.freedesktop.Flatpak io.github.tim_van_oudheusden.Dailies
```

For the Devel build, use `io.github.tim_van_oudheusden.Dailies.Devel` in both commands. Outside Flatpak (a native
Meson build) the command runs directly and needs no override.

## Code style

- ruff's style and lint rules as configured in `pyproject.toml`; 4-space indent (`.editorconfig`).
- `dailies/core` never imports `gi`. Prefer frozen dataclasses and pure functions there.
- Type hints on public functions; model absence with `None` or an explicit result, not sentinel strings.
- UI in Blueprint, current libadwaita widgets only (no deprecated ones), following the
  [GNOME HIG](https://developer.gnome.org/hig/). Every interactive element is reachable by keyboard and has an
  accessible name; colour never carries information on its own.
- Every user-facing string goes through gettext (`_()`).

## Dependencies

- Ask before adding, upgrading, or removing a dependency; state the package, exact version, and rationale.
- The app has **no third-party Python runtime dependencies**. Use the GNOME Platform (GLib, GIO, libsoup, GTK,
  WebKitGTK) and the standard library. A new runtime dependency means a new Flatpak module and needs explicit approval.
- Tools that only CI and `scripts/` use live in `scripts/requirements.txt`, pinned with hashes.
- GitHub Actions are pinned to a commit SHA with a `# vX.Y.Z` comment; Dependabot proposes updates.

## Agent safety layers

AI agents working in this repo are bounded by several layers:

1. **Instructions** — `AGENTS.md` (authoritative), `CLAUDE.md`, `.github/copilot-instructions.md` and
   `.cursor/rules/agent-guidance.mdc` state the rules.
2. **Project permissions** — `.claude/settings.json` pre-approves the quality gates, asks before dependency and
   history-rewriting commands, and denies reading secrets (`.env*`), force-pushes and `--no-verify` commits.
3. **Personal overrides** — `.claude/settings.local.json` (gitignored). Deny rules from the project file still apply.
4. **Structural gates** — the ruleset on `main` and CI must pass before merge, regardless of who wrote the change.

The security side of these layers (trust boundaries, secrets, supply chain, review focus, reporting) is set out in
[`docs/security/SECURITY-AI.md`](docs/security/SECURITY-AI.md).

How agent work fares is measured, not guessed: the weekly `PR metrics` workflow reports how many agent-authored PRs
(`claude/*` branches and the `hive-forge-app` GitHub App) were merged vs. closed unmerged. Every metric, its cadence,
where it is published and how to reproduce it locally is catalogued in [`docs/metrics/README.md`](docs/metrics/README.md).
