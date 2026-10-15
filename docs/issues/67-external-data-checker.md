---
key: 67
title: ci(flatpak): weekly flatpak-external-data-checker
type: Task
labels: milestone::M3, type::task, priority::low, ci, flatpak
parent: 5
blocked_by: 25, 51
---
> **Risk tier:** high · **Size:** XS

## Why

Neither Dependabot nor Renovate has a Flatpak-manifest manager. Bazaar uses `flatpak-external-data-checker` to bump `x-checker-data` sources. For Dailies it is only useful once the **release** manifest carries a real `v*` tag source with `x-checker-data` (#25, #51).

## Tasks

- [ ] `.github/workflows/external-data-checker.yml`: Bazaar's file with the cadence changed to **weekly** ([`flatpak-release-pipeline.md` Appendix A.5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)). It runs `docker://ghcr.io/flathub/flatpak-external-data-checker:latest --update --never-fork --require-important-update build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json`
- [ ] Permissions: `contents: write`, `pull-requests: write`. Off-zero cron minute
- [ ] Add the `:latest` docker reference to the reviewed allow-list in `tests/tooling/test_workflows.py` (#33), with a reason, or pin it by digest

## Acceptance criteria

- [ ] After a new `v*` tag, a dispatched run opens a PR bumping the release manifest's `tag` and `commit`
- [ ] With nothing to update, the run is a green no-op

## References

- [`mvp-first.md` §11 (external-data-checker row), §16 (M3)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`flatpak-release-pipeline.md` §8, Appendix A.5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
- [`bazaar.md` §8.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/bazaar.md)
