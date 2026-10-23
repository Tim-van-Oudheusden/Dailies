# Game icon taken down, wrong or inappropriate

Concerns the **data path**: the 64×64 PNGs in `data/v1/icons/` that every installed app shows on the game tiles,
published with the catalog on [Pages](../../.github/workflows/pages.yml) (see [Icons](../data-format.md#icons)). This
runbook covers removing an icon, because its site asked or because it should not be shown, and replacing it with a
correct one.

## Symptom

- A game's owner asks for its icon to be removed, in an issue or through the README's
  [Contact](../../README.md#contact), as the README's **Takedown** paragraph invites them to.
- An issue or a screenshot shows a tile with an icon that is not the game's: another site's logo, a favicon service's
  placeholder, or something offensive.
- A game was hijacked ([Game link hijacked, moved or dead](catalog-link.md)) and its icon was fetched after the domain
  changed hands.

## Why this app is different

- **Nothing removes an icon on its own.** `scripts/icons/fetch_icon.py` runs automatically only in stage B of the
  [game submission](../../.github/workflows/game-submission-approve.yml) workflow, for the game being added. There is no
  scheduled icon run, so a takedown listed in `scripts/data/icon-takedowns.txt` waits for the next approved submission
  unless you run the script yourself.
- **The takedown and its result must land together.** `tests/data/test_catalog_file.py` fails when a listed id still
  has a PNG, an `icon`, or an `icon_source` other than `none`. A pull request that only adds the id to the list does not
  pass CI.
- **Removing an icon reaches users faster than replacing it.** When an entry loses `icon`, the app deletes its cached
  copy and shows the category glyph at its next catalog update: within 6 hours of the window opening (`MAX_AGE` in
  `dailies/core/cache.py`), or at once on **Refresh Game List** (Ctrl+R). An icon replaced under the same
  `icons/<id>.png` is asked for again only after its cached copy is 7 days old (`MAX_AGE` in
  `dailies/core/icons.py`), and never on a metered network; Ctrl+R does not change that. An icon that must disappear now
  is removed first and replaced later.
- **The old file stays in git history.** Removing the PNG from `main` takes it off Pages and off the
  raw.githubusercontent.com fallback for `main`, but every earlier commit still holds it.

## Response

### Diagnose

1. Find where the icon came from and when:

   ```sh
   jq '.games[] | select(.id == "<id>") | {url, status, icon, icon_source}' data/v1/games.json
   git log --format='%h %ad %s' --date=short -- data/v1/icons/<id>.png
   ```

   `icon_source` is `site` (the game's own site), `google` or `duckduckgo` (a favicon service picked it) or `manual` (a
   maintainer placed it).
2. Decide:

   | Case | Change |
   | --- | --- |
   | The owner asks for removal | Take it down for good |
   | The icon is offensive, or belongs to whoever took over the domain | Take it down now; replace it later if needed |
   | The icon is merely wrong (a placeholder, a sister site's logo) | Replace it with a manual icon |

### Take it down

The takedown list is permanent: a listed id is never fetched again. Install the script dependencies once, add the id,
and run the fetcher with `--id` naming that game. For a listed id it downloads nothing; it applies the whole takedown
list, deletes the PNG and rewrites the entry as `icon_source: "none"` with a new `generated_at`. A second run changes
nothing.

```sh
python -m venv .venv && .venv/bin/pip install --require-hashes -r scripts/requirements.txt
git switch -c data/<issue>-icon-takedown-<id> origin/main
echo '<id>' >> scripts/data/icon-takedowns.txt
.venv/bin/python -I scripts/icons/fetch_icon.py --catalog data/v1/games.json --out data/v1/icons --id <id>
pytest tests/data/test_catalog_file.py
git status && git diff
```

The diff is the new list line, the deleted PNG, and the entry's `icon` and `icon_source` lines plus `generated_at`.
Commit it as `data(icons): take down the <name> icon (#<issue>)`, open a pull request that says `Fixes #<issue>`, and
merge it once the required checks pass.

To take an icon down without listing it, for example because a correct one follows soon, delete the PNG, remove the
entry's `icon` line, set `icon_source` to `none` and update `generated_at` by hand. The next full fetcher run may bring
the same icon back, so list it if that would be wrong.

### Replace it

A `manual` icon is never replaced by the fetcher. Put a square PNG, ICO, JPEG, GIF, WebP or BMP image of the game's
own logo at `/tmp/<id>-source.png` and convert it to the published format (64×64, centred on a transparent square)
with the fetcher's own conversion:

```sh
.venv/bin/python -I -c '
import sys; from pathlib import Path
sys.path.insert(0, "scripts/icons"); import fetch_icon
png, _ = fetch_icon.normalise(Path(sys.argv[1]).read_bytes())
Path(sys.argv[2]).write_bytes(png)' /tmp/<id>-source.png data/v1/icons/<id>.png
```

`normalise` fails on an image that is not nearly square or does not decode. In the entry, set
`"icon": "icons/<id>.png"` and `"icon_source": "manual"` right after `domain`, and update `generated_at`. If the id is
in `scripts/data/icon-takedowns.txt`, remove that line in the same pull request. Run
`pytest tests/data/test_catalog_file.py`, commit as `data(icons): replace the <name> icon (#<issue>)`, and open the
pull request as above.

### Confirm it is published

The merge triggers Pages. After a takedown, Pages answers 404 for the icon and the entry has no `icon`:

```sh
gh run list --workflow pages.yml --limit 1
curl -sS -o /dev/null -w '%{http_code}\n' https://tim-van-oudheusden.github.io/Dailies/v1/icons/<id>.png
curl -sS https://tim-van-oudheusden.github.io/Dailies/v1/games.json \
  | jq '.games[] | select(.id == "<id>") | {icon, icon_source}'
```

If the run failed or Pages still serves the old entry after 10 minutes, follow
[Published data not reaching users](pages.md).

### Tell users

Reply on the issue once Pages serves the change. A taken-down icon disappears within 6 hours of the app being opened,
or at once with **Refresh Game List** (Ctrl+R). A replaced icon appears within 7 days of the app last asking for it,
later on a metered network. Tell an owner who asked for removal that the PNG is gone from the published data and will
not be fetched again, but remains in the repository's history.

### Follow up

- The fetcher picked a wrong icon (`google` or `duckduckgo`, or a sister site's logo from the site's own markup): if it
  can happen to other games, file an issue for the fetcher.
- An offensive icon reached users: write a postmortem from [`docs/postmortems/TEMPLATE.md`](../postmortems/TEMPLATE.md).
  There is no telemetry; for **Impact**, give how long the icon was on Pages (the PNG's `git log`) plus the 6-hour
  refresh window.
- Someone needs the file gone from history too: that means rewriting `main`, which is a separate decision for the
  maintainer and not part of this runbook.

## Prevention

- The fetcher only downloads from public https addresses, caps size and pixels, and skips images that are not nearly
  square. The catalog tests check that every icon is a 64×64 PNG of at most 256 KiB, belongs to exactly one entry, and
  that no listed id has one.
- The app shows only a PNG of at most 256 KiB that decodes to at most 256×256, fetched from the data URLs, and deletes
  an icon the catalog no longer names.
- Not covered: nobody looks at an icon's content before it is published beyond reviewing the stage B pull request;
  icons are fetched once, so a site that changes its logo keeps the old one until someone reruns the fetcher; and a
  replacement takes up to a week to reach installed apps.
