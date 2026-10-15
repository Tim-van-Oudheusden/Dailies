# Risk tiers

Every pull request is classified into one of three risk tiers from the paths it changes.
`.github/workflows/tier-classifier.yml` runs `scripts/tier-classify.sh` on each PR and posts the tier, plus every
changed file with its own tier, to the `Risk tier` job summary. The classification is informational: it never fails the
run, it tells reviewers how closely to look.

The **highest tier of any changed file wins**, so one workflow edit makes the whole PR high risk. A path that matches no
rule is **medium**: new kinds of files get a real review until they are classified.

The workflow runs the **base branch's** script and policy (a second checkout of the base commit) against the PR's diff,
so a PR cannot lower its own tier by editing either. A change to the policy takes effect for the PRs after it merges.

Run it locally against your branch:

```sh
git diff --name-only --no-renames origin/main...HEAD | scripts/tier-classify.sh
```

`--no-renames` matters: with rename detection on, a moved file is listed only under its new path, so moving
`.github/workflows/ci.yml` to `docs/ci.yml` would read as a low-risk docs change. Without it, the old path is listed
too.

## Tier: high

Changes that alter how the app is built, gated, sandboxed or released, what data contract it reads, or how agents
behave. A mistake here can bypass every other check or ship to every user.

| Paths | Why |
| --- | --- |
| `.github/**` | CI gates, review rubric, release workflow, rulesets, this policy |
| `scripts/**` | Gate tooling, the submission validator, the link checker, the popularity pipeline |
| `build-aux/**` | Flatpak manifests: sandbox permissions (`finish-args`), runtime, sources |
| `meson.build` | The build, the version that a release is cut from, the install layout |
| `data/*.metainfo.xml.in` | Release notes, licence, branding and content rating shown to users and Flathub |
| `data/*.gschema.xml.in` | Stored settings: a removed or retyped key breaks existing installs |
| `data/v1/schema/**` | The data contract with every installed copy of the app |
| `AGENTS.md`, `CLAUDE.md`, `.claude/**` | Agent instructions, permissions and governance |

Review: a human reviews the full diff line by line. Dependency changes follow the rules in `AGENTS.md` (approved, exact
version, `scripts/requirements.txt` pinned with hashes). Workflow changes keep event fields in `env:`, never inline in
`run:`, and update `tests/tooling/test_workflows.py` when they add a workflow or widen a token scope. Manifest changes
justify every `finish-args` entry in one line, and never add `--talk-name=org.freedesktop.Flatpak` or a `--filesystem`
permission. A schema change is a breaking change: it goes to `data/v2/`, not into `data/v1/schema/`. Agents may propose
none of these without explicit maintainer approval ([`SECURITY-AI.md`](security/SECURITY-AI.md#dailies-rules)).

## Tier: medium

Application code and catalog data: `dailies/**` and `data/v1/*.json`, plus anything not otherwise classified, such as
`tests/`, `pyproject.toml`, `po/`, the Blueprint files, icons and desktop file under `data/`, and root files such as
`.editorconfig`.

Review: the standard rubric in `.github/workflows/review.yml`: TDD evidence, behaviour-level tests, no weakened tests,
looks like libadwaita and follows the HIG, keyboard and screen reader usable, quality gates green. A catalog change
has passed the submission validator and the schema check, and every new URL's final domain matches its `domain`.

## Tier: low

Prose that does not execute: `docs/**`, and Markdown files (`*.md`) outside the high-risk paths.

Review: a read-through for accuracy against the code and workflows it describes.

## Changing the tiers

The rules are policy as code in `.github/policies/risk-tiers.policy`: one `<tier> <glob>` rule per line, where the
**first matching rule wins**, so high-risk rules sit above broad globs such as `dailies/**` and `*.md` (`AGENTS.md` is
high even though `*.md` is low). `*` matches across `/`. `scripts/tier-classify.sh` evaluates the policy and fails
without a tier if a rule is malformed or names an unknown tier; set `RISK_TIER_POLICY` to try a different policy file
locally.

The engine and the shipped rules are covered by tests under `tests/`, which also check that every rule appears under its
tier above and that `.github/labeler.yml` labels the same paths. Update the policy, its tests, and this document in the
same PR. The policy file (`high .github/**`) and the script (`high scripts/**`) are high risk; the tests are medium and
this doc is low.
