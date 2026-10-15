---
key: 68
title: docs(runbooks): bad release, popularity, re-enable cron; popularity metric
type: Task
labels: milestone::M3, type::task, priority::low, documentation
parent: 5
blocked_by: 51, 62
---
> **Risk tier:** low · **Size:** S

## Runbooks (`docs/runbooks/`, MU shape: symptoms → diagnosis → fix → follow-up)

- [ ] `bad-release.md`: a broken bundle was published. Mark the GitHub Release as pre-release or delete its assets, publish a `vX.Y.Z+1` hotfix, and add a metainfo release note. Bundles don't self-update, so pin a notice to the README Status line. Write a postmortem from `docs/postmortems/TEMPLATE.md`
- [ ] `popularity.md`: the Monday PR is missing or wrong. Check the Actions run. If the `compute` job failed, check Tranco API health and the fail-closed threshold (> 20 % of domains). Re-run with `workflow_dispatch`. If the shelves look wrong, inspect the raw artifact (kept 90 days) and consider `domain_weights.json` (#13). If the narrative failed, the numbers PR is still valid; dispatch with `narrate: true` or skip the report for the week
- [ ] `re-enable-cron.md`: written in #62; review it and link it from the index
- [ ] Update `docs/runbooks/README.md` with an index of all three

## Metrics

- [ ] `docs/metrics/README.md` (#22): add the **popularity-report metric**: weekly run success rate, number of weeks the shelves were stale (`now > valid_until` at the time of the next run), and how many PRs merged unchanged vs edited by the maintainer

## Acceptance criteria

- [ ] Each runbook has been dry-run once by following it literally (note anything missing)
- [ ] `docs/runbooks/` keeps its plural name (it does not need to match ACMM L6's `docs/runbook/`)

## References

- [`mvp-first.md` §2 tree (runbooks, metrics), §16 (M3), §17 risk 6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`hive-acmm.md` §9 Phase 4–5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
