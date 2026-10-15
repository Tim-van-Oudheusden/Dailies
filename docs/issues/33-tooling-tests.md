---
key: 33
title: test(tooling): workflow invariant tests (tests/tooling/test_workflows.py)
type: Task
labels: milestone::M0, type::task, priority::medium, ci
parent: 2
blocked_by: 27, 29
---
> **Risk tier:** medium · **Size:** S

## Why

Seventeen workflows is a lot for one maintainer. MinimalUI pins its workflow conventions in a "tooling" test module so a careless edit fails CI instead of quietly weakening security. This ticket ports that module to Python/PyYAML.

## Invariants to assert (for every file in `.github/workflows/`)

- [ ] A top-level `permissions:` map exists and equals `{contents: read}` (or a reviewed allow-list per file kept in the test)
- [ ] Every job that needs more declares its own `permissions:`, matching a reviewed per-job map in the test
- [ ] Every job has `timeout-minutes`
- [ ] Every `uses:` that is not a local path is pinned to a **40-hex SHA** followed by a `# vX.Y.Z` comment. Docker refs (`docker://…`) must use a digest or appear in an explicit allow-list with a reason (e.g. `flatpak-external-data-checker:latest`, #67)
- [ ] No `${{ github.event.* }}` appears inside any `run:` script (values go through `env:`)
- [ ] `pull_request_target` appears **only** in `labeler.yml`, and that file has no `actions/checkout` step
- [ ] Every label in `.github/labeler.yml` exists in the list documented in #18, and every path label is also referenced by the risk-tier policy where relevant (labeler/policy parity)
- [ ] Every `data/v1/*.json` is included in the artifact path of `pages.yml`. Skip this check if `pages.yml` doesn't exist yet; it starts applying with #56
- [ ] Every scheduled `cron` avoids minute `0`

## Acceptance criteria

- [ ] `pytest tests/tooling` passes on `main`, and `Build, lint, test` (#27) runs it
- [ ] Each invariant has a negative test using an inline YAML fixture
- [ ] Workflows added later (#51, #56, #58, #59, #62, #66, #67, #73) must pass this module; it is the checklist for those PRs

## References

- [`mvp-first.md` §11 (shared properties), §12 (Tooling row)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`scaffolding-repos.md` §1, §8.5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md)
