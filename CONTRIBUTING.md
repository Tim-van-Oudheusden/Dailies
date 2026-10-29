# Contributing

Thanks for helping out. This guide covers how to get set up, find work, and ship changes through review. All
participation is covered by the [Code of Conduct](CODE_OF_CONDUCT.md).

Stack: Python 3 with PyGObject, GTK 4 and libadwaita, Blueprint for the UI, Meson for the build, Flatpak on the GNOME 51
runtime for packaging, ruff and pytest for lint and tests. The app has no third-party Python dependencies at runtime:
everything it imports comes from the GNOME Platform or the standard library.

## Getting started

You need:

- Flatpak with the Flathub remote, and `flatpak-builder` (your distribution's package, or `org.flatpak.Builder` from
  Flathub)
- The GNOME 51 SDK and Platform from Flathub; the Devel manifest builds against them
- Python ≥ 3.12 with `ruff`, `pytest`, `pytest-cov` and `check-jsonschema` (which brings `ruamel.yaml`, used by the
  workflow tests), for the gates that run outside Flatpak
- For a native Meson build: Meson ≥ 1.4, Ninja, GTK ≥ 4.24, libadwaita ≥ 1.10, PyGObject, `desktop-file-utils`,
  `appstream` and the GLib schema tools. `blueprint-compiler` comes from `subprojects/blueprint-compiler.wrap` (pinned
  to v0.22.2) when the system has none

```sh
flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Sdk//51 org.gnome.Platform//51
python3 -m pip install --user ruff pytest pytest-cov check-jsonschema
```

If your distribution does not ship the GNOME 51 libraries, skip the native build: the Flatpak gate runs the same Meson
tests inside the SDK. Without Flatpak either (an agent in a container, say), `scripts/sandbox.sh` runs every gate except
the Flatpak build in `Dockerfile.sandbox`, an unprivileged podman container whose root filesystem is the GNOME 51 SDK;
[`docs/testing.md`](docs/testing.md#agent-sandbox-what-runs-where) says what it covers and why the Flatpak build
cannot run in it.

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
scripts/                    CI and data scripts: gates, coverage, submission validator, link checker, popularity, icons
tests/                      core/, scripts/, data/, tooling/ (pytest); gi/ and e2e/ (Meson tests inside the SDK)
po/                         gettext: POTFILES.in, the dailies.pot template, LINGUAS and one .po per language
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
`tests/tooling/`. A workflow job that needs more than `contents: read` declares its own `permissions:` and gets a
reviewed row in `JOB_PERMISSIONS` in `tests/tooling/test_workflows.py`.

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
`Unit-test coverage floors`, `Static checks` and `Flatpak (x86_64)` checks pass. Pull requests merge with a merge
commit only (no squash or rebase), so each issue's single commit lands on `main` unchanged, and the head branch is
deleted on merge. Repository admins can bypass the ruleset when merging a pull request (the release-manifest pin pull
request, opened with `GITHUB_TOKEN`, runs no checks), never to push directly. The file is the source of truth: a
change to it lands by PR, then a maintainer applies it with
`gh api -X PUT repos/Tim-van-Oudheusden/Dailies/rulesets/<id> --input .github/rulesets/main.json` (the first time,
when no ruleset exists yet:
`gh api -X POST repos/Tim-van-Oudheusden/Dailies/rulesets --input .github/rulesets/main.json`).
`tests/tooling/test_ruleset.py` checks that every required check is the `name:` of a workflow job, so renaming a job
without updating the ruleset fails `pytest`.

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
| `meson setup … && meson test -C _build` | Native build, then `desktop-file-validate`, `appstreamcli validate`, `glib-compile-schemas --strict`, the Blueprint compile and the `po/dailies.pot` freshness check |
| `flatpak-builder … Devel.json` | The Devel Flatpak in the GNOME 51 SDK with `run-tests`, so the Meson tests and the e2e smoke test run inside the sandbox |

`meson setup` refuses an existing `_build`; use `meson setup --reconfigure _build -Dprofile=development` after the
first time. In CI, `Build, lint, test` runs ruff, pytest and `check-jsonschema` on both data files on a plain runner;
the `Flatpak (x86_64)` job, which the `main` ruleset requires, runs the Flatpak gate in the `gnome-51` image with
`flatpak-builder-lint` on the manifest and the exported repo. [`docs/testing.md`](docs/testing.md) says which test runs
where. The installed app runs from the files `dailies/meson.build` installs, not from the checkout, so a new module goes
into its `install_data` list too: `tests/tooling/test_meson_install.py` fails `pytest` when one is missing, before the
Flatpak job's launch test would.

The `main` ruleset also requires the **Unit-test coverage floors** check (`.github/workflows/coverage-gate.yml`): it
runs `pytest --cov=dailies/core --cov=scripts --cov-report=xml` and fails the PR if the line or branch coverage of
`core` or `scripts` drops below its floor in `.github/auto-qa-tuning.json`. See
[`docs/testing.md`](docs/testing.md#coverage-floors) to run it locally.

### Experimental Windows build

`.github/workflows/windows.yml` (#84) builds Dailies on Windows with MSYS2 UCRT64, the way Cartridges does
([`docs/research/stack-crossplatform.md`](docs/research/stack-crossplatform.md), Appendix A.3), on every pull request
and push to `main`. It is experimental: the job is `continue-on-error` and the `main` ruleset does not require it, so a
failing Windows build never blocks a merge. It installs with Meson into a prefix, copies the MSYS2 runtime next to it
with `build-aux/windows/bundle.sh`, and starts the result from another directory with `build-aux/windows/smoke.ps1`
([`docs/testing.md`](docs/testing.md#test-layers) lists the checks). The tree is uploaded as the
`Dailies-windows-x86_64-experimental` artifact (unzip it and run `Dailies.cmd`), with screenshots in
`windows-screenshots`.

The same tree is also packed into an installer (#242), uploaded as `Dailies-windows-x86_64-experimental-installer`.
Meson fills in `build-aux/windows/Dailies.iss.in` on Windows, with the version and the install prefix, and the job
compiles it with Inno Setup's `ISCC`. The `windows-2025` image no longer ships Inno Setup, so the job downloads the
release named by `INNOSETUP_VERSION` in `windows.yml` and checks it against `INNOSETUP_SHA256`. To bump it, take the
`sha256:` digest GitHub shows for the new `innosetup-<version>-x64.exe` asset on
[jrsoftware/issrc's releases](https://github.com/jrsoftware/issrc/releases) and update both. The installer installs
for the current user by default (no administrator needed), adds a Start-menu entry and starts Dailies when it
finishes; its icon, `Dailies.ico`, is rendered from the scalable app icon by `bundle.sh` (`rsvg-convert`, then
`build-aux/windows/make_ico.py`), so no binary icon is committed. `build-aux/windows/install-smoke.ps1` installs it on
the runner and checks all three, then uninstalls it and checks that no file is left, including the `__pycache__` that
Python wrote at run time (the script's `[UninstallDelete]` section removes those).

Neither the tree nor the installer is ever a GitHub Release asset until someone has tried them on real hardware.

What differs on Windows:

- **No built-in browser.** WebKitGTK does not exist on Windows, so Meson builds without it (`HAVE_WEBKIT` is false),
  Preferences hides the option, and games open in the default browser.
- **No game icons.** MSYS2's glycin has no typelibs and no loaders, and the app only decodes the downloaded icons in
  glycin's sandbox, so without it `Icons` fetches none and the tiles keep their category glyphs.
- **Relocatable paths.** Meson writes `PKGDATADIR` and `LOCALEDIR` relative to the prefix, and the launcher and
  `config.py` resolve them where they run, so the unzipped tree can live anywhere.
- **Translations work.** MSYS2's Python has no `locale.bindtextdomain`, so `main()` binds GLib's `libintl-8.dll`
  through `ctypes` and asks GLib for the user's languages; the gresource loads as on Linux. This is what broke i18n for
  Cartridges 2.13.1, which disables it on Windows.
- **Blueprint from the wrap.** MSYS2's `blueprint-compiler` is older than 0.22 and its Python package shadows the
  wrap's, so the job leaves it uninstalled and puts the wrap's source tree on `PYTHONPATH`.
- **Client-side decorations stay on.** GTK 4.24's window on the runner shows no black border or oversized shadow (see
  the screenshots), so there is no `-Ddecorations=no-csd` build. Window snapping still needs checking on real hardware.

### Shell scripts and workflows

The `main` ruleset also requires the **Static checks** job in `.github/workflows/ci.yml`. It downloads pinned
[shellcheck](https://www.shellcheck.net/) and [actionlint](https://github.com/rhysd/actionlint) releases (versions and
SHA-256 checksums in the job's `env:`) and runs `shellcheck -x` on every tracked `*.sh` file, then `actionlint` on
`.github/workflows/`. actionlint reads `.github/actionlint.yaml` and runs shellcheck on each `run:` block too. Run the
same locally, with both tools at the versions in `ci.yml` on your `PATH`:

```sh
shellcheck -x scripts/*.sh scripts/lib/*.sh build-aux/windows/*.sh
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
block ends only at a line holding nothing but a fence at least as long as its opening one, as GitHub renders it, so a
````` ````suggestion ````` block can carry a code block. Only `OWNER`/`MEMBER`/`COLLABORATOR` comments trigger it and
only their suggestions count; fork pull requests are refused, and so is a head committed after the command comment
(comment again once you have looked at it). Resolved or declined review threads are not detected (the REST API does not
expose thread state): delete or edit a suggestion you do not want before commenting. The apply script
(`scripts/apply-review-suggestions.sh`) runs from the default branch, never from the PR. Pushes made with the workflow
token start no CI run, so push again or re-run CI before merging.

### Handing work to Claude Code

`.github/workflows/claude.yml` runs [Claude Code](https://github.com/anthropics/claude-code-action) in CI. Label an
issue `ai-fix-requested`, or mention `@claude` in an issue comment, PR review, or review comment, and Claude works the
request on a `claude/*` branch and opens a pull request; it never pushes to `main`. On a pull request, `@claude review
this` asks for a review. Mentions only count from `OWNER`/`MEMBER`/`COLLABORATOR`, the label can only be applied by
triagers and only counts when a person applies it (a bot's or GitHub App's label is skipped), and fork pull requests
are refused, so outside contributors cannot start or steer a run. Claude may run only the quality-gate tools (`meson`,
`ninja`, `pytest`, `ruff`, `flatpak-builder`, `blueprint-compiler`); the full Flatpak build is left to CI. Its PRs go
through the same checks and human review as any other. The workflow needs the `CLAUDE_CODE_OAUTH_TOKEN` repo secret
and the Claude GitHub App.

For reviews, point Claude at the shared rubric in [`prompts/code-review.md`](prompts/code-review.md), e.g.
`@claude review this PR using prompts/code-review.md against issue #12`; [`prompts/`](prompts/README.md) also holds the
PR-body template.

### Approving game submissions

Games are added through the **Add a game** issue form, never by hand. `game-submission-check.yml` (stage A) checks
each submission on every edit and labels it `validated` or `needs-changes`. To accept one, add the `approved` label:
`game-submission-approve.yml` (stage B) validates it again, runs `scripts/add_game.py` to insert the entry sorted by
id, fetches the game's icon with `scripts/icons/fetch_icon.py --id <slug>`, checks the whole catalog with
`check-jsonschema` and `pytest tests/data`, and opens a pull request `data(games): add <name>` from `data/add-<slug>`
with `Closes #<issue>`. The label only counts when a person with write access to the repository adds it; from anyone
else, or from a bot, stage B stops before it opens anything. If the submission no longer passes, stage B comments on
the issue and opens no pull request; once it passes again, remove and re-add `approved`. The workflow's `add` job, which
reads the issue and fetches the icon, hands a patch to its `pull-request` job, which opens the pull request with the
repository's bot GitHub App token (#79), so the required checks run on it: review the diff (the new entry with its
`icon` and `icon_source`, `generated_at`, and `data/v1/icons/<slug>.png`, or only `icon_source: "none"` when the site
has no usable icon) and merge it once they pass. Catalog pull requests never merge themselves.

## Releasing

A release is a pushed tag `vX.Y.Z`. Three places name the version and must agree: `version:` in `project()` in
`meson.build` (the single source of truth), the newest `<release>` entry in
`data/io.github.tim_van_oudheusden.Dailies.metainfo.xml.in` (the human changelog, shown in the About dialog and on
Flathub), and the tag. The release manifest, `build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json`, builds
the Dailies source from a pinned `commit`, not from the checkout, so that pin has to point at the released code.

Pushing the tag runs `.github/workflows/release.yml`:

1. **Verify** runs `scripts/release_check.py verify`: the tag, the Meson version and the newest metainfo release must
   be the same version, and the release date must not be in the future. It then checks that the commit pinned in the
   release manifest has the same files as the tag, apart from the manifest itself. On any mismatch it stops before
   anything is built or published.
2. **Build** builds the release manifest for x86_64 (`ubuntu-latest`) and aarch64 (`ubuntu-24.04-arm`) in the
   `gnome-51` image, and runs `flatpak-builder-lint` on the manifest before and the repo after, with Flathub's rules
   and no exceptions. Like Flathub's builders, it mirrors the screenshots: it downloads them from the metainfo's tag
   URLs (so they only resolve once the tag is pushed), rewrites them to `dl.flathub.org/media` and commits them to
   the repo, which the repo lint requires. Until Dailies is on Flathub those media URLs do not resolve, so a software
   centre shows no screenshots for a release bundle.
   The x86_64 job also builds the FlatPark payload, `Dailies-flatpark.tar.xz`, with `scripts/flatpark_payload.py`
   (see below).
3. **Publish** creates the GitHub Release with `Dailies-x86_64.flatpak`, `Dailies-aarch64.flatpak`,
   `Dailies-flatpark.tar.xz` and `SHA256SUMS`. The body (`scripts/release_check.py notes`) is the newest metainfo
   release's description and the install instructions, followed by notes generated from the merged PRs
   (`.github/release.yml` sorts them into categories).

A tag with a `-` suffix (`v0.2.0-beta.1`) publishes a pre-release; `meson.build` and the metainfo then carry the same
`0.2.0-beta.1`. Bundles do not update themselves: users install the next bundle over the old one, and their
favourites and settings stay.

The FlatPark payload is what [FlatPark](https://flatpark.org) installs. FlatPark builds nothing from source: its
package pins this asset as Flatpak extra-data and unpacks it into `/app/extra/dailies` on the user's machine, offline,
inside `org.gnome.Platform`, which has no tool that unpacks a `.flatpak` bundle. The script runs a release-profile
`meson install` of the checkout with prefix `/app/extra/dailies` inside `org.gnome.Sdk//51` (`flatpak build`), so the
launcher and `config.py` name the paths the runtime and FlatPark use, and writes the tree as a reproducible tar.xz:
sorted members owned by root, every mtime the commit time (or `$SOURCE_DATE_EPOCH`). It holds no compiled code, so one
archive serves both arches. The `Flatpak (x86_64)` CI job builds it on every pull request too: it builds it twice and
fails unless both archives are byte-identical, then unpacks it with `bsdtar` into `/app/extra/dailies` and runs the e2e
smoke test (`tests/e2e/test_smoke.py`) against it on `org.gnome.Platform//51`. Build it locally (it needs the GNOME 51
SDK and Platform; the scratch directory `_flatpark/` is rebuilt each run):

```sh
python3 scripts/flatpark_payload.py --output Dailies-flatpark.tar.xz
```

Preview the checks and the release body locally:

```sh
python3 scripts/release_check.py verify --tag vX.Y.Z
python3 scripts/release_check.py notes
```

### Cutting a release

1. Open a pull request (`chore(release): X.Y.Z (#N)`) that raises `version:` in `meson.build` and adds a
   `<release version="X.Y.Z" date="YYYY-MM-DD">` entry at the top of `<releases>` in the metainfo, describing what
   changed for users. The Meson `appstreamcli validate` test checks the entry. Merge it.
2. Open a second pull request (`build(flatpak): pin release manifest to X.Y.Z (#N)`) that sets the `dailies` module's
   `commit` in the release manifest to the merge commit from step 1, and merge it with nothing else merged in
   between. The pin cannot go into the first pull request: a commit cannot name its own hash. It holds only a
   `commit`, so remove the `tag` that step 6 of the previous release added; a `tag` would have to point at that same
   commit, which the tag in step 4 does not.
3. Run the manual checklist below on the Devel bundle that CI built from the merge commit.
4. Tag the merge commit of step 2 and push the tag:

   ```sh
   git switch main && git pull
   git tag -a vX.Y.Z -m "Dailies X.Y.Z"
   git push origin vX.Y.Z
   ```

5. The `Release` workflow under **Actions** publishes the release, which then appears under **Releases**.
6. `.github/workflows/external-data-checker.yml` runs `flatpak-external-data-checker` every Monday (or dispatch it
   from **Actions**). It finds the new tag through the release manifest's `x-checker-data` and pins the manifest to
   the tag's `tag` and `commit`, the form a Flathub manifest uses; `create-pull-request` then opens a pull request
   from `flatpak/external-data`, labelled `flatpak` and `automated`. A pull request opened with the workflow's
   `GITHUB_TOKEN` starts no CI, so close and reopen it to run the required checks, then merge it.
   With nothing to update the run does nothing. If it runs between steps 2 and 4, it proposes the previous tag
   instead: close that pull request.

To retry a failed run, re-run its failed jobs from the Actions tab. If the tag points at the wrong commit, or Verify
reports that the pinned commit differs from the tag, delete the tag (`git push origin :refs/tags/vX.Y.Z`) and any
release it created, fix the cause, and tag again. A published release that turns out to be broken is fixed forward
with a new patch release; see [`docs/runbooks/bad-release.md`](docs/runbooks/bad-release.md).

### Manual checklist before tagging

The automated tests do not drive WebKit content or a real desktop session, so check these by hand:

- [ ] Open three games in the built-in browser, one of them a New York Times game
- [ ] Sign in or play a turn, restart Dailies, and check that the login and streak are still there
- [ ] Switch **Open games** to **Default browser** and check that a game opens in the system browser
- [ ] Dark style: the window, tiles and empty states read correctly
- [ ] Narrow the window to 360 px: the sidebar collapses and the grid stays usable
- [ ] With a screen reader (Orca), a tile reads as the game's name, then its category and difficulty
- [ ] Grant the host access ([Custom browser command](#custom-browser-command)), restart, pick **Custom command** with a
  browser command, and check that a game opens in that browser; revoke the access afterwards
- [ ] Turn off **Show games in other languages**: games in another language than the system's (Cémantix, in French)
  leave the grid and return when it is turned back on

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
grant it if you accept that. Dailies checks for the access once per run, so restart it after granting; then **Custom
command** appears under **Preferences → Opening games**, with a **Command** row for the command. Until then it is
hidden and inert, and a game set to it opens in the built-in or the default browser with a "Custom command
unavailable" toast. To take the access back:

```sh
flatpak override --user --no-talk-name=org.freedesktop.Flatpak io.github.tim_van_oudheusden.Dailies
```

For the Devel build, use `io.github.tim_van_oudheusden.Dailies.Devel` in both commands. Outside Flatpak (a native
Meson build) the command runs directly and needs no override.

The command is split like a shell would split it (`GLib.shell_parse_argv`, so quotes work), and the game's URL is
appended as one more argument; no shell runs, so nothing in the command or the URL is interpreted. Inside Flatpak it
runs as `flatpak-spawn --host -- <command…> <url>`. [Opening games](docs/architecture.md#opening-games) explains how
the access is detected.

## Translations

Dailies is translated with gettext, in the `dailies` domain. Mark strings as follows:

- Python: `_("…")`, and `ngettext("…", "…", n)` for plurals. Fill in values with named `{placeholders}` and
  `.format()` after the lookup, and put a `# Translators:` comment on the line above a string that needs context.
- Blueprint: `_("…")`. Data templates (`.desktop.in`, `.metainfo.xml.in`, `.gschema.xml.in`) are translated as
  they are.
- Not translated: log messages, ids, setting values and the catalog data in `data/v1/` (game names, descriptions,
  tags). Category and difficulty names are translated where they are shown, in `dailies/ui/library.py`; the English
  labels in `dailies/core/models.py` and `games.json` stay English.

Every file with translatable strings is listed in `po/POTFILES.in`, sorted. `tests/tooling/test_potfiles.py` (run by
`pytest`) fails when one is missing, when a listed file does not exist, or when a language in `po/LINGUAS` has no
`.po` file.

### Updating the template

After changing strings, regenerate `po/dailies.pot` and merge it into every translation, then commit both:

```sh
meson compile -C _build dailies-pot
meson compile -C _build dailies-update-po
```

This needs gettext, which the GNOME SDK has (`flatpak run --filesystem=$PWD --command=sh org.gnome.Sdk//51`).
xgettext warns that it does not know the `.blp` extension and reads those files as C, which is expected; a warning
about a missing file means `po/POTFILES.in` is out of date.

The Meson test `Template is up to date` (`tests/tooling/check_pot.py`) regenerates the template into a temporary
directory and fails when its strings differ from the committed `po/dailies.pot`, so a forgotten `dailies-pot` shows up
in `meson test` and the Flatpak build.

### Adding a language

1. Add the language code to `po/LINGUAS`, one per line, sorted.
2. Create the catalog: `msginit --no-translator -l <code> -i po/dailies.pot -o po/<code>.po`.
3. Translate it. Put your name (and optionally an email address or URL) in the `translator-credits` string to be
   credited in About; left untranslated, About lists no translator.
4. Check it: `msgfmt --check --check-accelerators=_ --statistics -o /dev/null po/<code>.po`.
5. Try it: build and install, then start the app with `LANGUAGE=<code>`. The C library ignores `LANGUAGE` under the
   `C` and `C.UTF-8` locales, so also set `LANG` to another UTF-8 locale (e.g. `LANG=en_US.UTF-8`), or the Blueprint
   strings stay in English.

`po/nl.po` (Dutch) is the first translation; `tests/gi/test_translations.py` reads it under `LANGUAGE=nl`.

### Weblate

Translations are meant to come in through [Weblate](https://weblate.org/): a project on Hosted Weblate (free libre
plan) or [Codeberg Translate](https://translate.codeberg.org/), connected to this repository through the Weblate
GitHub app. Weblate opens pull requests with translation updates and never pushes to `main`, so its changes pass the
same checks and review as any other. The component uses the gettext PO format with the file mask `po/*.po`, the
template `po/dailies.pot` and `po/LINGUAS` updated for new languages. Setting up the Weblate project is a step for
the maintainer and has not been done yet; until then, send translations as ordinary pull requests.

## Code style

- ruff's style and lint rules as configured in `pyproject.toml`; 4-space indent (`.editorconfig`).
- `dailies/core` never imports `gi`. Prefer frozen dataclasses and pure functions there.
- Type hints on public functions; model absence with `None` or an explicit result, not sentinel strings.
- UI in Blueprint, current libadwaita widgets only (no deprecated ones), following the
  [GNOME HIG](https://developer.gnome.org/hig/). Every interactive element is reachable by keyboard and has an
  accessible name; colour never carries information on its own.
- Every user-facing string goes through gettext (`_()`); see [Translations](#translations).

## Dependencies

- Ask before adding, upgrading, or removing a dependency; state the package, exact version, and rationale.
- The app has **no third-party Python runtime dependencies**. Use the GNOME Platform (GLib, GIO, libsoup, GTK,
  WebKitGTK) and the standard library. A new runtime dependency means a new Flatpak module and needs explicit approval.
- Tools that only CI and `scripts/` use live in `scripts/requirements.txt`, pinned with hashes.
- GitHub Actions are pinned to a commit SHA with a `# vX.Y.Z` comment; Dependabot proposes updates.
- Docker images, `docker://` actions and job `container:` images alike, are pinned by digest, and
  `tests/tooling/test_workflows.py` fails on a tag that is not on its reviewed allow-list. Dependabot does not update
  `docker://` references, so each pin below has its own bump procedure.
- `ghcr.io/flathub/flatpak-external-data-checker` in `.github/workflows/external-data-checker.yml`: Flathub publishes
  `:latest` in bursts, so the `checker-pin` job of `.github/workflows/nightly-compliance.yml` waits until the newest
  `:latest` was built 3 days ago, then moves the pin and its `as of` date and opens the `ci/checker-pin` pull request
  with the bot GitHub App's token (#269), so CI runs on it. Its body lists both digests, both build times and a link to
  the upstream commits in between. Skim those before you merge, as the image runs with `contents: write` and
  `pull-requests: write`. The nightly compliance row "External data checker image is :latest"
  (`scripts/check_checker_digest.py`) fails once a newer `:latest` is 10 days old and still not pinned. To bump by
  hand, run `python3 -I scripts/check_checker_digest.py --bump` (it moves the pin only once `:latest` is 3 days old),
  or replace the `sha256:…` after `@` and the date above it yourself; without `--bump` the script exits 0 while the
  pin is current or `:latest` is younger than 10 days.
- `ghcr.io/flathub-infra/flatpak-github-actions` (the `gnome-51` build image) in the `flatpak` job of
  `.github/workflows/ci.yml` and the `build` job of `.github/workflows/release.yml`. Flathub rebuilds the tag twice a
  week, so no nightly row tracks it (it would fail every few days); bump it by hand before cutting a release, when the
  runtime branch changes, and when a build needs a newer `flatpak-builder` or `flatpak-builder-lint`. Read the tag's
  current multi-arch index digest with
  `skopeo inspect --raw docker://ghcr.io/flathub-infra/flatpak-github-actions:gnome-51 | sha256sum`, then open a `ci:`
  pull request that puts it after `@sha256:` in both workflows and updates the `# gnome-51 as of <date>` comments. Both
  workflows use the same digest; the index covers x86_64 and aarch64, which `release.yml` builds on.
- `quay.io/gnome_infrastructure/gnome-build-meta:sdk-51` (GNOME's OCI mirror of `org.gnome.Sdk//51`) in
  `Dockerfile.sandbox`. Nothing runs it in CI, so nothing tracks it; bump it when the runtime branch changes, together
  with the `gnome-51` build image above. Read the tag's digest with
  `skopeo inspect docker://quay.io/gnome_infrastructure/gnome-build-meta:sdk-51 | jq -r .Digest`, put it after
  `@sha256:` and update the `sdk-51 as of <date>` comment. Its `ARG` tool versions copy `ci.yml`'s; bump them when
  `ci.yml` bumps its own.
- ruff, pytest and pytest-cov are pinned in the workflows' `pip install` lines, the ruff hook in
  `.pre-commit-config.yaml` and the `ARG`s of `Dockerfile.sandbox`; shellcheck and actionlint in the `Static checks`
  job and `Dockerfile.sandbox`. Dependabot updates none of them, and `pre-commit autoupdate` bumps only its own file,
  so bump every copy in one pull request: `tests/tooling/test_tool_pins.py` fails while any two differ.

## Agent safety layers

AI agents working in this repo are bounded by several layers:

1. **Instructions** — `AGENTS.md` (authoritative), `CLAUDE.md`, `.github/copilot-instructions.md` and
   `.cursor/rules/agent-guidance.mdc` state the rules.
2. **Project permissions** — `.claude/settings.json` pre-approves the quality gates, asks before dependency and
   history-rewriting commands, and denies reading secrets (`.env*`), force-pushes and `--no-verify` commits.
3. **Personal overrides** — `.claude/settings.local.json` (gitignored). Deny rules from the project file still apply.
4. **Structural gates** — the ruleset on `main` and CI must pass before merge, regardless of who wrote the change.

The security side of these layers (trust boundaries, secrets, supply chain, review focus, reporting) is set out in
[`docs/security/SECURITY-AI.md`](docs/security/SECURITY-AI.md). How the agents share the issue queue without stepping on
each other (claim and stage labels, hand-offs, what the workflows open) is in [`docs/multi-agent.md`](docs/multi-agent.md).

How agent work fares is measured, not guessed: the weekly `PR metrics` workflow reports how many agent-authored PRs
(`claude/*` branches and the `hive-forge-app` GitHub App) were merged vs. closed unmerged. Every metric, its cadence,
where it is published and how to reproduce it locally is catalogued in [`docs/metrics/README.md`](docs/metrics/README.md).
