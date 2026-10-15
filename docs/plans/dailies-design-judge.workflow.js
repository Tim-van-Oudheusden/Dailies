// Standalone Workflow script: Design + Judge phases for the Dailies architecture.
// Reads all inputs from the repository (docs/BRIEF.md, docs/research/, docs/proposals/)
// so it can run in a fresh session without repeating the Research phase.
// Usage: Workflow({ scriptPath: "docs/plans/dailies-design-judge.workflow.js", args: { repo: "/abs/path/to/Dailies" } })
export const meta = {
  name: 'dailies-design-judge',
  description: 'Write the missing architecture proposals for Dailies from docs/research, then judge all proposals on three lenses',
  phases: [
    { title: 'Design', detail: 'one architect per missing angle, writes docs/proposals/<angle>.md' },
    { title: 'Judge', detail: 'three lenses score all proposals, write docs/proposals/judgments.md' },
  ],
}

const REPO = (args && args.repo) || '/home/tim/Git/Dailies'
const BRIEF = `${REPO}/docs/BRIEF.md`
const DIGEST = `${REPO}/docs/research/README.md`
const RESEARCH = `${REPO}/docs/research`
const PROPOSALS = `${REPO}/docs/proposals`

const COVERAGE = `technology stack & versions; repository layout (every top-level dir/file, incl. Hive ACMM scaffolding mirrored from the owner's MinimalUI repo); app architecture (modules, data flow, state, GSettings keys, caching, offline behaviour); UI structure (window, sidebar with Favorites pinned first and weekly Popular/Trending, tiles, favorites, search, preferences, about, in-app browser); link-opening strategy and its settings model; data model + JSON schemas (catalog, popularity, local favorites); contribution pipeline (issue form -> validation -> PR -> merge -> publish); popularity pipeline (sources, weekly GitHub Action, agentic report composition, review gate, cost); Flatpak manifest & permissions; CI/CD (build, lint, flatpak-builder-lint, release bundles, optional GitHub Pages remote, Flathub path, .Devel builds); versioning/release process; logo/icon direction; testing strategy; security/privacy; cross-platform position; roadmap (M0..Mn) with risks and mitigations; open decisions. Prefer decisions over option lists. Cite the research report file (and source URL where the report gives one) for every claim; flag anything the research did not verify.`

const ANGLES = [
  { key: 'mvp-first', desc: 'MVP-first: the smallest coherent architecture that ships a usable Flatpak in weeks, with a clear path to grow. Optimize for low maintenance burden for a solo maintainer.' },
  { key: 'crossplatform-first', desc: 'Cross-platform-first: take the "if possible also cross-platform" goal seriously; choose a stack and abstractions (browser-opening strategy, packaging) that keep Windows/macOS viable without compromising the Flatpak/Libadwaita-native experience. Be honest about where it is not feasible (WebKitGTK is Linux-only).' },
  { key: 'community-data-first', desc: 'Community/data-first: optimize for the open-source contribution loop (issue-driven catalog, popularity pipeline, agentic weekly reports, Hive ACMM compliance, docs) and for data integrity, moderation, and trust (no accounts, privacy). The app is a thin, robust client of a well-designed data pipeline.' },
]

const EXISTS_SCHEMA = { type: 'object', properties: { existing: { type: 'array', items: { type: 'string' } } }, required: ['existing'] }
const PROPOSAL_SCHEMA = {
  type: 'object',
  properties: {
    angle: { type: 'string' },
    proposal_path: { type: 'string' },
    one_paragraph: { type: 'string' },
    key_decisions: { type: 'array', items: { type: 'object', properties: { decision: { type: 'string' }, choice: { type: 'string' }, rationale: { type: 'string' } }, required: ['decision', 'choice', 'rationale'] } },
    risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['angle', 'proposal_path', 'one_paragraph', 'key_decisions', 'risks'],
}
const SCORE_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    scores: { type: 'array', items: { type: 'object', properties: { angle: { type: 'string' }, score: { type: 'number' }, strengths: { type: 'array', items: { type: 'string' } }, weaknesses: { type: 'array', items: { type: 'string' } }, factual_errors: { type: 'array', items: { type: 'string' } } }, required: ['angle', 'score', 'strengths', 'weaknesses', 'factual_errors'] } },
    winner: { type: 'string' },
    must_graft: { type: 'array', items: { type: 'string' } },
    must_fix: { type: 'array', items: { type: 'string' } },
  },
  required: ['lens', 'scores', 'winner', 'must_graft', 'must_fix'],
}

phase('Design')
const probe = await agent(`List which of these files exist and have more than 2000 words: ${ANGLES.map(a => `${PROPOSALS}/${a.key}.md`).join(', ')}. Use Bash (wc -w). Return existing = the angle keys (file basenames without .md) that qualify.`, { label: 'design:probe', phase: 'Design', schema: EXISTS_SCHEMA, effort: 'low' })
const existing = new Set((probe && probe.existing) || [])
const missing = ANGLES.filter(a => !existing.has(a.key))
log(`Design: ${existing.size} proposal(s) already on disk, writing ${missing.length}`)

const written = (await parallel(missing.map(a => () => agent(`You are a senior software architect producing ONE complete architecture proposal for "Dailies".

Read first, with Bash cat: the brief ${BRIEF}; the research digest ${DIGEST}; then every full report in ${RESEARCH}/*.md that your proposal depends on (they contain verified details, reproduced files and sources).

Your assigned angle: ${a.desc}

Write the proposal as markdown to ${PROPOSALS}/${a.key}.md. It must cover, concretely and with rationale: ${COVERAGE}

Mark each claim [V] verified in a report (name the report), [I] your inference/decision, or [U] unverified.

Return structured output: angle="${a.key}", proposal_path, one_paragraph summary, key_decisions, risks.`, { label: `design:${a.key}`, phase: 'Design', schema: PROPOSAL_SCHEMA })))).filter(Boolean)

const proposals = ANGLES.map(a => ({ angle: a.key, proposal_path: `${PROPOSALS}/${a.key}.md` }))

phase('Judge')
const LENSES = [
  'feasibility & correctness: is every technical claim true per the research reports (verify by reading them and, where needed, primary sources)? Will it actually build and run as a Flatpak? Does the browser-opening strategy work inside the sandbox and pass Flathub review?',
  "product & UX: does it deliver the owner's stated features (categories, Favorites always first, weekly Popular/Trending, favorite button, no accounts, configurable browser preference chain, Libadwaita look like Cartridges/Bazaar)? Is the UX coherent and HIG-compliant?",
  'maintainability, community & compliance: Hive ACMM compliance, mirrored scaffolding, contribution pipeline quality, popularity pipeline robustness and cost, release/Flathub path, solo-maintainer sustainability, cross-platform honesty.',
]
const judgments = (await parallel(LENSES.map((lens, i) => () => agent(`You are judge #${i + 1} on a panel evaluating three architecture proposals for "Dailies". Read the brief ${BRIEF} first.

Your lens: ${lens}

Proposals (read each file fully with Bash cat): ${proposals.map(p => p.proposal_path).join(', ')}
Research reports for fact-checking: ${RESEARCH}/*.md (digest: ${DIGEST})

Score each proposal 1-10 under your lens with specific strengths, weaknesses and factual errors (quote the erroneous claim and the contradicting source). Name the winner under your lens, list must_graft ideas from the others, and must_fix items for the winner. Be skeptical and specific.`, { label: `judge:${i + 1}`, phase: 'Judge', schema: SCORE_SCHEMA })))).filter(Boolean)

const tally = {}
for (const j of judgments) for (const s of j.scores) tally[s.angle] = (tally[s.angle] || 0) + s.score
log(`Judge tally: ${JSON.stringify(tally)}`)

await agent(`Write ${PROPOSALS}/judgments.md: a markdown report of this judge panel. Include a scores table (angle x lens, with totals), per-lens strengths/weaknesses/factual errors, the overall winner, consolidated must_graft and must_fix lists (deduplicated). Data: ${JSON.stringify({ tally, judgments })}. Return the string "done".`, { label: 'judge:write-report', phase: 'Judge', effort: 'low' })

return { written, tally, judgments }
