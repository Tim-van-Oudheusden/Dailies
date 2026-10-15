---
key: 36
title: chore(hive): register Dailies with the owner's hive and verify ACMM Codebase L5
type: Task
labels: milestone::M0, type::chore, priority::high, ci
parent: 2
blocked_by: 11, 20, 21, 22, 23, 27, 28, 29, 30, 31, 32
---
> **Risk tier:** n/a (external system) · **Size:** XS · **Who:** owner

## Why

The brief says the repository "must meet ACMM requirements for Hive". In Hive that has an exact meaning: the dashboard's **ACMM Eval** scores each repo in `project.repos` against 50 file-existence criteria. Nothing in GitHub checks this; only a running hive can confirm it.

## Tasks

- [ ] Follow #11 for hosted vs self-hosted, `checkouts_dir` and Beads
- [ ] Install/authorise `hive-forge-app` on `Tim-van-Oudheusden/Dailies` if it isn't installed account-wide
- [ ] Spoke dashboard → **Settings → Repos → add `Dailies`** (or add it to `hive.yaml` `project.repos`). If `project.checkouts_dir` is set, add a checkout so `AGENTS.md` is injected into agent prompts
- [ ] Dashboard → **ACMM Eval → Re-evaluate** (results are cached for 1 h; `GET /api/acmm/evaluation?refresh=1`)
- [ ] For any red criterion, fix the file. Don't use **Open All**, which files `[ACMM L<n>] Add …` gap issues that would duplicate this backlog
- [ ] Set the hive's operational level for Dailies to **L2** (advisory) or **L3**. The advisor suggests L3 at coverage ≥ 40 % plus a green streak of 3, and L4 at 60 % / 5 / 70 % merge success
- [ ] Add `.acmm.yml` with `waivers: []`. Fill it only if `claude.yml` is later dropped for Hive's own agents (then waive `acmm:ai-fix-workflow` / `acmm:copilot-review-apply`)

## Acceptance criteria

- [ ] ACMM Eval shows **Codebase Level L5** with L0 8/8, L2 8/8, L3 8/8, L4 9/9, L5 5/5. L6 is not pursued (3/12 expected). Attach a screenshot
- [ ] `scripts/acmm-self-check.py` (#31) gives the same result locally; if not, re-sync the vendored criteria list
- [ ] Hive has created its own labels (`hold`, `hive/advisory`, `acmm`, `agent/*`, …) on the repo

## References

- [`mvp-first.md` §2 (ACMM result of this tree), §11 (Hive paragraph), §18.9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`hive-acmm.md` §3.2, §4, §5, §6, §9 "Registering Dailies"](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
