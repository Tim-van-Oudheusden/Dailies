---
key: 56
title: ci(data): publish data/v1 to GitHub Pages and make Pages the primary data URL
type: Task
labels: milestone::M2, type::task, priority::medium, ci, data
parent: 4
blocked_by: 18, 26, 39
---
> **Risk tier:** high (workflow) and medium (`config.py.in`) · **Size:** S

## Why

Measured cache behaviour: GitHub Pages serves `max-age=600` + ETag, and raw.githubusercontent serves `max-age=300` + ETag. The plan uses **Pages as primary and raw as fallback**, so one outage doesn't stop refreshes. Pages also serves the weekly reports from M3.

## Tasks

- [ ] `.github/workflows/pages.yml`: on `push: branches: [main]` with `paths: ['data/v1/**', 'docs/popularity/**']`, plus `workflow_dispatch`
  - Job `build`: assemble `_site/v1/` (a copy of `data/v1/`, including the schemas) and `_site/popularity/` (a copy of `docs/popularity/`, once it exists), add an `index.html` stub, then `actions/upload-pages-artifact@fc324d35… # v5.0.0`
  - Job `deploy`: `permissions: pages: write, id-token: write`, `environment: github-pages`, `actions/deploy-pages@368f8252… # v5.0.1` (full SHAs in [`data-pipeline.md`](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md) / [`flatpak-release-pipeline.md` Appendix A](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md))
  - Don't put symlinks in the artifact (Pages limitation)
- [ ] `dailies/config.py.in`: `DATA_URLS = ["https://tim-van-oudheusden.github.io/Dailies/v1/", "https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/main/data/v1/"]`. The fetcher (#39) already falls through on 5xx/429/network errors
- [ ] The `tests/tooling/test_workflows.py` (#33) rule "every `data/v1/*.json` is in the Pages artifact" now applies

## Acceptance criteria

- [ ] `curl -sI https://tim-van-oudheusden.github.io/Dailies/v1/games.json` returns 200 with an `ETag`, and a second request with `If-None-Match` returns 304
- [ ] With Pages blocked (`/etc/hosts` or a firewall rule), the app falls through to raw and still refreshes
- [ ] A merge that changes `data/v1/games.json` is live on Pages within ~10 minutes

## References

- [`mvp-first.md` §7.5, §11 (pages row)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
