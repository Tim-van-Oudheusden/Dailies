# Published data not reaching users

Concerns the **data path**: the copy of `data/v1/` (`games.json`, `popularity.json`, `icons/`) that the
[Pages](../../.github/workflows/pages.yml) workflow publishes to `https://tim-van-oudheusden.github.io/Dailies/v1/`
on every push to `main` that touches `data/v1/**` or `docs/popularity/**`. Every installed app fetches from there first.
This runbook covers a merged data change that never reaches Pages, and Pages no longer serving the files at all.

## Symptom

- A data pull request was merged (a retired or broken game, an icon takedown, a week's shelves), but Pages still serves
  the old file, or the **Pages** run for the merge failed or never started.
- `https://tim-van-oudheusden.github.io/Dailies/v1/games.json` answers 404, or the Pages site is gone from the
  repository's **Settings → Pages**.
- An issue reports the game list or the shelves stuck on old content after **Refresh Game List** (Ctrl+R), or the
  banner "Showing the game list from *date*" while the machine is online.

## Why this app is different

- **A 404 from Pages does not fall back.** The app tries the next data URL (`raw.githubusercontent.com`) only on a
  network failure, a 429 or a 5xx (`Refresh.handle` in `dailies/core/cache.py`; icons work the same way in
  `dailies/core/icons.py`). Any other answer, a 404 included, ends the refresh and keeps the cached copy.
  A Pages site that is switched off, unpublished, or moved by renaming the repository stops updates for every installed
  app, and the raw fallback does not help.
- **A failed deploy fails silently for users.** When the **Pages** run fails, Pages keeps serving the previous
  deployment. Those files are valid, so apps accept them and report nothing wrong: a fix such as retiring a hijacked
  game is merged on `main` but never reaches anyone.
- **The banner comes late.** It appears only after 14 days without a successful fetch (`STALE_BANNER_AFTER` in
  `dailies/core/cache.py`), and never while Pages serves a stale but valid file.
- **The URLs are built into every installed version.** `DATA_URLS` in `dailies/config.py.in` names this repository and
  its Pages path. Users who never update keep asking those URLs, so the fix is always to restore them, never to move
  them.

## Response

### Diagnose

1. Compare what Pages serves with `main`, byte for byte. `generated_at` is not enough: a pull request can change
   `games.json` without bumping it. Pages sends `max-age=600`, so allow 10 minutes after a deploy:

   ```sh
   git fetch origin
   for f in games popularity; do
     echo "$f main:  $(git show origin/main:data/v1/$f.json | sha256sum | cut -c1-16)"
     echo "$f pages: $(curl -sS https://tim-van-oudheusden.github.io/Dailies/v1/$f.json | sha256sum | cut -c1-16)"
   done
   curl -sS -o /dev/null -w '%{http_code}\n' https://tim-van-oudheusden.github.io/Dailies/v1/games.json
   ```

2. Find the run for the merge, and why it failed:

   ```sh
   gh run list --workflow pages.yml --limit 5
   gh run view <run-id> --log-failed
   ```

   - No run for the merge: the push changed nothing under `data/v1/` or `docs/popularity/`, so it was not meant to
     publish anything. Or the Actions tab shows the workflow as disabled (`gh workflow view pages.yml`).
   - **Assemble _site** failed with `_site contains symlinks`: a symbolic link under `data/v1/` or `docs/popularity/`
     points outside the tree or nowhere. Fix it in a pull request.
   - **Deploy** failed with a 404 asking to make sure GitHub Pages is enabled: the Pages site is gone or no longer
     built by Actions. Go to step 3.
   - **Deploy** was refused by the `github-pages` environment: the run was not on `main`. The environment deploys only
     from `main`.
   - **Deploy** timed out or failed with a 5xx: check [GitHub Status](https://www.githubstatus.com) for Pages or
     Actions, and re-run once it recovers.
3. Check the Pages configuration. A working site reports `"build_type": "workflow"` and the `github.io/Dailies/` URL:

   ```sh
   gh api repos/Tim-van-Oudheusden/Dailies/pages --jq '{html_url, build_type, public}'
   ```

   A 404 here means the site is switched off.

### Fix

- **The deploy failed or never ran.** Publish `main` again. The concurrency group runs one deployment at a time and
  never cancels the running one:

  ```sh
  gh workflow run pages.yml --ref main
  gh run list --workflow pages.yml --limit 1
  ```

  Re-running the failed run (`gh run rerun <run-id> --failed`) also works, but it publishes that run's commit, not the
  latest `main`.
- **Pages is switched off or builds from a branch.** Turn it back on with GitHub Actions as the source, then publish:

  ```sh
  gh api -X POST repos/Tim-van-Oudheusden/Dailies/pages -f build_type=workflow   # the site is gone
  gh api -X PUT repos/Tim-van-Oudheusden/Dailies/pages -f build_type=workflow    # the site builds from a branch
  gh workflow run pages.yml --ref main
  ```

- **The repository was renamed or transferred.** Every installed app still asks for the old URLs, and the old Pages
  URL answers 404, which does not fall back. Rename or move it back.

Then run the comparison from Diagnose step 1 again until both checksums match and Pages answers 200.

### Tell users

Users need to do nothing. Apps pick up the files within 6 hours of being opened, or at once with **Refresh Game List**
(Ctrl+R). If the outage held back a hijack or takedown fix, reply on that issue once Pages serves it, as
[Game link hijacked, moved or dead](catalog-link.md) and [Game icon taken down](game-icon.md) describe.

### Follow up

- If Pages served the wrong content for more than a day, or a hijack or takedown fix was held back, write a postmortem
  from [`docs/postmortems/TEMPLATE.md`](../postmortems/TEMPLATE.md). There is no telemetry; for **Impact**, give the
  time from the merge to the deploy that published it (`gh run list --workflow pages.yml`) plus the 6-hour refresh
  window.
- If the cause can happen again, file an issue for it.

## Prevention

- `pages.yml` refuses a `_site` with symbolic links before uploading, and the `github-pages` environment deploys only
  from `main`.
- The app checks every download before replacing its cached copy and keeps the last good one, so a broken deployment
  never empties the game list.
- Not covered: nothing compares what Pages serves with `main`, and nothing alerts when a **Pages** run fails apart
  from GitHub's own failed-run notification. After merging a data fix that has to reach users, check it as Diagnose
  step 1 describes.
