# Re-enable a scheduled workflow

Concerns the **data path**: the weekly `popularity.json` every installed app fetches from GitHub.

## Symptom

- No `data(popularity): week <ISO week>` pull request appeared on a Monday (the
  [Weekly popularity](../../.github/workflows/popularity.yml) workflow runs at 04:17 UTC).
- The app's This Week page shows its subtitle as "Week 2026-W42 (as of 12 Oct)" instead of "Week 2026-W42": the
  installed apps' `popularity.json` is past its `valid_until`.
- The Actions tab shows a banner on the workflow: "This scheduled workflow is disabled because there hasn't been
  activity in this repository for at least 60 days."

## Why this app is different

GitHub disables scheduled workflows in a public repository after 60 days without repository activity (pushes, pull
requests, issues and the like). Dailies has no server to notice that the shelves stopped moving, and the app does not
fail: `valid_until` is `generated_at` plus 10 days, so a late or skipped run is absorbed, and after that the app keeps
showing the last shelves with an "as of" date. Nothing breaks visibly; the shelves just stop rotating. The same rule
applies to the other scheduled workflows (`external-data-checker.yml`, `nightly-compliance.yml`, `pr-metrics.yml`,
`quality-report.yml`).

## Response

1. Confirm the cause. A workflow disabled for inactivity reports the state `disabled_inactivity`:

   ```sh
   gh api repos/Tim-van-Oudheusden/Dailies/actions/workflows/popularity.yml --jq .state
   gh workflow list --all
   ```

   `active` means the schedule is on and the run failed or was skipped instead: follow
   [Weekly popularity pull request missing or wrong](popularity.md).
2. Re-enable it: in the Actions tab, select **Weekly popularity** and choose **Enable workflow** on the banner, or run

   ```sh
   gh workflow enable popularity.yml
   ```

   Do the same for every other workflow `gh workflow list --all` shows as disabled.
3. Catch up without waiting for Monday: start a run by hand (Actions tab, **Run workflow**, or the command below),
   then review and merge the pull request it opens as usual.

   ```sh
   gh workflow run popularity.yml
   ```

4. Users need to do nothing: their apps pick up the new `popularity.json` at the next revalidation, within a few
   hours of the merge, and the "as of" date disappears.

## Prevention

- Merging the weekly data pull request, a Dependabot update or a game submission puts a commit on `main`, which
  resets the 60-day clock; the limit is only reached when nothing lands for two months.
- `valid_until` (+10 days) keeps the shelves looking current through one missed Monday; the "as of" subtitle makes a
  longer gap visible to users instead of hiding it.
- Nothing alerts the maintainer automatically: a missing Monday pull request is the signal to check.
