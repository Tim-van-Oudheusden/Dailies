# Plan: finish the Design and Judge phases

Status: Research phase complete (11/11 reports in [`docs/research/`](../research/README.md)). The Design phase was interrupted by an account usage limit on 2026-10-15 after one proposal (`mvp-first`) had been written to disk but before it was returned; the other two proposals and the Judge phase never ran. This document records what remains so the work can be resumed in a later session.

## Inputs already in the repository

- [`docs/BRIEF.md`](../BRIEF.md) — requirements.
- [`docs/research/README.md`](../research/README.md) — digest of all 11 reports (summary, open questions, sources) plus the full reports beside it.
- [`docs/proposals/mvp-first.md`](../proposals/mvp-first.md) — complete first-draft proposal for the MVP-first angle (about 9,700 words). It was never returned through the workflow's structured output, so it has not been judged. Treat it as a valid proposal; do not regenerate it unless a judge finds it defective.

## Remaining phases

### Phase 2 — Design (two proposals still to write)

Each proposal is one markdown file in `docs/proposals/<angle>.md`, written by an architect agent that reads the brief, the research digest and the full reports. Required coverage (same checklist for all three so the judges can compare like with like):

technology stack and versions; repository layout including the Hive ACMM scaffolding mirrored from MinimalUI; app architecture (modules, data flow, state, GSettings keys, caching, offline behaviour); UI structure (window, sidebar with Favorites pinned first and weekly Popular/Trending, tiles, favorites, search, preferences, about, in-app browser); link-opening strategy and its settings model; data model and JSON schemas (catalog, popularity, local favorites); contribution pipeline (issue form → validation → PR → merge → publish); popularity pipeline (sources, weekly Action, agentic report, review gate, cost); Flatpak manifest and permissions; CI/CD (build, lint, flatpak-builder-lint, release bundles, optional GitHub Pages remote, Flathub path, `.Devel` builds); versioning and release process; logo/icon direction; testing strategy; security and privacy; cross-platform position; roadmap (M0..Mn) with risks and mitigations; open decisions. Decisions, not option lists; every claim cites a research report and, where possible, a source URL; unverified claims are flagged.

Angles:

| Angle | File | Brief for the architect | State |
|---|---|---|---|
| MVP-first | `proposals/mvp-first.md` | Smallest coherent architecture that ships a usable Flatpak in weeks; low maintenance for a solo maintainer. | written |
| Cross-platform-first | `proposals/crossplatform-first.md` | Take "if possible also cross-platform" seriously: stack, browser-opening abstraction and packaging that keep Windows/macOS viable without compromising the Flatpak/Libadwaita experience. Be honest about where it is infeasible (WebKitGTK is Linux-only). | to do |
| Community/data-first | `proposals/community-data-first.md` | Optimise the contribution loop (issue-driven catalog, popularity pipeline, agentic weekly report, Hive ACMM compliance, docs) and data integrity, moderation, trust (no accounts, privacy). The app is a thin, robust client of a well-designed data pipeline. | to do |

### Phase 3 — Judge (three lenses, all proposals)

Three judge agents each read all three proposals and the research reports, score each proposal 1–10 under their lens with specific strengths, weaknesses and quoted factual errors, name a winner, and list `must_graft` ideas from the losers and `must_fix` items for the winner. Scores are summed across lenses; the top proposal becomes the base for the architecture document.

| Lens | Question |
|---|---|
| Feasibility and correctness | Is every technical claim true per the research? Will it build and run as a Flatpak? Does the browser-opening strategy work inside the sandbox and pass Flathub review? |
| Product and UX | Does it deliver the stated features (categories, Favorites always first, weekly Popular/Trending, favorite button, no accounts, configurable browser chain, Libadwaita look like Cartridges/Bazaar)? Is it HIG-compliant and coherent? |
| Maintainability, community, compliance | Hive ACMM compliance, mirrored scaffolding, contribution pipeline quality, popularity pipeline robustness and cost, release/Flathub path, solo-maintainer sustainability, cross-platform honesty. |

Judge output is saved to `docs/proposals/judgments.md` (scores table, winner, must-graft, must-fix).

### Phase 4 — Draft `docs/ARCHITECTURE.md`

One synthesis agent writes the final architecture/design document from the winning proposal, grafting the `must_graft` items and fixing the `must_fix` items. Then three adversarial verifiers (one per lens above) try to refute concrete claims against the research reports and primary sources; a revision agent applies confirmed corrections. Open decisions that need the owner go into a final "Decisions needed" section.

## How to resume

Option A — same Claude Code session still alive (cached research reused):

```
Workflow({
  scriptPath: "/home/tim/.claude/projects/-home-tim-Git-Dailies/2182a9c5-78fc-417e-b7f0-b30226f216ef/workflows/scripts/dailies-research-design-wf_4c21ce75-982.js",
  resumeFromRunId: "wf_4c21ce75-982",
  args: { scratch: "<scratchpad dir>", brief: "<contents of docs/BRIEF.md>" }
})
```

The 11 research agents return from cache; `design:mvp-first` will be re-run because it failed before returning (its file on disk is already saved here, so that re-run is wasted but harmless).

Option B — any new session (recommended; reads inputs from this repository, no research re-run):

```
Workflow({ scriptPath: "docs/plans/dailies-design-judge.workflow.js", args: { repo: "/home/tim/Git/Dailies" } })
```

The script in [`dailies-design-judge.workflow.js`](dailies-design-judge.workflow.js) skips any angle whose proposal file already exists, writes the missing proposals, runs the three judges, and writes `docs/proposals/judgments.md`. After reading the judgments, run the Phase 4 drafting/verification step (described above; script to be authored at that point from the judge output).

## Decisions the owner should make before or during Phase 4

Collected from the research open questions. None blocks the Design/Judge phases.

1. Flatpak app ID `io.github.tim_van_oudheusden.Dailies` (hyphens become underscores per Flathub rules). Icon file names and GSettings schema derive from it.
2. Whether a "configured specific browser" mode is offered at all. Inside the sandbox it needs `--talk-name=org.freedesktop.Flatpak` (a documented sandbox escape); the research recommends not requesting it in the manifest and supporting it only when the user grants it via `flatpak override`.
3. Default open mode: in-app WebKitGTK view versus external browser, given the NYT terms of service wording on framing.
4. Popularity signal set for v1: Tranco only, or Tranco plus Cloudflare Radar (needs an account and token) plus Wikipedia pageviews.
5. Narrative report step: `anthropics/claude-code-action` with the existing OAuth token, or a small SDK script; which model tier.
6. Whether to import the aukspot/dles directory (GPL-3.0) wholesale or seed only the curated 116 games; whether fan-made IP games are included by default.
7. Icon concept A (calendar card with guess-feedback grid) or B (sunrise over a board).
8. Whether Windows/macOS builds are in scope for v1 or deferred (the built-in browser can never work there).
9. Whether Dailies is enrolled in the owner's existing hive via `hive.yaml project.repos` or the hosted hub.
