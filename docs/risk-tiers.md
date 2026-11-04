# Risk tiers

Every pull request is classified into one of three risk tiers from the paths it changes.
`.github/workflows/tier-classifier.yml` runs `scripts/tier-classify.sh` on each PR and posts the tier, plus every
changed file with its own tier, to the `Risk tier` job summary. The classification never fails the run: it tells
reviewers how closely to look, and it decides who merges. The [merge queue](multi-agent.md#merge-queue) merges low- and
medium-risk pull requests once their required checks pass, so review them before then or add `hold`. It leaves
high-risk pull requests for the maintainer to merge after the review below.

The **highest tier of any changed file wins**, so one workflow edit makes the whole PR high risk. A path that matches no
rule is **medium**, and medium merges without a human review, so a new kind of file that configures a gate, the build
or the sandbox needs a high rule in the same PR that adds it.

The workflow runs the **base branch's** script and risk assessment (a second checkout of the base commit) against the
PR's diff, so a PR cannot lower its own tier by editing either. A change to the rules takes effect for the PRs after it
merges.

Run it locally against your branch:

```sh
git diff -z --name-only --no-renames origin/main...HEAD | scripts/tier-classify.sh -z
```

`--no-renames` matters: with rename detection on, a moved file is listed only under its new path, so moving
`.github/workflows/ci.yml` to `docs/ci.yml` would read as a low-risk docs change. Without it, the old path is listed
too.

`-z` on both sides passes the paths NUL-terminated. Without it, git C-quotes any path holding non-ASCII, `"`, `\` or a
control character (`".github/workflows/d\303\251ploy.yml"`); the script decodes a line in exactly that form back to
the path before matching it, so a high-risk file such as `.github/workflows/déploy.yml` is still high. A line that is
not exactly git's quoting is matched as written.

## Tier: high

Changes that alter how the app is built, gated, sandboxed or released, what data contract it reads, or how agents
behave. A mistake here can bypass every other check or ship to every user.

| Paths | Why |
| --- | --- |
| `.github/**` | CI gates, review rubric, release workflow, rulesets, the risk rules |
| `scripts/**` | Gate tooling, the submission validator, the link checker, the popularity pipeline |
| `tests/tooling/**` | The policy tests: workflows, token scopes, ruleset, CODEOWNERS, risk tiers, manifests, tool pins |
| `pyproject.toml` | ruff rules and per-file ignores, pytest `addopts`, coverage roots and omissions |
| `*/pyproject.toml`, `ruff.toml`, `*/ruff.toml`, `.ruff.toml`, `*/.ruff.toml` | ruff uses the nearest config, so one in a subdirectory replaces the root settings for the files under it |
| `conftest.py`, `*/conftest.py` | What pytest collects: `collect_ignore`, collection hooks |
| `pytest.ini`, `*/pytest.ini`, `.pytest.ini`, `*/.pytest.ini`, `pytest.toml`, `*/pytest.toml`, `.pytest.toml`, `*/.pytest.toml`, `tox.ini`, `*/tox.ini`, `setup.cfg`, `*/setup.cfg` | pytest reads the first config it finds from the common ancestor of its arguments (`tests/` in CI) upwards, so one of these in `tests/` replaces `pyproject.toml`'s `addopts` |
| `.coveragerc` | coverage.py reads it, and the `[coverage:*]` sections of `setup.cfg` and `tox.ini`, before `pyproject.toml` |
| `.pre-commit-config.yaml` | The local hooks and their pinned revisions |
| `Dockerfile.sandbox` | The image agents run the quality gates in |
| `build-aux/**` | Flatpak manifests: sandbox permissions (`finish-args`), runtime, sources |
| `meson.build`, `meson_options.txt` | The build, the version that a release is cut from, the install layout |
| `subprojects/**` | The wraps Meson falls back to, such as the `blueprint-compiler` tag the Windows build uses |
| `data/*.metainfo.xml.in` | Release notes, licence, branding and content rating shown to users and Flathub |
| `data/*.gschema.xml.in` | Stored settings: a removed or retyped key breaks existing installs |
| `data/v1/schema/**` | The data contract with every installed copy of the app |
| `AGENTS.md`, `CLAUDE.md`, `.claude/**`, `.cursor/**`, `prompts/**` | Agent instructions, permissions and governance |

Review: a human reviews the full diff line by line. Dependency changes follow the rules in `AGENTS.md` (approved, exact
version, `scripts/requirements.txt` pinned with hashes). Workflow changes keep event fields in `env:`, never inline in
`run:`, and update `tests/tooling/test_workflows.py` when they add a workflow or widen a token scope. Manifest changes
justify every `finish-args` entry in one line, and never add `--talk-name=org.freedesktop.Flatpak` or a `--filesystem`
permission. A schema change is a breaking change: it goes to `data/v2/`, not into `data/v1/schema/`. Agents may propose
none of these without explicit maintainer approval ([`SECURITY-AI.md`](security/SECURITY-AI.md#dailies-rules)).

`.github/CODEOWNERS` makes the maintainer the owner of exactly these paths, so a PR that touches one requests his
review automatically (GitHub skips the request when he opened the PR himself, as local agents do under his account).
`tests/tooling/test_codeowners.py` fails if a tracked file is rated high but has no owner, or has an owner but is not
rated high, so a new high-risk rule needs a matching CODEOWNERS pattern in the same PR. The ruleset does not require
the code owner's approval (`require_code_owner_review` is off in `.github/rulesets/main.json`), since an author cannot
approve his own PR: CODEOWNERS requests the review, it does not block the merge. What keeps a high-risk PR from
merging unreviewed is that only the maintainer merges it.

## Tier: medium

Application code and catalog data: `dailies/**` and `data/v1/*.json`, plus anything not otherwise classified, such as
the tests outside `tests/tooling/`, `po/`, the Blueprint files, icons and desktop file under `data/`, and root files such
as `.editorconfig`.

The ruleset requires no approving review, so the merge queue merges a medium-risk pull request as soon as its required
checks pass. The review below happens only if someone does it before then, or adds `hold` to make time for it.

Review: the standard rubric in `.github/workflows/review.yml`: TDD evidence, behaviour-level tests, no weakened tests,
looks like libadwaita and follows the HIG, keyboard and screen reader usable, quality gates green. A catalog change
has passed the submission validator and the schema check, and every new URL's final domain matches its `domain`.

## Tier: low

Prose that does not execute: `docs/**`, and Markdown files (`*.md`) outside the high-risk paths.

Review: a read-through for accuracy against the code and workflows it describes.

## Changing the tiers

The rules are policy as code in the risk assessment config, `.github/risk-assessment.yml`: an ordered `rules:` list of
`- <tier> <glob>` items, one per line, where the **first matching rule wins**, so high-risk rules sit above broad globs
such as `dailies/**` and `*.md` (`AGENTS.md` is high even though `*.md` is low, `data/v1/schema/**` is high even though
`data/v1/*.json` is medium). `*` matches across `/`, so the file writes a directory rule as `dir/*`; this document shows
it as `dir/**`. `scripts/tier-classify.sh` evaluates the rules and fails without a tier if a line is not a blank line, a
whole-line `#` comment, the `rules:` line or such an item, or if an item names an unknown tier; set `RISK_TIER_POLICY`
to try a different file locally.

`scripts/tier-classify.test.sh` covers the engine and the shipped rules, and `tests/tooling/test_tier_classify.py` runs
it under `pytest`, checks that the file is YAML and that every rule appears under its tier above. Update the rules,
their tests, and this document in the same PR. The config (`high .github/**`), the script and its shell tests
(`high scripts/**`) and the pytest file (`high tests/tooling/**`) are high risk; this doc is low.
