# Bad release

Concerns the **release path**: the `Dailies-x86_64.flatpak` and `Dailies-aarch64.flatpak` bundles and the FlatPark
payload `Dailies-flatpark.tar.xz` attached to a GitHub Release by the [Release](../../.github/workflows/release.yml)
workflow.

## Symptom

- An issue reports that Dailies crashes, shows an empty window or cannot open games, and the reporter's version (the
  About dialog, or `flatpak info io.github.tim_van_oudheusden.Dailies`) is the newest release.
- A downloaded bundle does not match the release's `SHA256SUMS`, or does not install.
- You notice it yourself while running the [manual checklist](../../CONTRIBUTING.md#manual-checklist-before-tagging)
  on the published bundle.

A `Release` run that failed before **Publish GitHub Release** published nothing; that is not this runbook. Re-run it
or delete the tag as [Releasing](../../CONTRIBUTING.md#releasing) describes.

## Why this app is different

- **Bundles do not update themselves.** There is no update channel to push a fix through: everyone who installed the
  broken bundle keeps it until they install another one by hand. The fix reaches them only through the Releases page,
  the README and the issue tracker.
- **A published version is never reused.** A tag and its version name one build; replacing the assets under the same
  tag would leave two different bundles called the same version. A bad `vX.Y.Z` is fixed forward with `vX.Y.(Z+1)`.
- **The data path still reaches the broken version.** Installed apps keep fetching `games.json` and `popularity.json`
  every few hours. If the breakage is triggered by data (a field an older version mishandles), fixing or reverting the
  data reaches every user within hours, without a release.

## Response

### Diagnose

1. Find the release and the run that published it:

   ```sh
   gh release list
   gh release view vX.Y.Z
   gh run list --workflow release.yml
   ```

2. Check the published files against their checksums (the release has `Dailies-x86_64.flatpak`,
   `Dailies-aarch64.flatpak`, `Dailies-flatpark.tar.xz` and `SHA256SUMS`):

   ```sh
   gh release download vX.Y.Z --dir /tmp/dailies-vX.Y.Z
   (cd /tmp/dailies-vX.Y.Z && sha256sum -c SHA256SUMS)
   ```

3. Reproduce on the published bundle, not a local build: the release bundle builds the commit pinned in the release
   manifest, and only the Devel manifest runs the tests. Installing it replaces your installed Dailies (not the Devel
   build); favourites, settings and website data stay:

   ```sh
   flatpak install --user --reinstall /tmp/dailies-vX.Y.Z/Dailies-x86_64.flatpak
   flatpak run io.github.tim_van_oudheusden.Dailies
   ```

   Note whether it breaks on one architecture only (aarch64 is built only on release and never tested in CI) and
   whether it depends on the data (start the Devel build against a local copy with `DAILIES_DATA_URLS`, see
   [`docs/testing.md`](../testing.md)).
4. If the data triggers it, fix the data first: revert the data commit, or merge a corrected `games.json` or
   `popularity.json`. That stops the impact for every user; continue below for the code fix.

### Fix

1. Stop new installs of the broken version. Mark the release as a pre-release so GitHub shows the previous release as
   **Latest**, and put a warning at the top of its notes:

   ```sh
   gh release edit vX.Y.Z --prerelease
   gh release view vX.Y.Z --json body --jq .body > /tmp/body.md   # add a warning line at the top
   gh release edit vX.Y.Z --notes-file /tmp/body.md
   gh release list                                                # the previous release now shows Latest
   ```

   If `Latest` did not move, set it: `gh release edit vPREVIOUS --latest`. If installing the bundle does harm (it
   loses data, or it cannot be uninstalled cleanly), also remove the assets and keep the release page as the record:

   ```sh
   gh release delete-asset vX.Y.Z Dailies-x86_64.flatpak
   gh release delete-asset vX.Y.Z Dailies-aarch64.flatpak
   gh release delete-asset vX.Y.Z Dailies-flatpark.tar.xz
   gh release delete-asset vX.Y.Z SHA256SUMS
   ```

   A [FlatPark](https://flatpark.org) package pins `Dailies-flatpark.tar.xz` from the release as extra-data
   ([Releasing](../../CONTRIBUTING.md#releasing)), so removing that asset also stops FlatPark from installing the
   broken version.

   Do not delete the tag: the version stays used. (With immutable releases turned on for the repository, the assets
   cannot be deleted; the pre-release flag and the notes remain editable.)
2. Tell users. Open an issue (`vX.Y.Z: <what breaks>`), pin it with `gh issue pin <number>`, and put a notice on the
   [README Status line](../../README.md#status) in a pull request (`docs(readme): warn about vX.Y.Z (#N)`): what
   breaks, and that the previous release can be installed over it:

   ```sh
   flatpak install --user --reinstall ./Dailies-x86_64.flatpak   # the previous release's bundle
   ```

   `--reinstall` uninstalls first without deleting the app's data, so favourites, settings and logins stay.
3. Fix forward: fix the bug test-first in a pull request that says `Fixes #<number>`, then cut `vX.Y.(Z+1)` as
   [Cutting a release](../../CONTRIBUTING.md#cutting-a-release) describes. Its metainfo release note says what it
   fixes; `scripts/release_check.py notes` puts that note at the top of the GitHub Release, and the About dialog shows
   it:

   ```xml
   <release version="X.Y.Z+1" date="YYYY-MM-DD">
     <description>
       <p>Fixes the crash on start in X.Y.Z when …</p>
     </description>
   </release>
   ```

4. Once the hotfix is published, point the README notice and the pinned issue at it, then remove the notice, unpin
   the issue (`gh issue unpin <number>`) and close it.

### Follow up

1. Write a postmortem: copy [`docs/postmortems/TEMPLATE.md`](../postmortems/TEMPLATE.md) to
   `docs/postmortems/YYYY-MM-DD-short-slug.md` and add it to the index in
   [`docs/postmortems/README.md`](../postmortems/README.md). For **Impact**, the only numbers available are the
   release download counts:

   ```sh
   gh release view vX.Y.Z --json assets --jq '.assets[] | "\(.name) \(.downloadCount)"'
   ```

2. File an issue for whatever would have caught it before tagging (a test, a checklist item, a release-time check).

## Prevention

- **Verify** in `release.yml` stops a tag whose version disagrees with `meson.build` or the metainfo, or whose pinned
  commit differs from the tag. `flatpak-builder-lint` checks the manifest and the exported repo with Flathub's rules.
- Every pull request builds the Devel manifest in CI's `Flatpak (x86_64)` job and runs the Meson, gi and e2e smoke
  tests in the sandbox.
- Not covered: the release build runs no tests, aarch64 is built only on release, and nothing drives WebKit content.
  The [manual checklist](../../CONTRIBUTING.md#manual-checklist-before-tagging) covers the last one on x86_64 only.
