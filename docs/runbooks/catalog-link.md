# Game link hijacked, moved or dead

Concerns the **data path**: an entry's `url` in `data/v1/games.json`, the catalog every installed app fetches from
GitHub. A game's site can die, move to a new domain, or lapse and be bought by someone else (in this genre, usually a
casino or slot site). The weekly link check catches most of these on its own schedule; this runbook covers acting on
one before that, and what to do once the change is merged.

## Symptom

- An issue reports that a game opens a different site (a casino, ads, a parked domain), an error page, or nothing.
  [`SECURITY.md`](../../SECURITY.md) sends reports of a malicious game site here too, as normal issues.
- The weekly `data: N broken links (week W)` issue, labelled `data`, lists the game.
- A `data/link-status` pull request proposes a `status` change for it; a hijacked game's pull request is labelled
  `priority::high`.

## Why this app is different

- **The app opens the catalog URL directly.** Selecting the tile opens the URL in the built-in browser or the user's
  own browser. There is no redirect of ours in between to switch off, so a hijacked entry sends every user who opens
  that game to the domain's new owner until the entry changes.
- **The fix is a data change, not a release.** Once `main` has the entry as `broken` or `retired` and
  [Pages](../../.github/workflows/pages.yml) has deployed it, the app hides the game from every shelf and category. As
  a favourite it shows as unavailable and does not open ("This game is no longer available").
- **Installed apps pick the change up only when they refresh.** That happens when the window opens with a cached
  catalog older than 6 hours (`MAX_AGE` in `dailies/core/cache.py`), or on **Refresh Game List** (Ctrl+R, or the main
  menu). There is no timer: a window left open keeps the old catalog until it is restarted or refreshed.
- **The automatic path is slow on purpose.** The link check runs only on Sundays, inside the
  [nightly compliance](../../.github/workflows/nightly-compliance.yml) workflow. A game becomes `broken` only after it
  fails the same check in two consecutive ISO weeks, and a manual run in the same week does not count as a second
  week. Only a redirect to another site whose page title holds a blocklisted gambling keyword (`hijacked`) is retired
  at once. Its pull request is opened with `GITHUB_TOKEN`, so it starts no CI and waits for a maintainer's merge. A
  hijack reported on a Monday can stay live for up to two weeks unless someone acts on it by hand, as below. See
  [Broken game links](../testing.md#broken-game-links) for the full rules.

## Response

### Diagnose

1. If a `data/link-status` pull request already proposes the change for this game, review it and merge it, using the
   ruleset's admin bypass because its checks never start. That is the fix: go to [Confirm it is
   published](#confirm-it-is-published).
2. Check the link from outside the app. Do not open a suspected hijack in your everyday browser; follow the redirects
   from the command line instead:

   ```sh
   curl -sSL -o /dev/null -w '%{http_code} %{url_effective}\n' '<url>'
   ```

3. Run the link checker on that one entry, with the same rules as the weekly check. Install the script dependencies
   once:

   ```sh
   python -m venv .venv && .venv/bin/pip install --require-hashes -r scripts/requirements.txt
   jq '.games |= map(select(.id == "<id>"))' data/v1/games.json > /tmp/one.json
   .venv/bin/python -I scripts/check_links.py --catalog /tmp/one.json --out /tmp/links.md
   cat /tmp/links.md
   ```

   It exits 0 when the entry passed and 1 when it failed. The report gives the outcome and a suggested `status`. To
   check the whole catalog on GitHub instead, start the compliance workflow with its link check forced:
   `gh workflow run nightly-compliance.yml -f force_links=true`.
4. Decide from the outcome:

   | Outcome | Meaning | Change |
   | --- | --- | --- |
   | `hijacked`, `blocked-title`, or `redirected-cross-domain` to a site that is not the game | The domain no longer belongs to the game | `status: retired` now, event `retired` |
   | `redirected-cross-domain` to the game's own new home | The game moved | New `url` and `domain` by hand, event `url-changed` |
   | `http-<code>`, `timeout`, `unreachable` | Possibly temporary | `status: broken` now if the reporter and you both see it; otherwise let the weekly streak decide |
   | `bot-walled` | The site blocks scripts; a warning, not a failure | Nothing |

### Fix

**Retire or break the entry** with the script that also applies the link-status pull request's changes. It sets
`status`, appends the `history` event, updates `generated_at` and keeps the file's committed format, so the diff is
those lines only. The `note` is at most 300 characters; the `event` is lower case with hyphens.

```sh
git switch -c data/<issue>-retire-<id> origin/main
cat > /tmp/changes.json <<'EOF'
{"changes": [{"id": "<id>", "status": "retired", "event": "retired", "note": "hijacked: redirects to <site> (#<issue>)"}]}
EOF
python -I scripts/apply_link_status.py --changes /tmp/changes.json --catalog data/v1/games.json
git diff
```

For a dead link, use `"status": "broken", "event": "broken"` instead. Commit it as
`data(games): retire <name> (#<issue>)` (or `mark <name> broken`), open a pull request that says `Fixes #<issue>`,
and merge it once the required checks pass. A pull request you push yourself runs CI as usual. Never delete the entry:
favourites must still resolve (see [`docs/data-format.md`](../data-format.md)).

**Move a game** by hand: change `url` and `domain` (the registrable domain of the new host), append
`{"date": "YYYY-MM-DD", "event": "url-changed", "note": "moved from <old domain>"}` to its `history`, and set
`generated_at` to the current UTC time. Check the new link with the one-entry link check above and the catalog with
`check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json`, then open the pull request.

**Restore a game** that was marked broken and works again. The weekly check restores it after two passing weeks; to
do it now, run the same script with `"status": "active", "event": "restored"`.

### Confirm it is published

The merge triggers Pages. Check that the run finished and that Pages serves the new status:

```sh
gh run list --workflow pages.yml --limit 1
curl -sS https://tim-van-oudheusden.github.io/Dailies/v1/games.json | jq '.games[] | select(.id == "<id>") | .status'
```

If the run failed or Pages still serves the old status after 10 minutes, follow
[Published data not reaching users](pages.md).

### Tell users

Reply on the issue once Pages serves the change. Apps pick it up within 6 hours of being opened; users who want it now,
or who are on a metered connection where the app skips the automatic refresh, can choose **Refresh Game List** (Ctrl+R).
After a hijack, users who opened the game in the built-in browser may have the new site's cookies and storage.
**Preferences → Clear website data…** removes them, but it also signs them out of every game and loses saved progress,
so say so. If the game opened in their own browser, that browser holds the data instead.

### Follow up

- A hijacked or redirected entry that reached users: write a postmortem from
  [`docs/postmortems/TEMPLATE.md`](../postmortems/TEMPLATE.md). There is no telemetry; for **Impact**, give how long the
  entry pointed at the wrong site (from the report, the link-check issue's history and the domain's registration
  date) plus the 6-hour refresh window.
- The weekly check missed a hijack because the new page's title has no blocklisted keyword: add the keyword to
  `scripts/data/title-blocklist.txt` in a pull request, test first, as its header describes.
- The game's icon was fetched after the domain changed hands (its PNG's `git log` is newer than the takeover): take it
  down as [Game icon taken down, wrong or inappropriate](game-icon.md) describes. Retiring the entry does not remove it.
- The same kind of failure keeps coming back: file an issue for it.

## Prevention

- Game submissions go through the submission validator twice (when the issue is opened and when it is approved): a
  public https host, a 2xx answer, a final registrable domain equal to the submitted one, and no blocklisted title.
- The weekly link check applies the same rules to every active entry, opens one issue for the failures, and opens a
  status pull request, retiring a gambling hijack at once.
- Not covered: the check runs only on Sundays; a hijack whose page title holds no blocklisted keyword counts as
  `redirected-cross-domain` and needs two weeks to become `broken`; nothing looks at the page beyond its title; and
  nothing alerts the maintainer except the issue and the pull request.
