# Research reports (2026-10-15)

Eleven parallel deep-dives produced by the `dailies-research-design` workflow (Research phase) on 2026-10-15. Each report was written by a dedicated agent with web and repository access; each ends with a Sources section and a Recommendations-for-Dailies section. Facts were verified against primary sources where possible; items the agent could not verify are flagged inside the report and listed under Open questions below.

These reports are inputs to the architecture document. See [`docs/plans/design-judge-plan.md`](../plans/design-judge-plan.md) for what happens next.

## Index

| Report | Confidence | Words |
|---|---|---|
| [hive-acmm](hive-acmm.md) | high | 10092 |
| [scaffolding-repos](scaffolding-repos.md) | high | 48263 |
| [cartridges](cartridges.md) | high | 9102 |
| [bazaar](bazaar.md) | high | 7307 |
| [stack-crossplatform](stack-crossplatform.md) | high | 5089 |
| [embedded-browser](embedded-browser.md) | high | 6399 |
| [flatpak-release-pipeline](flatpak-release-pipeline.md) | high | 7736 |
| [data-pipeline](data-pipeline.md) | high | 8362 |
| [logo-icon](logo-icon.md) | high | 7525 |
| [dle-catalog](dle-catalog.md) | high | 5742 |
| [libadwaita-ui-patterns](libadwaita-ui-patterns.md) | high | 8357 |
| [category-badge](category-badge.md) (2026-10-19) | high | 5238 |

## Summaries and open questions

### hive-acmm

Full report: [`hive-acmm.md`](hive-acmm.md)

ACMM is the "AI Codebase Maturity Model" (paper arXiv:2604.09388, Andy Anderson, IBM Research, v2 2026-04-27): a six-level framework (L1 Inception/Assisted, L2 Advisory/Instructed, L3 Quality-Gated/Measured, L4 Security-Aware/Adaptive, L5 Semi-Autonomous, L6 Fully Autonomous) describing how much autonomy a repo can safely give AI agents. Hive (hivecommons/hive, Apache-2.0, v5.175.0 on 2026-10-15) enforces the level operationally through four per-agent policy modes (advisory, measured, holdgated with literal `hold` label, full/auto-merge).

"Meeting ACMM requirements" has an exact mechanical meaning in Hive: the dashboard's ACMM Eval scores each repo in `project.repos` against 50 file-existence criteria defined in `src/pkg/dashboard/acmm_criteria.go` (`universalCriteria`; the code comment says 43 but there are 50), grouped L0 (8), L2 (8), L3 (8), L4 (9), L5 (5), L6 (12; 6 `acmm:` + 6 `aef:`). A criterion passes if ANY listed path exists (content is never inspected). A level passes at >= 70% detected criteria (`acmmLevelThreshold = 0.70`); Codebase Level = highest consecutively-passing level from L0 (L0 alone yields L1); Overall = min(Codebase Level, configured operational level). Compliance is checked only by a running Hive (dashboard section, `GET /api/acmm/evaluation`, `?refresh=1`, 1h cache); there is no CLI linter, GitHub check or badge. Gaps are filed as issues titled `[ACMM L<n>] Add <Name>` with labels `acmm` + `ai-fix-requested` via `POST /api/acmm/issue`. Waivers live in `.acmm.yml` (`waivers: [{id, satisfied_by, reason}]`) and can never advance a level. A separate advisor (`pkg/acmmadvisor`) recommends operational level-ups using coverage/green-streak/merge-rate thresholds (L3: 40%/3; L4: 60%/5/70%; L5: 75%/8/85%; L6: 90%/12/95%).

Key criteria and the files the owner's compliant repos use: L0 tests/ (or pyproject.toml/pytest.ini), e2e/ or tests/e2e/, .github/workflows/, .github/pull_request_template.md, .github/ISSUE_TEMPLATE/, CONTRIBUTING.md, .editorconfig or ruff.toml/rustfmt.toml, .github/workflows/coverage-gate.yml; L2 CLAUDE.md, .github/copilot-instructions.md, AGENTS.md, .cursor/rules, prompts/, .editorconfig, .claude/skills/, .claude/memory/; L3 .github/workflows/pr-metrics.yml, review.yml, quality-report.yml, ci.yml, .claude/settings.json (counts for three criteria), .claude/session-summary.md; L4 .github/auto-qa-tuning.json, nightly-compliance.yml, auto-review.yml, .github/labeler.yml + labeler.yml, claude.yml, tier-classifier.yml + docs/risk-tiers.md, docs/security/SECURITY-AI.md, docs/reflections/; L5 claude.yml, auto-qa-tuning.json, docs/metrics/, .github/policies/, docs/reflections/. My local re-implementation of the evaluator shows MinimalUI and website both at Codebase L5 (L2-L5 100%, L6 3/12), Dailies at 0/50. Both repos were brought to compliance by the owner's own hive (id `hive-tall-slug`, GitHub App `hive-forge-app`) filing gap issues.

Registration with Hive is separate: hosted hub wizard at hive.hivecommons.dev/get-started (GitHub login, repo URL, pick L1-L3, admin approves, then install Hive GitHub App), `hivectl --server https://hive.hivecommons.dev enroll OWNER/REPO` (lite, capped at L2), or adding the repo to an existing spoke's `project.repos` (recommended for Dailies since the owner runs a hive). AGENTS.md is injected into agent prompts only if `project.checkouts_dir` is configured. Joining the Hive Commons org (proposal issue; Apache-2.0, DCO, CNCF CoC required) is NOT needed for compliance and does not fit a GPL-3.0 game launcher. Hive provides templates: L1 Inception scaffold (README/AGENTS.md/CLAUDE.md/CONTRIBUTING/CI), PR template, issue templates, `.acmm.yml`, `hive.yaml.example`, ADR convention.

The report contains a phased L0->L5 checklist for Dailies with GTK/Flatpak-specific adaptations (ruff.toml/rustfmt.toml, tests/e2e/, Flatpak-aware risk tiers and SECURITY-AI.md, nightly Flatpak-runtime/DLE-URL checks), verbatim copies of the language-agnostic owner scaffolding (claude.yml, review.yml + pr-review-check.sh, pr-metrics.yml + pr-metrics.sh, tier-classifier.yml + tier-classify.sh + risk-tiers.policy, labeler, nightly-compliance, coverage-gate, quality-report, .claude/settings.json, PR/issue templates, CLAUDE.md body, learning artefacts, dependabot, ruleset), Hive's own templates, and a CI self-check script. Recommendation: scaffold to Codebase L5 on day one, run the hive at operational L2-L3 initially, do not chase L6.

Open questions:

- Is the owner's hive (id hive-tall-slug, GitHub App hive-forge-app) hosted on hive.hivecommons.dev or self-hosted? This decides whether Dailies is added via the hub dashboard Settings -> Repos or by editing hive.yaml project.repos; the registration mechanism is the same either way.
- Does the owner want project.checkouts_dir configured on the spoke so Dailies' AGENTS.md is actually injected into Hive agent prompts (otherwise AGENTS.md only serves CLI agents like Claude Code/Copilot/Cursor)?
- Which toolchain (Python/PyGObject vs Rust/gtk4-rs, Meson) Dailies uses determines the concrete code-style, test-suite and coverage-gate files; the checklist gives both variants.
- Should Dailies keep the owner's Beads (.beads/, bd) issue-mirror convention? It is in both reference repos but is not an ACMM criterion.
- Whether to drop the in-repo claude.yml in favour of Hive's own agents later (then add .acmm.yml waivers for acmm:ai-fix-workflow / acmm:copilot-review-apply as Danathar/sensi did).
- The acmm_criteria.go comment says 43 criteria while the slice holds 50; the pattern list may change in future Hive releases, so a vendored self-check needs periodic re-sync.
- The paper's HTML versions return 404; level definitions were extracted from the PDF via pdf-parse and tables may have lost some formatting.

Sources (as returned by the agent; full list inside the report):

- https://github.com/hivecommons/hive (README.md, AGENTS.md, ADOPTERS.md, src/docs/acmm-policy-matrix.md, acmm-advisor.md, acmm-waivers.md, adr/0003-acmm-autonomy-levels.md, agents-md.md, dashboard-sections.md, hosted-hub.md, lite-enrollment.md, getting-started.md, github-app-setup.md, inception.md, compliance.md, credly-badges.md, labels-and-control-signals.md, src/hive.yaml.example, src/pkg/dashboard/acmm_criteria.go, api_acmm_eval.go, acmm_waivers.go, src/pkg/acmmadvisor/acmmadvisor.go, .github/PULL_REQUEST_TEMPLATE.md, .github/ISSUE_TEMPLATE/*) @ 1bf213d0cb772ff8425e1787586a33b01f7ea27e, 2026-10-15
- https://github.com/hivecommons/.github (GOVERNANCE.md, CONTRIBUTING.md, ADOPTERS.md, .github/ISSUE_TEMPLATE/join-hive-commons.yml)
- https://github.com/Tim-van-Oudheusden/MinimalUI (full tree; gh issue list -S ACMM --state all)
- https://github.com/Tim-van-Oudheusden/website (full tree; gh issue list -S ACMM --state all)
- https://arxiv.org/abs/2604.09388 and https://arxiv.org/pdf/2604.09388v2 (The AI Codebase Maturity Model, Andy Anderson, v2 2026-04-27)
- https://docs.hivecommons.dev (navigation), https://docs.hivecommons.dev/docs/hive/security/acmm-policy-matrix, https://docs.hivecommons.dev/docs/community/join-hive-commons
- https://hivecommons.dev
- https://hive.hivecommons.dev/get-started
- gh release list -R hivecommons/hive (v5.175.0, 2026-10-15T10:59:51Z)

### scaffolding-repos

Full report: [`scaffolding-repos.md`](scaffolding-repos.md)

Both of the owner's repositories carry one shared scaffolding layer, authored in `website` between 2026-09-29 and 2026-10-06 in direct response to 34 Hive ACMM gap issues (`[ACMM L0..L5] Add …`, label `acmm`+`ai-fix-requested`, filed by the owner and then by `app/hive-forge-app`), and ported to `MinimalUI` in issues #13–#27 on 2026-10-12/13. 58 paths exist in both repos; only `.github/workflows/labeler.yml` is byte-identical, the rest differ by stack (Gradle/Kotlin vs Bun/TypeScript) and later polish. **MinimalUI (HEAD 510282a, 2026-10-15) is the better template**: its AGENTS.md is rewritten without the stale generated beads block website still has, and it adds SECURITY.md, a committed branch ruleset (`.github/rulesets/main.json`, matching live ruleset 24941495: merge-commit only, 0 approvals, required checks `PR review rubric`, `Build, lint, test`, `Unit-test coverage floors`, `Static checks`), `release.yml` + `scripts/release-version.sh` (version in one file → tag `vX.Y.Z` → `gh release create` with signed artifact; `-suffix` = prerelease), a `Static checks` job (shellcheck 0.11.0 + actionlint 1.7.12, SHA-256 pinned), `.github/actionlint.yaml`, `docs/runbooks/`, a second issue form, `type::*`/`priority::*` labels, and a `tooling` test module pinning workflow invariants (reviewed token scopes, `timeout-minutes` on every job, 40-hex SHA pins, no `${{ github.event.* }}` in `run:`, `pull_request_target` only in labeler.yml). Take from website: `docs/postmortems/{README,TEMPLATE}.md` and the `e2e/` directory convention.

ACMM is verified as a pure file-existence model: `hivecommons/hive` (`v5`, release v5.175.0) `src/pkg/dashboard/acmm_criteria.go` lists 43 criteria (8 L0, 8 L2, 8 L3, 9 L4, 5 L5, 12 L6/aef), each passing if ANY listed path exists; the full table with accepted paths and each repo's matching file is in the report. Both repos meet every criterion through L5, except MinimalUI has no path on the `acmm:prereq-test-suite` or `acmm:prereq-e2e` lists (Gradle `src/test` is not listed). For Dailies (Python/GTK/Meson) the cheapest L0 matches are `pyproject.toml`, `tests/` + `tests/e2e/`, `.editorconfig`/`ruff.toml`, `coverage-gate.yml`. Hive-specific in-repo references are minimal: `pr-metrics.sh` detects agent PRs as `claude/*` branches or author `hive-forge-app`; SECURITY-AI.md names hive agents as data-not-instructions; no `.acmm.yml`, `hive.yaml` or other manifest exists. Hive creates its own labels (`hold`, `hive/advisory`, `acmm`, `agent/*`, `hive/covered-by-pr`, `needs-human`…) once pointed at a repo.

Conventions: Conventional Commits enforced by regex in `scripts/pr-review-check.sh` on PR titles; one commit per issue `type(scope): summary (#N)`; branches `<type>/<number>-<slug>`; PR body must say `Fixes #N`; merge commits only, branch deleted on merge; SemVer with `v` tags; docs collections each have a `README.md` with Format + Index, dated entries `YYYY-MM-DD-slug.md`, root policy docs in SCREAMING-CASE; **no ADRs or numbered decision records in either repo**; three-tier agent memory (session-summary.md overwritten, corrections.tsv append-only, docs/reflections kept). README skeleton: centred banner, `·`-separated link row, badges (ci.yml, coverage-gate.yml, v/release, license, last-commit), screenshots, Status/About/Requirements/Installing/Tech stack/Architecture (Mermaid)/Building/Documentation table/Contributing/Acknowledgments/Contact/Licence table; terse, honest tone, full-sentence alt text.

Recommendations: copy MinimalUI's layer wholesale (all files reproduced verbatim in Appendix B), substitute Meson/Flatpak/ruff/pytest gates in the ~10 places the gradle commands appear, rewrite `scripts/lib/coverage.sh` for Cobertura XML, port the workflow-invariant tests to `tests/tooling/test_workflows.py`, adapt `release.yml` to read `version:` from `meson.build` and attach `dailies-vX.Y.Z.flatpak` bundles + sha256, add a second issue form for DLE submissions, and complete the repo-settings checklist (merge-commit only, delete-branch-on-merge, CodeQL, Dependabot alerts, private vulnerability reporting, labels, `CLAUDE_CODE_OAUTH_TOKEN`, Claude GitHub App) before applying the ruleset. The Dailies repo currently has none of this (verified via gh: squash/rebase allowed, no ruleset, default labels only).

Open questions:

- Hive's acmm:prereq-test-suite and acmm:prereq-e2e path lists contain no Gradle paths, yet MinimalUI has never received [ACMM] gap issues; it is unclear whether the owner's Hive evaluates per-repo (then MinimalUI reads as L0) or applies a hive-wide level (hive docs say levels are hive-wide; per-repo levels were declined in RFC #6235). Check the Hive dashboard before deciding how literally Dailies must satisfy every L0 path.
- Whether the Hive Forge App is installed account-wide (Dailies picked up automatically once added to the spoke's hive.yaml) or needs explicit enrolment via hivectl enroll Tim-van-Oudheusden/Dailies.
- Dependabot has no ecosystem for Flatpak manifests; the nightly-compliance equivalent for Flatpak sources (e.g. flatpak-external-data-checker) is not in either template and needs its own design.
- The Static checks job pins shellcheck/actionlint release archives by SHA-256; hashes must be recomputed whenever those versions move (current as of MinimalUI HEAD 2026-10-15).
- .beads/ files are generated by bd init (bd 1.3.1, Dolt backend) and carry MinimalUI's project_id and dolt remote; Dailies should run bd init fresh rather than copy them.
- Neither template has ADRs or numbered decision records; if the Dailies design document introduces docs/decisions/NNNN-slug.md that will be a new convention, not a copied one.
- Whether the owner wants the website's E2E pattern (Playwright) replaced by a GTK smoke test under tests/e2e/ (xvfb-run/dbus-run-session) to satisfy acmm:prereq-e2e, or a waiver (.acmm.yml) instead.

Sources (as returned by the agent; full list inside the report):

- https://github.com/Tim-van-Oudheusden/MinimalUI (clone @ 510282a; issues #1-#40 titles, #13 #14 #23 #27 bodies; gh repo view, gh label list, gh api repos/.../rulesets/24941495)
- https://github.com/Tim-van-Oudheusden/website (clone @ c97570e; issue #1 and all 34 acmm-labelled issue bodies; gh repo view, gh label list, gh api repos/.../rulesets/24664373; gh pr list authorship)
- https://github.com/Tim-van-Oudheusden/Dailies (gh repo view, gh label list, local checkout 0a47a09)
- https://github.com/hivecommons/hive/blob/v5/src/pkg/dashboard/acmm_criteria.go
- https://github.com/hivecommons/hive/blob/v5/src/docs/acmm-policy-matrix.md
- https://github.com/hivecommons/hive/blob/v5/src/docs/labels-and-control-signals.md
- https://github.com/hivecommons/hive/blob/v5/src/docs/acmm-waivers.md
- https://github.com/hivecommons/hive/blob/v5/src/docs/lite-enrollment.md
- https://github.com/hivecommons/hive/blob/v5/src/docs/forge-app-setup.md
- https://github.com/hivecommons/hive/blob/v5/src/docs/design/repo-acmm-onboarding.md
- https://github.com/hivecommons/hive (README via WebFetch; release v5.175.0 2026-10-15)
- https://hivecommons.dev (WebFetch)
- https://docs.hivecommons.dev (WebFetch)
- https://arxiv.org/abs/2604.09388 (ACMM paper, cited by Hive; not fetched)
- https://www.conventionalcommits.org/ (linked from both CONTRIBUTING.md files)

### cartridges

Full report: [`cartridges.md`](cartridges.md)

Cartridges (page.kramo.Cartridges, GPL-3.0-or-later, Python/PyGObject + Blueprint + Meson) was cloned and read end-to-end. Two headline facts change how Dailies should use it: (1) the project is no longer maintained — GitHub mirror archived 2026-09-03, Flathub repo marked end-of-life (`flathub.json` = {"end-of-life": ...}), and the README explicitly says not to copy `main` because of poor quality; (2) the `rewrite` branch (last commit 2026-04-05) is the author's recommended, modern code even though "not everything is functional". So: copy repository/build/CI/release/i18n plumbing from `main` (v2.13.1, GNOME 49 runtime) and UI architecture plus code-style tooling from `rewrite`.

Toolchain (main): Meson ≥0.59 with `profile` option (release|development) that switches App ID (`page.kramo.Cartridges` vs `.Devel`), gresource prefix and a `devel` CSS class; every `.in` (desktop, gschema, metainfo, gresource.xml, shared.py, launcher) runs through `configure_file`; Blueprint compiled via `blueprint-compiler batch-compile` from a Meson wrap (v0.16.0; upstream now v0.22.2, 2026-07-10); metainfo bundled into the gresource for `Adw.AboutDialog.new_from_appdata`; validation tests (desktop-file-validate, appstreamcli validate --no-net, glib-compile-schemas --strict) run under `flatpak-builder --run-tests`. Code style: Black/Pylint/isort on main; `rewrite` uses pre-commit with ruff (select ALL + ignore list), pyright strict, `blueprint-compiler format`, `meson format`, prettier, svgo, plus `python.install_sources`, `meson.options`, Meson ≥1.1.

UI: main = Adw.ApplicationWindow → Adw.ToastOverlay → Adw.NavigationView (library/hidden/details pages) → Adw.OverlaySplitView with a hand-built Gtk.ListBox `navigation-sidebar` and a Gtk.FlowBox grid of 200×300 `card` tiles (hover-revealed OSD play/menu buttons), Gtk.SearchBar bound to a ToggleButton, Adw.PreferencesDialog with SwitchRow/ExpanderRow(show-enable-switch)/ActionRow(property)/EntryRow/ButtonRow(destructive-action), Adw.ShortcutsDialog referencing action names, breakpoint at 564px. rewrite = Adw.Sidebar (libadwaita 1.9/GNOME 50) sections bound to Gio.ListModels, Gtk.GridView over NoSelection→FilterListModel(EveryFilter[custom CollectionFilter, AnyFilter of StringFilters, BoolFilter hidden])→SortListModel, BuilderListItemFactory, Blueprint closures ($if/$format/$shortcut) and `try {}` (GTK 4.22/GNOME 51), per-widget Gio.SimpleActionGroups, GSettings-backed `create_action("sort-mode")`, undo toasts.

Data: one JSON per game under `$XDG_DATA_HOME/cartridges/games/<id>.json` (spec in docs/game_id.json.md), covers as TIFF/GIF, two GSettings schemas (`<APP_ID>` prefs and `<APP_ID>.State` width/height/is-maximized/sort-mode/show-sidebar). No favorites; "hidden" is a boolean filter with Undo toast, and rewrite's "Collections" (stored in GSettings `aa{sv}` with game-id lists, filtered by a Gtk.Filter subclass, shown as Adw.SidebarItems and an Adw.WrapBox of toggle buttons) is the direct template for Dailies' Favorites.

Sandbox escape: executables via `flatpak-spawn --host /bin/sh -c` (needs `--talk-name=org.freedesktop.Flatpak`); URLs via `Gio.AppInfo.launch_default_for_uri` (portal, no permission). Dailies' external-browser path needs only the latter.

Flatpak: dev manifest in-tree with `type: dir` source, `run-tests: true`, `-Dprofile=development`, pip modules generated by flatpak-pip-generator; Flathub manifest pins git `tag`+`commit`; finish-args mostly import-specific (Dailies needs ~network, ipc, wayland, fallback-x11, dri). CI: flatpak-builder action v6.5 in `bilelmoussaoui/flatpak-github-actions:gnome-47` (current: `flatpak/flatpak-github-actions/flatpak-builder@v6`, latest v6.8 2026-08-30, image `ghcr.io/flathub-infra/flatpak-github-actions:gnome-48` — newest published tag; newer runtimes download at build time) plus Windows (MSYS2+Inno Setup) and macOS (Homebrew+PyInstaller) jobs. Release: bump meson version + add `<release>` in metainfo → push tag → workflow downloads CI artifacts for the SHA, extracts newest release notes from metainfo with a regex, publishes via softprops/action-gh-release; Linux had no bundle on Releases (Flathub only) — Dailies should attach the CI `.flatpak`. Metainfo includes branding colours, supports/requires display_length 360, url types, developer id, OARS, raw-URL screenshots (data/screenshots/1-4.png, 1146×698 etc.), a DOAP file for GNOME Circle. Icons: 128px full-colour SVG + 16px symbolic, `.Devel` variants installed by profile; no editable icon source committed. Translations: gettext via Weblate, POTFILES incl. .blp, `translator-credits`, `__builtins__.pyi` for `_`. Full file reproductions (window/game/preferences .blp, rewrite window/game-item/cover .blp, CSS, closures, filter, toasts, gschema, metainfo, gresource, doap, pre-commit, pyproject, manifests, both workflows, launcher) are in the report appendices with a 14-point recommendations list.

Open questions:

- Hosted Weblate project page (https://hosted.weblate.org/projects/cartridges/) returned HTTP 403 to automated fetch; its existence is inferred from the README badge/URL and metainfo only.
- Whether ghcr.io/flathub-infra/flatpak-github-actions images newer than gnome-48 (gnome-49/50/51) exist; the README table and docker.yml matrix list only up to gnome-48 as of master. Building a runtime-version 51 manifest inside the gnome-48 image should work (runtime downloaded) but was not test-built.
- Flathub screenshot size/aspect quality guidelines were not checked; Cartridges uses 1146x698 and portrait dialog shots.
- The rewrite branch is explicitly non-functional in places; its patterns (Adw.Sidebar, GridView filters, closures) were read, not executed. Dailies should prototype them against the GNOME 51 runtime before committing to the design.
- Codeberg may hold commits newer than the GitHub mirror (mirror last pushed 2026-09-03); not checked beyond GitHub.
- Whether Dailies' 'configured browser' option is acceptable to Flathub reviewers if implemented via flatpak-spawn --host (requires --talk-name=org.freedesktop.Flatpak); Cartridges got away with it because launching host binaries is its core purpose.

Sources (as returned by the agent; full list inside the report):

- https://github.com/kra-mo/cartridges (clone, commit d56323e6dd0ba9b500ee4f2b11d95f2e6240b05f; tag v2.13.1; branch origin/rewrite d82bdf1b)
- https://codeberg.org/kramo/cartridges
- https://git.kramo.page/cartridges (canonical URL in metainfo)
- https://github.com/flathub/page.kramo.Cartridges (page.kramo.Cartridges.json, flathub.json, commit history)
- https://github.com/flatpak/flatpak-github-actions (README, releases v6.5–v6.8)
- https://github.com/flathub-infra/flatpak-github-actions (README image table, Dockerfile, .github/workflows/docker.yml)
- https://gitlab.gnome.org/GNOME/blueprint-compiler/-/tags
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Sidebar.html
- https://docs.gtk.org/gtk4/class.TryExpression.html
- https://discourse.gnome.org/t/gnome-51-released/38820
- https://discourse.gnome.org/t/introducing-gnome-50/34400
- https://phoronix.com/news/GNOME-50-Released
- https://docs.flatpak.org/en/latest/available-runtimes.html
- GitHub API via gh: repos/kra-mo/cartridges, releases, repos/flathub/page.kramo.Cartridges/commits

### bazaar

Full report: [`bazaar.md`](bazaar.md)

Bazaar (io.github.kolunmi.Bazaar) is a GNOME-Circle Flatpak app store written in C (GNU C11) with GTK4 >= 4.22.1, libadwaita >= 1.8, Blueprint >= 0.20 (batch-compiled .blp), Meson >= 1.0, libdex (fibers/futures for all async), libsoup3 + json-glib (HTTP/JSON), libyaml, glycin (sandboxed image decode), WebKitGTK 6.0 (only for Flathub OAuth login). The GitHub repo bazaar-org/bazaar is a frozen mirror (HEAD 2026-08-18, v0.9.4); the canonical repo is gitlab.gnome.org/World/bazaar (latest release v0.9.8 2026-10-13, version.sh 0.9.9, GNOME 51 runtime). Layout: meson.build + version.sh (single version source, also CACHE_VERSION that wipes on-disk cache), data/ (desktop.in, metainfo.xml.in with 58 releases + <branding> colours + screenshots, gschema.xml, icons/hicolor/{scalable,symbolic}/apps + AppID.Devel.svg + AppID.Source.svg Inkscape master), build-aux/flatpak/<AppID>.json (nightly manifest), docs/ (overview.md for distributors, example.yaml), po/, src/ (one bz-<widget>.{c,h,blp} per widget, style.css, gresource, 91 symbolic + 17 colour category icons), bge/ (own widget lib: carousel, markdown render). Data-holder GObjects are generated from tiny .txt specs by src/gen_gobject.sh.

UI: Adw.ApplicationWindow (1220x900, min 360) -> Adw.NavigationView -> Adw.ViewStack with Adw.ViewSwitcher in header collapsing to Adw.ViewSwitcherBar at max-width 700px (adds window.narrow class); no sidebar. Explore page: hero carousel, then Adw.ToggleGroup {styles round, huge} "Trending | Popular | New | Updated" driving an Adw.ViewStack (visible-child-name bound bidirectionally) of category sections, each title-1 + GtkFlowBox of BzAppTile (Button.card, 64px icon + heading + 1-2 line description + small-pill) sliced via SliceListModel (12) with pill "More" pushing a NavigationPage; Adw.Clamp max 1500/tightening 1400, 30px margins; breakpoints at 1250sp/970sp/700px reduce columns. Category tiles = Button.card.category-tile with 135deg gradient per category and 48px colour icon (CSS "modified from GNOME Software"). Every page is an Adw.ViewStack with loading (64px Adw.Spinner + title-3 label) / empty or offline (Adw.StatusPage + pill button) / content, enable-transitions 400ms. Detail page: NavigationPage, 128px icon, title-1, small-pill suggested-action buttons incl. BzFavoriteButton (bookmark-outline/filled-symbolic, count revealer, spinner crossfade), lozenges, header title revealer on scroll. Favorites are Flathub-account based (ListView with navigation-sidebar style, StatusPage "No Favorites" starred-symbolic) so Dailies must replace storage with local GSettings/JSON.

Curated content: YAML files (compile-time -Dhardcoded_content_config_path=/run/host/etc/bazaar/config.yaml + main-config curated-config-paths), hot-reloaded via GFileMonitor (BzContentProvider), parsed by a generic BzYamlParser driven by a 6-line XML schema mapping YAML keys onto GObject properties (typehints for list element types). Format: rows: [ section {title, subtitle{string: markdown}, appids{list}, list-type: rich, overflow-count, enable-bulk-install} | featured-carousel {appids, disable-auto-rotate} | banner {height, image{uri|light-uri/dark-uri, fit, alt, can-shrink, halign}, light-color, dark-color (any CSS bg)} | articles {aspect-ratio, uri (remote YAML feed), list} ]. BzRowView dispatches by which sub-object is non-null. Remote data: single SoupSession, helpers bz_query_flathub_v2_json ("https://flathub.org/api/v2…") and bz_query_bazaar_json ("https://usebazaar.org…"); daily state fetched with for_day=YYYY-MM-DD (/app-picks/apps-of-the-week/<day>, /collection/popular, /collection/trending, /collection/category/<cat>…) -> named categories looked up by name in Blueprint; whole state serialised to GVariant cache so the app opens offline with a "viewing cached version" Adw.Banner; refresh scheduled with randomised hour offset, paused on metered networks. Images: BzAsyncTexture (lazy GdkPaintable, MD5(url) file cache in $XDG_CACHE_HOME/<AppID>/, 24h TTL sidecar, in-memory dedupe), downloads in 8 dl-worker subprocesses, decode via glycin, image-missing-symbolic placeholder. Links opened with g_app_info_launch_default_for_uri / GtkUriLauncher.

Flatpak: nightly JSON manifest (org.gnome.Platform 51, tags nightly, desktop-file-name-suffix " (Nightly)", finish-args network/ipc/fallback-x11/wayland/dri + flatpak-specific extras, cleanup list, modules with x-checker-data); Flathub manifest is YAML in flathub/io.github.kolunmi.Bazaar pointing at a GitLab git commit, flathub.json require-important-update. CI: GitHub build-flatpak.yml (SHA-pinned actions, permissions: {}, x86_64 + aarch64 matrix, ghcr.io/flathub-infra/flatpak-github-actions:gnome-50 container, flatpak-builder action producing Bazaar.flatpak artifact, .flatpak-builder cache) + daily flatpak-external-data-checker.yml; GitLab CI uses GNOME citemplates flatpak_ci_initiative + basic-release-with-dist (release on tag) + nightly publishing. Release process: bump version.sh, add <release> in metainfo (xmllint extracts newest into in-app release notes), tag vX, GitHub/GitLab release (no .flatpak assets attached), Flathub PR. Meson tests run desktop-file-validate, appstreamcli validate --no-net --explain, glib-compile-schemas --strict. Icon: 128px GNOME-palette market stall, Devel variant, 16px symbolic, Inkscape source with template layer.

Recommendations for Dailies: adopt the same GTK4/libadwaita/Blueprint/Meson/GNOME-51 skeleton and repo layout; implement a catalogue file + weekly curated YAML (rows/sections of IDs for Popular/Trending) served from GitHub, with Favorites as a local first section; copy the ToggleGroup+ViewStack section switcher, card tile, FlowBox with breakpoint-driven columns, ViewStack loading/offline/content pattern, Adw.Banner for cached data, URL-hash image cache with TTL; use WebKitGTK (proven in-Flatpak) for the built-in browser tier and GtkUriLauncher/Gio.AppInfo for the others; copy build-flatpak.yml (add a release-upload step since Bazaar attaches no bundles), external-data-checker, metainfo branding/validation tests, Justfile bundle recipe, YAML issue form. Skip libflatpak/daemon/search-provider/hooks/blocklists and account favorites. Full report with verbatim appendices (example.yaml, workflows, .gitlab-ci.yml, metainfo, tile/category/section Blueprints, CSS, Justfile, version.sh) at the report path.

Open questions:

- Whether the curated YAML format changed on GitLab main after v0.9.4 (format was read from the frozen GitHub mirror; GitLab deps/manifest/CI/releases were cross-checked but docs/example.yaml was not re-diffed).
- Exact call that registers src/icons resources with GtkIconTheme (gresource listing verified; gtk_icon_theme_add_resource_path call not located).
- flatpak/flatpak-github-actions artifact naming and the extra step needed to attach the .flatpak bundle to a GitHub Release (Bazaar attaches no release assets).
- Ranking semantics of Flathub /collection/trending and /collection/popular are server-side and undocumented in the repo; Dailies needs its own popularity definition.
- Language choice for Dailies: Bazaar's C+gen_gobject+libbge approach is heavy; the same Blueprint/Meson/Flatpak skeleton works with Python, Rust or Vala but this was not evaluated here.

Sources (as returned by the agent; full list inside the report):

- https://github.com/bazaar-org/bazaar
- https://gitlab.gnome.org/World/bazaar
- https://gitlab.gnome.org/World/bazaar/-/raw/main/.gitlab-ci.yml
- https://gitlab.gnome.org/World/bazaar/-/raw/main/version.sh
- https://gitlab.gnome.org/World/bazaar/-/raw/main/src/meson.build
- https://gitlab.gnome.org/World/bazaar/-/raw/main/build-aux/flatpak/io.github.kolunmi.Bazaar.json
- https://gitlab.gnome.org/World/bazaar/-/raw/main/data/io.github.kolunmi.Bazaar.metainfo.xml.in
- https://gitlab.gnome.org/World/bazaar/-/raw/main/README.md
- https://gitlab.gnome.org/api/v4/projects/World%2Fbazaar/releases
- https://github.com/bazaar-org/bazaar/releases/tag/v0.9.4
- https://github.com/flathub/io.github.kolunmi.Bazaar
- https://raw.githubusercontent.com/flathub/io.github.kolunmi.Bazaar/master/io.github.kolunmi.Bazaar.yaml
- https://raw.githubusercontent.com/flathub/io.github.kolunmi.Bazaar/master/flathub.json
- https://gitlab.gnome.org/GNOME/citemplates/-/raw/master/templates/basic-release-with-dist.yml
- https://flathub.org/api/v2
- https://usebazaar.org/
- clone: /tmp/claude-1000/-home-tim-Git-Dailies/2182a9c5-78fc-417e-b7f0-b30226f216ef/scratchpad/clones/bazaar (meson.build, meson_options.txt, version.sh, Justfile, CONTRIBUTING.md, CODESTYLE.md, bazaar.doap, .github/workflows/*, .github/ISSUE_TEMPLATE/bug_form.yml, build-aux/flatpak/io.github.kolunmi.Bazaar.json, data/*, docs/overview.md, docs/example.yaml, docs/debugging.md, src/*.blp, src/style.css, src/bazaar.gresource.xml, src/curated-config-schema.xml, src/bz-curated-*.txt, src/bz-yaml-parser.*, src/bz-content-provider.c, src/bz-flathub-state.c, src/global-net.*, src/bz-async-texture.*, src/dl-worker.c, src/io.c, src/bz-dynamic-list-view.*, src/bz-section-view.c, src/bz-row-view.c, src/bz-article-list-view.c, src/gen_gobject.sh, screenshots/*.png, data/icons/**)

### stack-crossplatform

Full report: [`stack-crossplatform.md`](stack-crossplatform.md)

Recommendation: build Dailies in Python 3 + PyGObject with Blueprint UI files, a Meson build, and Flatpak on org.gnome.Platform//51. This is exactly the stack of Cartridges (the owner's named UI reference), which already ships Flatpak + Windows (MSYS2 UCRT64 pacman + Inno Setup) + macOS (Homebrew + PyInstaller .app) from one meson.build and one GitHub Actions workflow; those files are reproduced in the report so they can be copied. Fallback: Rust with gtk4-rs 0.11.5 (feature v4_24) + libadwaita-rs 0.9.2 (feature v1_10) using org.freedesktop.Sdk.Extension.rust-stable//26.08 and flatpak-cargo-generator; Cartero (Windows x64+arm64 via MSYS2 ucrt64/clangarm64, macOS via dehesselle's jhb) and Rnote (Windows installer) prove that path. Vala, C and GJS/TypeScript are all fully supported inside the GNOME 51 SDK (valac, gjs 1.90.0, blueprint-compiler 0.22.2, pygobject 3.58.0 are SDK elements; TypeScript needs the typescript 5.9.3 + node26 extensions) but no cross-platform libadwaita app in those languages could be verified, so they are not recommended for Dailies.

Exact targets (verified from gnome-build-meta gnome-51 branch and Flathub on 2026-10-15): GNOME runtime 51 = GTK 4.24.0, libadwaita 1.10.0, WebKitGTK 2.54.1 (webkitgtk-6.0 API), PyGObject 3.58.0. meson minimums: gtk4 >= 4.24, libadwaita-1 >= 1.10, webkitgtk-6.0 >= 2.54 as optional dependency. GNOME 50 (GTK 4.22, libadwaita 1.9, same WebKitGTK 2.54.1) is the one-step fallback; GNOME 48 is EOL on Flathub since 2026-03-24; 49 (GTK 4.20.4, adw 1.8.8) is still published but will be EOL'd imminently (51.0 shipped 2026-09-16; 52.0 due 2027-03-17). Flathub app ID must be io.github.tim_van_oudheusden.Dailies.

Cross-platform reality: libadwaita 1.10.0 / GTK 4.24.1 are packaged in MSYS2 (also gjs 1.90.1, vala 0.56.19, python-gobject 3.58.1 on Python 3.14, blueprint-compiler only 0.18.0) and Homebrew (libadwaita 1.10.0, pygobject3 3.58.1, blueprint-compiler 0.22.2; bottles Apple-Silicon only). libadwaita natively follows OS dark mode/accent on Windows and macOS but has no native window-control styling; GNOME developers (Discourse, May 2025) report lower stability, giant shadows, no snapping, poor font rendering on Windows; GTK 4.23/4.24 fixed the black-border bug and reworked Windows (DirectX 11/12 + DirectComposition) and macOS (native window controls, Edit menu). Cartero disables CSD on Windows (-Ddecorations=no-csd), a pattern Dailies should adopt as a switch. PyGObject ships no wheels, so Windows/macOS Python comes from MSYS2/Homebrew/gvsbuild (2026.8.0). MSIX has no verified GTK4 precedent; all examples use Inno Setup or NSIS and winget via wingetcreate.

Critical constraint: WebKitGTK is Linux-only (no Windows support since 2.4/2014; maintainers in 2025 say porting is expensive and uninteresting; no MSYS2 package; Homebrew webkitgtk formula is Linux-only). Therefore the built-in browser works only in Linux/Flatpak builds regardless of language; the preference chain must be configured command -> embedded WebKit (if `gi.require_version('WebKit','6.0')` succeeds) -> Gtk.UriLauncher external browser. Using Soup/Gio via GI for HTTP yields a zero-pip-dependency manifest (no flatpak-pip-generator needed). Flatpak CI: flatpak/flatpak-github-actions/flatpak-builder@v6 with image ghcr.io/flathub-infra/flatpak-github-actions:gnome-50 (gnome-51 tag unverified). Startup-time data for Python vs Rust does not exist publicly; measure in the Flatpak before deciding it matters. Report includes copy-ready Cartridges manifest, ci.yml, Inno .iss, PyInstaller spec, Blueprint wrap/meson snippet, Rust manifest skeleton and a proposed Dailies manifest.

Open questions:

- Does the container image ghcr.io/flathub-infra/flatpak-github-actions:gnome-51 exist yet (check flathub-infra/actions-images)? Otherwise use gnome-50 image with runtime-version 51.
- Are the Windows CSD problems (black border, oversized shadows, no snapping) resolved with GTK 4.24 as shipped by MSYS2? Needs a smoke test; otherwise ship server-side decorations on Windows like Cartero's -Ddecorations=no-csd.
- Do gresources and gettext work for a Python/Meson app on MSYS2 today? Cartridges 2.13.1 disables i18n on Windows for that reason.
- Support Intel macOS? Homebrew bottles for libadwaita/pygobject3 are listed only for Apple Silicon, so Intel CI builds from source.
- Exact Python version in the GNOME 51 / freedesktop 26.08 runtime was not verified (likely 3.14).
- Measured cold/warm startup of a PyGObject + libadwaita app in the Flatpak (no public Python-vs-Rust benchmark exists).
- Is --talk-name=org.freedesktop.Flatpak (host command for 'configured browser') acceptable for Flathub review, or should the configured-browser option be limited to Gtk.UriLauncher/portal?
- Whether any non-GTK webview (WebView2/WKWebView/CEF) could realistically be embedded for Windows/macOS later; no verified GTK4 precedent found.

Sources (as returned by the agent; full list inside the report):

- https://gitlab.gnome.org/GNOME/libadwaita/-/raw/main/NEWS
- https://gitlab.gnome.org/api/v4/projects/GNOME%2Flibadwaita/repository/tags?per_page=10
- https://gitlab.gnome.org/GNOME/gtk/-/raw/main/NEWS
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/gtk.bst
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/libadwaita.bst
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/webkitgtk.inc
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/webkitgtk-6.0.bst
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/blueprint-compiler.bst
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/pygobject.bst
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/gjs.bst
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-49/elements/sdk/gtk.bst
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-49/elements/sdk/libadwaita.bst
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-49/elements/sdk/webkitgtk.inc
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-50/elements/sdk/webkitgtk.inc
- https://gitlab.gnome.org/api/v4/projects/GNOME%2Fgnome-build-meta/repository/tree?ref=gnome-51&path=elements/sdk
- https://webkitgtk.org/news.html
- https://docs.flatpak.org/en/latest/available-runtimes.html
- https://docs.flathub.org/docs/for-app-authors/requirements
- https://docs.flathub.org/docs/for-app-authors/maintenance
- https://github.com/flatpak/flatpak-builder-tools
- https://github.com/flatpak/flatpak-github-actions
- https://github.com/flathub-infra/flatpak-github-actions/issues/17
- https://github.com/kra-mo/cartridges
- https://github.com/bazaar-org/bazaar
- https://github.com/gaphor/gaphor
- https://docs.gaphor.org/en/latest/_sources/windows.md.txt
- https://docs.gaphor.org/en/latest/_sources/macos.md.txt
- https://github.com/flxzt/rnote
- https://github.com/danirod/cartero
- https://codeberg.org/valos/Komikku
- https://github.com/giantpinkrobots/varia
- https://github.com/dino/dino
- https://gnome.pages.gitlab.gnome.org/blueprint-compiler/
- https://gnome.pages.gitlab.gnome.org/blueprint-compiler/setup.html
- https://gnome.pages.gitlab.gnome.org/blueprint-compiler/packaging.html
- https://gitlab.gnome.org/api/v4/projects/GNOME%2Fblueprint-compiler/repository/tags?per_page=6
- https://gtk-rs.org/gtk4-rs/stable/latest/book/installation_windows.html
- https://gtk-rs.org/gtk4-rs/stable/latest/book/libadwaita.html
- https://crates.io/api/v1/crates/gtk4
- https://crates.io/api/v1/crates/libadwaita
- ... 31 more in the report

### embedded-browser

Full report: [`embedded-browser.md`](embedded-browser.md)

Research on how Dailies should open DLE game URLs (user-configured browser -> built-in WebKitGTK view -> system default browser). Full report at the path below; main findings:

1. WebKitGTK 6.0 is already in the GNOME Flatpak runtime: org.gnome.Platform//49, //50 and //51 all ship libwebkitgtk-6.0.so.4.19.4, WebKit-6.0.typelib and the WebKitWebProcess/NetworkProcess/GPUProcess helpers (verified by running the runtimes locally). gnome-build-meta gnome-49 builds WebKitGTK 2.54.1 (released 2026-10-02) with -DUSE_GTK4=ON. No module to build; libportal is NOT in the runtime (Epiphany bundles it). Runtime 49 also has GTK 4.20.4, Python 3.13.15, PyGObject 3.54.5, GJS 1.86.0.

2. Persistence of game progress needs a non-ephemeral WebKit.NetworkSession.new(data_dir, cache_dir) (localStorage/IndexedDB under data_dir) PLUS an explicit cookie_manager.set_persistent_storage(path, SQLITE): WebKit's own doc comment says "By default, cookie_manager doesn't store the cookies persistently". Tangram, Wike and Komikku all do this. Popups: handle WebView::create (return NULL + open externally) and decide-policy NEW_WINDOW_ACTION/RESPONSE; downloads: cancel + open externally (Tangram/Tuba pattern, avoids --filesystem=xdg-download). Settings: set_user_agent_with_application_details("Dailies", VERSION); hardware-acceleration-policy only ALWAYS/NEVER in 6.0; 2.46+ uses Skia/DMA-BUF so --device=dri is required. WebKit's subprocess sandbox inside Flatpak uses flatpak-spawn --sandbox (portal, no extra permission). Minimal finish-args: --share=network --share=ipc --socket=wayland --socket=fallback-x11 --device=dri (+pulseaudio). Memory numbers unmeasured.

3. System default browser: Gtk.UriLauncher (4.10+; gtk_show_uri deprecated 4.10). In a sandbox GTK uses org.freedesktop.portal.OpenURI (>=v3) and passes no "ask" option. The portal source special-cases http/https ("We skip the app chooser for Internet URIs") and launches the host default browser via g_app_info_launch_uris; choices are stored in permission-store table "desktop-used-apps" with threshold 3 (confirmed on this machine). Bazaar uses gtk_uri_launcher_launch everywhere; Tuba falls back to Gio.AppInfo.launch_default_for_uri_async.

4. Specific user-chosen browser: inside the sandbox host browsers are invisible (gio mime x-scheme-handler/https in the runtime -> "No default applications"; /run/host/share has only icons). Options: (a) portal chooser via OpenURI ask=true (libportal XDP_OPEN_URI_FLAG_ASK or direct D-Bus) - sandbox-clean; (b) flatpak-spawn --host needs --talk-name=org.freedesktop.Flatpak, which flatpak itself documents as "a sandbox escape allowing arbitrary code execution"; Flathub linter finish-args-flatpak-spawn-access is "granted on sufficient explanation", 168 of 1542 apps in exceptions.json hold it, and io.github.alyraffauf.Switchyard has it precisely for "Required to launch browsers the user has installed". There is no narrower way to launch another Flatpak (Flathub Discourse). Recommendation: do not request it in the manifest; support a 'custom' mode only when the user grants it via flatpak override.

5. Obsidian: Web viewer core plugin (1.8.0, 2024-12-18), Electron <webview> (Chromium), off by default, "Open external links" setting, right-click "open in default browser", ad blocking on by default, warns plugins can read cookies.

6. Cross-platform: WebKitGTK has no Windows port since 2.4 (2014); MSYS2 ships libadwaita 1.10 but no webkitgtk; Tauri uses WebView2/WKWebView/WebKitGTK. Make WebKit an optional Meson feature (Tuba's -Din-app-browser pattern) and degrade to external browser.

7. Legal/privacy: NYT ToS (effective 2026-01-20) restricts "display (including framing and inline linking)" and non-personal/commercial use; a top-level WebView is a browser not a frame (inference) but Dailies must not block ads, inject scripts, spoof UA, or scrape; always show real URL and an "Open in Browser" escape hatch. Shared persistent session recommended by default (sibling NYT games share login) with optional per-game isolation.

Recommended design + full GSettings schema: open-mode enum {in-app (default), external, ask, custom}, external-browser-command, session-isolation {shared, per-game}, cookie-policy, itp-enabled, hardware-acceleration, user-agent, clear-web-data-on-exit, developer-extras; relocatable per-game schema with open-mode-override and isolated-session. Python sketch, finish-args and reference code excerpts (Tangram, Komikku, Tuba) included in the report.

Open questions:

- Memory footprint of WebKitGTK 2.54 (WebKitWebProcess + NetworkProcess) per open game inside Flatpak is unmeasured; benchmark with /usr/libexec/webkitgtk-6.0/MiniBrowser in org.gnome.Platform//49 when a display is available.
- Default values of WebKitSettings:hardware-acceleration-policy and NetworkSession ITP in 6.0/2.54 are not stated in the docs read; confirm at runtime.
- Whether publishers (notably NYT, ToS effective 2026-01-20 restricting 'framing and inline linking') regard a top-level embedded WebView as acceptable is a legal judgement; decide how prominently to disclose and whether to default to in-app or external.
- Final Flatpak app ID (assumed io.github.tim_van_oudheusden.Dailies) must match the repository-scaffolding research before the GSettings schema id/path is fixed.
- Whether to expose the portal 'ask' mode (OpenURI ask=true) at all, given GTK's UriLauncher cannot do it and libportal is not in the GNOME 49 runtime (would need a direct D-Bus call or bundling libportal).
- Whether to support the opt-in 'custom' mode (flatpak-spawn --host via user-granted org.freedesktop.Flatpak) at all, or keep only in-app/external/ask to avoid any sandbox-escape discussion with Flathub reviewers.
- GLib's portal fallback behaviour for Gio.AppInfo.launch_default_for_uri_async inside the sandbox could not be re-verified (docs page 404 this session).

Sources (as returned by the agent; full list inside the report):

- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-49/elements/sdk/webkitgtk.inc
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-49/elements/sdk/webkitgtk-6.0.bst
- https://webkitgtk.org/
- https://webkitgtk.org/reference/webkitgtk/stable/class.NetworkSession.html
- https://webkitgtk.org/reference/webkitgtk/stable/ctor.NetworkSession.new.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.WebsiteDataManager.html
- https://webkitgtk.org/reference/webkitgtk/stable/flags.WebsiteDataTypes.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.CookieManager.html
- https://webkitgtk.org/reference/webkitgtk/stable/enum.CookieAcceptPolicy.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.WebView.html
- https://webkitgtk.org/reference/webkitgtk/stable/signal.WebView.create.html
- https://webkitgtk.org/reference/webkitgtk/stable/property.WebView.related-view.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.Settings.html
- https://webkitgtk.org/reference/webkitgtk/stable/method.Settings.set_user_agent_with_application_details.html
- https://webkitgtk.org/reference/webkitgtk/stable/enum.HardwareAccelerationPolicy.html
- https://webkitgtk.org/reference/webkitgtk/stable/enum.PolicyDecisionType.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.Download.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.WebContext.html
- https://webkitgtk.org/2024/10/04/webkitgtk-2.46.html
- https://blogs.igalia.com/carlosgc/?p=1029
- https://trac.webkit.org/wiki/EnvironmentVariables
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/API/glib/WebKitCookieManager.cpp
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/API/glib/WebKitWebsiteDataManager.cpp
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/WebsiteData/glib/WebsiteDataStoreGLib.cpp
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/gtk/AcceleratedBackingStore.cpp
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/Launcher/glib/ProcessLauncherGLib.cpp
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebCore/platform/glib/UserAgentGLib.cpp
- https://github.com/sonnyp/Tangram
- https://github.com/hugolabe/Wike
- https://codeberg.org/valos/Komikku
- https://github.com/GeopJr/Tuba
- https://github.com/kra-mo/cartridges
- https://gitlab.gnome.org/World/bazaar
- https://gitlab.gnome.org/GNOME/epiphany/-/raw/main/org.gnome.Epiphany.json
- https://github.com/flathub/com.github.hugolabe.Wike
- https://github.com/flathub/io.gitlab.news_flash.NewsFlash
- https://github.com/flathub/dev.geopjr.Tuba
- https://github.com/flathub/info.febvre.Komikku
- https://github.com/flathub/io.github.flattool.Warehouse
- https://github.com/flathub/org.gnome.Builder
- ... 30 more in the report

### flatpak-release-pipeline

Full report: [`flatpak-release-pipeline.md`](flatpak-release-pipeline.md)

Research on the full Flatpak build/release pipeline for Dailies (GitHub-hosted GTK4/Libadwaita app), verified against primary sources and cloned repos on 2026-10-15.

Build action: use `flatpak/flatpak-github-actions/flatpak-builder@v6.8` (2026-08-30, commit 7932741...) with the Flathub container image `ghcr.io/flathub-infra/flatpak-github-actions:gnome-51`. The `flathub-infra` *action* fork is deprecated (issue #17 says only the images stay there; images are built from `flathub-infra/actions-images`, tags currently freedesktop-24.08/25.08/26.08, gnome-49/50/51, kde-*). The image is `FROM ghcr.io/flathub/flatpak-builder-lint`, so `flatpak-builder-lint` is on PATH in CI for `manifest`/`repo`/`appstream` checks with `--gha-format`. The action runs `flatpak-builder --repo=repo --disable-rofiles-fuse --install-deps-from=flathub --force-clean --default-branch=.. [--ccache] [--gpg-sign]` then `flatpak build-bundle repo <bundle> --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo --arch=..`. Multi-arch: native runners `ubuntu-latest` + `ubuntu-24.04-arm`/`ubuntu-26.04-arm` (free for public repos; no `ubuntu-latest-arm`); QEMU path still documented but unnecessary. Bazaar's CI (gnome-50 image, v6.7, arm matrix, manual actions/cache around the step citing upstream issue #239) is the better template; Cartridges' CI uses an outdated Docker Hub image.

App ID: Flathub rule "dashes become underscores" in the domain part; the linter demangles `_`→`-` and lowercases to `github.com/tim-van-oudheusden/dailies`. Verified real examples: io.github.nate_xyz.Resonance, io.github.celluloid_player.Celluloid. Therefore `io.github.tim_van_oudheusden.Dailies` and dev ID `io.github.tim_van_oudheusden.Dailies.Devel` (5 components = max). Verification requires logging in to Flathub with the GitHub account that owns the repo.

Runtime: GNOME 51 (released 2026-09-16; Flathub requires latest at submission). Observed EOL practice: GNOME 46 EOL 2025-04-17 (4 weeks after 48), GNOME 48 EOL 2026-03-24 (6 days after 50) → branch N dies when N+2 ships (~1 year). GNOME 49 is not flagged EOL yet per `flatpak remote-info` but should be any day. GNOME 52 lands 2027-03-17.

Releases: on `v*` tags build the release manifest for both arches, attach `Dailies-x86_64.flatpak`, `Dailies-aarch64.flatpak`, SHA256SUMS and the `.flatpakref` via `softprops/action-gh-release@v3.0.3` (or `gh release create --notes-file --verify-tag`); release body extracted from the newest metainfo `<release>` (Cartridges pattern) plus `.github/release.yml` auto-notes. Install: `flatpak install --user ./Dailies-x86_64.flatpak`; GNOME 51 runtime from Flathub is the prerequisite (bundle's `--runtime-repo` prompts to add it); bundles do not self-update unless built with `--repo-url`.

Self-hosted remote: Flatpak docs provide a GitLab Pages template (flatpak-builder --gpg-sign → build-bundle → `flatpak build-update-repo --gpg-sign --generate-static-deltas --prune`, multi-arch merged before update-repo, `.flatpakrepo`/`.flatpakref` with base64 GPGKey). `andyholmes/flatter` v1.0.0 is a GitHub Pages action (generates index.flatpakrepo, incremental cache, needs max-parallel:1). GitHub Pages limits: 1 GB site, 100 GB/month soft bandwidth, 10-min deploy, no symlinks in the Pages artifact. Report includes a hand-rolled pages-repo.yml (ostree pull-local merge of both arches, GPG via crazy-max/ghaction-import-gpg v7.0.0, actions/upload-pages-artifact v5 + deploy-pages v5).

Flathub: submission flow (fork flathub/flathub, branch from `new-pr`, PR "Add <id>", `bot, build`), required files, metainfo requirements (developer id, launchable, OARS, branding light/dark, screenshots on tag/commit URLs, releases with dates), quality guidelines (name <20 chars, summary ≤35, screenshots ≤1000x700, icon rules), linter never-granted errors, WebKitGTK 6.0 is in org.gnome.Platform (no module needed), only `--share=network --share=ipc --socket=wayland --socket=fallback-x11 --device=dri` needed. Policy risks for Dailies: "thin wrappers or launchers" and "simple web wrapper applications" are rejected, "insufficient development history" is a rejection reason, and "Flathub manifests must not contain AI-generated or AI-assisted content; AI tools must not open submission PRs".

.Devel: meson `profile` combo option (Cartridges) producing `<id>.Devel`, `@APP_ID@`-templated desktop/metainfo/gschema; manifest keys `tags`/`desktop-file-name-suffix` (Bazaar). Never publish Devel to Flathub. Versioning: recommend SemVer `vX.Y.Z` tags (Bazaar/MinimalUI convention), meson version as source of truth, metainfo `<release>` as changelog, `appstreamcli news-to-metainfo/metainfo-to-news/vercmp` available. Automation: `ghcr.io/flathub/flatpak-external-data-checker` weekly with `--update --never-fork --require-important-update` and `x-checker-data` (git tag-pattern, pypi, json, anitya); Dependabot `github-actions` weekly (MinimalUI's file reused); neither Dependabot nor Renovate has a Flatpak manager. Report contains copy-paste ci.yml, release.yml, pages-repo.yml, flatter alternative, external-data-checker.yml, dependabot.yml, release.yml, both manifest skeletons, meson profile snippet, and reproduced reference files with all action SHAs resolved.

Open questions:

- Will Flathub reviewers classify Dailies as a 'thin wrapper/launcher' or 'simple web wrapper'? The written policy rejects both; native value (favorites, categories, popularity, search provider, offline catalog) and a real release history are needed before submitting, and the manifest/submission PR must be human-authored per Flathub's Generative-AI policy.
- Exact GNOME 49 runtime EOL date: GNOME 51 shipped 2026-09-16 but org.gnome.Platform//49 carried no EOL flag on 2026-10-15; monitor flatpak remote-info / Flathub Discourse and target 51 regardless.
- flatpak/flatpak-github-actions issue #239 ('caching is broken upstream', cited in Bazaar's workflow) was not read; decide whether to copy Bazaar's manual actions/cache restore/save pattern or trust the built-in cache.
- Whether andyholmes/flatter runs unmodified inside ghcr.io/flathub-infra/flatpak-github-actions:gnome-51 (flatter has no gnome:51 image yet); the hand-rolled pages-repo.yml avoids this dependency but its ostree pull-local merge step is untested here.
- Behaviour of the linter error appstream-latest-release-is-prerelease for '~beta' versions if pre-releases are ever published to Flathub beta.
- Flathub's JSON style wording ('4-tab indentation') is ambiguous; Cartridges/Bazaar use 2-space JSON and the external-data-checker honours .editorconfig; pick one and add .editorconfig.
- Which local linter exceptions the Devel app ID actually needs (e.g. appid-url-not-reachable) must be discovered on the first CI run.

Sources (as returned by the agent; full list inside the report):

- https://github.com/flatpak/flatpak-github-actions
- https://github.com/flathub-infra/flatpak-github-actions/issues/17
- https://github.com/flathub-infra/actions-images
- https://github.com/flathub-infra/flatpak-builder-lint
- https://github.com/flathub-infra/flatpak-external-data-checker
- https://docs.flathub.org/docs/for-app-authors/requirements
- https://docs.flathub.org/docs/for-app-authors/submission
- https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines
- https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines/quality-guidelines
- https://docs.flathub.org/docs/for-app-authors/linter
- https://docs.flathub.org/docs/for-app-authors/maintenance
- https://docs.flathub.org/docs/for-app-authors/verification
- https://docs.flathub.org/docs/for-app-authors/runtimes
- https://docs.flatpak.org/en/latest/hosting-a-repository.html
- https://github.com/flatpak/flatpak-docs/blob/main/docs/hosting-a-repository.rst
- https://docs.flatpak.org/en/latest/single-file-bundles.html
- https://man.archlinux.org/man/flatpak-build-update-repo.1.en
- https://man.archlinux.org/man/flatpak-build-bundle.1.en
- https://man.archlinux.org/man/appstreamcli.1.en
- https://release.gnome.org/calendar/
- https://handbook.gnome.org/maintainers/making-a-release.html
- https://developer.gnome.org/documentation/tutorials/application-id.html
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/master/elements/sdk/webkitgtk.bst
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes
- https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference
- https://docs.renovatebot.com/modules/manager/
- https://github.com/actions/upload-pages-artifact
- https://github.com/andyholmes/flatter
- https://github.com/kra-mo/cartridges
- https://github.com/bazaar-org/bazaar
- https://github.com/flathub/page.kramo.Cartridges
- https://github.com/flathub/io.github.kolunmi.Bazaar
- https://github.com/flathub/io.github.nate_xyz.Resonance
- https://github.com/Tim-van-Oudheusden/MinimalUI
- https://github.com/softprops/action-gh-release
- https://github.com/crazy-max/ghaction-import-gpg
- https://discourse.flathub.org/t/org-gnome-platform-branch-46-is-end-of-life/9675
- https://discourse.ubuntu.com/t/the-gnome-48-runtime-is-no-longer-supported-as-of-march-24-2026-ubuntu-24-04-4-lts-flatpak/80598
- ... 1 more in the report

### data-pipeline

Full report: [`data-pipeline.md`](data-pipeline.md)

Research for the Dailies data architecture, written to the scratchpad report (about 7,000 words plus copy-ready appendices). Key findings and recommendations:

(1) Submissions: use a GitHub Issue Form `.github/ISSUE_TEMPLATE/new-game.yml` (name, https URL, category dropdown, difficulty dropdown, description with min_length, optional tags/language/icon_url, required checkboxes) auto-labelled `game-submission`. Verified schema facts: ids are alphanumeric/-/_, `validations.required` only enforced on public repos, multi-select dropdowns render as "A, B". Parse with `stefanbuck/github-issue-parser` v3.2.5 (SHA cb6e9715..., dropdown -> string, checkboxes -> array, `_No response_` -> ""); `issue-ops/parser` v5.0.0 is the alternative (dropdown -> array); `issue-ops/validate` 404s, do not rely on it. Two-stage IssueOps: stage A on opened/edited validates with a Python script (https only, public host, HEAD/GET reachability, URL/slug duplicate check, JSON Schema) and comments + toggles `validated`/`needs-changes`; stage B on maintainer label `approved` (author_association guard like the owner's claude.yml) appends the entry, fetches the icon, opens a PR via `peter-evans/create-pull-request` v8.1.1 (SHA 5f6978fa...) with `Closes #N`. Caveat verified: PRs opened with GITHUB_TOKEN do not trigger CI; use a fine-grained PAT or validate before opening. Auto-merge needs "Allow auto-merge" + ruleset; recommend human merge for v1.

(2) Catalog: `data/v1/games.json` validated by `data/v1/schema/catalog.schema.json` (2020-12; full schema in report): immutable slug `id`, `status` soft-delete, `schema_version`, `/v1/` path for breaking changes, `domain` and `wikipedia` helper fields. CI via `check-jsonschema`. Seed source: Wordles of the World (780 entries, CC0).

(3) Distribution, measured by curl: raw.githubusercontent `max-age=300` + ETag/304 works; GitHub Pages `max-age=600` + ETag, 100 GB/month soft cap, 429 possible; jsDelivr branch TTL 12h, `@latest` 7 days, browser max-age 7 days; release assets redirect to 1-hour signed URLs with `no-cache`. Recommend Pages primary, raw fallback, bundled snapshot in the Flatpak, 6-hour conditional revalidation with descriptive User-Agent.

(4) Popularity sources: Tranco `GET https://tranco-list.eu/api/ranks/domain/{domain}` is free, keyless, 1 req/s, 30 daily ranks, and covers even tiny DLE domains (observed ranks 21k to 1.49M for eight sample games) -> primary. Cloudflare Radar free with token (Account > Radar Read), CC BY-NC 4.0, per-domain rank/bucket plus first-party TRENDING_RISE ranking, 1,200 req/5 min -> optional secondary. Wikipedia pageviews CC0, no key, strict UA, 200 req/min for compliant bots, but only famous games have articles (Connections/Framed/Scrandle 404) -> tertiary. HN Algolia keyless 10k/h -> low-weight buzz. Reddit (OAuth, 100 QPM, gated registration), Google Trends (pytrends archived Apr 2025, official API gated alpha since 2025-07-24), Similarweb (paid) excluded; telemetry excluded per brief. Composite score proposed: 0.8 Tranco log-rank + 0.15 Wikipedia + 0.05 HN with shared-domain splitting.

(5) Weekly job: cron `17 4 * * 1` (not minute 0; public-repo schedules disabled after 60 days inactivity), deterministic Python collect/compute (fail closed, raw signals as artifact, carried_forward flags), optional Claude narrative via `anthropics/claude-code-action` v1.0.250 (SHA a26b07d8..., automation mode with `prompt`, `claude_args --allowedTools "Read,Write" --disallowedTools Bash...`, OAuth token already used by the owner) or a 20-line Anthropic SDK script; schema validation; PR via create-pull-request. Cost roughly $0.15-0.35/week on claude-opus-5-5.

(6) Icons: build-time fetch into `data/v1/icons/<id>.png` (manifest/apple-touch-icon/link rel=icon -> /favicon.ico -> Google faviconV2 (unofficial, 301 to t0.gstatic.com, max-age 7d) -> DuckDuckGo ip3 (unofficial ICO, max-age 30d)), served from Pages, symbolic fallback, keep out of the Flatpak payload, takedown note.

(7) Rotation: `popularity.json` keyed by ISO week with `generated_at`, `valid_until` (+10 days), `method_version`, `popular` (top N trailing 28 days), `trending` (largest positive delta vs 4-week mean, excluding top-5 popular, backfilled with new games), per-game `scores`, `sources` health, `attribution`. Full schema and example included.

Open questions:

- Shared domains (nytimes.com hosts Wordle, Connections, Spelling Bee, Strands): split the Tranco signal equally or maintain a manual domain_weights.json?
- Include Cloudflare Radar in v1 (requires a Cloudflare account and CLOUDFLARE_RADAR_TOKEN secret, CC BY-NC 4.0 attribution) or start Tranco-only?
- Narrative step: claude-code-action with the existing CLAUDE_CODE_OAUTH_TOKEN, or a small Anthropic SDK script with ANTHROPIC_API_KEY; which model (claude-opus-5-5 default vs cheaper Sonnet/Haiku 5.5)?
- Enable auto-merge for automated data PRs from day one or after a probation period?
- Use a fine-grained PAT (DATA_BOT_TOKEN) so CI runs on PRs opened by workflows, or accept that GITHUB_TOKEN-created PRs show no checks?
- Final category taxonomy (11 proposed enum values) to align with the UI design.
- Store icons in the main repo or only on a gh-pages/orphan branch to keep history small?
- Tranco's own license is not stated on its site; confirm reuse terms with its maintainers.
- Cloudflare Radar per-domain endpoint query parameters (date, rankingType, limit) were not verifiable from the fetched reference pages.
- SHAs for actions/download-artifact and peter-evans/find-comment still need to be resolved before pinning.
- Flathub policy on third-party trademark icons in the bundled payload was not checked; current recommendation keeps icons out of the Flatpak.

Sources (as returned by the agent; full list inside the report):

- https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms
- https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema
- https://github.com/stefanbuck/github-issue-parser
- https://github.com/issue-ops/parser
- https://github.com/peter-evans/create-pull-request
- https://github.com/anthropics/claude-code-action
- https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows
- https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-auto-merge-for-pull-requests-in-your-repository
- https://cli.github.com/manual/gh_pr_merge
- https://github.com/jsdelivr/jsdelivr
- https://github.com/orgs/community/discussions/46691
- https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/access-policy.html
- https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits
- https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
- https://developers.cloudflare.com/radar/investigate/domain-ranking-datasets/
- https://developers.cloudflare.com/radar/get-started/first-request/
- https://developers.cloudflare.com/api/resources/radar/subresources/ranking/
- https://developers.cloudflare.com/fundamentals/api/reference/limits/
- https://blog.cloudflare.com/radar-domain-rankings/
- https://radar.cloudflare.com/about
- https://tranco-list.eu/api_documentation
- https://hn.algolia.com/api
- https://github.com/reddit-archive/reddit/wiki/API
- https://developers.google.com/search/blog/2025/07/trends-api
- https://github.com/python-jsonschema/check-jsonschema
- https://rwmpelstilzchen.gitlab.io/wordles/
- https://github.com/Tim-van-Oudheusden/MinimalUI
- https://github.com/Tim-van-Oudheusden/website

### logo-icon

Full report: [`logo-icon.md`](logo-icon.md)

Dailies icon/logo research (2026-10-15). Deliverables for a GNOME/Flathub app are exactly three SVGs named after the app ID: a 128x128 full-color icon in data/icons/hicolor/scalable/apps/<ID>.svg, a 16x16 monochrome <ID>-symbolic.svg in hicolor/symbolic/apps/, and a striped <ID>.Devel.svg for development builds (auto-generated by App Icon Preview). Flatpak only exports icons named $FLATPAK_ID[.foo|-foo]; the Flathub linter requires appstreamcli compose to produce a 128px PNG (satisfied by an installed SVG), SVG-only in scalable/, Icon= in the .desktop equal to the app ID, and a <launchable> tag. Recommended app ID per Flathub rules (io.github prefix, lowercase, hyphen to underscore): io.github.tim_van_oudheusden.Dailies. Copy-ready Meson snippets from Cartridges (plain) and Bazaar (-Ddevelopment switch installing the Devel art renamed) are in the report.

HIG "App Icons" (page last substantively edited 2024-08-10; no 2025/2026 full-color style refresh exists): simple geometric metaphor tied to the name and function; no mascots/third-party logos; drawn inside 128px without filling it, using the template's base shapes (square 104x104 at 12..116, wide 112x88, tall 88x112, circle d=120, baseline y~117, 2px/8px grid); not flat - a darker front "chin" of about 4 nominal px (8 canvas px; Cartridges/Bazaar use ~12); flat colors on straight surfaces, gradients only on curves; shadows inside the silhouette only, light from above; GNOME palette (full table and .gpl reproduced); legible at 32px; symbolic uses the same metaphor, 16px, 2px strokes, 1px margin, pixel-aligned. "No text" is not a written HIG rule; Flathub says avoid small text; treated as a strong convention. Tooling verified: App Icon Preview 3.5.1 (2025-04-23; template is a 192x152 document with #hicolor and #symbolic artboards; export via Ctrl+E), HIG-app-icons template repo (last commit 2026-05-26, Inkscape 1.4.2 template, sketch templates), Color Palette 3.0.0, Symbolic Preview 0.0.9, Icon Library 0.0.23, Flathub app-icon-grid.svg and banner-preview. 2026 change: GTK 4.22 (2026-03-06) added a stateful/animated symbolic format (gpa: namespace, .gpa, Shaper editor) and GtkSvg; classic -symbolic.svg keeps working; relevant only for optional in-app UI icons. KDE note: Bazaar PR #895 removed clip masks because Qt's SVG renderer breaks on them - keep exported icons free of clipPath/mask/filters.

Benchmarks: Cartridges (purple cartridge by kramo; Purple 2 top, Purple 3/5 chin gradient, Dark 3 details, 2.7 KB clean SVG, symbolic outline, hand-colored Devel, brand #d5b0e7/#501a5c, screenshots ~1146x698 window+shadow). Bazaar (market stall by Tobias Bernard, PR #864 2025-12-31; browns + red/white awning, gradients only on round goods, App Icon Preview .Source.svg committed, brand #ffbe6f/#c11c2b, light+dark screenshots at 1x and 2x).

Flathub quality rules for brand colors (light+dark, colorful, dark = darker/muted, contrast with icon) and screenshots (window only with native shadow/rounded corners, window <=1000x700 or 2000x1400 HiDPI, 3-6 shots, default settings, dark only as extra, one-sentence captions, link to tag not branch) are reproduced; GNOME HIG has no screenshot page.

Three concepts: A "Daily Grid" (recommended) - tear-off calendar card (Blue 3 header, Blue 4 edge, Light 2 page, Light 4 chin, Dark 2 rings) whose page shows a 3x2 guess-feedback grid (Green 4, Yellow 4, Light 3); symbolic = header bar + 2x3 tiles; brand Blue 1 #99c1f1 / Blue 5 #1a5fb4; draft full-color and symbolic SVGs included. B "Sunrise Board" - Yellow 3 sun rising behind a Dark 3 board with one guess row; contrast risk on dark backgrounds. C "Game Tray" - 2x2 colored game tiles with a star; too generic, dropped. Report includes an actionable checklist, MetaInfo fragment, open questions (app ID confirmation, Wordle-color association, design-team review channel, Devel ID strategy, cross-platform .ico/.icns).

Open questions:

- Confirm the Flathub-compliant app ID io.github.tim_van_oudheusden.Dailies before drawing the icon (file names and App Icon Preview project name derive from it; renaming later needs a <replaces> entry).
- Owner choice between Concept A (calendar card with guess-feedback grid) and Concept B (sunrise over a board); acceptability of the green/yellow feedback-tile motif given its Wordle association (GNOME palette hues used, no legal assessment done).
- Whether to request a GNOME design-team/Discourse review of the icon; the exact icon-request tracker URL could not be verified.
- Devel build strategy: separate <ID>.Devel app ID (GNOME style, symbolic installed renamed) vs Bazaar-style same-ID artwork swap via -Ddevelopment.
- Whether cross-platform builds are in scope, which would require generating .ico/.icns from the 128px SVG (Cartridges commits pre-built files; generation method not in its repo).
- No 2024-2026 full-color icon style refresh was found; confirm nothing is announced on GNOME Discourse before finalizing (GTK 4.22's new animated symbolic format affects UI icons only).

Sources (as returned by the agent; full list inside the report):

- https://developer.gnome.org/hig/guidelines/app-icons.html
- https://gitlab.gnome.org/Teams/Design/hig-www/-/blob/main/source/guidelines/app-icons.rst
- https://developer.gnome.org/hig/guidelines/ui-icons.html
- https://developer.gnome.org/hig/reference/palette.html
- https://gitlab.gnome.org/Teams/Design/HIG-app-icons
- https://flathub.org/apps/org.gnome.design.AppIconPreview
- https://gitlab.gnome.org/World/design/app-icon-preview
- https://flathub.org/apps/org.gnome.design.Palette
- https://flathub.org/apps/org.gnome.design.SymbolicPreview
- https://flathub.org/apps/org.gnome.design.IconLibrary
- https://gitlab.gnome.org/Teams/Design/icon-development-kit
- https://blogs.gnome.org/tbernard/2019/12/30/designing-an-icon-for-your-app/
- https://docs.gtk.org/gtk4/icon-format.html
- https://discourse.gnome.org/t/animated-icons-for-gtk/31564
- https://blogs.gnome.org/gtk/2026/02/25/an-update-on-svg-in-gtk/
- https://www.phoronix.com/news/GTK-4.22-Released
- https://docs.flatpak.org/en/latest/conventions.html#application-icons
- https://docs.flathub.org/docs/for-app-authors/requirements
- https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines/
- https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines/quality-guidelines
- https://docs.flathub.org/img/app-icon-grid.svg
- https://docs.flathub.org/banner-preview
- https://docs.flathub.org/docs/for-app-authors/linter
- https://www.freedesktop.org/software/appstream/docs/chap-Metadata.html#tag-branding
- https://github.com/kra-mo/cartridges
- https://github.com/bazaar-org/bazaar
- https://github.com/bazaar-org/bazaar/pull/864
- https://github.com/bazaar-org/bazaar/pull/895
- https://gitlab.gnome.org/Teams/Circle/-/blob/main/membership_guide.md
- https://discourse.flathub.org/t/quality-guidelines-help-with-screenshots/7414

### dle-catalog

Full report: [`dle-catalog.md`](dle-catalog.md)

Compiled and liveness-checked a seed catalog of 116 daily "-dle" games for Dailies (all requested titles plus sports, logic, non-English and publisher games), written to the report with a validated JSON appendix matching {id,name,url,category,difficulty,description,tags,free_no_account}. Every URL was curl-fetched on 2026-10-15 with title/meta captured; 112 are verified live, 4 are Cloudflare bot-walled but live per the open-source aukspot/dles directory (Immaculate Grid, Immaculate Footy, Artle, Bracket City), and WaPo Keyword was unreachable from this network. Only two entries need an account/subscription: NYT Spelling Bee (limited free play) and GeoGuessr Daily Challenge.

Key verifications: Scrandle is real at scrandle.com ("daily web game of food comparison... scran", UK stadium food; scrandle.cc is a mirror/clone). Wheredle is real at wheredle.xyz (Street View US-state detective game). Pokédle (pokedle.net) and LoLdle (loldle.net) are live fan games by the same developer. Heardle was shut down by Spotify in May 2023; Bandle, Heardle Decades and Songless are the live successors. Several commonly listed domains are now hijacked gambling redirects or dead and must NOT be seeded: moviedle.app (game moved to moviedle.xyz), absurdle.online (original at qntm.org), posterdle.com, cladder.io, cloudle.app, foodle.io (food-le.com is a low-confidence clone). Factle moved to frontofficesports.com; Quordle/Octordle are now Merriam-Webster; Cinematrix lives at a vulture.com article URL; PlusWord was removed by aukspot in 2026.

Taxonomy: aggregators use 7-19 categories, with Words dominating (dles.gg: 379/1068; aukspot: 245/785 active). Proposed 10 fixed primary categories (words, geography, music, movies-tv, video-games, numbers-logic, trivia, visual, food, sports) plus a curated tag vocabulary (mechanics like wordle-like/grouping/grid, media, subject, publisher such as nyt/merriam-webster/teuteuf/linkedin/fan-made, language, and machine-relevant flags account-required/subscription-limited/weekdays-only/not-daily/bot-walled/low-confidence). Difficulty stays easy/medium/hard with a rubric; no aggregator publishes difficulty, so it is the one field that must be maintainer-curated.

Prior art: The Dles (aukspot, GPL-3.0, SvelteKit, 877 YAML records with status and dated add/remove history, favorites/done-today/random, GitHub issue template intake) is the best model and its schema is reproduced; DLES.gg (1068), Dle Hunt (859, account-gated ratings/streaks), Alldle (1606), Dle Games (600+, paid ad-free), dle.wtf (hosts 12 games, links 22, 7 categories, "Games belong to their respective creators"), Puzzmo and NYT Games are publisher platforms; a tiny Chrome "Daily Games Tracker" extension exists; small iOS apps host their own mini-games. No DLE launcher exists on Flathub or as a GTK app (only single-game Blurble, Puzzled, Crosswords), so Dailies would be first. Common weaknesses: category sprawl, stale/hijacked links persisting for months, no difficulty, popularity gated or absent.

Legal: NYT ToS §2.2 forbids display "including framing and inline linking" and automated scraping; NYT filed WORDLE application serial 97510050 (status suspended as of 2026-07) and issued 2024 DMCA takedowns against Reactle and ~1,900 forks claiming the name and 5x6 green/yellow/grey trade dress; NYT opposed the WORLDLE mark (outcome unknown) and lost a German WORDLE case in 2024. Recommendations: Dailies only links/launches (nominative use), ships no third-party icons (runtime favicon cache only), avoids Wordle trade dress in its logo, adds a non-affiliation disclaimer, never iframes or injects scripts in the built-in WebView, keeps "open externally" one click away, stores one YAML per game with status/history, runs a weekly link checker that flags cross-domain redirects and gambling titles, and uses directory co-listing counts as a cheap popularity proxy. "Dailies" has no name collision with an existing launcher.

Open questions:

- Exact free-play limit of NYT Spelling Bee and whether The Mini is still free without a subscription (needs a manual logged-out browser check; nytimes.com blocks automated fetch and the ToS forbids scraping).
- Whether LinkedIn games (Pinpoint, Queens) are playable without a LinkedIn account (aukspot says yes for Crossclimb; not independently verified).
- Washington Post Keyword could not be reached (curl 000) from this network; verify liveness by hand.
- Outcome of the NYT vs Worldle USPTO trademark opposition and the current status of WORDLE serial 97510050 on TSDR.
- Policy decision: include fan-made IP games (Pokedle, LoLdle, Smashdle, Narutodle...) by default given takedown/churn risk, or gate behind a tag filter.
- Provenance/content of food-le.com and birdlegame.com (both low-confidence; consider dropping from the seed).
- Whether to import aukspot/dles data wholesale (GPL-3.0 compatible) or seed only the curated 116 and credit them.

Sources (as returned by the agent; full list inside the report):

- https://github.com/aukspot/dles
- https://dles.aukspot.com/
- https://dles.gg/
- https://dlehunt.com/
- https://www.alldle.net/all-dles
- https://dlegames.org/
- https://dle.wtf/
- https://help.nytimes.com/hc/en-us/articles/115014893428-Terms-of-Service
- https://www.geoguessr.com/daily-challenges
- https://scrandle.com/
- https://scrandle.cc/
- https://wheredle.xyz/
- https://moviedle.xyz/
- https://qntm.org/files/absurdle/absurdle.html
- https://www.vulture.com/article/daily-movie-grid-trivia-game-cinematrix.html
- https://flathub.org/api/v2/appstream/app.drey.Blurble
- https://www.404media.co/nytimes-files-copyright-takedowns-against-hundreds-of-wordle-clones/
- https://www.engadget.com/the-new-york-times-is-cracking-down-on-wordle-clones-100004668.html
- https://gizmodo.com/nyt-dmca-takedown-request-wordle-clones-reactle-1851320538
- https://wjla.com/news/offbeat/nyt-fighting-off-wordle-copycats-with-several-takedown-notices-word-guessing-game-new-york-times-look-alikes-digital-millenium-copycat-act-github-trademark-battle
- https://www.trademarkelite.com/trademark/trademark-detail/97510050/WORDLE
- https://www.techdirt.com/tag/wordle/
- https://www.goodmans.ca/insights/post/goodmans-ip-blog/worldle--faces-a-wordle-hurdle
- https://www.euronews.com/business/2024/07/21/new-york-times-unable-to-push-germanys-wordle-out-of-puzzle-market
- https://www.techradar.com/news/spotify-just-killed-the-best-wordle-like-game-for-music-fans
- https://www.niemanlab.org/2025/06/wordle-who-the-atlantic-launches-a-suite-of-new-daily-puzzles-and-games/
- https://www.ggrecon.com/word-games/pokedle-answers-hints-today/
- https://www.chromeboard.com/extension/daily-games-tracker-lilhdhmnjimhilmalbhfbdkdockefoja
- https://linuxphoneapps.org/games/app.drey.blurble/
- https://ohayou.bookriot.com/the-new-york-times-mini-crossword-is-no-longer-free-to-play/

### libadwaita-ui-patterns

Full report: [`libadwaita-ui-patterns.md`](libadwaita-ui-patterns.md)

Current stack (verified Oct 2026): GNOME 51 shipped 2026-09-16 with GTK 4.24.0 and libadwaita 1.10.0; org.gnome.Sdk//51 and Platform//51 are on Flathub (remote build 51.0-14, 2026-10-14) and installed on the owner's machine; libadwaita main is 1.11.alpha. The brief's "1.7/1.8, GNOME 48/49" is two cycles stale (1.7↔48, 1.8↔49, 1.9↔50, 1.10↔51). Blueprint is bundled in the GNOME SDK: 0.18.0 (49), 0.20.4 (50), 0.22.2 (51; also upstream latest tag), so no Flatpak module is needed; keep a subprojects wrap for native builds. The GNOME Platform 51 runtime contains WebKitGTK 2.54.1 (libwebkitgtk-6.0, WebKit-6.0.typelib) for a zero-cost in-app browser, plus glycin 2.2.1 (GlyGtk4-2) which GTK's docs recommend for untrusted images, and libsoup 3.

Recommended skeleton: Adw.ApplicationWindow (360×294 min per HIG) → Adw.ToastOverlay → Adw.NavigationView {library, browser} → Adw.NavigationSplitView whose sidebar is an Adw.Sidebar (new in 1.9; sections: title-less Favorites pinned first, "This Week" Popular/Trending, "Categories" filled from data), collapsing via Adw.Breakpoint `max-width: 500sp` → `collapsed: true; sidebar.mode: page`. Split-view defaults: 180sp/280sp/25%. Primary menu (open-menu-symbolic, `primary: true`) sits above the sidebar list per HIG; standard final group Preferences / Keyboard Shortcuts / About, no Quit. Content: Gtk.GridView (max-columns default 7; Bazaar pattern with breakpoints lowering columns) inside Adw.ClampScrollable, backed by Gio.ListStore→FilterListModel→SortListModel; tiles are Gtk.Button.card inside a Gtk.Overlay with a ToggleButton.circular.osd star (never button-in-button). Empty/loading/feedback: Adw.StatusPage (.compact; pill suggested-action button), Adw.Spinner (1.6, 16–64px), Adw.Toast (default timeout 5 s; dismiss_all 1.7). Search: Gtk.SearchBar with key-capture-widget + connect_entry, Ctrl+F as app action, Escape closes; SearchEntry search-changed/search-delay. Preferences: Adw.PreferencesDialog (search-enabled defaults FALSE — set true), ComboRow+StringList for browser mode, EntryRow(show-apply-button) for command, SwitchRow; Gio.Settings.bind flags documented; schema with <enum> key, separate .State schema; Meson install_data + glib-compile-schemas --strict --dry-run test + gnome.post_install(glib_compile_schemas). About: adw_about_dialog_new_from_appdata(resource_path, release_notes_version) reads name/icon/developer/version/urls/license/release notes from the bundled metainfo. Shortcuts: Adw.ShortcutsDialog (1.8) auto-wired by AdwApplication when the gresource has shortcuts-dialog.ui with id shortcuts_dialog (Cartridges aliases it); GtkShortcutsWindow deprecated GTK 4.18. Favorite icons starred-symbolic / non-starred-symbolic exist in Adwaita (symbolic/status) — bundle copies in the gresource. Drag-reorder via GtkDragSource(prepare→ContentProvider)/GtkDropTarget(GType, MOVE) plus Move Up/Down menu for a11y (HIG). No .badge class exists; difficulty badge needs ~6 lines of CSS using libadwaita variables in one style.css with media queries (style-dark.css deprecated 1.9).

Deprecated to avoid: AdwLeaflet/Flap/Squeezer/ViewSwitcherTitle (1.4); AdwAboutWindow/MessageDialog/PreferencesWindow, .opaque (1.6); .dim-label→.dimmed (1.7); style-dark/hc css (1.9); AdwEnumListModel→GtkEnumList (1.10); GtkShortcutsWindow (4.18); Picture keep-aspect-ratio→content-fit (4.8); Texture.new_for_pixbuf (4.20); GtkDialog/ComboBoxText (4.10). The report includes five hand-written Blueprint skeletons (window with sidebar+grid, game tile, preferences, WebKit browser page, shortcuts dialog), CSS, a gschema, and verbatim copies of Cartridges' meson/gresource/icons scaffolding and Bazaar's GridView/favorite-button files. Design decisions flagged: a "configured specific browser" is not launchable from the sandbox without --talk-name=org.freedesktop.Flatpak/flatpak-spawn --host; libadwaita floor 1.9 (AdwSidebar) vs 1.8 (ListBox.navigation-sidebar) for Hive/native packaging.

Open questions:

- Flathub app-ID form for a GitHub-hosted project (io.github.tim_van_oudheusden.Dailies, hyphen→underscore) was not re-verified against docs.flathub.org in this run.
- Can a user-'configured' specific browser be launched from the Flatpak sandbox? Likely requires --talk-name=org.freedesktop.Flatpak and flatpak-spawn --host (Cartridges requests this to launch games); otherwise only the default browser via the OpenURI portal (Gtk.UriLauncher) is reachable. Needs a design decision.
- libadwaita floor: 1.9 (needed for Adw.Sidebar, GNOME 50+) vs 1.8 (GNOME 49, fall back to GtkListBox.navigation-sidebar as Cartridges does) for Hive/native packaging.
- Gtk.GridView (model-driven, HIG-named) vs Gtk.FlowBox (simpler manual drag-reorder) if reorderable favorites are a day-one requirement.
- The five Blueprint skeletons were hand-checked against the v0.22 grammar and reference apps but NOT compiled (no blueprint-compiler on host; GNOME 51 SDK not installed). Compile inside org.gnome.Sdk//51 before adopting.
- Gtk.UriLauncher (GTK 4.10) and libadwaita named-colors variable names (--success-bg-color etc.) were cited from memory, not re-fetched.
- Exact GTK versions in GNOME 49/50 runtimes (4.20/4.22) inferred from cadence; GtkSearchEntry:search-delay default and GtkGridView:min-columns default not stated on fetched pages.
- AdwSpinnerPaintable usage with AdwStatusPage and the HIG writing-style page were not fetched; the report uses Bazaar's Adw.Spinner loading pattern instead.

Sources (as returned by the agent; full list inside the report):

- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.NavigationSplitView.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.OverlaySplitView.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Sidebar.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.BreakpointBin.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Breakpoint.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/adaptive-layouts.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ViewSwitcher.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.InlineViewSwitcher.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ToggleGroup.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.StatusPage.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Spinner.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Toast.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/property.Toast.timeout.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.PreferencesDialog.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ComboRow.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.SwitchRow.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.EntryRow.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ButtonContent.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Clamp.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.WrapBox.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.AboutDialog.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/ctor.AboutDialog.new_from_appdata.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ShortcutsDialog.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Dialog.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/migrating-to-adaptive-dialogs.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Application.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/style-classes.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/boxed-lists.html
- https://gitlab.gnome.org/GNOME/libadwaita (NEWS, tags 1.8.8/1.9.4/1.10.0)
- https://docs.gtk.org/gtk4/class.GridView.html
- https://docs.gtk.org/gtk4/property.GridView.max-columns.html
- https://docs.gtk.org/gtk4/class.FlowBox.html
- https://docs.gtk.org/gtk4/class.SearchBar.html
- https://docs.gtk.org/gtk4/class.SearchEntry.html
- https://docs.gtk.org/gtk4/class.ShortcutsWindow.html
- https://docs.gtk.org/gtk4/drag-and-drop.html
- https://docs.gtk.org/gtk4/class.DragSource.html
- https://docs.gtk.org/gtk4/class.DropTarget.html
- ... 45 more in the report

### category-badge

Full report: [`category-badge.md`](category-badge.md)

Follow-up research (2026-10-19) on the tile's category badge, the 12 px category glyph on a 20 px circle that sits on a game icon's corner, and on a Preferences switch to hide it. Root cause, from source: `.tile-badge` mixes 18 % of the category colour with `--card-bg-color`, which is opaque white in the light style but `rgb(255 255 255 / 8%)` in the dark style. GTK's `color-mix()` premultiplies alpha, so in dark mode the disc is about 25 % opaque and its 2 px ring 8 % white. The icon shows through, and glyph contrast falls to 1.9-2.9:1 (WCAG 1.4.11 asks 3:1). In light mode contrast is 3.6-5.7:1, but 12 px is off the HIG's 16 px symbolic grid. libadwaita's own small badges (AdwIndicatorBin badge, AdwTabButton attention dot, AdwAvatar below 25 px) are all opaque, with a white or accent-fg glyph on a saturated fill. GNOME Software, Nautilus and Bazaar keep bare 16 px status glyphs off the icon. The accent palette (`--accent-*`) is identical in light and dark and is documented as background colours paired with white. Recommendation (Option A): `pixel-size: 16` on a 24 px opaque `--category-color` disc with a `white` glyph and a 2 px card-coloured ring. The ring is painted as background layers (`image(--card-bg-color)` over `--window-bg-color`, `background-clip: padding-box, border-box`), so it is opaque in both styles. Glyph contrast is 3.01-5.91:1 in light and dark; high contrast uses a neutral disc with a `--card-fg-color` glyph (about 12.5:1). An optional `transform: translate(4px, 4px)` with an RTL mirror (AdwTabButton precedent) reduces overlap with the icon. Alternatives: an opaque tint with libadwaita's standalone colour `oklab(from … var(--standalone-color-oklab))` (4.6-6.8:1), or moving the glyph off the icon next to the category caption. Do not use the `opacity` property: GTK fades the whole widget, glyph included. Preference: GSettings boolean `show-category-badge` (default true), an `Adw.SwitchRow` bound with `DEFAULT`, and each tile binding a GObject property with `Gio.SettingsBindFlags.GET`. GET-only avoids GIO's automatic `sensitive` binding, and the binding keeps the GSettings alive and follows `changed::`. The switch only hides the corner badge; games without an icon keep the glyph in the big square.

Open questions:

- Does GTK 4.24 apply `-gtk-icon-weight` to Dailies' legacy class-based stroked symbolics? This decides whether a 12 px glyph can be kept with heavier strokes.
- Is a 28 px badge (16 px glyph + 4 px disc padding + 2 px ring) acceptable over the 40 px game icon, or should the icon shrink or the badge be offset outward?
- White on the "visual" yellow (`#c88800`) scores exactly 3.01:1; should that category's disc use a darker palette yellow?
- Switch-label capitalisation: the HIG asks for header-capitalised nouns, but Dailies' Preferences rows use sentence case throughout. Settle this app-wide.
- The dark-style numbers assume the grid sits on `--window-bg-color`; recompute if the library moves onto a `.view` background.

Sources (selection; full list inside the report):

- https://docs.gtk.org/gtk4/css-properties.html
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkcsscolor.c#L780-830
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkwidget.c#L12151-12174
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkiconhelper.c#L186-235
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/css-variables.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/style-classes.html
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_view-switcher.scss#L83-124
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/adw-indicator-bin.c#L143-200
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/adw-avatar.c#L756-762
- https://developer.gnome.org/hig/guidelines/ui-icons.html
- https://developer.gnome.org/hig/patterns/controls/switches.html
- https://docs.gtk.org/gio/method.Settings.bind.html
- https://gitlab.gnome.org/GNOME/glib/-/blob/ae8632bab1b5f09f2bb996c9637b1added5b038f/gio/gsettings.c
- https://www.w3.org/TR/WCAG22/#non-text-contrast
- https://gitlab.gnome.org/GNOME/gnome-software/-/blob/b71574d2cbc1eb45df62b08065c72658daadb4cb/src/gs-summary-tile.ui
- https://gitlab.gnome.org/GNOME/nautilus/-/blob/8fd4b29261e641d1e6bdb83cc841837d12aefff6/src/nautilus-grid-cell.c
- https://github.com/bazaar-org/bazaar/blob/3d347d5d0fb828a0ff6ff0c1dcd356b26ddfdd33/src/bz-app-tile.blp
- ... 32 more in the report
