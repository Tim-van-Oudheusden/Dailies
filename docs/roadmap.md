# Roadmap

Where Dailies goes after the MVP. The original plan, M0 to M5, is §16 of the
[MVP-first proposal](proposals/mvp-first.md#16-roadmap), tracked by #1; it stays there as the record. This page picks
up from it: where the project stands, the next milestone, where effort goes when nothing on that milestone is ready,
and what is deliberately left off. Every number below comes from `main`, the GitHub releases or the issues named next
to it, as of 2026-11-17.

## Where things stand

| Milestone | Epic | State |
| --- | --- | --- |
| M0 Scaffold | #2 | done |
| M1 Usable launcher → v0.1.0 | #3 | done |
| M2 Data pipeline → v0.2.0 | #4 | done |
| M3 Agentic report and hygiene → v0.3.0 | #5 | done |
| M4 Distribution | #6 | open: waits on the FlatPark pull request (#206) |
| M5 Growth | #7 | done (12 of 12 sub-issues) |

**M4 waits on one step, and it is the owner's.** Everything #206 depended on has landed: the FlatPark payload
(#205, #208), v0.3.0, and since then v0.3.1 and v0.3.2. The package drafted on 2026-10-21 still pins v0.3.0. Before
the pull request is opened on `flatpark/flatpark`, re-run `resolve-update.sh | update-pins.mjs` as #206 describes, so
the listing starts at the newest release. Under FlatPark's playbook (rule 2) the developer opens that pull
request, so nothing in this repository can finish M4.

**Baseline**, to measure the launch against:

| Signal | Value |
| --- | --- |
| Stars / forks | 0 / 0 |
| Release downloads (both bundles plus the FlatPark payload) | v0.3.0: 4, v0.3.1: 8, v0.3.2: 4 |
| Catalog | 117 games, all `active` |
| Games added after 2026-10-16 | 1: Mapcade (#469, 2026-11-15), submitted through the form by an outside contributor |
| Candidate backlog (`scripts/catalog_candidates.py`, #313) | about 650 games The Dles has and the catalog lacks (October 2026); none added from it yet |

**Where the work went.** Of the 127 commits on `main` from `v0.3.0` (2026-10-29) to 2026-11-17, 34 are `test`, 29
`ci`, 21 `docs`, 26 `fix` (about half of them user-visible) and 1 `feat`. With M5 closed and M4 out of reach, nothing
said what came next, so the hardening work filled the gap.

## M6 Launch and catalog

**Goal:** a user who finds Dailies can install it with one command, keeps getting updates, and finds the games that
are being played now.

| Track | Work | Who |
| --- | --- | --- |
| Launch | Open the FlatPark pull request, pinned to the newest release (#206); then the launch checklist in #259: README Status, the website's Dailies page, the repository homepage, the announcement | Owner opens and posts; an agent drafts the README, website and announcement text once the listing is live |
| Catalog | Each month, run `scripts/catalog_candidates.py` with `--since` the previous run's day ([Growing the catalog](runbooks/catalog-link.md#growing-the-catalog)), pick the games that meet the [submission rules](data-format.md#submission-rules), and file each through the **Add a game** form, with a description and tags written fresh. Stage A and B and the maintainer's `approved` label stay as they are | Run and file: an agent or the owner. Approve and merge: the maintainer |
| Releases | Cut a patch release once user-visible fixes are waiting on `main` that no release carries, following the contributing guide's "Releasing" section. A catalog change needs no release: the app picks it up from Pages | Owner tags |

**Exit criteria**

- [ ] `flatpak install flatpark io.github.tim_van_oudheusden.Dailies` installs the newest release. This is also M4's
  exit criterion, so meeting it closes M4.
- [ ] The catalog has grown by at least 20 active games since 2026-11-17, across at least two monthly candidate runs.
- [ ] Two weeks after the announcement, the stars, release downloads and any FlatPark install count are recorded on
  #259, next to the baseline above.

## Where effort goes between milestone items

When nothing on M6 can move, for example while the launch waits on the owner, effort goes to these, in order:

1. **User-visible fixes:** reported bugs first, then problems found by using the app: keyboard-only navigation,
   narrow windows, slow or failed catalog refreshes.
2. **Catalog upkeep:** the weekly link-check issue and `data/link-status` pull requests, hijacked or moved games
   ([runbook](runbooks/catalog-link.md)), and the monthly candidate run.
3. **Release readiness:** the metainfo `<release>` notes and screenshots for the next tag.
4. **CI, tests and tooling,** when a failure, a report or a review points at a specific gap. The suite already has
   coverage floors, mutation testing and nightly compliance, so a new test needs a defect it would have caught, not
   only a survivor count to bring down.

## Not on this roadmap

Each of these has a trigger that puts it back on.

| Item | Why not now | Trigger |
| --- | --- | --- |
| Flathub (#207) | Flathub's policy bars AI-assisted manifests and AI-opened submissions, so it is owner-authored | The owner decides to submit |
| Self-hosted OSTree remote and `.flatpakref` (#73) | The fallback for FlatPark; it also needs a GPG key held as repository secrets | FlatPark rejects or de-lists Dailies, or users ask for a first-party remote |
| Windows release assets | The experimental build (`windows.yml`) is a CI artifact only, never tried on real hardware | Someone runs it on Windows and reports back |
| More translations | Only Dutch (`po/LINGUAS`) exists; a translation needs a speaker | A translator offers one ([Translations](../CONTRIBUTING.md#translations)) |
| New app features beyond M5 | No user has asked for one yet | A feature request from a user, or a gap the launch feedback shows |
