---
key: 29
title: ci: PR-time governance — review rubric, risk-tier classifier, path labeler
type: Task
labels: milestone::M0, type::task, priority::high, ci
parent: 2
blocked_by: 18
---
> **Risk tier:** high · **Size:** M · **ACMM:** `pr-review-rubric`, `tier-classifier`, `change-classification`, `auto-label`, `policy-as-code`

## Why

These three workflows run on every PR. **`PR review rubric`** is a required check. The tier classifier and the labeler make the risk of each change visible.

## Tasks

### Review rubric
- [ ] `.github/workflows/review.yml` + `scripts/pr-review-check.sh` + `scripts/pr-review-check.test.sh`: MU verbatim ([`hive-acmm.md` Appendix A.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)). Job name **`PR review rubric`**. The check enforces a Conventional Commits PR title (regex in the script) and `Fixes #N` in the body. Inputs reach the script **only via `env:`** (`PR_TITLE`, `PR_BODY`, `PR_AUTHOR`)
- [ ] Edit the rubric bullets to "Looks like libadwaita / follows HIG", "No new finish-args" and "Catalog change validated"

### Tier classifier
- [ ] `.github/workflows/tier-classifier.yml` + `scripts/tier-classify.sh`: MU verbatim. The classifier runs **from the base branch**, so a PR cannot weaken its own classification
- [ ] `.github/policies/risk-tiers.policy`. First matching rule wins; a path that matches nothing is medium:

```text
# high — gates, tooling, packaging, schemas, agent instructions
high .github/*
high scripts/*
high build-aux/*
high meson.build
high meson_options.txt
high data/*.metainfo.xml.in
high data/*.gschema.xml.in
high data/v1/schema/*
high AGENTS.md
high CLAUDE.md
high .claude/*
high .cursor/*
high prompts/*
# medium — app code and catalog data
medium dailies/*
medium data/v1/*.json
# low — prose
low docs/*
low *.md
```

`docs/risk-tiers.md` (#22) must describe the same rules.

### Labeler
- [ ] `.github/workflows/labeler.yml`: **byte-identical** to MU/website. It is the **only** workflow allowed to use `pull_request_target`, and it never checks out PR code
- [ ] `.github/labeler.yml` with these path labels:

| Label | Paths |
|---|---|
| `app` | `dailies/**`, `data/ui/**` |
| `data` | `data/v1/**`, `scripts/popularity/**`, `scripts/*submission*`, `scripts/add_game.py`, `scripts/check_links.py` |
| `flatpak` | `build-aux/**`, `data/*.metainfo.xml.in`, `data/*.desktop.in` |
| `ci` | `.github/**` |
| `documentation` | `docs/**`, `*.md` |

## Acceptance criteria

- [ ] A PR titled `wip stuff` without `Fixes #N` fails `PR review rubric`, and the failure lists both problems
- [ ] A PR touching `build-aux/flatpak/*.json` gets tier `high` and the label `flatpak`
- [ ] `scripts/pr-review-check.test.sh` passes; shellcheck and actionlint pass
- [ ] Labeler/policy parity is asserted by `tests/tooling/test_workflows.py` (#33)

## References

- [`mvp-first.md` §2 tree (policies, labeler), §11 (review, tier-classifier, labeler rows), §14 (Risk tiers)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`hive-acmm.md` §9 Phase 2–3, Appendix A.2, A.4, A.5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
