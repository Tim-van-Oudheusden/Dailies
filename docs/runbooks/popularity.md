# Weekly popularity pull request missing or wrong

Concerns the **data path**: `data/v1/popularity.json`, the Popular and Trending shelves every installed app fetches
from GitHub. The [Weekly popularity](../../.github/workflows/popularity.yml) workflow writes it every Monday at
04:17 UTC and opens a `data(popularity): week <ISO week>` pull request on the branch `data/popularity`, which merges
itself once the required checks pass (#79); a failed check leaves it open for a maintainer.

## Symptom

- No `data(popularity): week …` pull request on a Monday, or one that is still open from an earlier week.
- The pull request's shelves look wrong: a game far too high or missing, one publisher crowding a shelf, the same
  games as last week, many failed or unranked domains in its body.
- The pull request stays open: a required check failed, or auto-merge was never turned on.
- In the app, This Week's subtitle reads "Week 2026-W42 (as of 12 Oct)": the merged file is past its `valid_until`.

## Why this app is different

- **Wrong shelves reach every user within hours of the auto-merge**, without a release and without a person reading
  them first. The app validates the file's structure, not whether the ranking makes sense; compute.py's fail-closed
  rules, the guard and CI are the only checks before users see it.
- **Missing a week is cheap.** `valid_until` is `generated_at` plus 10 days, so last week's shelves stay current until
  the Thursday after a missed Monday, and after that the app keeps showing them with an "as of" date. Closing a bad
  pull request is always a safe answer.
- **The workflow fails closed.** `scripts/popularity/compute.py` exits 1 and writes nothing when Tranco failed for more
  than 20 % of the active games' domains (`MAX_FAILED_SHARE = 0.2`; with 97 domains, 20 or more failures), so a
  Tranco outage produces no pull request rather than a broken one.

## Response

### Diagnose

1. Find the run and its jobs, **Collect and compute** (`compute`), **Write the report** (`publish`) and **Open and
   auto-merge the data pull request** (`pull-request`):

   ```sh
   gh run list --workflow popularity.yml
   gh run view <run-id>
   gh run view <run-id> --log-failed
   ```

   No run on a Monday at all: the schedule may be disabled; follow
   [Re-enable a scheduled workflow](re-enable-cron.md).
2. If **Collect and compute** failed, the failing step says why:
   - **Compute shelves**, exit 1, `compute: Tranco failed for N of M domains (more than 20%)`: Tranco was down or
     rate-limiting. Check that it answers (one request; a second within the same second gets a 429):

     ```sh
     curl -sS -o /dev/null -w '%{http_code}\n' https://tranco-list.eu/api/ranks/domain/nytimes.com
     ```

   - **Compute shelves**, exit 2, `compute: <domain>: unknown game '<id>'` or `weights must sum to 1`:
     `data/v1/domain_weights.json` no longer matches `data/v1/games.json` (a game was deleted or moved domain).
     Fix the weights in a pull request; compute.py's checks are listed in
     [`docs/data-format.md`](../data-format.md).
   - **Validate against the schema** or **Install script dependencies** failed: a code or dependency problem; fix it
     in a pull request like any other bug.
3. If **Open and auto-merge the data pull request** failed: **Guard the changed paths and link the report** fails on
   any change outside `data/v1/popularity.json` and the week's report; **Create the bot token** fails when the `bot`
   environment's App key is missing or revoked, or the App lost access to the repository; **Create pull request** and
   **Merge once the required checks pass** fail when the token may not push, open or merge pull requests, or when
   "Allow auto-merge" is off under Settings > General.
4. If the shelves look wrong, inspect the inputs. Every run uploads the `popularity-raw` artifact (kept 90 days, also
   when compute failed closed): `raw/tranco.json` (each domain's daily ranks, `ok`, HTTP `status`, `error`) and
   `result/summary.json` (failed and unranked domains, both shelves, the top movers). The computed file itself is in
   the pull request, or in the `popularity-result` artifact (kept 7 days):

   ```sh
   gh run download <run-id> -n popularity-raw -D /tmp/popularity-raw
   jq '.sources' /tmp/popularity-raw/result/summary.json
   jq '.domains["nytimes.com"]' /tmp/popularity-raw/raw/tranco.json
   ```

   Reproduce the week locally from the downloaded ranks (pass `--now` with the run's time to get the same `week` and
   trend):

   ```sh
   python -I scripts/popularity/compute.py --catalog data/v1/games.json --raw /tmp/popularity-raw/raw/ \
     --previous data/v1/popularity.json --out /tmp/popularity.json --summary /tmp/summary.json \
     --now 2026-10-19T04:21:09Z
   ```

   Usual causes: a domain that failed and was carried forward (`"reason": "carried_forward"` on its `popular[]` or
   `trending[]` item), an unranked domain (scores 0), a shared domain whose games are picked in the wrong order
   (`data/v1/domain_weights.json`), or a catalog change since last week. The method is in
   [`docs/data-format.md`](../data-format.md).
5. If the pull request stays open: one of its required checks failed (`gh pr checks <number>`), or the **Merge once
   the required checks pass** step failed.

### Fix

- **Re-run after a Tranco outage or a fixed bug.** Re-run the failed jobs, or start a new run from `main` (Actions
  tab, **Weekly popularity → Run workflow**). One run goes at a time; a new run replaces the commit on the open
  `data/popularity` pull request:

  ```sh
  gh run rerun <run-id> --failed
  gh workflow run popularity.yml
  ```

- **Shared-domain order wrong.** Change the weights in `data/v1/domain_weights.json` (numbers between 0 and 1 that
  sum to 1 per domain; the heaviest game is picked first, at most two per domain per shelf) in a pull request, merge
  it, then start a new run.
- **Shelves wrong for another reason.** Before it merges: turn auto-merge off (`gh pr merge --disable-auto <number>`)
  and close the pull request; the current shelves stay. Or push a correcting commit to `data/popularity` and let it
  merge; the [popularity-report metric](../metrics/README.md#popularity-report) counts it as edited. After it merged:
  revert the merge commit in a pull request.
- **A required check failed.** Read the failing check, fix the cause in its own pull request if it is a code bug, then
  start a new run, or merge the open pull request by hand once its checks pass.
- **Weekly report.** If the workflow has the `narrate` input wired to a report step (#66) and only the report failed,
  the numbers in the pull request are still valid: merge it, then either start a run with the report
  (`gh workflow run popularity.yml -f narrate=true`) or skip the report for that week. Until #66 lands, `narrate` is
  accepted and ignored.

Users need to do nothing: their apps fetch the merged file within a few hours.

### Follow up

- Shelves that reached users wrong, or more than one missed week: write a postmortem from
  [`docs/postmortems/TEMPLATE.md`](../postmortems/TEMPLATE.md).
- A recurring cause (the same domain failing, a weights file falling behind the catalog): file an issue for it.

## Prevention

- compute.py fails closed above 20 % failed domains, validates against `data/v1/schema/popularity.schema.json`, and
  rejects a malformed weights file; the workflow validates once more with `check-jsonschema` and refuses changes
  outside its paths.
- Every change waits for the required checks before it merges itself; the pull request body lists the top five and the
  failed and unranked domains, so a broken week is visible in the merged pull request.
- The [popularity-report metric](../metrics/README.md#popularity-report) tracks failed runs, stale weeks and edited
  pull requests over time.
- Nothing alerts the maintainer: a missing Monday pull request is the signal to check.
