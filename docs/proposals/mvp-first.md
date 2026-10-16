# Dailies — Architecture proposal (angle: MVP-first)

Author: architecture subagent, 2026-10-15. Angle: the smallest coherent architecture that ships a usable Flatpak in
weeks, with a clear path to grow, optimised for a solo maintainer.

Research reports referenced below live in
`docs/research/` and are cited as
`<key>.md §n`. Legend: **[V]** backed by a verified fact in a report (source URL given there or here); **[I]** my
decision/inference; **[U]** the research could not verify this; treat as a risk, not a fact.

---

## 0. Summary

Dailies is a Python 3 + PyGObject + Blueprint + Meson app on `org.gnome.Platform//51`, packaged as
`io.github.tim_van_oudheusden.Dailies`, with **zero third-party Python dependencies at runtime** (HTTP via libsoup 3,
JSON via the standard library, images via GTK). The window is `Adw.NavigationSplitView` + `Adw.Sidebar` (Favorites
pinned first, then weekly Popular/Trending, then ten fixed categories) over a model-driven `Gtk.GridView` of card tiles
with a star toggle; a game opens in a built-in WebKitGTK 6.0 page pushed onto the `Adw.NavigationView` by default, or in
the system browser via the OpenURI portal, with a hidden opt-in "custom command" mode that only works when the user
grants host access themselves. Data is two JSON files in the repository (`data/v1/games.json`,
`data/v1/popularity.json`), bundled into the Flatpak as an offline snapshot and revalidated from GitHub with ETags.
Games enter the catalog through a GitHub Issue Form that a two-stage IssueOps workflow validates and turns into a PR;
popularity is a Monday cron that pulls Tranco ranks, computes shelves deterministically, optionally lets Claude write a
400-word report, and opens a PR. The repository copies MinimalUI's Hive/ACMM scaffolding wholesale (Codebase Level L5
from the first commit), swaps the Gradle gates for Meson/ruff/pytest, and ships `.flatpak` bundles for x86_64 and
aarch64 on every `v*` tag via `flatpak/flatpak-github-actions`.

What is deliberately **not** in the MVP: a GitHub Pages Flatpak remote, drag-reordering favourites, per-game web
sessions, game favicons, Windows/macOS builds, Cloudflare Radar/Wikipedia signals, auto-merge of bot PRs, and anything
that needs `--talk-name=org.freedesktop.Flatpak` in the manifest. Each has a documented slot in the roadmap (§16).

---

## 1. Technology stack and versions

| Layer | Decision | Version / id | Why (and source) |
|---|---|---|---|
| Language | **Python 3 + PyGObject** | PyGObject 3.58.0 in the GNOME 51 SDK; code targets Python ≥ 3.12 (runtime 49 ships 3.13.15; 51 is probably 3.14 **[U]**) | The owner's named UI reference (Cartridges) is Python/Blueprint/Meson; no CPU-bound work; the data scripts in `scripts/` are Python too, so one language for app, tooling and pipeline. `stack-crossplatform.md §3.1` **[V]**, `embedded-browser.md §1.1` for 3.13 **[V]** |
| UI toolkit | **GTK 4.24 + libadwaita 1.10**, Meson floors `gtk4 >= 4.24`, `libadwaita-1 >= 1.10` | GNOME 51 (released 2026-09-16) | Current stable; `Adw.Sidebar` needs ≥ 1.9, `Adw.ShortcutsDialog` ≥ 1.8. `libadwaita-ui-patterns.md §1` **[V]** |
| UI language | **Blueprint** `.blp` → `.ui` via `blueprint-compiler batch-compile --minify` | 0.22.2 bundled in `org.gnome.Sdk//51`; `subprojects/blueprint-compiler.wrap` pinned to `v0.22.2` for native builds | No Flatpak module needed; wrap keeps version parity off-Flatpak. `libadwaita-ui-patterns.md §13`, `stack-crossplatform.md Appendix C` **[V]** |
| Build | **Meson ≥ 1.4** with `gnome`, `python`, `i18n` modules; `profile` combo option (`release`/`development`) | — | Cartridges' pattern: one tree yields both `<id>` and `<id>.Devel`. `cartridges.md §4.1`, `flatpak-release-pipeline.md Appendix B.3` **[V]** |
| Runtime / SDK | **`org.gnome.Platform//51`**, `org.gnome.Sdk//51`, no SDK extensions | Flathub build 51.0-14 (2026-10-14) | Flathub requires the latest runtime at submission; 49 is about to be EOL'd (48 was EOL'd six days after 50 shipped). `flatpak-release-pipeline.md §5` **[V]** |
| HTTP | **libsoup 3 via GI** (`Soup.Session`), conditional GET with `If-None-Match` | in the Platform | Zero pip dependencies, so no `flatpak-pip-generator`, no `python3-requirements.json`, no pypi checker. `stack-crossplatform.md §3.1` **[V]** |
| JSON / schema | stdlib `json`; schema validation only in CI (`check-jsonschema`) | — | The app does a structural sanity check (`schema_version == 1`, required keys), not full JSON Schema, to stay dependency-free **[I]** |
| Built-in browser | **WebKitGTK 6.0** (`WebKit 6.0` typelib) imported lazily behind `try/except`; `HAVE_WEBKIT` flag | WebKitGTK 2.54.1 in Platform 49/50/51 | Already in the runtime; no module to build. `embedded-browser.md §1.1` **[V]** |
| External browser | `Gtk.UriLauncher` (GTK ≥ 4.10) with `Gio.AppInfo.launch_default_for_uri_async` fallback | — | Portal-aware, no finish-args. `embedded-browser.md §3` **[V]** |
| Images | `Gtk.Image` with bundled symbolic category glyphs in MVP; glycin (`GlyGtk4-2`, 2.2.1 in Platform 51) when remote icons arrive | — | GTK docs recommend glycin for untrusted images. `libadwaita-ui-patterns.md §9` **[V]** |
| Code style | **ruff** (check + format), `.editorconfig`, `blueprint-compiler format`, `meson format` | ruff via pre-commit (Cartridges `rewrite` config as base) | `cartridges.md §2.2` **[V]**; `ruff.toml`/`.editorconfig` also satisfy ACMM `prereq-code-style` **[V]** `hive-acmm.md §4` |
| Tests | pytest (+ pytest-cov, Cobertura XML) for pure-Python core and scripts; Meson tests for desktop/metainfo/schema validation; one GTK smoke test under `xvfb-run` | — | `cartridges.md §4.3` for the Meson tests **[V]**; `scaffolding-repos.md §8.4` for Cobertura **[V]** |
| Flatpak CI | `flatpak/flatpak-github-actions/flatpak-builder@v6.8` (`79327416…`) in `ghcr.io/flathub-infra/flatpak-github-actions:gnome-51` | v6.8 2026-08-30; image tag `gnome-51` exists | `flatpak-release-pipeline.md §1.1` **[V]** — note this supersedes the older "only gnome-48 published" statements in `cartridges.md §0.4` and `stack-crossplatform.md §1.6`, which read the deprecated README table |

Rejected for the MVP: Rust/gtk4-rs (compile times, two crate versions to bump, no gain for a data-driven launcher —
`stack-crossplatform.md §2`); C like Bazaar (74k lines of C for a launcher is the wrong tool — `bazaar.md §2`); Vala/GJS
(no verified cross-platform precedent — `stack-crossplatform.md §3.4`). Fallback trigger to Rust: measured cold start in
the Flatpak above ~1 s on a modern laptop, or repeated PyInstaller/MSYS2 breakage if cross-platform is pursued
(`stack-crossplatform.md §3.3`).

---

## 2. Repository layout

Every top-level entry, with its origin. "MU" = copied from `Tim-van-Oudheusden/MinimalUI` (`scaffolding-repos.md`
Appendix B has the verbatim files); "WS" = from `Tim-van-Oudheusden/website`; "new" = written for Dailies.

```text
Dailies/
├── README.md                         new: MU skeleton (§2.1 below)
├── LICENSE                           existing: GPL-3.0
├── AGENTS.md                         MU: authoritative agent rules; gates swapped for Meson/ruff/pytest/flatpak-builder
├── CLAUDE.md                         MU: short companion, "AGENTS.md wins"           [acmm:claude-md]
├── CONTRIBUTING.md                   MU structure; Getting started/Quality gates/Releasing rewritten for Meson + Flatpak
├── SECURITY.md                       MU                                              (GitHub security policy)
├── BRANDING.md                       MU outline; §6 cites the GNOME HIG palette and icon concept
├── meson.build                       new: project('dailies', version: '0.1.0'); profile → app_id/prefix; post_install
├── meson_options.txt                 new: option('profile', combo release|development)
├── pyproject.toml                    new: [tool.ruff], [tool.pytest.ini_options], [tool.coverage]  [acmm:prereq-test-suite]
├── (no ruff.toml)                    ruff config lives in pyproject.toml; pyproject.toml + .editorconfig already satisfy prereq-code-style
├── .editorconfig                     MU base + [*.py] 4, [meson.build] 2, [*.blp] 2, [*.json] 2   [acmm:editor-config]
├── .gitattributes  .gitignore  .git-blame-ignore-revs   MU; .gitignore rewritten for _build/, .flatpak-builder/, repo/, *.flatpak, subprojects/blueprint-compiler
├── .pre-commit-config.yaml           new (from Cartridges rewrite): ruff, ruff-format, blueprint-compiler format, meson format
├── .acmm.yml                         new, empty `waivers: []` placeholder (only filled if claude.yml is ever dropped for Hive agents)
├── .claude/
│   ├── settings.json                 MU/WS deny+ask lists; allow: Bash(meson *), Bash(ninja *), Bash(pytest *), Bash(ruff *),
│   │                                 Bash(flatpak-builder *), Bash(flatpak run *), Bash(blueprint-compiler *)  [acmm:layered-safety, mechanical-enforcement, structural-gates]
│   ├── session-summary.md            MU header, empty                                 [acmm:session-summary, session-continuity]
│   ├── memory/corrections.tsv        MU header only                                   [acmm:correction-capture]
│   └── skills/github-issue-flow/SKILL.md   MU, gate commands swapped                  [acmm:simple-skills]
├── .cursor/rules/agent-guidance.mdc  MU (same body as CLAUDE.md, alwaysApply: true)   [acmm:cursor-rules]
├── .github/
│   ├── copilot-instructions.md       MU (same body as CLAUDE.md)                      [acmm:copilot-instructions]
│   ├── pull_request_template.md      MU, gate commands swapped                        [acmm:prereq-pr-template]
│   ├── ISSUE_TEMPLATE/
│   │   ├── issue.yml                 MU; "Device" input → "Flatpak version and desktop"
│   │   ├── new-game.yml              new: the DLE submission form (§8)               [acmm:prereq-issue-template]
│   │   └── config.yml                new: blank issues on, contact link for broken-link reports
│   ├── dependabot.yml                MU: github-actions weekly (prefix ci) + pip for scripts/requirements.txt (prefix build(deps))
│   ├── labeler.yml                   MU shape; labels app, data, flatpak, ci, documentation   [acmm:auto-label]
│   ├── actionlint.yaml               MU
│   ├── auto-qa-tuning.json           MU shape: {"margin": 2, "floors": {"core": {...}, "scripts": {...}}}   [acmm:auto-qa-tuning, auto-qa-self-tuning]
│   ├── policies/risk-tiers.policy    MU shape; high: .github/**, scripts/**, build-aux/**, meson.build, data/*.metainfo.xml.in,
│   │                                 data/*.gschema.xml.in, data/v1/schema/**, AGENTS.md, CLAUDE.md, .claude/**; medium: dailies/**, data/v1/*.json; low: docs/**, *.md   [acmm:policy-as-code]
│   ├── rulesets/main.json            MU; required checks: PR review rubric, Build, lint, test, Unit-test coverage floors, Static checks
│   ├── release.yml                   new: auto-notes categories (games/catalogue, features, fixes)
│   └── workflows/                    (§11 lists each)                                [acmm:prereq-cicd]
│       ci.yml  coverage-gate.yml  review.yml  pr-metrics.yml  quality-report.yml  tier-classifier.yml  labeler.yml
│       claude.yml  auto-review.yml  nightly-compliance.yml  release.yml  pages.yml
│       game-submission-check.yml  game-submission-approve.yml  popularity.yml  external-data-checker.yml
├── build-aux/
│   ├── flatpak/
│   │   ├── io.github.tim_van_oudheusden.Dailies.Devel.json   new: dir source, -Dprofile=development, run-tests
│   │   ├── io.github.tim_van_oudheusden.Dailies.json         new: git tag+commit source (release / Flathub copy)
│   │   └── lint-exceptions.json                              new: Devel-ID-only linter exceptions
│   └── Justfile or justfile-free `scripts/dev.sh`            new: build-devel, run, bundle, lint (one file; prefer a shell script to avoid a `just` dependency)
├── data/
│   ├── meson.build                   new: configure_file for every .in, blueprints custom_target, gresource, icons, tests
│   ├── io.github.tim_van_oudheusden.Dailies.desktop.in
│   ├── io.github.tim_van_oudheusden.Dailies.metainfo.xml.in
│   ├── io.github.tim_van_oudheusden.Dailies.gschema.xml.in
│   ├── dailies.gresource.xml.in
│   ├── ui/ window.blp  game-tile.blp  browser-page.blp  preferences.blp  shortcuts-dialog.blp  style.css
│   ├── icons/
│   │   ├── hicolor/scalable/apps/<id>.svg, <id>.Devel.svg     new (Concept A, §13)
│   │   ├── hicolor/symbolic/apps/<id>-symbolic.svg
│   │   ├── <id>.Source.svg                                     App Icon Preview project (Bazaar pattern)
│   │   └── categories/*-symbolic.svg                           10 category glyphs + starred/non-starred, bundled in gresource
│   ├── screenshots/1.png … 4.png     added at v0.1.0 (referenced by tag URL)
│   └── v1/
│       ├── games.json                the catalog (seeded from dle-catalog.md Appendix A, ~110 entries after pruning)
│       ├── popularity.json           weekly shelves (first one hand-written with reason: "new")
│       └── schema/catalog.schema.json, popularity.schema.json
├── dailies/                          Python package (§3)
│   ├── meson.build                   python.install_sources + configure_file(config.py.in) + launcher
│   ├── dailies.in                    launcher script → $bindir/dailies
│   ├── __init__.py  __main__.py  application.py  window.py  config.py.in  config.pyi
│   ├── core/   models.py  catalog.py  popularity.py  search.py          (pure Python, no gi; unit-tested anywhere)
│   ├── data/   fetcher.py  favorites.py  store.py                      (gi: Soup, Gio.Settings, GLib)
│   └── ui/     game_object.py  filters.py  tile.py  library.py  browser_page.py  preferences.py  opener.py
├── scripts/
│   ├── pr-review-check.sh (+.test.sh)  tier-classify.sh  pr-metrics.sh  quality-report.sh  auto-qa-tuner.sh
│   ├── nightly-compliance.sh  apply-review-suggestions.sh  coverage-check.sh  lib/coverage.sh (rewritten for Cobertura)
│   ├── acmm-self-check.py            port of hive-acmm.md Appendix C evaluator; vendored criteria list + hive commit hash
│   ├── requirements.txt              pinned with hashes: check-jsonschema, requests, tldextract, Pillow (icons, later)
│   ├── validate_submission.py  add_game.py  check_links.py
│   ├── popularity/ collect.py  compute.py  (narrate.py optional alternative)
│   └── icons/fetch_icon.py           post-MVP
├── tests/
│   ├── core/  test_catalog.py  test_popularity.py  test_search.py
│   ├── scripts/ test_validate_submission.py  test_compute.py  test_check_links.py
│   ├── tooling/ test_workflows.py    MU "tooling" invariants ported to PyYAML (§12)
│   ├── e2e/   test_smoke.py          launches the installed app under dbus-run-session + xvfb-run, waits for the window, quits   [acmm:prereq-e2e]
│   └── data/  test_catalog_file.py   schema + sorted ids + unique URLs + enum membership
├── po/ LINGUAS  POTFILES.in  meson.build                            gettext wired day one, English only
├── prompts/ README.md  code-review.md  pull-request.md               MU                 [acmm:prompts-catalog]
├── docs/
│   ├── architecture.md               this proposal, trimmed; Mermaid diagrams
│   ├── data-format.md                catalog + popularity schema, categories, difficulty rubric, submission rules
│   ├── testing.md  risk-tiers.md     MU, rewritten
│   ├── metrics/README.md             MU + popularity-report metric                     [acmm:public-metrics]
│   ├── reflections/README.md         MU, empty index                                   [acmm:cross-session-knowledge, reflection-log]
│   ├── runbooks/README.md  bad-release.md  popularity.md  re-enable-cron.md             MU shape
│   ├── postmortems/README.md  TEMPLATE.md                                               WS
│   ├── security/SECURITY-AI.md       MU, adapted (§14)                                 [acmm:security-ai-md]
│   └── popularity/YYYY-Www.md        weekly reports written by the pipeline
└── subprojects/blueprint-compiler.wrap
```

**ACMM result of this tree** (checked against the 50 criteria in `hive-acmm.md §4` **[V]**): L0 8/8, L2 8/8, L3 8/8,
L4 9/9, L5 5/5, L6 3/12 → Codebase Level **L5**, identical to the owner's two repos (`hive-acmm.md §8.1`). L6 is not
chased (`hive-acmm.md §9 Phase 5`). `docs/runbooks/` keeps MU's plural spelling deliberately; it does not match the L6
`docs/runbook/` pattern and we do not need it to.

Conventions carried over verbatim (`scaffolding-repos.md §5` **[V]**): Conventional Commits on PR titles (regex in
`scripts/pr-review-check.sh`), one commit per issue `type(scope): summary (#N)`, branches `<type>/<number>-<slug>`,
`Fixes #N` in PR bodies, merge commits only, delete branch on merge, every `uses:` pinned to a 40-hex SHA with a
`# vX.Y.Z` comment, `permissions: contents: read` at top level, `timeout-minutes` on every job, `pull_request_target`
only in `labeler.yml`. No ADRs; decisions are "**Decision:** … Why: …" paragraphs in `docs/architecture.md`.

### 2.1 README

MU skeleton (`scaffolding-repos.md §6` **[V]**): centred banner (`data/icons/.../<id>.svg` at 128 px + H1 "Dailies"),
link row `Download · Add a game · Flathub (later) · buildwithtim.dev`, badges (`ci.yml`, `coverage-gate.yml`,
`v/release?include_prereleases`, `license`, `last-commit`), two screenshots, then Status → About (five bold-led feature
sentences) → Installing ("Pick one": release bundle `flatpak install --user ./Dailies-x86_64.flatpak` with the Flathub
runtime prerequisite spelled out; CI artifact; build from source) → Adding a game (link to the issue form) → Tech stack →
Architecture (two Mermaid diagrams: runtime data flow and the data/release pipelines) → Documentation table →
Contributing ("AI agents follow AGENTS.md") → Acknowledgments (Cartridges, Bazaar, The Dles by aukspot, Tranco) →
Non-affiliation disclaimer (§14) → Contact → Licence table (code GPL-3.0-or-later, metainfo CC0-1.0, catalog data CC0,
popularity data attribution). Link to the owner's other repositories (MinimalUI, website) in Contact as the brief asks.

---

## 3. Application architecture

### 3.1 Modules and responsibilities

```mermaid
flowchart LR
  subgraph bundled["/app/share/dailies/data/v1 (bundled snapshot)"]
    BG[games.json]:::f
    BP[popularity.json]:::f
  end
  subgraph remote["GitHub (raw → Pages)"]
    RG[games.json]:::f
    RP[popularity.json]:::f
  end
  subgraph cache["$XDG_CACHE_HOME/dailies/v1"]
    CG[games.json + .etag + .fetched]:::f
    CP[popularity.json + .etag + .fetched]:::f
  end
  F[data/fetcher.py<br/>Soup 3, If-None-Match] --> cache
  remote --> F
  bundled -. first run / fallback .-> cache
  cache --> C[core/catalog.py<br/>parse, validate, merge status]
  C --> S[data/store.py<br/>Gio.ListStore of GameObject]
  P[core/popularity.py<br/>shelves, ranks] --> S
  FAV[data/favorites.py<br/>GSettings 'favorites' as] --> S
  S --> FL[Gtk.FilterListModel<br/>ui/filters.py: section + search]
  FL --> SO[Gtk.SortListModel]
  SO --> NS[Gtk.NoSelection] --> GV[Gtk.GridView<br/>BuilderListItemFactory → GameTile]
  GV -- activate --> OP[ui/opener.py<br/>in-app | external | custom]
  OP --> WK[ui/browser_page.py<br/>WebKit.WebView]
  OP --> UL[Gtk.UriLauncher → OpenURI portal]
  classDef f fill:#f6f5f4,stroke:#9a9996,color:#241f31
```

| Module | gi? | Responsibility |
|---|---|---|
| `core/models.py` | no | `@dataclass(frozen=True) Game(id, name, url, category, difficulty, description, tags, language, added, status, domain, …)`; `Category` enum of the 10 ids + display names + glyph icon names; `Difficulty` enum. Unknown category → raised at parse time in CI, mapped to `trivia` at runtime so a newer catalog never crashes an older app **[I]**. |
| `core/catalog.py` | no | `parse(bytes) -> Catalog`; structural validation (`schema_version == 1`, required keys, enum membership with tolerant fallback); `is_newer(a, b)` by `generated_at`; filters out `status != "active"` for display but keeps the record so favourites still resolve (`data-pipeline.md §2.3` **[V]**). |
| `core/popularity.py` | no | `parse(bytes) -> Popularity(week, generated_at, valid_until, popular: [id], trending: [id], scores)`; `rank_of(id)`; `is_stale(now)`. |
| `core/search.py` | no | Case- and accent-folded substring match over name, description, tags, category label. |
| `data/fetcher.py` | Soup, Gio, GLib | One `Soup.Session` with `User-Agent: Dailies/<VERSION> (+https://github.com/Tim-van-Oudheusden/Dailies)`; `refresh(name, urls, max_age)` does a conditional GET against the first URL, falls through to the next on 5xx/429/network error, honours `Retry-After`, validates with `core.*.parse` before atomically replacing the cache file; never retries in a loop. Catalog max age 6 h, popularity 24 h (`data-pipeline.md §3.2` **[V]** for cache headers). |
| `data/favorites.py` | Gio | Wraps the `favorites` `as` key: `is_favorite`, `toggle`, `order`; emits `changed(id)`. Order = insertion order (newest last). |
| `data/store.py` | Gio | Owns the `Gio.ListStore(GameObject)`; applies catalog + popularity + favourites; exposes `reload(catalog, popularity)` which diffs by id so the GridView keeps scroll position. |
| `ui/game_object.py` | GObject | `GameObject(GObject.Object)` with properties `game` (boxed dataclass), `favorite: bool`, `popular_rank: int`, `trending_rank: int` so Blueprint bindings and filters work. |
| `ui/filters.py` | Gtk | `SectionFilter(Gtk.Filter)` matching the current sidebar section (`favorites`, `popular`, `trending`, or a category id) and `SearchFilter(Gtk.Filter)`; combined in `Gtk.EveryFilter`. `SectionSorter(Gtk.Sorter)`: Popular/Trending by shelf rank, Favorites by favourite order, categories by name (sort menu can override). Pattern from Cartridges `rewrite` (`cartridges.md §5.3, §7` **[V]**). |
| `ui/tile.py` + `game-tile.blp` | Gtk, Adw | `GameTile(Gtk.Overlay)`: `Gtk.Button.card` (icon, name, category · difficulty caption) + overlaid `Gtk.ToggleButton.circular.osd` star; never button-in-button (`libadwaita-ui-patterns.md §8.2` **[V]**). |
| `ui/library.py` + `window.blp` | Adw | Window, sidebar, grid, search bar, empty states, toasts. |
| `ui/browser_page.py` + `browser-page.blp` | WebKit | In-app browser page (§5). Only imported when `HAVE_WEBKIT`. |
| `ui/opener.py` | Gtk, Gio | Resolves `open-mode` to an action (§5.1). |
| `ui/preferences.py` + `preferences.blp` | Adw | `Adw.PreferencesDialog` (§4.6). |
| `application.py` | Adw | `Adw.Application`; actions `quit`, `preferences`, `about`, `refresh`, `shortcuts` (auto), accelerators; `.devel` CSS class when `PROFILE == "development"`; About via `Adw.AboutDialog.new_from_appdata(PREFIX + "/" + APP_ID + ".metainfo.xml", VERSION)` (`cartridges.md §5.7` **[V]**). |
| `config.py.in` | — | `APP_ID`, `VERSION`, `PREFIX`, `PROFILE`, `PKGDATADIR`, `DATA_URLS` (list), `LOCALEDIR` set by Meson `configure_file`. |

The split "core is pure Python, ui/data touch gi" is the single most important maintenance decision: unit tests for
catalog parsing, popularity maths and search run on a plain `ubuntu-latest` runner with `pip install pytest`, no GNOME
SDK, in seconds; coverage floors apply to `dailies/core` and `scripts/` only **[I]**.

### 3.2 Data flow at startup

1. `Store.load_initial()`: read `$XDG_CACHE_HOME/dailies/v1/games.json`; if missing or unparsable, copy the bundled
   `PKGDATADIR/data/v1/games.json` into the cache. Same for `popularity.json`. The grid is populated before the window
   is shown (tens of KB; no spinner needed except on a cold first run).
2. `Fetcher.refresh_all()` runs after the window maps, in a `Gio.Task`-style async call: for each file, if
   `now - fetched_at > max_age` send a conditional GET; on `304` only bump `fetched_at`; on `200` validate, write
   `*.json`, `*.etag`, `*.fetched`, then `Store.reload()`; on any failure log and keep the old data.
   `Gio.NetworkMonitor` `network-metered` → skip the refresh (Bazaar pattern, `bazaar.md §6.3` **[V]**).
3. Banner rule: an `Adw.Banner` "Showing the game list from <date>" is revealed only when the last successful fetch is
   older than 14 days **and** the app is online (so a fresh install with no network stays quiet) **[I]**. Popular/
   Trending show the subtitle "Week <ISO week>" from `popularity.json`; if `now > valid_until` the subtitle reads
   "Week <ISO week> (as of <date>)" — the shelves are still shown (`data-pipeline.md §7.1` **[V]**).
4. `app.refresh` (primary menu, Ctrl+R on the library page) forces a revalidation and toasts the outcome.

### 3.3 Settings (GSettings)

Schema `io.github.tim_van_oudheusden.Dailies` at `/io/github/tim_van_oudheusden/Dailies/` (path and id are
`@APP_ID@`-templated so the Devel build gets its own). Enum keys are stored as strings; Python reads them with
`get_enum` or `get_string` (`libadwaita-ui-patterns.md §11.1` **[V]**).

```xml
<schemalist gettext-domain="dailies">
  <enum id="@APP_ID@.OpenMode">
    <value nick="in-app"   value="0"/>
    <value nick="external" value="1"/>
    <value nick="custom"   value="2"/>
  </enum>
  <enum id="@APP_ID@.SortMode">
    <value nick="default"    value="0"/>   <!-- shelf rank / favourite order / name -->
    <value nick="name"       value="1"/>
    <value nick="difficulty" value="2"/>
  </enum>
  <schema id="@APP_ID@" path="@PREFIX_PATH@/">
    <key name="favorites" type="as"><default>[]</default>
      <summary>Favourite game ids in display order</summary></key>
    <key name="open-mode" enum="@APP_ID@.OpenMode"><default>'in-app'</default>
      <summary>How games are opened</summary></key>
    <key name="external-browser-command" type="s"><default>''</default>
      <summary>Host command for the custom open mode</summary>
      <description>Run through flatpak-spawn --host with the URL appended. Ignored unless the sandbox has been granted --talk-name=org.freedesktop.Flatpak by the user.</description></key>
    <key name="clear-web-data-on-exit" type="b"><default>false</default></key>
    <key name="sort-mode" enum="@APP_ID@.SortMode"><default>'default'</default></key>
    <key name="show-other-languages" type="b"><default>true</default>
      <summary>Show games whose language differs from the system locale</summary></key>
  </schema>
  <schema id="@APP_ID@.State" path="@PREFIX_PATH@/State/">
    <key name="width" type="i"><default>1100</default></key>
    <key name="height" type="i"><default>760</default></key>
    <key name="is-maximized" type="b"><default>false</default></key>
    <key name="last-section" type="s"><default>'favorites'</default></key>
  </schema>
</schemalist>
```

Deferred keys (post-MVP, from `embedded-browser.md §9.2`): `session-isolation`, `cookie-policy`, `itp-enabled`,
`hardware-acceleration`, `user-agent`, `developer-extras`, and the relocatable per-game schema. They are additive, so
adding them later does not migrate anything.

Window geometry is bound with `Gio.Settings.bind` to `default-width/height/maximized` exactly as Cartridges does
(`cartridges.md §5.1` **[V]**). Favourites live in GSettings rather than a JSON file because the list is small, needs
no schema versioning, survives reinstalls via `~/.var/app/<id>/config/glib-2.0/settings/keyfile` **[I]**, and
Cartridges' `rewrite` proves `as`/`aa{sv}` collections in GSettings work well (`cartridges.md §6.2` **[V]**).

### 3.4 Caching and offline behaviour, summarised

| Item | Location | Policy |
|---|---|---|
| Catalog + popularity | `$XDG_CACHE_HOME/dailies/v1/` (inside Flatpak: `~/.var/app/<id>/cache/dailies/v1/`) | Seeded from bundle; conditional GET every 6 h / 24 h; last-good kept on failure; offline = fully functional |
| Website data (built-in browser) | `$XDG_DATA_HOME/dailies/web/shared/` (+ cache dir) | Persistent `WebKit.NetworkSession` + `cookies.sqlite`; cleared via Preferences or on exit if enabled |
| Favourites, prefs, window state | GSettings | — |
| Game icons | none in MVP | category glyphs from the gresource |

---

## 4. UI structure

All widgets are current libadwaita 1.10 API; the deprecated list in `libadwaita-ui-patterns.md §14` **[V]** is
respected (no `AdwLeaflet`, no `.dim-label`, no `GtkShortcutsWindow`, no `style-dark.css`). Blueprint skeletons for the
window, tile, preferences, browser page and shortcuts dialog exist in `libadwaita-ui-patterns.md` Appendix A — they were
hand-checked against the v0.22 grammar but **not compiled** **[U]**; compiling them inside `org.gnome.Sdk//51` is the
first task of M1.

### 4.1 Window

`Adw.ApplicationWindow` (default 1100×760, `width-request: 360`, `height-request: 294` per HIG adaptive minimum) →
`Adw.ToastOverlay` → `Adw.NavigationView` with two pages:

- **`library`**: `Adw.NavigationSplitView` (`min-sidebar-width: 200`, `max-sidebar-width: 280`,
  `sidebar-width-fraction: 0.22`). `Adw.Breakpoint max-width: 500sp` → `split_view.collapsed: true`,
  `sidebar.mode: page`, `grid_view.max-columns: 2`; `max-width: 900sp` → `grid_view.max-columns: 3`.
- **`browser`**: pushed at runtime when a game opens in-app (§5.2); the header bar gets the back arrow for free.

### 4.2 Sidebar

`Adw.Sidebar` (`libadwaita-ui-patterns.md §2.4` **[V]**) with three sections:

1. Title-less section: **Favorites** (`starred-symbolic`) — always first, as the brief requires; the sidebar
   `selected` defaults to it (restored from `State.last-section`).
2. **This Week**: Popular (`emblem-favorite-symbolic`), Trending (`view-refresh-symbolic` placeholder; replace with a
   bundled `trending-symbolic` from the Icon Development Kit when the icon set is drawn). Subtitle widget shows
   "Week 2026-W42".
3. **Categories**: the ten fixed categories from `dle-catalog.md §2.2` **[V]** — Words, Geography, Music, Movies & TV,
   Video Games, Numbers & Logic, Trivia, Pictures & Colors, Food, Sports — appended at startup from `Category`, each
   with its glyph. Categories with zero active games are hidden.

The primary menu button (`open-menu-symbolic`, `primary: true`, tooltip "Main Menu") sits in the sidebar header bar,
above the list, per HIG (`libadwaita-ui-patterns.md §12` **[V]**); menu: Refresh Game List · — · Preferences, Keyboard
Shortcuts, About Dailies (no Quit). `activated` handler sets the `SectionFilter`, updates the content page title, and
calls `split_view.set_show_content(True)` so a tap navigates when collapsed.

### 4.3 Content: tiles and grid

`Adw.ToolbarView` with a header bar (`[end]` sort `MenuButton`, `[end]` search `ToggleButton`), a `Gtk.SearchBar`
(`key-capture-widget: split_view`, Ctrl+F is the `win.search` app action, Escape closes) and a `Gtk.Stack`
(crossfade) with pages `grid`, `empty-favorites`, `no-results`, `empty-section`:

- `grid`: `Gtk.ScrolledWindow` → `Adw.ClampScrollable` (`maximum-size: 1400`, `tightening-threshold: 1200`) →
  `Gtk.GridView` (`min-columns: 1`, `max-columns: 5`, `single-click-activate: true`, `enable-rubberband: false`)
  with a `BuilderListItemFactory` whose child is `$DailiesGameTile { game: bind template.item as <$DailiesGameObject>; }`.
  CSS reset `#grid > child { padding: 0; background: none; outline: none; box-shadow: none; }` from Cartridges
  `rewrite` (`cartridges.md §5.9` **[V]**).
- `GameTile`: `Gtk.Overlay` whose child is a `Gtk.Button` with `styles ["card", "game-tile"]` containing a 64 px
  category glyph in a rounded square tinted per category (CSS classes `cat-words`, …, using libadwaita colour
  variables so light/dark/HC follow automatically), the game name (`heading`, ellipsised), and a caption
  "Geography · Medium" (`caption`, `dimmed`). The difficulty is also encoded as a small pill (`.difficulty-badge`,
  ~6 lines of CSS with `--success-bg-color` / `--warning-bg-color` / `--error-bg-color`) because the HIG forbids
  colour-only information (`libadwaita-ui-patterns.md §8.4, §12` **[V]**). `[overlay]` top-end: `Gtk.ToggleButton`
  `styles ["circular", "osd"]`, `icon-name` bound to `starred-symbolic`/`non-starred-symbolic`, tooltip
  "Add to Favorites"/"Remove from Favorites", `accessibility { label: _("Favorite"); }`. Visible always (not
  hover-only) so touch and keyboard users can reach it **[I]**. The card has `accessibility { labelled-by: title;
  described-by: caption; }`.
- Activating a tile (click/Enter) calls `opener.open(game)`; toggling the star updates `Favorites`, which emits
  `changed`, the `GameObject.favorite` property flips, the `SectionFilter` is re-evaluated with
  `filter.changed(Gtk.FilterChange.DIFFERENT)`, and a toast "Removed from Favorites — Undo" appears on removal only
  (`cartridges.md §7` **[V]** for the undo-toast pattern).
- Empty states (`Adw.StatusPage`): Favorites → `non-starred-symbolic`, "No Favorites Yet", "Press the star on any game
  to pin it here", pill button "Browse Popular Games" (`win.show-section('popular')`); search → `system-search-symbolic`,
  "No Games Found"; a category with nothing → "Nothing Here Yet", "Suggest a game on GitHub" pill opening the issue form
  externally.

Keyboard: Ctrl+F search, Ctrl+D toggle favourite of the focused tile, Ctrl+R refresh (library) / reload (browser),
Alt+Left/Right history (browser), Ctrl+L focus URL (browser), Ctrl+, preferences, Ctrl+? shortcuts, Ctrl+Q quit, F10
menu — the HIG reference set (`libadwaita-ui-patterns.md §12` **[V]**). `shortcuts-dialog.ui` with id
`shortcuts_dialog` in the gresource makes `app.shortcuts` automatic (`libadwaita-ui-patterns.md §6.2` **[V]**).

### 4.4 Search

`Gtk.SearchEntry` inside an `Adw.Clamp(500)`; `search-changed` sets `SearchFilter.text`; search is global across the
current section (switching to a section keeps the query, HIG "search global across views"). Fuzzy matching is a
roadmap item; MVP is folded substring over name/description/tags/category label.

### 4.5 Favourites behaviour

- Store: ordered `as` list; display order = order added; "Move up/down" context menu and drag-reorder are roadmap items
  (both HIG-required together — `libadwaita-ui-patterns.md §10` **[V]**).
- A favourite whose catalog entry becomes `status: broken|retired` stays in the list but its tile shows a "Unavailable"
  pill and opens a toast with "Remove from Favorites" (`data-pipeline.md §2.3` **[V]** for soft delete).
- No account, no sync, nothing leaves the device.

### 4.6 Preferences (`Adw.PreferencesDialog`, `search-enabled: true`)

One page "General":

- Group **Opening games**: `Adw.ComboRow` "Open games" with `Gtk.StringList` [Built-in browser, Default browser,
  Custom command]; "Built-in browser" entry hidden when `HAVE_WEBKIT` is false; "Custom command" entry hidden unless
  host access was detected (§5.1). `Adw.EntryRow` "Command" (`show-apply-button: true`, monospace) visible only in
  custom mode. A dimmed caption under the group explains: "Games open inside Dailies by default. You can always open the
  current game in your browser from its menu."
- Group **Built-in browser**: `Adw.SwitchRow` "Clear website data on exit"; `Adw.ButtonRow` "Clear website data…"
  (`destructive-action`, confirmation `Adw.AlertDialog`) calling `WebsiteDataManager.clear(ALL, 0)`.
- Group **Catalog**: `Adw.SwitchRow` "Show games in other languages"; `Adw.ActionRow.property` "Last updated" with
  the fetch date and a flat refresh button.

Bindings via `Gio.Settings.bind` for booleans; the combo row's `selected` ↔ enum string mapping is done by hand in
Python (`libadwaita-ui-patterns.md §11.3` **[V]**).

### 4.7 About

`Adw.AboutDialog.new_from_appdata()` reads name, icon, developer, version, URLs, licence and the newest `<release>`
notes from the metainfo bundled in the gresource (`cartridges.md §4.2, §5.7` **[V]**). Add `set_developers`,
`set_designers`, `set_translator_credits(_("translator-credits"))`, and a legal section "Trademarks" carrying the
non-affiliation text (§14).

---

## 5. Link-opening strategy and its settings model

The brief's preference order is "configured browser → built-in browser → external browser". Inside a Flatpak a
*specific* host browser is unreachable without `--talk-name=org.freedesktop.Flatpak`, which flatpak itself documents as
"a sandbox escape allowing arbitrary code execution" and Flathub grants only "on sufficient explanation"
(`embedded-browser.md §4.2` **[V]**: measured `gio mime x-scheme-handler/https` → "No default applications" inside
`org.gnome.Platform//49`). The MVP therefore maps the brief onto what the sandbox can do without that permission:

### 5.1 Resolution order (`ui/opener.py`)

```text
mode = settings.open-mode
if mode == custom and host_access_granted and command != "":
    flatpak-spawn --host <command> <url>           # only works after the user ran:
                                                   # flatpak override --user --talk-name=org.freedesktop.Flatpak <APP_ID>
elif (mode == in-app or mode == custom) and HAVE_WEBKIT:
    push BrowserPage(url)                          # built-in browser
else:
    Gtk.UriLauncher(url).launch(window)            # OpenURI portal → host default browser
    on error: Gio.AppInfo.launch_default_for_uri_async(url)
```

- `host_access_granted` is probed once per session by calling `org.freedesktop.Flatpak.Development` with an invalid
  argument and treating `AccessDenied`/`ServiceUnknown` as "not granted" (`embedded-browser.md §4.3` **[I]**). Outside
  Flatpak (`/.flatpak-info` absent) the custom command runs directly via `Gio.Subprocess`.
- The manifest never requests `--talk-name=org.freedesktop.Flatpak`; the "Custom command" option is simply absent from
  Preferences until the user grants it. `CONTRIBUTING.md`/README explain the `flatpak override` line. This keeps the
  Flathub submission clean and still honours the brief's first preference for power users **[I]**, following the
  recommendation in `embedded-browser.md §9.1`.
- Default is `in-app` because the built-in browser is the differentiator over a bookmark folder, keeps streaks across
  sibling games (shared session), and is what Obsidian-style "web viewer" users expect; "Default browser" is one setting
  away and every game page has "Open in Browser" (Ctrl+Shift+O) in its menu **[I]**.
- The "Ask which app" portal-chooser mode (`OpenURI ask=true` via a direct D-Bus call) is **not** in the MVP; it
  degenerates to "external" for users with one browser (`embedded-browser.md §10.5`).

### 5.2 Built-in browser page (`ui/browser_page.py`)

An `Adw.NavigationPage` (not a dialog) with `Adw.ToolbarView`: header `[start]` Back/Forward (sensitivity bound to
`can-go-back/forward` on `load-changed`), Reload/Stop (bound to `is-loading`), `[title]` `Adw.WindowTitle { title: bind
web_view.title; subtitle: host }`, `[end]` `MenuButton` with Open in Browser · Copy Link · — · Clear Data for This
Site; a 2 px `Gtk.ProgressBar.osd` overlaid at the top bound to `estimated-load-progress` (Tuba pattern,
`embedded-browser.md §7.3` **[V]**).

Session setup (`embedded-browser.md §2.1, §9.4` **[V]** — the cookie line is the one everybody forgets):

```python
session = WebKit.NetworkSession.new(data_dir, cache_dir)        # persistent localStorage/IndexedDB
session.get_cookie_manager().set_persistent_storage(
    f"{data_dir}/cookies.sqlite", WebKit.CookiePersistentStorage.SQLITE)   # REQUIRED for streaks
session.get_cookie_manager().set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)  # NYT login redirects need it
session.set_tls_errors_policy(WebKit.TLSErrorsPolicy.FAIL)
session.connect("download-started", lambda s, d: (d.cancel(), open_external(d.get_request().get_uri())))
settings = WebKit.Settings(javascript_can_open_windows_automatically=False,
                           allow_top_navigation_to_data_urls=False, enable_webrtc=False,
                           enable_back_forward_navigation_gestures=True, enable_smooth_scrolling=True)
settings.set_user_agent_with_application_details("Dailies", VERSION)
```

Behavioural rules: `create` → open externally, return `None`; `decide-policy` `NEW_WINDOW_ACTION` → load in the same
view; `RESPONSE` with unsupported MIME → external; `permission-request` → `deny()`; **no `UserContentManager` scripts or
styles, no ad blocking, no UA spoofing** (ToS, §14); destroy the view (`try_close()`) when the page is popped; one live
`WebView` at a time. One shared session for all games in the MVP (sibling NYT games share a login); per-game isolation
is a roadmap key. Memory footprint is unmeasured **[U]** (`embedded-browser.md §2.7`); M1 includes a `smem` check with
MiniBrowser on a NYT game.

---

## 6. Data model and JSON schemas

Decision: **one catalog file**, `data/v1/games.json`, JSON Schema 2020-12 in `data/v1/schema/catalog.schema.json`,
validated in CI with `check-jsonschema` (`data-pipeline.md §2` **[V]**). Why not one YAML per game (aukspot pattern,
`dle-catalog.md §5.2`): a second format, a build step to concatenate, and nothing the solo maintainer needs at ~100–300
entries; the single file stays under 100 KB and one ETag. Per-entry history is kept as a `history` array inside the
entry instead (aukspot's best idea, `dle-catalog.md §3` **[V]**).

### 6.1 Catalog (`data/v1/games.json`)

Schema = `data-pipeline.md §2.2` with three additions from `dle-catalog.md` Appendix C: `free_no_account` (boolean),
`history` (array of `{date, event, note}`), and the category enum replaced by the ten-value taxonomy (no `other`):

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-15T12:00:00Z",
  "games": [
    {
      "id": "worldle",
      "name": "Worldle",
      "url": "https://worldle.teuteuf.fr/",
      "category": "geography",
      "difficulty": "easy",
      "description": "Identify a country from its silhouette, with distance and direction hints.",
      "tags": ["teuteuf", "countries", "silhouette"],
      "language": "en",
      "free_no_account": true,
      "added": "2026-10-15",
      "status": "active",
      "domain": "teuteuf.fr",
      "wikipedia": "Worldle",
      "source_issue": 12,
      "history": [{ "date": "2026-10-15", "event": "added", "note": "issue #12" }]
    }
  ]
}
```

Rules: `id` matches `^[a-z0-9][a-z0-9-]{1,48}$`, immutable, never reused; `url` must be `https://`; `category` ∈
{words, geography, music, movies-tv, video-games, numbers-logic, trivia, visual, food, sports}; `difficulty` ∈ {easy,
medium, hard}; `status` ∈ {active, broken, retired}; entries are sorted by `id`; apps ignore unknown fields; breaking
changes go to `data/v2/`. Seed: the 116-entry list in `dle-catalog.md` Appendix A **[V]** minus `food-le`, `birdle`
and anything the first link-check run flags; the graveyard (`moviedle.app`, `absurdle.online`, `posterdle.com`,
`cladder.io`, `cloudle.app`, `foodle.io`) becomes link-checker test fixtures. Difficulty is maintainer-curated per the
rubric in `dle-catalog.md §2.4`.

### 6.2 Popularity (`data/v1/popularity.json`)

Exactly the schema in `data-pipeline.md §7.2` **[V]**: `schema_version`, `method_version`, `week` (`2026-W42`),
`generated_at`, `valid_until` (+10 days), `stale`, `popular[]` and `trending[]` of `{id, rank, score, delta?, reason}`,
per-game `scores`, per-source `sources` health, `attribution[]`, `report`. The app only reads `week`, `valid_until`,
`popular`, `trending`. `method_version` lets the app show "methodology changed" if it ever matters.

### 6.3 Favourites (local)

GSettings key `favorites` (`as`), see §3.3. If the owner later wants export/import (aukspot has it), it is a JSON
`{"schema_version": 1, "favorites": [...]}` file written by a menu action — not in MVP.

---

## 7. Contribution pipeline (issue form → validation → PR → merge → publish)

Day one (M0): the form exists and the maintainer edits `games.json` by hand from issues. M2 adds the automation; the
form does not change.

1. **Issue form** `.github/ISSUE_TEMPLATE/new-game.yml` — the copy-ready template in `data-pipeline.md §1.3` **[V]**
   with the category dropdown replaced by the ten labels (no "Other"); fields: Name*, URL* (https), Category*,
   Difficulty*, Description* (min 20 chars), Tags, Language, Checks* ("publishes a new puzzle every day", "no account
   required", "I am not the author, or I consent"). Title `game: <name>`, label `game-submission`. GitHub enforces
   `required` on public repos **[V]**.
2. **Stage A — `game-submission-check.yml`** on `issues: [opened, edited]` filtered by the label; `permissions:
   contents: read, issues: write`; parse with `stefanbuck/github-issue-parser@cb6e9715… # v3.2.5`; run
   `python -I scripts/validate_submission.py` (https only, host resolves to a public IP, HEAD then GET with 10 s
   timeout and ≤ 5 redirects, **final registrable domain must equal the submitted one** — the hijacked-domain lesson
   from `dle-catalog.md §1.4` **[V]** —, title blocklist for gambling keywords, duplicate URL/slug/alias check,
   candidate entry validated against the schema); post one updatable comment via
   `peter-evans/create-or-update-comment@e8674b07… # v5.0.0`; toggle labels `validated` / `needs-changes`. All form
   values reach shell only through `env:` (`data-pipeline.md §1.4` **[V]**).
3. **Stage B — `game-submission-approve.yml`** on `issues: [labeled]` where `label.name == 'approved'` and the sender's
   `author_association` ∈ {OWNER, MEMBER, COLLABORATOR} (same guard as the owner's `claude.yml`); re-runs the validator
   (never trusts stage A), `scripts/add_game.py` inserts the entry sorted by id with `history[0]`, then
   `peter-evans/create-pull-request@5f6978fa… # v8.1.1` opens `data/add-<slug>` with title `data(games): add <name>`,
   body `Closes #N`, labels `data, automated`.
4. **Merge**: human click. PRs opened with `GITHUB_TOKEN` do not trigger `pull_request` workflows **[V]**, so the
   required checks would never appear; the MVP accepts that stage B already validated the entry and the maintainer
   merges with the ruleset's bypass (admin). When volume justifies it, add a fine-grained PAT `DATA_BOT_TOKEN`
   (`contents`, `pull-requests` write) so CI runs and auto-merge becomes possible (`data-pipeline.md §8` open question
   4/5 — decided: PAT later, auto-merge later).
5. **Publish**: `pages.yml` on push to `main` touching `data/v1/**` deploys `data/v1/` to GitHub Pages
   (`actions/upload-pages-artifact@fc324d35… # v5.0.0`, `actions/deploy-pages@368f8252… # v5.0.1`); the app's
   `DATA_URLS` is `["https://tim-van-oudheusden.github.io/Dailies/v1/", "https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/main/data/v1/"]`.
   Pages: `max-age=600` + ETag; raw: `max-age=300` + ETag (`data-pipeline.md §3.1` measured **[V]**). In M1, before
   `pages.yml` exists, the list is just the raw URL — one constant changes in M2.
6. **Link hygiene**: `scripts/check_links.py` runs inside `nightly-compliance.yml` weekly (Sunday) over all active
   entries with the same redirect/blocklist rules; failures are written to the job summary and open one issue
   `data: N broken links (week W)` labelled `data`; the maintainer flips `status` (never deletes) in a PR. Automating
   the status flip is a roadmap item.

Labels to create by hand (Hive creates its own): `game-submission`, `validated`, `needs-changes`, `approved`, `data`,
`automated`, `ai-fix-requested`, `type::*`, `priority::*`, path labels `app`, `data`, `flatpak`, `ci`,
`documentation` (`scaffolding-repos.md §2.4, §8.7` **[V]**).

---

## 8. Popularity pipeline

Design principle from `data-pipeline.md §5.2` **[V]**: **numbers are deterministic Python; Claude writes prose only**.

- **Sources, MVP**: Tranco only — `GET https://tranco-list.eu/api/ranks/domain/{domain}`, no key, 1 req/s, 30 daily
  ranks, covers tiny DLE domains (observed ranks 21k–1.49M for eight sample games, `data-pipeline.md §4.1` **[V]**).
  Wikipedia pageviews (CC0) and HN Algolia are wired as optional collectors behind flags but off by default; Cloudflare
  Radar (token, CC BY-NC 4.0) is roadmap. Tranco's own licence is not stated on its site **[U]** — `attribution[]`
  names it and the maintainer should email them once (`data-pipeline.md §8.8`).
- **Score** (`scripts/popularity/compute.py`, `method_version: 1`): `tranco_score = clamp(1 − (log10(rank) − 2)/4.5,
  0, 1)` on the mean of the last 7 daily ranks; `popularity = tranco_score` while other sources are off; games sharing
  a registrable domain (all `nytimes.com` games) split that domain's contribution equally unless
  `data/v1/domain_weights.json` overrides it (`data-pipeline.md §4.2`; decided: equal split + optional override file).
  `trend = popularity − mean(previous 4 weeks)`, null until two prior weeks exist. *Superseded by #88
  (`method_version: 2`): every game gets its domain's full score, each shelf holds at most 2 games per domain, and
  `domain_weights.json` orders a domain's games instead of splitting its score.*
- **Shelves**: `popular` = top `N = max(5, min(12, 10 % of active))`; `trending` = positive `trend > 0.02` not in the
  top 5 popular, backfilled with the newest `added` games flagged `reason: "new"` so the shelf is never empty
  (`data-pipeline.md §7.1`). Fail closed: if Tranco failed for > 20 % of domains, exit non-zero and leave the old file.
- **Workflow** `popularity.yml` = the skeleton in `data-pipeline.md` Appendix A4 **[V]**: `cron: '17 4 * * 1'` (not
  minute 0; public-repo schedules are disabled after 60 days without activity → `docs/runbooks/re-enable-cron.md`),
  `workflow_dispatch` with a `narrate` boolean; job `compute` (collect → compute → `check-jsonschema` → upload raw
  signals as a 90-day artifact); job `publish` (optional Claude step → guard that only `docs/popularity/*` changed →
  `create-pull-request` on branch `data/popularity`, title `data(popularity): week 2026-W42`, labels `data, automated`).
- **Agentic report**: `anthropics/claude-code-action@a26b07d8… # v1.0.250` in automation mode with
  `claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}` (the owner already uses this token in MinimalUI, so
  it bills the subscription, not API credits), prompt: read `summary.json` + `popularity.json`, write
  `docs/popularity/<week>.md` (overview, Popular/Trending tables, movers, "Data quality"), never change numbers;
  `claude_args: --max-turns 6 --allowedTools "Read,Write" --disallowedTools "Bash,Edit,WebSearch,WebFetch"`;
  `continue-on-error: true`. A `git status` guard fails the job if anything but `docs/popularity/*` changed.
  Prompt-injection surface: the model sees only numbers and maintainer-approved game names — never issue text or fetched
  HTML (`data-pipeline.md §5.2` **[V]**). The narrative step is added in M3; M2 ships numbers-only PRs.
- **Review gate**: PR, human merge, `main` protected. Auto-merge after a month of clean runs is the stated path.
- **Cost**: Actions minutes free (public repo), ~5 min/week; Claude ~20–60k input + 2–4k output tokens per run ≈
  $0.15–0.35/week at `claude-opus-5-5` API prices, roughly $0 extra on the OAuth subscription path; Haiku 5.5 would be
  under a cent (`data-pipeline.md §5.1` **[V]** from the bundled pricing table, cached 2026-10-06 **[U]** for current
  prices).
- **Icons**: none in MVP. Build-time favicon fetch into Pages (`data-pipeline.md §6`) versus never shipping
  third-party icons (`dle-catalog.md §4`) is left as an open decision (§18).

---

## 9. Flatpak manifest and permissions

`build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json` (release / Flathub copy) — `flatpak-release-pipeline.md`
Appendix B.2 **[V]** minus the `python3-requirements.json` module (no pip deps):

```json
{
  "id": "io.github.tim_van_oudheusden.Dailies",
  "runtime": "org.gnome.Platform",
  "runtime-version": "51",
  "sdk": "org.gnome.Sdk",
  "command": "dailies",
  "finish-args": [
    "--share=network",
    "--share=ipc",
    "--socket=fallback-x11",
    "--socket=wayland",
    "--device=dri"
  ],
  "cleanup": ["/include", "/lib/pkgconfig", "/man", "/share/doc", "/share/gtk-doc", "/share/man", "/share/pkgconfig", "*.la", "*.a"],
  "modules": [
    {
      "name": "dailies",
      "buildsystem": "meson",
      "builddir": true,
      "config-opts": ["-Dprofile=release"],
      "sources": [
        {
          "type": "git",
          "url": "https://github.com/Tim-van-Oudheusden/Dailies.git",
          "tag": "v0.1.0",
          "commit": "<40-char sha>",
          "x-checker-data": { "type": "git", "tag-pattern": "^v([\\d.]+)$", "version-scheme": "semantic", "is-main-source": true, "is-important": true }
        }
      ]
    }
  ]
}
```

The `.Devel.json` variant uses `"id": "...Dailies.Devel"`, `"tags": ["devel"]`, `"desktop-file-name-suffix": " (Devel)"`,
`"run-tests": true`, `"config-opts": ["-Dprofile=development"]`, `"sources": [{"type": "dir", "path": "../.."}]`
(Appendix B.1). Permissions justification, one line each for the Flathub PR: network (catalog fetch + web games), ipc +
fallback-x11 (X11 fallback; `finish-args-x11-without-ipc` is never granted), wayland, dri (WebKitGTK ≥ 2.46 renders with
Skia on the GPU and shares DMA-BUFs — `embedded-browser.md §1.4` **[V]**). `--socket=pulseaudio` is **not** requested
in v0.1; add it in the first release after users ask for audio games (Bandle, Heardle Decades), with the metainfo
release note saying so **[I]**. No `--filesystem`, no `--talk-name`. WebKit's own process sandbox uses
`flatpak-spawn --sandbox` through the always-available portal, no extra permission (`embedded-browser.md §1.4` **[V]**).

Manifests are JSON with 2-space indent and an `.editorconfig` entry (Flathub's "4-tab" wording is ambiguous;
Cartridges/Bazaar use 2 spaces — `flatpak-release-pipeline.md §10.6`).

---

## 10. Versioning and release process

- SemVer `MAJOR.MINOR.PATCH`, tags `vX.Y.Z` (MinimalUI and Bazaar convention, `flatpak-release-pipeline.md §7` **[V]**).
  Single source of truth: `project('dailies', version: '0.1.0')` in `meson.build`. Human changelog: the newest
  `<release version="0.1.0" date="2026-11-..">` in the metainfo, with `<description translate="no">`.
- **Release = push a tag.** `release.yml` (`flatpak-release-pipeline.md` Appendix A.2 **[V]**): job `verify` asserts tag
  == meson version == newest metainfo release and the date is not in the future; job `build` runs the release manifest
  for `x86_64` (`ubuntu-latest`) and `aarch64` (`ubuntu-24.04-arm`, free native runner) in the `gnome-51` image with
  `flatpak-builder-lint manifest` before and `flatpak-builder-lint repo repo` after (both Flathub rules, no exceptions
  for the release ID); job `publish` downloads both bundles, writes `SHA256SUMS`, extracts the release notes from the
  metainfo (Cartridges' regex), and publishes with `softprops/action-gh-release@efb35369… # v3.0.3`
  (`generate_release_notes: true` appends PR-based notes from `.github/release.yml`). Assets:
  `Dailies-x86_64.flatpak`, `Dailies-aarch64.flatpak`, `SHA256SUMS`.
- Why tag-push instead of MinimalUI's "push to main touching the version file": a Flatpak release needs the metainfo
  release entry and the tag to exist together, and `v*` tags are what `x-checker-data` and the later Flathub manifest
  consume **[I]**.
- Install instructions (README + release body, `flatpak-release-pipeline.md §2.2` **[V]**):
  `flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo` then
  `flatpak install --user ./Dailies-x86_64.flatpak`. Bundles do not self-update; the README says so and points to the
  Releases feed. A `.flatpakref` + GitHub Pages OSTree remote (signed, `flatter` or the hand-rolled `pages-repo.yml`)
  is roadmap M4, triggered when a third release exists or users ask for updates.
- Pre-releases: `v0.2.0-beta.1` tags set `prerelease: true`; never published to Flathub.
- Flathub: submit after ≥ 3 tagged releases and visible users (inclusion policy: "insufficient development history" and
  "thin wrappers or launchers" are rejection reasons — `flatpak-release-pipeline.md §4.2` **[V]**). The manifest and
  submission PR must be written by the owner, not an AI tool, per Flathub's Generative-AI policy **[V]**. Target the
  latest GNOME runtime at that time; bump `runtime-version` every March/September.

---

## 11. CI/CD

Workflows, with their origin and what they gate. "MU verbatim" files need only the toolchain lines swapped.

| Workflow | Trigger | Jobs / check names | Origin |
|---|---|---|---|
| `ci.yml` | push main, PR, dispatch | **`Build, lint, test`** (ubuntu-latest: `pip install ruff pytest pytest-cov pyyaml check-jsonschema`; `ruff check . && ruff format --check .`; `pytest tests/core tests/scripts tests/tooling tests/data`; `check-jsonschema` on both JSON files); **`Static checks`** (MU verbatim: shellcheck 0.11.0 + actionlint 1.7.12, SHA-256 pinned archives); **`Flatpak (x86_64)`** (gnome-51 container: `flatpak-builder-lint --gha-format --user-exceptions build-aux/flatpak/lint-exceptions.json manifest`, `flatpak-builder@v6.8` with `run-tests: true` → Meson tests incl. `tests/e2e/test_smoke.py` under xvfb, `flatpak-builder-lint repo repo`, Devel bundle artifact). aarch64 only on release to keep PR CI short **[I]** | MU shape + `flatpak-release-pipeline.md` A.1 |
| `coverage-gate.yml` | PR, push main | **`Unit-test coverage floors`**: `pytest --cov=dailies/core --cov=scripts --cov-report=xml`, `scripts/coverage-check.sh` reading Cobertura via rewritten `scripts/lib/coverage.sh`; floors in `.github/auto-qa-tuning.json` | MU, coverage lib rewritten |
| `review.yml` | PR | **`PR review rubric`**: Conventional Commits title, `Fixes #N`; rubric bullets edited: "Looks like libadwaita / follows HIG", "No new finish-args", "Catalog change validated" | MU verbatim + bullets |
| `tier-classifier.yml` | PR | risk tier label from `.github/policies/risk-tiers.policy`, classifier runs from base branch | MU verbatim |
| `labeler.yml` | `pull_request_target` (no checkout) | path labels | MU byte-identical |
| `pr-metrics.yml` | weekly Mon 06:17 | acceptance rate, agent (`claude/*` or `hive-forge-app`) vs human | MU verbatim |
| `quality-report.yml` | weekly | Markdown report to summary + artifact; `auto-qa-tuner.sh` ratchets floors | MU verbatim |
| `auto-review.yml` | `/apply-suggestions` comment | applies suggestion blocks from trusted reviewers | MU verbatim |
| `claude.yml` | `ai-fix-requested` label / `@claude` | `anthropics/claude-code-action@1d6de8cb… # v1.0.248` (bump to v1.0.250 SHA `a26b07d8…`), fork refusal, `--allowedTools "Bash(meson *),Bash(ninja *),Bash(pytest *),Bash(ruff *),Bash(flatpak-builder *),Bash(blueprint-compiler *)"`; toolchain step installs `python3-gi` is **not** needed for core tests; Flatpak builds are left to CI | MU + tools swapped |
| `nightly-compliance.yml` | daily 03:23 | `scripts/nightly-compliance.sh`: Dependabot alerts ≥ high, `pip-audit` on `scripts/requirements.txt`, GNOME runtime EOL check (`flatpak remote-info flathub org.gnome.Platform//51` for an EOL string), `scripts/acmm-self-check.py` (vendored criteria list), weekly (Sun) `scripts/check_links.py` | MU + Dailies rows |
| `release.yml` | tag `v*` | verify → build x86_64 + aarch64 → publish bundles | `flatpak-release-pipeline.md` A.2 |
| `pages.yml` | push main touching `data/v1/**`, dispatch | upload `data/v1/` + `docs/popularity/` as Pages artifact, deploy | new (M2) |
| `game-submission-check.yml` / `game-submission-approve.yml` | issues | §7 | `data-pipeline.md` A2/A3 (M2) |
| `popularity.yml` | Mon 04:17 | §8 | `data-pipeline.md` A4 (M2 numbers, M3 narrative) |
| `external-data-checker.yml` | weekly | `docker://ghcr.io/flathub/flatpak-external-data-checker:latest --update --never-fork --require-important-update build-aux/flatpak/<id>.json` | Bazaar's file, cadence weekly (M3; only useful once the release manifest has `x-checker-data`) |

Shared properties: top-level `permissions: contents: read`, every job `timeout-minutes`, every action SHA-pinned (the
resolved SHAs for 2026-10-15 are in `flatpak-release-pipeline.md` Appendix A and `data-pipeline.md §1.2/§5.1`), no
`${{ github.event.* }}` in `run:`; all of this is pinned by `tests/tooling/test_workflows.py` (§12). Dependabot keeps
the actions current weekly, grouped minor+patch (`flatpak-release-pipeline.md` A.6 **[V]**).

`.Devel` builds: every CI run uploads `io.github.tim_van_oudheusden.Dailies.Devel-x86_64.flatpak` as an artifact; the
window gets the `.devel` striped header bar and the striped icon; Devel is never published anywhere else. Which linter
exceptions the Devel ID needs (probably `appid-url-not-reachable`) is discovered on the first run **[U]**.

Repository settings to flip before applying the ruleset (`scaffolding-repos.md §5, §8.7` **[V]**; Dailies currently
has squash/rebase allowed, no ruleset, no security policy flag): merge commits only, delete branch on merge, CodeQL
default setup (`actions`, `python`), Dependabot alerts + security updates, private vulnerability reporting, Pages source
"GitHub Actions", "Allow GitHub Actions to create and approve pull requests", secrets `CLAUDE_CODE_OAUTH_TOKEN` (later
`DATA_BOT_TOKEN`, `CLOUDFLARE_RADAR_TOKEN`), Claude GitHub App, then `gh api -X POST repos/Tim-van-Oudheusden/Dailies/rulesets
--input .github/rulesets/main.json` after the four check contexts have run once on `main`.

Hive: install/authorise `hive-forge-app` on the repo, add `Dailies` to the spoke's `project.repos` (dashboard Settings →
Repos), "Re-evaluate" in ACMM Eval, expect Codebase L5; run the hive at operational L2–L3 initially (the advisor wants
coverage ≥ 40 % and a 3-green streak before L3) — `hive-acmm.md §6.3, §9` **[V]**. Whether the owner's hive is hosted
or self-hosted is unknown **[U]** but the dashboard path works for both.

---

## 12. Testing strategy

| Layer | What | Where it runs | Gate |
|---|---|---|---|
| Unit (pure Python) | `tests/core/*`: catalog parsing incl. tolerant unknown category/status, popularity parsing + `is_stale`, search folding; `tests/scripts/*`: validator (fixtures incl. the graveyard redirects), `compute.py` with synthetic Tranco data, shared-domain split, fail-closed threshold, link checker | `ubuntu-latest`, plain pytest, seconds | `Build, lint, test`; coverage floors on `dailies/core` + `scripts` (start at 70 % lines, let the tuner ratchet) |
| Data | `tests/data/test_catalog_file.py`: schema, sorted unique ids, unique normalised URLs, every `domain` matches `url`, enum membership, `popularity.json` ids exist in the catalog | same | `Build, lint, test` |
| Tooling | `tests/tooling/test_workflows.py` (PyYAML): top-level permissions map, per-job permissions, `timeout-minutes` everywhere, 40-hex SHA pins with version comments, no `${{ github.event.* }}` in `run:`, `pull_request_target` only in `labeler.yml` without checkout, labeler/policy parity, every `data/v1/*.json` referenced by `pages.yml` | same | `Build, lint, test` |
| Build validation | Meson `test()`s: `desktop-file-validate`, `appstreamcli validate --no-net --explain`, `glib-compile-schemas --strict --dry-run`, `blueprint-compiler compile` of each `.blp` (the Meson custom target already fails the build on syntax errors) | inside `flatpak-builder --run-tests` | `Flatpak (x86_64)` |
| E2E smoke | `tests/e2e/test_smoke.py`: `dbus-run-session xvfb-run -a dailies --quit-after 3` style run (an `--smoke` hidden CLI flag exits after the window maps) and asserts exit 0 + no `CRITICAL` in stderr; registered as a Meson test with `env: GSETTINGS_BACKEND=memory` | inside `flatpak-builder --run-tests` (the action adds xvfb) | `Flatpak (x86_64)`; also satisfies ACMM `prereq-e2e` by directory name |
| Manual before tagging | Checklist in `CONTRIBUTING.md` §Releasing: open 3 games in-app (one NYT), check streak persistence across restart, external open, dark style, 360 px width, screen reader name on tiles | owner | — |

Not tested in MVP: pixel/UI snapshots, WebKit content, Windows/macOS.

---

## 13. Logo and icon direction

Decision: **Concept A "Daily Grid"** from `logo-icon.md §10` **[V]** — a tear-off desk-calendar card whose page is a
guess-feedback tile grid (3×2) — because it ties the *name* (a daily page) and the *purpose* (guessing games) into one
object, survives 32 px, and has a trivial symbolic. Two adjustments **[I]**:

1. The solved row uses **Blue 4 `#1c71d8` / Orange 3 `#ff7800` / Blue 4** and the unsolved row **Light 3 `#deddda`**
   instead of Green 4/Yellow 4. `dle-catalog.md §4` documents NYT's 2024 DMCA campaign asserting trade dress over the
   green/yellow/grey grid; the GNOME-palette green/yellow in the draft is probably fine, but the launcher gains nothing
   from the association and loses a risk by dropping it. The owner can revert to the draft colours in one commit.
2. Keep the 3×2 grid (never 5×6).

Construction follows the draft SVG in `logo-icon.md` Appendix F (square base shape 104×104 at 12..116, rx 8, header
Blue 3, header edge Blue 4, page Light 2, 8 px chin Light 4, rings Dark 2, baseline y 116); symbolic = header bar + 2×3
tiles. Deliverables: `<id>.svg`, `<id>.Devel.svg` (App Icon Preview stripes), `<id>-symbolic.svg`, `<id>.Source.svg`
committed; no `clipPath`/`mask`/filters (KDE Qt renderer, Bazaar PR #895 **[V]**); run `svgo`. Brand colours Blue 1
`#99c1f1` (light) / Blue 5 `#1a5fb4` (dark) in `<branding>`. Category glyphs for tiles come from the Icon Development Kit
(CC0) where available, else drawn at 16 px with 2 px strokes. Screenshots: 4 shots at ~960×640 on a default GNOME
session, light first, one dark, referenced by **tag** URL after v0.1.0 (`logo-icon.md §9` **[V]**). Metainfo fragment:
`logo-icon.md` Appendix G.

---

## 14. Security and privacy

- **No accounts, no telemetry, nothing leaves the device** except: conditional GETs to GitHub for the two JSON files
  (descriptive User-Agent, no identifiers) and the game pages the user opens. State: `docs/security/SECURITY-AI.md`
  and README.
- **Sandbox**: five finish-args (§9); no filesystem, no D-Bus names, no `flatpak-spawn --host` permission in the
  manifest. The custom-command mode is inert unless the user grants it with `flatpak override` and is documented as a
  sandbox escape they choose.
- **Built-in browser**: persistent cookies and storage live under `~/.var/app/<id>/data/dailies/web/`, like a browser
  profile; Preferences offers "Clear website data" and "Clear on exit"; downloads are cancelled and handed to the
  external browser (no `--filesystem=xdg-download`); `permission-request` denied; WebRTC off; `data:` top-navigation
  off; TLS errors fail; the real URL is always shown; **no content scripts, no ad blocking, no UA spoofing** so the app
  never "modifies" or "frames" a publisher's content (NYT ToS §2.2 effective 2026-01-20, `embedded-browser.md §7.1`,
  `dle-catalog.md §3.1` **[V]**; whether a top-level WebView is acceptable to publishers is a legal judgement
  **[U]** — the design keeps "Open in Browser" one click away as mitigation).
- **Trademarks**: the catalog only links (nominative use); no third-party logos in the repo or Flatpak in MVP; About and
  README carry: "Dailies is not affiliated with The New York Times, Merriam-Webster, LinkedIn or any game listed. Game
  names are trademarks of their owners; Dailies only opens their public websites." Icon avoids Wordle trade dress (§13).
- **Supply chain**: every action SHA-pinned, Dependabot weekly, Static checks job, `--require-hashes` for
  `scripts/requirements.txt`, no pip in the Flatpak, CodeQL on `python` + `actions`, `SECURITY.md` with private
  vulnerability reporting.
- **IssueOps**: stage A runs with `contents: read`; form values only via `env:`; validator refuses private/loopback
  hosts after DNS resolution (SSRF bound), caps redirects, requires the final registrable domain to match (stops the
  hijacked-domain class of attack from entering the catalog); stage B re-validates and requires an OWNER/MEMBER/
  COLLABORATOR to apply `approved`.
- **Agents**: `claude.yml` refuses fork PRs and only trusted roles trigger it; the popularity narrative sees numbers
  only and a guard reverts any file outside `docs/popularity/`; `SECURITY-AI.md` names Hive agents, bot issues and DLE
  URLs as data-not-instructions and forbids agents from widening `finish-args`, editing `data/v1/schema/**`, or touching
  `.github/workflows/**` without the `high` tier review (`hive-acmm.md §9 Phase 3` **[V]** for the adaptation list).
- **Risk tiers**: `high` = workflows, scripts, manifests, `meson.build`, metainfo, gschema, schemas, agent instruction
  files; `medium` = app code and catalog data; `low` = docs.

---

## 15. Cross-platform position

Flatpak is the only supported channel for the MVP and the foreseeable roadmap. The architecture keeps the door open at
zero cost: `dailies/core` is pure Python; WebKit is optional (`HAVE_WEBKIT`), and the UI hides the built-in option
when it is absent; no `flatpak-spawn` dependency; Blueprint/Meson build identically on MSYS2 and Homebrew. The verified
facts (`stack-crossplatform.md §1.3–1.4` **[V]**): libadwaita 1.10 and PyGObject 3.58 are packaged in MSYS2 and
Homebrew; Cartridges shipped Windows (MSYS2 UCRT64 + Inno Setup) and macOS (Homebrew + PyInstaller) from one
`meson.build`, and those CI jobs are reproduced in `stack-crossplatform.md` Appendix A; **WebKitGTK does not exist on
Windows** (no port since 2.4/2014, no MSYS2 package, Homebrew formula Linux-only), so the built-in browser is
Linux-only in every language. Windows CSD problems may be fixed in GTK 4.24 but no post-4.24 report confirms it
**[U]**; Cartero's `-Ddecorations=no-csd` is the fallback. Decision: an experimental `windows` CI job
(`continue-on-error: true`, artifact labelled experimental) is roadmap M5, only after Flathub; macOS after that;
neither gets a GitHub Release asset until someone tests it.

---

## 16. Roadmap

Weeks are calendar weeks of part-time solo work; each milestone ends in something installable.

| Milestone | Target | Deliverables | Exit criterion |
|---|---|---|---|
| **M0 Scaffold** | week 1 | Copy MU layer (§2), swap gates, `pyproject.toml`, `tests/` skeleton with one passing test per directory, `.github/workflows/*` (ci, coverage-gate, review, tier-classifier, labeler, pr-metrics, quality-report, auto-review, claude, nightly-compliance), repo settings + ruleset, Hive registration, `new-game.yml` form, `games.json` seed + schema + data tests, Meson skeleton that builds an empty `Adw.ApplicationWindow` in the Devel Flatpak, icon draft (§13), Blueprint skeletons compiled in the SDK | ACMM Eval shows L5; `Flatpak (x86_64)` green; `flatpak run <id>.Devel` opens a window |
| **M1 Usable launcher → v0.1.0** | weeks 2–3 | Sidebar with Favorites/Popular/Trending/categories, GridView tiles with star, search, favourites in GSettings, bundled snapshot + raw.githubusercontent fetch with ETag, in-app WebKit page with persistent session, external open via portal, Preferences (open mode, clear data), About, Shortcuts, e2e smoke test, hand-written first `popularity.json` (`reason: "new"`), `release.yml`, metainfo with branding + OARS + 4 screenshots, README | Tag `v0.1.0`; GitHub Release with `Dailies-x86_64.flatpak` + `Dailies-aarch64.flatpak` + `SHA256SUMS`; `flatpak-builder-lint repo` clean for the release ID; WebKit memory measured and noted in `docs/architecture.md` |
| **M2 Data pipeline → v0.2.0** | weeks 4–5 | `pages.yml` + Pages as primary `DATA_URLS`; stage A/B submission workflows; `check_links.py` in nightly; `popularity.yml` numbers-only (Tranco), first automated PR merged; custom-command open mode with host-access probe; "Show games in other languages" filter | Two games added via the form end-to-end; one Monday run merged; v0.2.0 tagged |
| **M3 Agentic report & hygiene → v0.3.0** | weeks 6–8 | Claude narrative step + guard; `docs/popularity/` reports; `external-data-checker.yml`; runbooks (bad release, re-enable cron, popularity); `docs/metrics/README.md` popularity metric; undo toasts polish; optional `--socket=pulseaudio` decision; `.flatpakref`-ready release manifest | Three tagged releases exist; `nightly-compliance` green for 2 weeks |
| **M4 Distribution** | weeks 9–12 | Flathub submission PR (human-written manifest), or, if rejected as a "launcher", the GitHub Pages OSTree remote (`pages-repo.yml`, GPG-signed) so bundles self-update; `.flatpakref` on Releases | App installable from Flathub **or** `flatpak install --user https://tim-van-oudheusden.github.io/Dailies/<id>.flatpakref` |
| **M5 Growth** | later | Per-game session isolation + cookie policy keys; favourite reorder (drag + Move up/down); "Done today" marker; game favicons (decision §18); Wikipedia/Radar signals; auto-merge of data PRs with `DATA_BOT_TOKEN`; export/import favourites; experimental Windows job; translations via Weblate | — |

---

## 17. Risks and mitigations

| # | Risk | Likelihood / impact | Mitigation |
|---|---|---|---|
| 1 | **Flathub rejects Dailies as a "thin wrapper or launcher" / "simple web wrapper"** (`flatpak-release-pipeline.md §4.2` **[V]**; reviewer judgement **[U]**) | medium / high for discoverability | Ship native value first (favourites, categories, weekly shelves, search, offline catalog, HIG UI); submit only after ≥ 3 releases; M4 has the Pages remote as the fallback distribution so the project does not depend on Flathub |
| 2 | **Publisher ToS (NYT "framing and inline linking")** | low–medium / medium | Top-level WebView, no injection/ad-block/UA spoof, real URL shown, "Open in Browser" always present, "Default browser" one setting away, disclaimer; revisit default if a publisher objects |
| 3 | **Hijacked/dead domains redirecting to gambling sites** (recurring in the genre, `dle-catalog.md §1.4` **[V]**) | high / medium (reputation) | Final-domain-must-match rule in validator and weekly link checker; `status: broken` soft delete; graveyard fixtures in tests |
| 4 | **WebKitGTK memory per open game unmeasured** **[U]** | medium / medium on low-RAM machines | One live WebView at a time, destroyed on pop, `CacheModel.DOCUMENT_VIEWER`; measure in M1 and record |
| 5 | **GNOME runtime EOL cadence (~1 year; 49 EOL imminent)** | certain / low | `runtime-version` bump every March/September; nightly EOL check row; Flatpak users unaffected by distro versions |
| 6 | **Scheduled workflows disabled after 60 days of inactivity** (`data-pipeline.md §5.1` **[V]**) | medium / low | Dependabot and submissions count as activity; `docs/runbooks/re-enable-cron.md`; `valid_until` +10 days keeps shelves "fresh" in the app |
| 7 | **Blueprint skeletons were not compiled; `AdwSidebar` API in Python not exercised** **[U]** | medium / low | First task of M1 is compiling in the SDK; fallback to `GtkListBox.navigation-sidebar` (Cartridges `main`) if `AdwSidebar` misbehaves |
| 8 | **Python startup time in Flatpak** (no public benchmark **[U]**) | low / medium | Lazy `WebKit` import, no pip deps, measure with `hyperfine` in M1; Rust port is the documented fallback trigger (>~1 s) |
| 9 | **Tranco licence unstated; Radar is CC BY-NC** **[U]** | low / low | Attribution in README and `popularity.json`; email Tranco; Radar off by default |
| 10 | **Single maintainer bus factor and scaffold weight** (17 workflows) | medium / medium | All MU workflows are copy-verbatim and self-contained; invariants pinned by tests; Hive at L2–L3 does triage; `AGENTS.md` lets Claude Code pick up `ai-fix-requested` issues |
| 11 | **Cartridges is unmaintained and its `rewrite` branch is partly non-functional** (`cartridges.md §0` **[V]**) | certain / low | Copy patterns, not code; the stack itself (PyGObject, Blueprint, Meson, Flatpak) is maintained upstream |
| 12 | **PRs opened with `GITHUB_TOKEN` show no checks** | certain / low | Stage B validates before opening; `DATA_BOT_TOKEN` in M5 if volume grows |
| 13 | **Devel ID linter exceptions unknown until first run** **[U]** | certain / trivial | `lint-exceptions.json` applies to the Devel ID only; release ID stays exception-free |
| 14 | **Fan-made IP games churn (takedowns)** | high / low | `fan-made` tag; link checker flips status; favourites degrade gracefully |

---

## 18. Open decisions for the owner

1. **Icon colours**: keep the draft's Green 4/Yellow 4 solved row (closer to the genre's visual language) or the
   Blue/Orange variant proposed in §13 (avoids Wordle trade dress). Default here: Blue/Orange.
2. **Default open mode**: `in-app` (proposed) vs `external`. `dle-catalog.md §5.7` argued for external-by-default on
   ToS grounds; `embedded-browser.md §9.5` for in-app. Proposed: in-app with a first-run banner.
3. **Game icons**: (a) none (category glyphs, MVP), (b) build-time favicons published via Pages with a takedown note
   (`data-pipeline.md §6`), (c) runtime favicon fetch from the game's own domain, cached locally, never redistributed
   (`dle-catalog.md §4`), which leaks the user's catalog view to every game host. Proposed order: (a) now, decide (b)
   vs (c) at M5 after asking on the issue tracker.
4. **Audio**: request `--socket=pulseaudio` in v0.1 (music games work in-app) or wait for user demand. Proposed: wait.
5. **Catalog breadth**: seed with the curated ~110 (proposed) or import aukspot's 785 active entries wholesale
   (GPL-3.0-compatible, `dle-catalog.md §5.10`). Proposed: curated seed, credit aukspot.
6. **Fan-made IP games** (Pokédle, LoLdle, …): include by default with a `fan-made` tag (proposed) or hide behind a
   filter.
7. **Shared-domain weighting**: equal split (proposed) vs a hand-maintained `domain_weights.json` from day one.
8. **Narrative model/path**: `claude-code-action` with the existing `CLAUDE_CODE_OAUTH_TOKEN` (proposed; no API bill) vs
   a 30-line SDK script with `ANTHROPIC_API_KEY` on Haiku 5.5.
9. **Hive**: configure `project.checkouts_dir` on the spoke so `AGENTS.md` is actually injected into Hive agent prompts
   (`hive-acmm.md §6.3` **[V]**), and keep or drop Beads (`.beads/`, not an ACMM criterion). Proposed: configure
   checkouts; skip Beads unless the owner uses it daily.
10. **Versioning trigger**: tag-push release (proposed) vs MinimalUI's push-to-main-on-version-change.
11. **Dutch locale default**: should `show-other-languages` default to false for non-matching locales? Proposed: true
    (show everything) until translations exist.

---

## 19. What the research did not verify (consolidated)

Python version in runtime 51 (likely 3.14); `ghcr.io/flathub-infra/flatpak-github-actions:gnome-51` was verified in
`flatpak-release-pipeline.md` but two other reports said otherwise from older sources — trust the direct README read;
WebKitGTK memory footprint; WebKit `hardware-acceleration-policy`/ITP defaults; GNOME 49 exact EOL date; whether
Flathub reviewers accept a launcher; NYT Spelling Bee/Mini free limits; LinkedIn games without account; WaPo Keyword
liveness; Tranco licence; Cloudflare Radar per-domain query parameters; Blueprint skeletons compile; `AdwSidebar`
Python usage; Windows GTK 4.24 CSD status; `flatter` inside the gnome-51 image; `andyholmes/flatter` vs hand-rolled
Pages repo untested; Devel-ID linter exceptions; hosted vs self-hosted hive; Hive Forge App installation scope;
`acmm_criteria.go` says 43 while holding 50 entries (code used); Anthropic prices cached 2026-10-06.
