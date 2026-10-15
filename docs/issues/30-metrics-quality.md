---
key: 30
title: ci: PR metrics, weekly quality report + auto-QA tuner, apply-suggestions workflow
type: Task
labels: milestone::M0, type::task, priority::medium, ci
parent: 2
blocked_by: 28
---
> **Risk tier:** high · **Size:** S (all copied, almost verbatim) · **ACMM:** `pr-acceptance-metric`, `quality-dashboard`, `auto-qa-self-tuning`, `copilot-review-apply`

## Tasks

- [ ] `.github/workflows/pr-metrics.yml` + `scripts/pr-metrics.sh`: MU verbatim ([`hive-acmm.md` Appendix A.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)). Weekly on **Monday 06:17 UTC**. Reports acceptance rate, split into agent PRs (`claude/*` branches or author `hive-forge-app`) and human PRs
- [ ] `.github/workflows/quality-report.yml` + `scripts/quality-report.sh` + `scripts/auto-qa-tuner.sh`: MU verbatim ([`hive-acmm.md` Appendix A.8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)). Weekly Markdown report to the job summary plus an artifact. The tuner ratchets the floors in `.github/auto-qa-tuning.json` (#28) up by at most `margin`. Swap the gate commands for the #21 list
- [ ] `.github/workflows/auto-review.yml` + `scripts/apply-review-suggestions.sh`: MU verbatim ([`hive-acmm.md` Appendix A.9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)). An `/apply-suggestions` comment from a trusted reviewer (OWNER/MEMBER/COLLABORATOR) applies suggestion blocks
- [ ] Every scheduled cron uses an off-zero minute (`17`, `23`, …), never `0`

## Acceptance criteria

- [ ] `workflow_dispatch` runs of `pr-metrics.yml` and `quality-report.yml` succeed and write their Markdown to the job summary
- [ ] The tuner reads the #28 JSON, and a dry run proposes no change when coverage equals floor + margin
- [ ] shellcheck and actionlint pass

## References

- [`mvp-first.md` §11 (pr-metrics, quality-report, auto-review rows)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`hive-acmm.md` §9 Phase 2–3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
