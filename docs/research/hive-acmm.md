# Hive / ACMM compliance research for Dailies

Research key: `hive-acmm` · Date: 2026-10-15 · Hive version examined: `hivecommons/hive` @ `1bf213d0cb772ff8425e1787586a33b01f7ea27e` (2026-10-15, latest release **v5.175.0**, 2026-10-15T10:59:51Z). Owner repos examined: `Tim-van-Oudheusden/MinimalUI` (last commit 2026-10-15 16:34 +0200) and `Tim-van-Oudheusden/website` (last commit 2026-10-15 11:20 +0200). All clones are in `<scratch>/clones/hive-acmm/` (`hive/`, `MinimalUI/`, `website/`, `hivecommons-dotgithub/`, `paper/`).

Legend: **[V]** verified against a primary source (file in the cloned repo, official page, or GitHub API); **[I]** inference or recommendation.

---

## 1. Executive summary

1. **ACMM = "AI Codebase Maturity Model"** [V] (Hive README, `src/docs/acmm-policy-matrix.md`, and the paper arXiv:2604.09388 by Andy Anderson, IBM Research, v1 2026-04-10, v2 2026-04-27). It is a six-level model (L1 Inception/Assisted → L6 Fully Autonomous) of how much autonomy a repository can safely give AI agents. hivecommons.dev's marketing page expands it once as "AI-native Capability Maturity Model" [V, inconsistency noted]; the code and docs use "AI Codebase Maturity Model".
2. **"Meeting ACMM requirements" has a precise, mechanical meaning in Hive**: the dashboard's **ACMM Eval** section scores each configured repository against **50 file-existence criteria** (`universalCriteria` in `src/pkg/dashboard/acmm_criteria.go`; the code comment still says 43) grouped into levels **L0, L2, L3, L4, L5, L6** (there are no L1 criteria). A level **passes when ≥ 70 % of its criteria are detected** (`acmmLevelThreshold = 0.70`). The repo's **Codebase Level** is the highest level reached by consecutive passes from L0 upward; passing L0 alone yields L1. **Overall ACMM = min(Codebase Level, Operational Level)** where Operational Level is the ACMM level the hive is configured to run at. [V]
3. Each criterion passes if **any one** of its listed paths exists (directory patterns end in `/`). Content is never inspected: the generated gap issue literally says "The ACMM evaluation checks for file existence — the content can follow your project's conventions." [V]
4. **Compliance is checked by a running Hive instance** (dashboard section "ACMM Eval", REST `GET /api/acmm/evaluation`, `?refresh=1` to bypass the 1 h cache, debounce 1 min), **not by a CLI linter, GitHub App check, or badge**. There is **no ACMM badge** program (Credly badges are a planned contributor-reward design, unrelated to repo compliance). Gaps are filed as GitHub issues titled `[ACMM L<n>] Add <Criterion name>` with labels `acmm` + `ai-fix-requested` via `POST /api/acmm/issue`. [V] The owner's two repos contain exactly such issues (e.g. website #275 "[ACMM L2] Add CLAUDE.md instruction file", MinimalUI #553 "[ACMM L5] Add Public metrics"), filed by the owner's hive (hive id `hive-tall-slug`, GitHub App `hive-forge-app`). [V]
5. **Both reference repos score Codebase Level L5** by the file check (my local re-implementation of the evaluator): L2–L5 are 100 %, L6 is 3/12 (25 %). MinimalUI's L0 is 6/8 (Gradle test layouts are not in the "Test suite" pattern list); website's L0 is 8/8. [V, computed from the clones with the exact pattern lists]
6. **A brand-new Dailies repo scores 0/50 (L0 fails)** today. The checklist in §9 lists, per criterion, the exact file the owner's repos use and the Flatpak/GTK-appropriate equivalent, so Dailies can reach **L5 Codebase Level on day one** (L6 is only reachable with 9/12 L6 artifacts and is not recommended).
7. **Registering with Hive** is separate from compliance: (a) hosted hub wizard at `https://hive.hivecommons.dev/get-started` (GitHub login → repo URL → ACMM level L1–L3 → request → admin approves → install Hive GitHub App), (b) `hivectl --server https://hive.hivecommons.dev enroll OWNER/REPO [--acmm-level N]` ("lite", capped at L2), or (c) adding the repo to `project.repos` in an existing spoke's `hive.yaml` (the owner already runs one). **Joining the Hive Commons organisation** is a different thing again (project-proposal issue, Apache-2.0 + DCO + CNCF CoC required) and is **not** needed for ACMM compliance; Dailies is GPL-3.0 and would need relicensing to join. [V]

---

## 2. What Hive and Hive Commons are [V]

- **Hive** (github.com/hivecommons/hive, Apache-2.0, CNCF sandbox candidate, cncf/sandbox#516) is a "co-maintainer" that watches a repo's issues/PRs/CI/CVEs/Dependabot alerts and dispatches short-lived AI coding agents (Claude Code, Copilot CLI, Gemini CLI, Goose, Codex, …) under deterministic filters, gates and an audit log. It ships as a single Go binary (control plane + Node gateway + ttyd) on Kubernetes, Podman Quadlet or Docker Compose. **Spoke** = one running Hive serving repos; **Hub** = control plane for many spokes. Hosted hub: https://hive.hivecommons.dev. (README.md; docs.hivecommons.dev.)
- **Hive Commons** (hivecommons.dev, docs.hivecommons.dev, github.com/hivecommons) is the umbrella community: Hive, Spektacular (spec → plan → implementation), hotshot, pluk, promptargs, rationguard, dibs. Governance in `hivecommons/.github/GOVERNANCE.md` (maintainer committee, lazy consensus 72 h / 7 d, 2/3 supermajority; "Agents are tooling, not members", every agent has a responsible human, every merge an accountable human). Biweekly meeting Thursdays 10:00 ET.
- Hive's own repo already carries the artefacts it preaches: `AGENTS.md` (with `CLAUDE.md -> AGENTS.md` symlink), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `GOVERNANCE.md`, `ADOPTERS.md`, `OWNERS`, `changelog.d/`, `.github/CODEOWNERS`, `.github/dependabot.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/{bug_report.md,feature_request.md,guide-gap.md,contributor-story.yml,config.yml}`, `.github/workflows/ai-fix.yml`, `scorecard.yml`, OpenSSF Best Practices badge (bestpractices.dev/projects/14261), FOSSA badge, `security-insights.yml`, ADR directory `src/docs/adr/0001…0023`.

---

## 3. What ACMM is

### 3.1 The paper's model (arXiv:2604.09388 v2) [V, extracted from the PDF]

"The AI Codebase Maturity Model: From Assisted Coding to Fully Autonomous Systems — A Practitioner Experience Report from KubeStellar Console and Hive", Andy Anderson (IBM Research). Three principles: each level subsumes the previous ("You cannot skip levels"); levels are defined by **feedback-loop topology**, not tool choice; progression = degree to which human judgment is encoded in **system artifacts** (instruction files, tests, metrics, workflow rules).

| Level | Name | Feedback loop | Key artifacts | Human role |
|---|---|---|---|---|
| 1 | Assisted | Open loop | None | Executor |
| 2 | Instructed | One-way (human→AI) | Instruction files (CLAUDE.md, .github/copilot-instructions.md, dev guides, PR templates with AI-readable checklists) | Rule-writer |
| 3 | Measured | Two-way (with human interpretation) | Metrics, test suites (PR acceptance rate per category, coverage gating on every PR, nightly suites, error monitoring, flaky-test analysis; `auto-qa-tuning.json` acceptance logs) | Analyst |
| 4 | Adaptive | Closed loop (automated response) | Self-tuning configs (`auto-qa-tuning.json`), closed-loop CI/CD, automated triage loops | Governor |
| 5 | Semi-automated | Multi-loop (self-improving) | "The codebase itself" — tests as trust constraints, workflows as policy; system proposes, humans approve | Operator |
| 6 | Fully Autonomous | Multi-loop with external orchestration | Agent fleet + policy files + Beads ledger; governor; push notifications; observability runbook | Strategist |

Paper §5.3 "Level 6 Criteria" (verbatim criterion names): Automated issue generation; Multi-agent orchestration; Merge queue / auto-merge; Strategic dashboard; Risk assessment config; Production feedback signal; Observability runbook; Rollback drill. Paper advice (§7): "Start with Level 2. Writing a CLAUDE.md file takes 30 minutes… Then invest in test coverage." Reported evidence: 74 workflows, 32 nightly suites, 91 % coverage, 36+ feedback loops, 5× PR and 37× issue throughput from L2 to L6.

### 3.2 Hive's operational levels and policy modes [V: `src/docs/acmm-policy-matrix.md`, README]

Four per-agent **policy modes**:

| Mode | Suffix | Beads | Issues | PRs | Merge | GH Auth |
|------|--------|-------|--------|-----|-------|---------|
| Advisory | `-advisory.md` | Yes | No | No | No | No |
| Measured | `-measured.md` | Yes | Yes | No | No | Yes |
| Holdgated | `-holdgated.md` | Yes | Yes | Yes + `hold` label | No | Yes |
| Full | `-full.md` | Yes | Yes | Yes | Yes (auto on green CI) | Yes |

Six **levels** (pack files `src/pkg/config/packs/level-{1..6}.yaml`):

| Level | Name | What agents can do |
|---|---|---|
| L1 | Inception (Assisted) | Interactive advisor and project inception (guide + brainstorm agents). Advisory beads only. |
| L2 | Advisory (Instructed) | Observe and report findings as dashboard beads. No GitHub interaction. |
| L3 | Quality-Gated (Measured) | Quality agent opens issues and PRs gated by the literal `hold` label. Others advisory. |
| L4 | Security-Aware (Adaptive) | All agents file issues. Quality, sec-check and ci-maintainer open `hold`-gated PRs. |
| L5 | Semi-Autonomous (Semi-Automated) | All agents open `hold`-gated PRs; humans batch-review. Reviewer, architect, strategist, dedupe join. |
| L6 | Fully Autonomous | Agents open PRs and auto-merge when checks pass; outreach PRs still held. |

Key rules: level holds use the literal label `hold`; `hive-pause/<hive-id>` is the dashboard's manual hold; `hive/<hive-id>` is provenance only; advisory agents never receive GitHub auth; brainstorm and supervisor are always advisory; changing level = `PUT /api/packs/level {"level": N}` (or dashboard "Change level"; TUI `hivectl tui` key `A` with typed confirmation). ADR-0003 records the decision to use L1–L6 as the public autonomy model.

### 3.3 Two separate "readiness" computations in Hive [V]

| | Codebase readiness (ACMM Eval) | Operational level-up advisor |
|---|---|---|
| Code | `src/pkg/dashboard/acmm_criteria.go`, `api_acmm_eval.go`, `acmm_waivers.go` | `src/pkg/acmmadvisor/acmmadvisor.go`, `api_acmm_recommendation.go` |
| Input | File existence in each repo in `project.repos` via GitHub Contents API (up to ~29 `GetContents` calls/repo, 20 s per-repo timeout) | Live signals: coverage %, green-CI streak, merge success rate, actionable issues, open holds, presence of a `quality` agent |
| Output | `codebase_level`, per-level `score`/`passed`, per-criterion results; `overall_level = min(codebase, operational)` | `GET /api/acmm-recommendation`: `advise` = `stay`/`raise`, met/unmet checklist; advisory only |
| Thresholds | 0.70 per level | L2: quality agent; L3: ≥40 % cov, streak ≥3; L4: ≥60 %, ≥5, merge ≥70 %; L5: ≥75 %, ≥8, ≥85 %, ≤25 issues, ≤15 holds; L6: ≥90 %, ≥12, ≥95 %, ≤10, ≤5 (compile-time constants) |

So "ACMM requirements for Hive" for a repository = the file-existence criteria in §4 (codebase side), plus — if the owner wants to *run* at a level — the operational thresholds above and GitHub App permissions in §6.3.

---

## 4. The complete criteria list (verbatim from `src/pkg/dashboard/acmm_criteria.go`) [V]

Structure: `{ID, Source ("acmm"|"aef"), Level (0,2,3,4,5,6), Category, Name, Patterns []}`. A criterion passes if **any** pattern exists; a trailing `/` means directory. Level names (`acmmLevelNames`): 0 "Prerequisites not met", 1 "Inception", 2 "Advisory", 3 "Quality-Gated", 4 "Security-Aware", 5 "Semi-Autonomous", 6 "Fully Autonomous". Directories pre-fetched for the check: root, `.github`, `.github/workflows`, `.github/ISSUE_TEMPLATE`, `.github/prompts`, `.github/agents`, `.claude`, `docs`, `docs/security`.

### L0 — Prerequisites (8 criteria; need ≥ 6 to pass → yields Level 1)

| ID | Name | Category | Patterns (any one) |
|---|---|---|---|
| `acmm:prereq-test-suite` | Test suite | prerequisite | `vitest.config.ts`, `vitest.config.js`, `jest.config.js`, `jest.config.ts`, `go.mod`, `pytest.ini`, `pyproject.toml`, `test/`, `tests/`, `__tests__/`, `spec/` |
| `acmm:prereq-e2e` | E2E tests | prerequisite | `playwright.config.ts`, `playwright.config.js`, `cypress.config.ts`, `e2e/`, `web/e2e/`, `web/playwright.config.ts`, `web/playwright.config.js`, `test/e2e/`, `tests/e2e/` |
| `acmm:prereq-cicd` | CI/CD pipeline | prerequisite | `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/` |
| `acmm:prereq-pr-template` | PR template | prerequisite | `.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE.md` |
| `acmm:prereq-issue-template` | Issue templates | prerequisite | `.github/ISSUE_TEMPLATE/`, `.github/issue_template.md` |
| `acmm:prereq-contrib-guide` | Contributing guide | prerequisite | `CONTRIBUTING.md`, `docs/contributing.md`, `.github/CONTRIBUTING.md` |
| `acmm:prereq-code-style` | Code style config | prerequisite | `.eslintrc`, `.eslintrc.json`, `.eslintrc.js`, `eslint.config.js`, `eslint.config.mjs`, `.prettierrc`, `.prettierrc.json`, `prettier.config.js`, `ruff.toml`, `.golangci.yml`, `.golangci.yaml`, `.golangci.toml`, `.golangci.json`, `biome.json`, `.shellcheckrc`, `.editorconfig`, `.clang-format`, `checkstyle.xml`, `config/checkstyle/checkstyle.xml`, `.rubocop.yml`, `.rubocop.yaml`, `rustfmt.toml`, `.rustfmt.toml`, `clippy.toml`, `.clippy.toml`, `.swiftlint.yml`, `.stylelintrc`, `.stylelintrc.json`, `.stylelintrc.yaml`, `.stylelintrc.yml` |
| `acmm:prereq-coverage-gate` | Coverage gate | prerequisite | `codecov.yml`, `.codecov.yml`, `.github/workflows/coverage-gate.yml`, `coverage.yml`, `.coverage-thresholds.json` |

### L2 — Advisory (8 criteria; need ≥ 6)

| ID | Name | Category | Patterns |
|---|---|---|---|
| `acmm:claude-md` | CLAUDE.md instruction file | feedback-loop | `CLAUDE.md`, `.claude/CLAUDE.md` |
| `acmm:copilot-instructions` | Copilot instructions | feedback-loop | `.github/copilot-instructions.md` |
| `acmm:agents-md` | AGENTS.md | feedback-loop | `AGENTS.md` |
| `acmm:cursor-rules` | Cursor rules | feedback-loop | `.cursorrules`, `.cursor/rules` |
| `acmm:prompts-catalog` | Prompts catalog | feedback-loop | `prompts/`, `.prompts/`, `docs/prompts/`, `.github/prompts/`, `.github/agents/` |
| `acmm:editor-config` | EditorConfig | feedback-loop | `.editorconfig` |
| `acmm:simple-skills` | Simple skills | feedback-loop | `.claude/skills/`, `.claude/commands/`, `skills/` |
| `acmm:correction-capture` | Correction capture | learning | `.claude/memory/`, `.memory/`, `corrections.jsonl` |

### L3 — Quality-Gated (8 criteria; need ≥ 6)

| ID | Name | Category | Patterns |
|---|---|---|---|
| `acmm:pr-acceptance-metric` | PR acceptance metric | feedback-loop | `scripts/build-accm-history.mjs`, `.github/workflows/accm-history-update.yml`, `scripts/pr-metrics.mjs`, `.github/workflows/pr-metrics.yml`, `docs/metrics.md` |
| `acmm:pr-review-rubric` | PR review rubric | feedback-loop | `.github/workflows/review.yml`, `docs/review-rubric.md`, `.github/review-checklist.md`, `.github/prompts/review.md`, `docs/qa/` |
| `acmm:quality-dashboard` | Quality dashboard | observability | `public/analytics.js`, `web/public/analytics.js`, `web/src/components/analytics/`, `docs/quality.md`, `.github/workflows/quality-report.yml`, `docs/AI-QUALITY-ASSURANCE.md` |
| `acmm:ci-matrix` | CI test matrix | feedback-loop | `.github/workflows/ci.yml`, `.github/workflows/test.yml`, `.github/workflows/build.yml` |
| `acmm:layered-safety` | Layered safety model | governance | `.claude/settings.json`, `.claude/settings.local.json` |
| `acmm:mechanical-enforcement` | Mechanical enforcement | governance | `.claude/settings.json` |
| `acmm:session-summary` | Session summary artifact | learning | `.claude/session-summary.md`, `.claude/checkpoint.md` |
| `acmm:structural-gates` | Structural gates | traceability | `.claude/settings.json` |

### L4 — Security-Aware (9 criteria; need ≥ 7, i.e. 0.78 ≥ 0.70; 6/9 = 0.67 fails)

| ID | Name | Category | Patterns |
|---|---|---|---|
| `acmm:auto-qa-tuning` | Auto-QA self-tuning | self-tuning | `.github/auto-qa-tuning.json`, `.github/workflows/auto-qa.yml`, `scripts/auto-qa-tuner.mjs` |
| `acmm:nightly-compliance` | Nightly compliance | feedback-loop | `.github/workflows/nightly-compliance.yml`, `.github/workflows/nightly.yml`, `.github/workflows/nightly-test.yml`, `.github/workflows/nightly-test-suite.yml` |
| `acmm:copilot-review-apply` | Automated review application | feedback-loop | `.github/workflows/copilot-review-apply.yml`, `.github/workflows/apply-copilot.yml`, `.github/workflows/ai-fix.yml`, `.github/workflows/auto-review.yml` |
| `acmm:auto-label` | Automated issue labeling | feedback-loop | `.github/labeler.yml`, `.github/workflows/labeler.yml`, `.github/workflows/triage.yml` |
| `acmm:ai-fix-workflow` | AI-fix-requested workflow | feedback-loop | `.github/workflows/ai-fix.yml`, `.github/workflows/ai-fix-requested.yml`, `.github/workflows/claude.yml` |
| `acmm:tier-classifier` | Change classification | governance | `.github/workflows/tier-classifier.yml`, `docs/risk-tiers.md`, `.github/risk-tiers.yml`, `.github/workflows/pr-size.yml` |
| `acmm:security-ai-md` | AI security policy | governance | `docs/security/SECURITY-AI.md`, `SECURITY-AI.md`, `docs/SECURITY-AI.md` |
| `acmm:session-continuity` | Session continuity | learning | `.claude/checkpoint.md`, `.claude/session-summary.md` |
| `acmm:cross-session-knowledge` | Cross-session knowledge | learning | `knowledge.jsonl`, `.knowledge/`, `docs/reflections/` |

### L5 — Semi-Autonomous (5 criteria; need ≥ 4)

| ID | Name | Category | Patterns |
|---|---|---|---|
| `acmm:github-actions-ai` | GitHub Actions AI integration | feedback-loop | `.github/workflows/claude.yml`, `.github/workflows/claude-code-review.yml` — *also auto-credited ("Hive agent loop") for a repo with Hive agent activity in the last 30 days* |
| `acmm:auto-qa-self-tuning` | Auto-QA with self-tuning | self-tuning | `.github/workflows/auto-qa.yml`, `.github/auto-qa-tuning.json` |
| `acmm:public-metrics` | Public metrics | observability | `web/netlify/functions/analytics-accm.mts`, `web/public/analytics.js`, `docs/metrics/` |
| `acmm:policy-as-code` | Policy-as-code | governance | `policies/`, `.github/policies/`, `kyverno/`, `conftest.yaml`, `opa/` |
| `acmm:reflection-log` | Reflection log | feedback-loop | `.claude/reflections/`, `memory/`, `.memory/`, `docs/reflections/`, `REFLECTIONS.md` |

### L6 — Fully Autonomous (12 criteria: 6 `acmm:` + 6 `aef:` "Agentic Engineering Framework"; need ≥ 9)

| ID | Name | Category | Patterns |
|---|---|---|---|
| `acmm:auto-issue-gen` | Auto issue generation | autonomy | `.github/workflows/auto-issues.yml`, `.github/workflows/auto-issue.yml`, `.github/workflows/issue-gen.yml`, `.github/workflows/auto-generate-issues.yml`, `scripts/generate-issues.mjs` |
| `acmm:multi-agent-orchestration` | Multi-agent orchestration | autonomy | `.github/workflows/dispatcher.yml`, `.github/workflows/orchestrate.yml`, `scripts/orchestrate.mjs`, `docs/multi-agent.md`, `.claude/dispatcher/`, `orchestrator/` |
| `acmm:strategic-dashboard` | Strategic dashboard | observability | `web/src/components/acmm/`, `docs/strategy.md`, `.github/workflows/strategy-report.yml`, `docs/autonomous-work-log.md` |
| `acmm:merge-queue` | Merge queue | autonomy | `.github/workflows/merge-queue.yml`, `.github/merge-queue.yml`, `.prow.yaml`, `tide.yaml` |
| `acmm:risk-assessment-config` | Risk assessment config | governance | `risk-config.json`, `.claude/risk-config.json`, `.github/risk-assessment.yml` |
| `acmm:observability-runbook` | Observability runbook | governance | `docs/ai-ops-runbook.md`, `docs/runbook/`, `RUNBOOK.md` |
| `aef:task-traceability` | Task traceability | governance | `.agent/tasks/`, `docs/agent-tasks/`, `.github/agent-log/`, `agent-tasks.md` |
| `aef:structural-gates` | Structural gates | governance | `CODEOWNERS`, `.github/CODEOWNERS`, `.agent/boundaries.yml`, `docs/agent-boundaries.md` |
| `aef:session-continuity` | Session continuity | governance | `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md`, `docs/agent-context.md` |
| `aef:audit-trail` | Audit trail workflow | governance | `.github/workflows/ai-audit.yml`, `.github/workflows/agent-audit.yml`, `scripts/ai-audit-report.mjs` |
| `aef:cross-tool-config` | Cross-tool agent config | governance | `AGENTS.md`, `docs/ai-contributors.md`, `.github/ai-config.yml` |
| `aef:change-classification` | Change classification | governance | `docs/change-classification.md`, `.github/change-tiers.yml`, `docs/risk-tiers.md` |

Total: 8 + 8 + 8 + 9 + 5 + 12 = **50** criteria.

### 4.1 Scoring rules [V: `api_acmm_eval.go` `scoreResults`, `evaluateAllRepos`]

- Per level: `score = matched/total`; `detected_score = (matched − waived)/total`; `passed = detected_score ≥ 0.70`.
- Codebase level: iterate levels ascending (0,2,3,4,5,6); set level to each passing level; **stop at the first failure**. If only L0 passed, codebase level = **1**. If L0 fails, codebase level = 0 ("Prerequisites not met") regardless of higher levels.
- Multi-repo hives: an aggregate criterion passes if **any** repo passes it; the aggregate also marks whether it was detected, waived or Hive-credited.
- `blocked_at_level` = first non-passing level (−1 if none).
- `overall_level = min(codebase_level, operational_level)` where operational level = `detectCurrentLevel()` (the configured `acmm_level`).
- Cache: results cached 1 h (`acmmEvalTTL`); `?refresh=1` honours a 1-minute debounce.

### 4.2 Waivers — `.acmm.yml` / `.acmm.yaml` at repo root [V: `src/docs/acmm-waivers.md`, `acmm_waivers.go`]

```yaml
waivers:
  - id: acmm:ai-fix-workflow
    satisfied_by: hive
    reason: >
      The in-repo AI-fix path was removed in PR #118 — it duplicated what
      hive already does at ACMM L4, across a second trust boundary. Hive is
      the sole autonomous path. See docs/SECURITY-AI.md.
  - id: acmm:copilot-review-apply
    satisfied_by: hive
    reason: Same removal; hive applies review feedback. See docs/SECURITY-AI.md.
```

All three fields (`id`, `satisfied_by`, `reason`) are required; `id` must be a real criterion ID. A waiver (1) **can never advance a level** (pass/fail uses detected criteria only), (2) is consulted only when detection failed, (3) is shown with a `⌾ waived` chip and a red asterisk on the level line. Costs nothing for repos without the file.

### 4.3 Gap issues [V: `acmmIssueContent`]

Title: `[ACMM L<level>] Add <Name>`. Labels: `acmm` (colour `0075ca`, description "ACMM criterion gap identified by hive evaluation") and `ai-fix-requested`. Body template:

```
## ACMM Gap: <Name>

**Level:** L<n> <Level name>
**Category:** <category>
**Criterion ID:** `<id>`

### What's needed

This repository is missing one of the following files or directories:

- `<pattern 1>`
- `<pattern 2>`

Adding any one of these will satisfy this criterion and help the repository advance to ACMM Level <n> (<Level name>).

### Why it matters

<category text, e.g. "Prerequisites are foundational — without test suites, CI/CD, and templates, AI agents lack the guardrails needed for safe autonomous work.">

### How to fix

Create one of the files listed above. The ACMM evaluation checks for file existence — the content can follow your project's conventions.

---
*Opened by Hive ACMM Evaluation*
```

`governor.acmm.issue_tracker: github | work_source` chooses GitHub Issues vs Linear. The owner's repos show 35 such issues on website (#2–#7, #275–#283, #458, #486–#492, #499, #503–#509, #552–#554) and several on MinimalUI, all closed except website #7 "Coverage gate", #4 "PR template" and #275 "CLAUDE.md" which were later superseded (files now exist). [V via `gh issue list`]

---

## 5. How compliance is checked, surfaced and "certified" [V]

| Mechanism | Exists? | Details |
|---|---|---|
| Dashboard section **ACMM Eval** | Yes | "How ready your repositories are for Hive to work on them alone, scored against a published checklist." Tiles: Codebase Readiness, Operational Autonomy, Overall ACMM, Criteria Passed. Buttons **Re-evaluate**, **Open Issue** (per criterion), **Open All**, **Change level**. (`src/docs/dashboard-sections.md`) |
| REST API | Yes | `GET /api/acmm/evaluation[?refresh=1]` → `ACMMEvaluation` JSON; `POST /api/acmm/issue` `{repo, criterion_id, criterion_level, tracker?}` (owner role); `GET /api/acmm-recommendation` (advisor); `PUT /api/packs/level`. |
| Terminal | Partly | `hivectl tui` shows ACMM level and lets an operator change it (overlay `A`); it does **not** run the file evaluation. |
| CLI linter / pre-commit / GitHub Action for ACMM | **No** | Nothing in the repo evaluates a checkout locally. (My script `scratchpad/scripts/acmm_eval.py` re-implements the check for a local directory and can be adopted by Dailies as a CI self-check [I].) |
| GitHub App check / commit status | **No** | The Hive GitHub App is used for agent writes, not for a compliance status. |
| Badge | **No** | No ACMM badge exists. `src/docs/credly-badges.md` describes a *planned* contributor-milestone Credly integration, "design only". Hive's own README uses OpenSSF Best Practices and FOSSA badges (independent programs). |
| Certification / registry | **No** | `ADOPTERS.md` (both in `hivecommons/hive` and `hivecommons/.github`) is a self-service table; entries may state the ACMM level ("two ACMM L5/L6 spokes"). |
| Hive-side credit | Yes | `acmm:github-actions-ai` is auto-satisfied for a repo with Hive agent activity in the last 30 days (`hiveAgentLoopCredit`). |

---

## 6. How a repository registers with Hive [V]

### 6.1 Hosted hub wizard — https://hive.hivecommons.dev/get-started
Steps (hub page + `src/docs/hosted-hub.md`): **Login** with GitHub (no account permissions requested) → **Your Repo/Project**: paste repo URL (GitHub.com or GHE; GitLab/Gitea/Forgejo rejected) → **Choose autonomy level**: wizard offers **L1–L3**, recommends **L3 Quality-Gated (Measured)**; L4–L6 "Available after provisioning" → **Details** (name required; Slack ID, country optional) → **Request a Hive** → admin approves and provisions → hive appears under **My Hives** → dashboard welcome checklist prompts **Install GitHub App** (nothing to install beforehand). Unconfigured/inactive hosted hives are **reaped** on a timer; finish the App install in the first session. Hives are reachable at `https://<id>.hive.hivecommons.dev`.

### 6.2 Lite enrollment (CLI) — `src/docs/lite-enrollment.md`
```bash
export HIVE_DASHBOARD_TOKEN="$(unset GITHUB_TOKEN && gh auth token)"
hivectl --server https://hive.hivecommons.dev enroll OWNER/REPO
hivectl enroll OWNER/REPO --acmm-level 1
hivectl enroll OWNER/REPO --installation-id 123456
```
Prereqs: `gh` logged in; Hive GitHub App installed on the repo owner (or installation ID known). Zero repo secrets, no workflow shim, advisory lanes only, **ACMM capped at L2**. If you already own a spoke for the org, the repo is added to that spoke's `project.repos`.

### 6.3 Self-hosted / existing spoke — `hive.yaml`
```yaml
project:
  org: your-org
  repos:
    - repo-one
    - repo-two
  ai_author: your-bot-user
  primary_repo: repo-one
  # checkouts_dir: /data/checkouts   # required for AGENTS.md injection (src/docs/agents-md.md)
acmm_level: 3
```
The owner already operates a hive (labels `hive/hive-tall-slug`, `agent/*`, `hive/covered-by-pr`, App author `hive-forge-app`), so Dailies registers by adding `Dailies` to that spoke's `project.repos` (dashboard **Settings → Repos**, which checks App access and offers "Install/authorize the App for `<org>`"). [V for mechanism; I for applying it to Dailies]

**AGENTS.md injection caveat** [V]: Hive agents work over the GitHub API and keep no clones; a repo's `AGENTS.md` is prepended to kick prompts **only** if `project.checkouts_dir` points at a host directory containing `<checkouts_dir>/<repo>`. Parser supports optional YAML front-matter `skills: [...]`, `## Skill: <name>` sections, and `skills/<name>.md` files. The injected block states that the repo's instructions outrank Hive's defaults (except Hive safety rules and explicit assignment instructions).

**GitHub App repository permissions** (`src/docs/github-app-setup.md`): Metadata R; Contents R/W; Issues R/W; Pull requests R/W; Checks R; Actions R; Administration R (branch-protection read); Workflows R/W (optional, for agent PRs touching `.github/workflows/`); Organization Members R. Fine-grained PAT alternative by tier: L1–L2 Contents R, Issues R/W, PRs R; L3–L4 same; L5–L6 Contents R/W, PRs R/W.

### 6.4 Joining the Hive Commons organisation (optional, different thing)
Proposal issue on `github.com/hivecommons/.github` using template `.github/ISSUE_TEMPLATE/join-hive-commons.yml` (title `[project proposal] <project name>`, label `project-proposal`): project name, repo URL, what it does, fit with the family, **License (Apache-2.0 or OSI with relicensing)**, commitments (**DCO on every commit**, **CNCF Code of Conduct**, willing to move under `hivecommons` org, maintainer attends biweekly meeting for first quarter), maintainers, adoption. Decided by lazy consensus. You get a home in the org, a docs-site section synced from your repo, a card on hivecommons.dev, meeting slot, optionally a hive. **Not required for ACMM compliance.** Dailies (GPL-3.0, a GTK game launcher) does not fit the family's scope ("tools that remove friction for people working with coding agents") and would need relicensing — recommend **not** proposing it [I].

**Listing as an adopter**: PR adding one row to `hivecommons/.github/ADOPTERS.md` (`| Organization | Contact | Level (evaluation/development/production) | Since | Use case |`, alphabetical, signed commit) or `hivecommons/hive/ADOPTERS.md` (`| Organization | Description | Maturity Level (Production/Pre-production/Evaluation) | Further Information |`, PR title `📖 docs: add <Organization> to ADOPTERS.md`).

---

## 7. Templates Hive itself provides [V]

| Template | Where | Notes |
|---|---|---|
| Inception scaffold (L1) | Dashboard Inception panel / `GET /api/inception/scaffold`, `/download` (zip) | Generates `README.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, CI workflows, `.gitignore`, language stubs (Go, Python, TypeScript, JavaScript, Rust, Java, shell) from a brainstorm interview. Requires running a hive at L1 with the `brainstorm` agent and owner role. Not inspected here; content is generated per project. |
| `.acmm.yml` waiver file | `src/docs/acmm-waivers.md` | Reproduced in §4.2. |
| `hive.yaml.example` | `src/hive.yaml.example` | Operator config, `project:` section reproduced in §6.3. |
| PR template | `.github/PULL_REQUEST_TEMPLATE.md` | Summary / Related issues (`Fixes #`) / Testing / Contributor checklist (changelog fragment, release line, emoji title convention `✨ feature`, `🐛 fix`, `📖 docs`, `🌱 chore`, `⚠️ breaking`, DCO sign-off, docs updated, no secrets). Full text in Appendix B. |
| Issue templates | `.github/ISSUE_TEMPLATE/bug_report.md`, `feature_request.md`, `guide-gap.md`, `contributor-story.yml`, `config.yml` (Discord contact link) | Bug report reproduced in Appendix B. |
| `AGENTS.md` | repo root, `CLAUDE.md` is a symlink to it | Agent rules: CI runs tests (not agents), changelog fragment per PR, signed commits, emoji PR titles. Reproduced in Appendix B. |
| Governance set | `hivecommons/.github`: `GOVERNANCE.md`, `MAINTAINERS.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (CNCF), `SECURITY.md`, `ADOPTERS.md`, `community/meeting-notes-template.md` | Apache-2.0/DCO specific; useful as prose reference only for a GPL project. |
| ADR convention | `src/docs/adr/0001-record-architecture-decisions.md` … `0023` | Format: `# ADR-NNNN: Title`, `Status:`, `## Context`, `## Decision`, `## Consequences`. ADRs are **not** an ACMM criterion, but Hive uses them. |

---

## 8. The owner's compliant repositories: what they contain and how they score [V]

### 8.1 Evaluation (local re-implementation of `checkCriterion`/`scoreResults`, run on the clones)

| Level | MinimalUI | website | Dailies (today) |
|---|---|---|---|
| L0 Prerequisites | 6/8 = 0.75 PASS (missing `acmm:prereq-test-suite`, `acmm:prereq-e2e`: Gradle layout has no `test/`, `tests/`, `pytest.ini` …) | 8/8 PASS (`test/`, `playwright.config.ts`) | 0/8 FAIL |
| L2 Advisory | 8/8 | 8/8 | 0/8 |
| L3 Quality-Gated | 8/8 | 8/8 | 0/8 |
| L4 Security-Aware | 9/9 | 9/9 | 0/9 |
| L5 Semi-Autonomous | 5/5 | 5/5 | 0/5 |
| L6 Fully Autonomous | 3/12 (`aef:session-continuity` via CLAUDE.md, `aef:cross-tool-config` via AGENTS.md, `aef:change-classification` via docs/risk-tiers.md) FAIL | 3/12 FAIL | 0/12 |
| **Codebase level** | **L5**, blocked at L6 | **L5**, blocked at L6 | **L0** |

### 8.2 Criterion → file mapping used by the owner's repos (what to copy)

| Criterion | File in MinimalUI / website | Shared verbatim? |
|---|---|---|
| prereq-cicd | `.github/workflows/` | — |
| prereq-pr-template | `.github/pull_request_template.md` | project-specific text |
| prereq-issue-template | `.github/ISSUE_TEMPLATE/issue.yml` (+ `device-report.yml` in MinimalUI) | project-specific dropdowns |
| prereq-contrib-guide | `CONTRIBUTING.md` (23 KB in MinimalUI) | project-specific |
| prereq-code-style | `.editorconfig` (MinimalUI), `eslint.config.js` (website) | `.editorconfig` differs slightly |
| prereq-coverage-gate | `.github/workflows/coverage-gate.yml` (job name `Unit-test coverage floors`, reads `.github/auto-qa-tuning.json`, calls `scripts/coverage-check.sh <module> <functions> <lines>`) | structure same, toolchain differs |
| claude-md | `CLAUDE.md` | mirrors `.github/copilot-instructions.md` and `.cursor/rules/agent-guidance.mdc` ("AGENTS.md wins") |
| copilot-instructions | `.github/copilot-instructions.md` | same text as CLAUDE.md |
| agents-md | `AGENTS.md` | authoritative ruleset |
| cursor-rules | `.cursor/rules/agent-guidance.mdc` (front-matter `alwaysApply: true`) | same text as CLAUDE.md |
| prompts-catalog | `prompts/README.md`, `prompts/code-review.md`, `prompts/pull-request.md` | similar |
| editor-config | `.editorconfig` | — |
| simple-skills | `.claude/skills/github-issue-flow/SKILL.md` | project commands differ |
| correction-capture | `.claude/memory/corrections.tsv` | format shared |
| pr-acceptance-metric | `.github/workflows/pr-metrics.yml` + `scripts/pr-metrics.sh` (weekly Mon 06:17 UTC; agent = `claude/*` branch or author `hive-forge-app`) | **language-agnostic, copy as is** |
| pr-review-rubric | `.github/workflows/review.yml` + `scripts/pr-review-check.sh` (Conventional Commits title regex + `Fixes #N` link; rubric to job summary) | language-agnostic apart from rubric bullets |
| quality-dashboard | `.github/workflows/quality-report.yml` + `scripts/quality-report.sh` + `scripts/auto-qa-tuner.{sh,ts}` | toolchain-specific body |
| ci-matrix | `.github/workflows/ci.yml` | toolchain-specific |
| layered-safety / mechanical-enforcement / structural-gates | `.claude/settings.json` (`permissions.allow/ask/deny`) | deny list shared; allow list per toolchain |
| session-summary / session-continuity | `.claude/session-summary.md` | format shared |
| auto-qa-tuning / auto-qa-self-tuning | `.github/auto-qa-tuning.json` (`{"margin": 2, "floors": {"<module>": {"functions": N, "lines": N}}}`) | module names differ |
| nightly-compliance | `.github/workflows/nightly-compliance.yml` + `scripts/nightly-compliance.sh` (daily 03:23 UTC; dependency audit, artefact `nightly-compliance.md`) | website variant is simplest to adapt |
| copilot-review-apply | `.github/workflows/auto-review.yml` + `scripts/apply-review-suggestions.sh` (`/apply-suggestions` comment by OWNER/MEMBER/COLLABORATOR applies ```suggestion blocks) | language-agnostic, copy as is |
| auto-label | `.github/labeler.yml` + `.github/workflows/labeler.yml` (`actions/labeler@v7`, `pull_request_target`, no checkout) | paths differ |
| ai-fix-workflow / github-actions-ai | `.github/workflows/claude.yml` (`anthropics/claude-code-action` pinned SHA, `label_trigger: ai-fix-requested`, `trigger_phrase: '@claude'`, `branch_prefix: claude/`, refuses fork PRs, needs secret `CLAUDE_CODE_OAUTH_TOKEN`) | copy; adjust `--allowedTools` |
| tier-classifier / aef:change-classification | `.github/workflows/tier-classifier.yml` + `scripts/tier-classify.sh` + `.github/policies/risk-tiers.policy` + `docs/risk-tiers.md` | script language-agnostic; policy paths differ |
| security-ai-md | `docs/security/SECURITY-AI.md` | adapt |
| cross-session-knowledge / reflection-log | `docs/reflections/README.md` + dated entries | format shared |
| public-metrics | `docs/metrics/README.md` | adapt |
| policy-as-code | `.github/policies/risk-tiers.policy` | adapt paths |
| Not ACMM but present | `SECURITY.md`, `BRANDING.md`, `.github/dependabot.yml`, `.github/rulesets/main.json` (required checks `PR review rubric`, `Build, lint, test`, `Unit-test coverage floors`, `Static checks`), `.devcontainer/`, `Dockerfile.sandbox`, `.beads/` (Beads issue mirror, `bd`), `docs/postmortems/{README,TEMPLATE}.md` (website), `docs/runbooks/` (MinimalUI; note `docs/runbooks/` does **not** match the L6 pattern `docs/runbook/`), `tooling/` tests pinning workflow invariants (MinimalUI) | — |

Both repos were brought to compliance **by the owner's hive filing `[ACMM Ln] Add …` issues and the owner (or Claude via `claude.yml`) closing them**; the file set above is therefore exactly what Hive looks for.

---

## 9. Concrete compliance checklist for Dailies (new repository)

Target: **Codebase Level L5 from the first scaffold PR**, operational level chosen later (start L2/L3 per Hive guidance "trust > level"). Toolchain assumption: GTK4/Libadwaita app in **Python (PyGObject) or Rust (gtk4-rs)**, built with Meson, packaged as Flatpak [I — other research tracks decide]. Where the owner's file is language-agnostic, copy it from the clone path given in §8.2.

### Phase 0 — L0 prerequisites (need 6/8; aim for 8/8)
- [ ] `tests/` directory (Python: also `pyproject.toml` with `[tool.pytest.ini_options]`; Rust: `tests/` integration tests) → `acmm:prereq-test-suite`
- [ ] `tests/e2e/` (GTK UI smoke tests under `xvfb-run`/`dbus-run-session`, or Flatpak install-and-launch test) → `acmm:prereq-e2e`
- [ ] `.github/workflows/` with `ci.yml` → `acmm:prereq-cicd` (+ `acmm:ci-matrix`)
- [ ] `.github/pull_request_template.md` (copy MinimalUI's; swap quality-gate commands) → `acmm:prereq-pr-template`
- [ ] `.github/ISSUE_TEMPLATE/issue.yml` **plus** the Dailies-specific `add-dle.yml` form (name, URL, category, difficulty — the project's data-entry channel) and `config.yml` → `acmm:prereq-issue-template`
- [ ] `CONTRIBUTING.md` → `acmm:prereq-contrib-guide`
- [ ] `.editorconfig` **and** a linter config (`ruff.toml` for Python; `rustfmt.toml` + `clippy.toml` for Rust) → `acmm:prereq-code-style` (+ `acmm:editor-config`)
- [ ] `.github/workflows/coverage-gate.yml` (job name `Unit-test coverage floors`; Python: `pytest --cov` + `scripts/coverage-check.sh`; Rust: `cargo llvm-cov --json`) → `acmm:prereq-coverage-gate`

### Phase 1 — L2 Advisory (need 6/8; aim 8/8)
- [ ] `AGENTS.md` (authoritative; include GitHub-issue-first workflow, TDD, dependency rules, Flatpak build commands, "never push to main") → `acmm:agents-md`, `aef:cross-tool-config`
- [ ] `CLAUDE.md` (Claude summary; "AGENTS.md wins") → `acmm:claude-md`, `aef:session-continuity`
- [ ] `.github/copilot-instructions.md` (same body) → `acmm:copilot-instructions`
- [ ] `.cursor/rules/agent-guidance.mdc` (same body, front-matter `alwaysApply: true`) → `acmm:cursor-rules`
- [ ] `prompts/README.md`, `prompts/code-review.md`, `prompts/pull-request.md` → `acmm:prompts-catalog`
- [ ] `.claude/skills/github-issue-flow/SKILL.md` (+ consider `add-dle-entry/SKILL.md` for the data pipeline) → `acmm:simple-skills`
- [ ] `.claude/memory/corrections.tsv` (header only) → `acmm:correction-capture`

### Phase 2 — L3 Quality-Gated (need 6/8; aim 8/8)
- [ ] `.github/workflows/pr-metrics.yml` + `scripts/pr-metrics.sh` (copy verbatim) → `acmm:pr-acceptance-metric`
- [ ] `.github/workflows/review.yml` + `scripts/pr-review-check.sh` (copy; edit rubric bullets: "GTK/Libadwaita HIG", "Flatpak permissions justified", "no new finish-args") → `acmm:pr-review-rubric`
- [ ] `.github/workflows/quality-report.yml` + `scripts/quality-report.sh` + `scripts/auto-qa-tuner.sh` → `acmm:quality-dashboard`
- [ ] `.github/workflows/ci.yml` (job named `Build, lint, test`; Meson build, unit tests, lint, `flatpak-builder` build via `flathub/flatpak-github-actions` in a later job) → `acmm:ci-matrix`
- [ ] `.claude/settings.json` (copy website's deny/ask lists; allow list: `Bash(meson *)`, `Bash(ninja *)`, `Bash(pytest *)`/`Bash(cargo test *)`, `Bash(flatpak-builder *)`, `Bash(flatpak run *)`; deny `Read(./.env*)`, force-push, `--no-verify`, `sudo`, `rm -rf /`) → `acmm:layered-safety`, `acmm:mechanical-enforcement`, `acmm:structural-gates`
- [ ] `.claude/session-summary.md` → `acmm:session-summary`, `acmm:session-continuity`

### Phase 3 — L4 Security-Aware (need 7/9; aim 9/9)
- [ ] `.github/auto-qa-tuning.json` (`{"margin": 2, "floors": {"dailies": {"functions": N, "lines": N}}}`) → `acmm:auto-qa-tuning`, `acmm:auto-qa-self-tuning`
- [ ] `.github/workflows/nightly-compliance.yml` + `scripts/nightly-compliance.sh` (daily 03:23 UTC; checks: `pip-audit`/`cargo audit`, Flatpak runtime EOL check via `flatpak remote-info`, DLE catalog URL liveness, Dependabot alert count via `gh api`) → `acmm:nightly-compliance`
- [ ] `.github/workflows/auto-review.yml` + `scripts/apply-review-suggestions.sh` (copy verbatim) → `acmm:copilot-review-apply`
- [ ] `.github/labeler.yml` + `.github/workflows/labeler.yml` (labels: `app`, `data` for `data/**`, `flatpak` for `build-aux/**`/`*.json` manifest, `ci`, `documentation`) → `acmm:auto-label`
- [ ] `.github/workflows/claude.yml` (copy; `--allowedTools` for meson/pytest/cargo; secret `CLAUDE_CODE_OAUTH_TOKEN`) → `acmm:ai-fix-workflow`, `acmm:github-actions-ai`
- [ ] `.github/workflows/tier-classifier.yml` + `scripts/tier-classify.sh` + `.github/policies/risk-tiers.policy` + `docs/risk-tiers.md` (high: `.github/*`, `scripts/*`, Flatpak manifest, `*.gschema.xml`, `AGENTS.md`, `CLAUDE.md`, `.claude/*`, `prompts/*`, `data/dles.json` schema; medium: `src/*`; low: `docs/*`, `*.md`) → `acmm:tier-classifier`, `aef:change-classification`
- [ ] `docs/security/SECURITY-AI.md` (adapt: in-app browser/WebKitGTK is runtime attack surface; agents never widen Flatpak `finish-args`; DLE URLs are untrusted data) → `acmm:security-ai-md`
- [ ] `docs/reflections/README.md` → `acmm:cross-session-knowledge`, `acmm:reflection-log`

### Phase 4 — L5 Semi-Autonomous (need 4/5; aim 5/5)
- [ ] `docs/metrics/README.md` (catalog of quality gates, coverage floors, PR acceptance, nightly compliance, risk tier; **plus** Dailies' popularity-report metric) → `acmm:public-metrics`
- [ ] `.github/policies/` (risk-tiers.policy from Phase 3) → `acmm:policy-as-code`
- [ ] `claude.yml`, `auto-qa-tuning.json`, `docs/reflections/` from earlier phases cover the rest.

### Phase 5 — L6 (optional; need 9/12). Cheap wins the owner's repos lack: `.github/CODEOWNERS` (`aef:structural-gates`), `docs/runbook/` or `RUNBOOK.md` (`acmm:observability-runbook`; MinimalUI's `docs/runbooks/` misses the pattern by one letter), `docs/agent-tasks/` (`aef:task-traceability`), `.github/workflows/ai-audit.yml` (`aef:audit-trail`), `.github/risk-assessment.yml` (`acmm:risk-assessment-config`). Even with these five, 8/12 = 0.67 < 0.70; you would also need a merge-queue or auto-issue workflow. **Recommendation: do not chase L6**; Hive's own guidance says most mature teams settle at L4–L5. [I]

### Non-ACMM scaffolding to copy anyway (Hive governance + owner convention) [I]
`SECURITY.md` (private vulnerability reporting), `.github/dependabot.yml` (github-actions + pip/cargo), `.github/rulesets/main.json` (required checks: `PR review rubric`, `Build, lint, test`, `Unit-test coverage floors`, `Static checks`; apply with `gh api -X PUT repos/Tim-van-Oudheusden/Dailies/rulesets/<id> --input .github/rulesets/main.json`), `.gitattributes`, `.git-blame-ignore-revs`, `.devcontainer/devcontainer.json` (GNOME SDK image), `docs/postmortems/{README,TEMPLATE}.md`, `BRANDING.md` + `docs/brand/`, `.beads/` only if the owner keeps using Beads. Conventional Commits titles; branch `<type>/<number>-<slug>`; `Fixes #N` in PR body; all Actions pinned to commit SHAs (e.g. `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`, `actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2`, `actions/labeler@bf12e9b00b37c5c0ca2b87b79b2daf7891dbda13 # v7.0.0`, `anthropics/claude-code-action@1d6de8cb0c237e7c15e9e1bdf973826ebae490cc # v1.0.248`, all as of the owner's repos on 2026-10-15).

### Registering Dailies with the owner's hive [I, mechanism V]
1. Push the scaffold; install/authorize the `hive-forge-app` GitHub App on `Tim-van-Oudheusden/Dailies`.
2. Spoke dashboard → **Settings → Repos → add `Dailies`** (or `project.repos` in `hive.yaml`). If `project.checkouts_dir` is set, add a checkout so `AGENTS.md` is injected.
3. Dashboard **ACMM Eval → Re-evaluate**; expect Codebase L5; use **Open All** on any red criterion.
4. Optionally add `.acmm.yml` waivers only for capabilities deliberately moved into Hive (e.g. if `claude.yml` is dropped in favour of Hive's own agents).
5. Keep the hive's operational level at L2–L3 initially; the advisor needs coverage ≥ 40 % and a green-CI streak ≥ 3 before suggesting L3, ≥ 60 %/5/70 % merge success for L4.

### Self-check in CI [I]
Add `scripts/acmm-self-check.py` (port of `scratchpad/scripts/acmm_eval.py`, reading the pattern list vendored from `acmm_criteria.go` with its commit hash) to `nightly-compliance.sh`, so a renamed file that silently drops a level shows up as a red nightly row instead of a surprise gap issue. Re-sync the vendored list when `hivecommons/hive` changes `acmm_criteria.go` (track via the `acmm` label and CHANGELOG).

---

## 10. Open questions / things not verified

- The paper's HTML version (arxiv.org/html/2604.09388v{1,2}) returns 404; level definitions were extracted from the PDF via pdf-parse and may miss table formatting nuances.
- `src/pkg/dashboard/acmm_criteria.go` says "43 repo-universal ACMM criteria"; the slice actually contains 50 entries. I used the code, not the comment.
- Whether the owner's hive (`hive-tall-slug`) is hosted on hive.hivecommons.dev or self-hosted was not checked; registration steps differ slightly (dashboard "Settings → Repos" works for both).
- The Inception scaffold's generated `AGENTS.md`/`CLAUDE.md`/CI content was not inspected (requires a live hive run).
- `hivectl enroll` output and the hub's current L1–L3 wizard range were taken from docs synced from `v5`; the live hub UI may differ.
- Hive Commons' hivecommons.dev page expands ACMM as "AI-native Capability Maturity Model" while every other source says "AI Codebase Maturity Model"; treated as a marketing-copy inconsistency.
- Whether the owner wants Beads (`.beads/`, `bd`) in Dailies is a preference question; it is not an ACMM criterion.

---

## 11. Sources

Primary (cloned 2026-10-15):
- https://github.com/hivecommons/hive — `README.md`, `AGENTS.md`, `ADOPTERS.md`, `src/docs/acmm-policy-matrix.md`, `src/docs/acmm-advisor.md`, `src/docs/acmm-waivers.md`, `src/docs/adr/0003-acmm-autonomy-levels.md`, `src/docs/agents-md.md`, `src/docs/dashboard-sections.md`, `src/docs/hosted-hub.md`, `src/docs/lite-enrollment.md`, `src/docs/getting-started.md`, `src/docs/github-app-setup.md`, `src/docs/inception.md`, `src/docs/compliance.md`, `src/docs/credly-badges.md`, `src/docs/labels-and-control-signals.md`, `src/hive.yaml.example`, `src/pkg/dashboard/acmm_criteria.go`, `src/pkg/dashboard/api_acmm_eval.go`, `src/pkg/dashboard/acmm_waivers.go`, `src/pkg/acmmadvisor/acmmadvisor.go`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/*`
- https://github.com/hivecommons/.github — `GOVERNANCE.md`, `CONTRIBUTING.md`, `ADOPTERS.md`, `.github/ISSUE_TEMPLATE/join-hive-commons.yml`
- https://github.com/Tim-van-Oudheusden/MinimalUI and https://github.com/Tim-van-Oudheusden/website — full trees; ACMM gap issues via `gh issue list -S ACMM --state all`
- https://arxiv.org/abs/2604.09388 and https://arxiv.org/pdf/2604.09388v2 (PDF, 28 pages)
- https://docs.hivecommons.dev (navigation), https://docs.hivecommons.dev/docs/hive/security/acmm-policy-matrix, https://docs.hivecommons.dev/docs/community/join-hive-commons
- https://hivecommons.dev, https://hive.hivecommons.dev/get-started
- `gh release list -R hivecommons/hive` (v5.175.0, 2026-10-15)

---

## Appendix A — Reproduced owner scaffolding (copy sources)

Clone root: `<scratch>/clones/hive-acmm/`. Files below are verbatim from that clone unless marked.

### A.1 `.github/workflows/claude.yml` (MinimalUI)
```yaml
name: Claude Code

# Hands an issue to Claude Code when a maintainer labels it `ai-fix-requested`,
# or when a trusted collaborator mentions @claude on an issue or PR. Claude
# works on a `claude/*` branch and opens a PR; it never pushes to main.
# Needs the CLAUDE_CODE_OAUTH_TOKEN repo secret and the Claude GitHub App.

on:
  issues:
    types: [labeled]
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  pull_request_review:
    types: [submitted]

# Jobs that need more ask for it themselves.
permissions:
  contents: read

concurrency:
  group: >-
    claude-${{ github.event.issue.number || github.event.pull_request.number }}-${{
    (github.event.label.name == 'ai-fix-requested'
    || (contains(format('{0}{1}', github.event.comment.body, github.event.review.body), '@claude')
    && contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.comment.author_association || github.event.review.author_association)))
    && 'queue' || github.run_id }}
  cancel-in-progress: false

jobs:
  claude:
    name: Claude Code
    if: >-
      (github.event_name == 'issues'
        && github.event.label.name == 'ai-fix-requested')
      || (github.event_name == 'issue_comment'
        && contains(github.event.comment.body, '@claude')
        && contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.comment.author_association))
      || (github.event_name == 'pull_request_review_comment'
        && contains(github.event.comment.body, '@claude')
        && contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.comment.author_association))
      || (github.event_name == 'pull_request_review'
        && contains(github.event.review.body, '@claude')
        && contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.review.author_association))
    runs-on: ubuntu-latest
    timeout-minutes: 60
    permissions:
      contents: write
      pull-requests: write
      issues: write
      id-token: write
      actions: read
    steps:
      - name: Refuse fork pull requests
        if: github.event.issue.pull_request || github.event.pull_request
        env:
          GH_TOKEN: ${{ github.token }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.issue.number || github.event.pull_request.number }}
        run: |
          set -euo pipefail
          head_repo="$(gh api "repos/$REPO/pulls/$PR_NUMBER" --jq '.head.repo.full_name // ""')"
          if [ "$head_repo" != "$REPO" ]; then
            echo "::error::Fork pull requests are not supported by the Claude workflow; review them locally."
            exit 1
          fi
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 1
      # (toolchain setup steps: JDK + Gradle in MinimalUI; replace with GNOME SDK / Python / Rust for Dailies)
      - name: Run Claude Code
        # Third-party action pinned to a commit SHA (v1.0.248).
        uses: anthropics/claude-code-action@1d6de8cb0c237e7c15e9e1bdf973826ebae490cc
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          label_trigger: ai-fix-requested
          trigger_phrase: '@claude'
          branch_prefix: claude/
          additional_permissions: |
            actions: read
          claude_args: >-
            --allowedTools "Bash(./gradlew test:*),Bash(./gradlew lint:*),Bash(./gradlew assembleDebug:*),Bash(./gradlew check:*),Bash(./gradlew spotlessApply:*),Bash(./gradlew :core:test:*),Bash(./gradlew :app:testDebugUnitTest:*)"
```
(The two toolchain steps elided above are `actions/setup-java@de7274f081f381c8f8158605e0321c36c376e2e6 # v6.0.1` and `gradle/actions/setup-gradle@3f5f9adaf7d9fecd50b5935e54106014257a94e6 # v6.4.0`.)

### A.2 `.github/workflows/review.yml` + `scripts/pr-review-check.sh` (MinimalUI)
```yaml
name: PR review rubric

on:
  pull_request:
    types: [opened, edited, synchronize, reopened, ready_for_review]

permissions:
  contents: read

jobs:
  rubric:
    name: PR review rubric
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - name: Check title and issue link
        env:
          PR_TITLE: ${{ github.event.pull_request.title }}
          PR_BODY: ${{ github.event.pull_request.body }}
          PR_AUTHOR: ${{ github.event.pull_request.user.login }}
        run: scripts/pr-review-check.sh
      - name: Reviewer rubric
        if: always()
        run: |
          cat >> "$GITHUB_STEP_SUMMARY" <<'EOF'
          ## Reviewer rubric

          Automated above: Conventional Commits title, linked issue. CI covers
          unit tests, Android lint and the debug build.

          Check by hand:

          - [ ] **TDD evidence** — the PR shows a test that failed before the change and passes after.
          - [ ] **Behaviour, not implementation** — tests assert observable output, not private state.
          - [ ] **No test tampering** — existing tests were not weakened to pass; no `@Suppress` added to silence failures.
          - [ ] **Scope** — one issue per PR; unrelated changes split out.
          - [ ] **Dependencies** — none added without approval; any new one pinned in `gradle/libs.versions.toml`.
          - [ ] **Keyboard first** — UI changes are fully usable without touch.
          EOF
```
```bash
#!/usr/bin/env bash
# PR review rubric: the mechanically checkable items of the PR template.
# Reads PR_TITLE, PR_BODY and PR_AUTHOR from the environment; reports every
# failed item and exits 1 if any failed.
set -uo pipefail

title="${PR_TITLE:-}"
body="${PR_BODY:-}"
author="${PR_AUTHOR:-}"
failures=0

fail() {
  echo "::error::$1"
  failures=$((failures + 1))
}

types='build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test'
if [[ "$title" =~ ^($types)(\([a-z0-9._/-]+\))?!?:\ .+ ]]; then
  echo "ok: title follows Conventional Commits"
else
  fail "PR title '$title' must follow Conventional Commits, e.g. 'feat(launcher): add app search' (types: ${types//|/, })"
fi

if [[ "$author" == *"[bot]" ]]; then
  echo "ok: bot author, issue link not required"
elif printf '%s' "$body" |
  grep -Eiq '(^|[^[:alnum:]_])(fix(es|ed)?|close[sd]?|resolve[sd]?|refs?):?[[:space:]]+([[:alnum:]_.-]+/[[:alnum:]_.-]+)?#[0-9]+'; then
  echo "ok: body links a GitHub issue"
else
  fail "PR body must link its GitHub issue, e.g. 'Fixes #123' (see .github/pull_request_template.md)"
fi

[ "$failures" -eq 0 ] || exit 1
```

### A.3 `.github/workflows/pr-metrics.yml` + `scripts/pr-metrics.sh` (MinimalUI, language-agnostic)
```yaml
name: PR metrics

on:
  schedule:
    - cron: '17 6 * * 1'
  workflow_dispatch:
    inputs:
      days:
        description: Reporting window in days
        required: false
        default: '28'

permissions:
  contents: read
  pull-requests: read

jobs:
  acceptance:
    name: PR acceptance rate
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Compute acceptance metric
        env:
          GH_TOKEN: ${{ github.token }}
          REPO: ${{ github.repository }}
          DAYS: ${{ inputs.days || '28' }}
        run: |
          set -euo pipefail
          [[ "$DAYS" =~ ^[0-9]+$ ]] || { echo "::error::days must be a whole number, got '$DAYS'"; exit 1; }
          since="$(date -u -d "${DAYS} days ago" +%Y-%m-%d)"
          gh pr list --repo "$REPO" --state closed --limit 1000 \
            --search "closed:>=${since}" \
            --json number,mergedAt,headRefName,author > prs.json
          scripts/pr-metrics.sh --since "$since" --days "$DAYS" < prs.json | tee -a "$GITHUB_STEP_SUMMARY"
```
```bash
#!/usr/bin/env bash
# PR acceptance metric: of the pull requests closed in the reporting window,
# how many were merged vs. closed without merging, split by agent-authored vs.
# other PRs. Reads the JSON of `gh pr list --json number,mergedAt,headRefName,author`
# on stdin and prints a Markdown table.
#
# usage: pr-metrics.sh --since YYYY-MM-DD --days N
set -uo pipefail

since=""
days=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --since) since="${2:-}"; shift 2 ;;
    --days) days="${2:-}"; shift 2 ;;
    *) echo "usage: $0 --since YYYY-MM-DD --days N" >&2; exit 2 ;;
  esac
done
if [ -z "$since" ] || [ -z "$days" ]; then
  echo "usage: $0 --since YYYY-MM-DD --days N" >&2
  exit 2
fi

jq -r --arg since "$since" --arg days "$days" '
  def agent: ((.headRefName // "") | startswith("claude/"))
    or ((.author.login // "") | IN("app/hive-forge-app", "hive-forge-app[bot]"));
  def row($label; $set):
    ($set | length) as $total
    | ($set | map(select(.mergedAt != null)) | length) as $merged
    | "| \($label) | \($total) | \($merged) | \($total - $merged) | "
      + (if $total == 0 then "n/a"
         else "\(($merged * 1000 / $total | round) / 10)%" end)
      + " |";
  if type != "array" then error("expected a JSON array of pull requests") else . end
  | map(select(agent)) as $agent
  | map(select(agent | not)) as $other
  | "## PR acceptance metric",
    "",
    "PRs closed since \($since) (last \($days) days).",
    "",
    "| Source | Closed | Merged | Rejected | Acceptance |",
    "| --- | ---: | ---: | ---: | ---: |",
    row("Agent"; $agent),
    row("Other"; $other),
    row("**All**"; .),
    "",
    "Agent: head branch `claude/*` or author `hive-forge-app` (GitHub App)."
'
```

### A.4 `.github/workflows/tier-classifier.yml`, `scripts/tier-classify.sh`, `.github/policies/risk-tiers.policy` (website variant)
```yaml
name: Change classification

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]

permissions:
  contents: read

jobs:
  classify:
    name: Risk tier
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Check out the base branch's classifier
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          path: .tier-base
          persist-credentials: false
      - name: Classify changed files
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: |
          set -euo pipefail
          classifier=.tier-base/scripts/tier-classify.sh
          if [ ! -f "$classifier" ]; then
            echo "::warning title=Risk tier::base branch has no classifier; using this PR's own copy"
            classifier=scripts/tier-classify.sh
          fi
          git diff --name-only --no-renames "${BASE_SHA}...${HEAD_SHA}" | bash "$classifier" > "$RUNNER_TEMP/tier.txt"
          tier="$(sed -n 's/^tier=//p' "$RUNNER_TEMP/tier.txt")"
          echo "::notice title=Risk tier::${tier} (see docs/risk-tiers.md)"
          {
            echo "## Risk tier: ${tier}"
            echo
            echo "Highest tier of any changed file wins; see \`docs/risk-tiers.md\` for what each tier asks of reviewers."
            echo
            echo '```'
            grep -v '^tier=' "$RUNNER_TEMP/tier.txt" || true
            echo '```'
          } >> "$GITHUB_STEP_SUMMARY"
```
```bash
#!/usr/bin/env bash
# Change classification: reads changed file paths (one per line) on stdin,
# prints each path with its risk tier, then the PR's overall tier as
# `tier=<low|medium|high>`. The highest tier of any changed file wins.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
policy="${RISK_TIER_POLICY:-$ROOT/.github/policies/risk-tiers.policy}"

names=(_ low medium high)
declare -A tier_rank=([low]=1 [medium]=2 [high]=3)

fail() {
  echo "tier-classify: $*" >&2
  exit 2
}

[ -r "$policy" ] || fail "cannot read policy file ${policy}"

rule_ranks=()
rule_globs=()
lineno=0
while IFS=$' \t\r' read -r tier glob extra || [ -n "${tier:-}" ]; do
  lineno=$((lineno + 1))
  [ -z "${tier:-}" ] || [[ $tier == \#* ]] && continue
  [ -n "${glob:-}" ] && [ -z "${extra:-}" ] \
    || fail "${policy}:${lineno}: expected '<tier> <glob>'"
  [ -n "${tier_rank[$tier]:-}" ] \
    || fail "${policy}:${lineno}: unknown tier '${tier}' (expected low, medium or high)"
  rule_ranks+=("${tier_rank[$tier]}")
  rule_globs+=("$glob")
done < "$policy"

max=1
while IFS= read -r path || [ -n "$path" ]; do
  [ -n "$path" ] || continue
  r=2
  for i in "${!rule_globs[@]}"; do
    # shellcheck disable=SC2053
    if [[ $path == ${rule_globs[i]} ]]; then
      r="${rule_ranks[i]}"
      break
    fi
  done
  printf '%-6s  %s\n' "${names[$r]}" "$path"
  [ "$r" -gt "$max" ] && max="$r"
done

echo "tier=${names[$max]}"
```
```
# Risk-tier policy for pull requests. Evaluated by scripts/tier-classify.sh;
# what each tier asks of reviewers is in docs/risk-tiers.md.
#
# One rule per line: `<tier> <glob>`, where tier is low, medium or high.
# A changed path takes the tier of the FIRST rule whose glob matches it, so
# high-risk rules come before the broad low-risk ones (AGENTS.md is high even
# though *.md is low). `*` matches across `/`. A path matching no rule is
# medium. Blank lines and lines starting with `#` are ignored.

# CI gates, review rubric, release job, and this policy itself.
high    .github/*

# Runtime and image configuration.
high    deploy/*
high    Dockerfile*
high    */Dockerfile
high    .devcontainer/*

# Gate and release tooling.
high    scripts/*

# Dependencies (supply chain).
high    package.json
high    */package.json
high    bun.lock

# Agent instructions and governance.
high    AGENTS.md
high    CLAUDE.md
high    .claude/*
high    .cursor/*
high    .beads/*
high    prompts/*

# Prose and static assets that do not execute.
low     content/*
low     docs/*
low     research/*
low     public/*
low     *.md
```

### A.5 `.github/workflows/labeler.yml` (identical in both repos) and `.github/labeler.yml` (MinimalUI)
```yaml
name: Labeler

# Applies path-based labels from .github/labeler.yml to pull requests.
# pull_request_target runs against the base branch's config so fork PRs can be
# labelled too; the job never checks out PR code.

on:
  pull_request_target:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  label:
    name: Label by changed paths
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/labeler@bf12e9b00b37c5c0ca2b87b79b2daf7891dbda13 # v7.0.0
```
```yaml
# Path-based PR labels, applied by .github/workflows/labeler.yml (actions/labeler).
app:
  - changed-files:
      - any-glob-to-any-file: 'app/**'
core:
  - changed-files:
      - any-glob-to-any-file: 'core/**'
build:
  - changed-files:
      - any-glob-to-any-file:
          - 'gradle/**'
          - '*.gradle.kts'
          - 'gradle.properties'
          - 'gradlew'
          - 'gradlew.bat'
          - '.devcontainer/**'
          - 'Dockerfile*'
          - '**/Dockerfile'
          - '.dockerignore'
          - '.gitattributes'
ci:
  - changed-files:
      - any-glob-to-any-file: ['.github/**', 'scripts/**', 'tooling/**', '.beads/**']
documentation:
  - changed-files:
      - any-glob-to-any-file:
          - 'docs/**'
          - '*.md'
          - '.github/copilot-instructions.md'
          - '.cursor/**'
          - '.claude/**'
          - 'prompts/**'
```

### A.6 `.github/workflows/nightly-compliance.yml` + `scripts/nightly-compliance.sh` (website variant, simplest)
```yaml
name: Nightly compliance

on:
  schedule:
    - cron: '23 3 * * *'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  compliance:
    name: Nightly compliance
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      # (toolchain setup: oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6 # v2.2.0 in website)
      - name: Run compliance checks
        run: scripts/nightly-compliance.sh > nightly-compliance.md
      - name: Publish job summary
        if: always()
        run: cat nightly-compliance.md >> "$GITHUB_STEP_SUMMARY"
      - name: Upload compliance report
        if: always()
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: nightly-compliance
          path: nightly-compliance.md
```
```bash
#!/usr/bin/env bash
# Print a Markdown nightly compliance report for the repository to stdout.
# Checks that can go stale without a code change run on a schedule.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

commit="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"
failed=0

row() {
  if [ "$2" -eq 0 ]; then
    echo "| $1 | ✅ pass |"
  else
    echo "| $1 | ❌ fail |"
    failed=1
  fi
}

echo "# Nightly compliance"
echo
echo "Commit: \`${commit}\`"
echo
echo "| Check | Result |"
echo "| ----- | ------ |"

# website: `bun audit --audit-level=high` with an AUDIT_IGNORE list; MinimalUI: Dependabot alerts via gh api + wrapper validation.
# Dailies: pip-audit / cargo audit, Flatpak runtime EOL, DLE URL liveness.
bun audit --audit-level=high >&2
row "Dependency audit (high+)" $?

exit "$failed"
```

### A.7 `.github/workflows/coverage-gate.yml` (website) and `.github/auto-qa-tuning.json`
```yaml
name: Coverage gate

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.sha }}
  cancel-in-progress: true

jobs:
  coverage:
    name: Unit-test coverage floors
    runs-on: ubuntu-latest
    timeout-minutes: 20
    # Floors live in .github/auto-qa-tuning.json, tuned by scripts/auto-qa-tuner.ts.
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      # (toolchain setup)
      - name: Back-end coverage
        run: |
          funcs="$(jq -er '.floors["back-end"].functions' .github/auto-qa-tuning.json)"
          lines="$(jq -er '.floors["back-end"].lines' .github/auto-qa-tuning.json)"
          scripts/coverage-check.sh back-end "$funcs" "$lines"
```
```json
{
  "margin": 2,
  "floors": {
    "back-end": { "functions": 95, "lines": 90 },
    "shared":   { "functions": 90, "lines": 90 },
    "front-end": { "functions": 91, "lines": 91 }
  }
}
```

### A.8 `.github/workflows/quality-report.yml` (website)
```yaml
name: Quality report

on:
  push:
    branches: [main]
  schedule:
    - cron: "17 6 * * 1"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  report:
    name: Quality report
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      # (toolchain setup)
      - name: Generate quality report
        run: scripts/quality-report.sh > quality-report.md
      - name: Propose coverage floors
        if: always()
        run: |
          echo >> quality-report.md
          bun scripts/auto-qa-tuner.ts --report quality-report.md --write >> quality-report.md
      - name: Publish job summary
        if: always()
        run: cat quality-report.md >> "$GITHUB_STEP_SUMMARY"
      - name: Upload quality report
        if: always()
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: quality-report
          path: quality-report.md
      - name: Upload tuned coverage floors
        if: always()
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: auto-qa-tuning
          path: .github/auto-qa-tuning.json
```

### A.9 `.github/workflows/auto-review.yml` (MinimalUI; language-agnostic) — key shape
Trigger `issue_comment: created`; `if: github.event.issue.pull_request && startsWith(github.event.comment.body, '/apply-suggestions') && contains(fromJSON('["OWNER", "MEMBER", "COLLABORATOR"]'), github.event.comment.author_association)`; permissions `contents: write`, `pull-requests: write`; steps: react 👀, resolve PR head (refuse forks; refuse heads committed after the comment), check out default-branch `scripts/apply-review-suggestions.sh` into `trusted/` and PR head into `pr/` (both `persist-credentials: false`), fetch review comments via `gh api --paginate`, run `../trusted/scripts/apply-review-suggestions.sh`, commit as `github-actions[bot]` with message `chore(review): apply review suggestions (#N)`, push `HEAD:refs/heads/$HEAD_REF` with the token in an `extraheader`, post report comment. Full file: `clones/hive-acmm/MinimalUI/.github/workflows/auto-review.yml` (6.3 KB) and `scripts/apply-review-suggestions.sh`.

### A.10 `.claude/settings.json` (website variant — closer to a non-Gradle project)
```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(bun run test)", "Bash(bun run test *)", "Bash(bun test)", "Bash(bun test *)",
      "Bash(bun run typecheck)", "Bash(bun run lint)", "Bash(bun run build)",
      "Bash(bun run --filter *)", "Bash(bun install --frozen-lockfile)",
      "Bash(git status)", "Bash(git status *)", "Bash(git diff)", "Bash(git diff *)",
      "Bash(git log *)", "Bash(git show *)",
      "Bash(bd ready)", "Bash(bd show *)", "Bash(bd prime)"
    ],
    "ask": [
      "Bash(bun add *)", "Bash(bun remove *)", "Bash(bun update *)", "Bash(npm install *)",
      "Bash(git rebase *)", "Bash(git reset *)", "Bash(git clean *)", "Bash(git branch -D *)",
      "Bash(gh pr merge *)"
    ],
    "deny": [
      "Read(./.env)", "Read(./.env.*)", "Read(./**/.env)", "Read(./**/.env.*)",
      "Read(./.beads-credential-key)",
      "Edit(./bun.lock)", "Write(./bun.lock)",
      "Bash(git push --force *)", "Bash(git push -f *)", "Bash(git push * --force)", "Bash(git push * -f)",
      "Bash(git commit --no-verify *)", "Bash(git commit * --no-verify *)", "Bash(git commit * --no-verify)",
      "Bash(* --legacy-peer-deps *)", "Bash(* --legacy-peer-deps)",
      "Bash(bun add * --force *)", "Bash(bun add * --force)", "Bash(bun install --force *)", "Bash(bun install --force)",
      "Bash(rm -rf /)", "Bash(rm -rf ~)", "Bash(rm -rf ~/*)", "Bash(sudo *)"
    ]
  }
}
```

### A.11 `.github/pull_request_template.md` (MinimalUI)
```markdown
<!--
Title must follow Conventional Commits, e.g. `feat(launcher): ...`, `fix(input): ...`, `docs(agents): ...`.
-->
## Summary

**What:** <!-- one or two sentences: the change -->

**Why:** <!-- the problem it solves; link the GitHub issue -->

Fixes #<!-- issue number -->

## Testing

<!-- Evidence, not claims. Paste failing-before/passing-after output for the changed path. -->

- [ ] New/changed behaviour covered by a test written first (TDD); test confirmed failing before implementation
- [ ] Test asserts observable behaviour, never implementation internals
- [ ] UI changes checked on a device or emulator (keyboard-only navigation included)

## Quality gates

- [ ] `./gradlew check` passes (unit tests, lint, formatting; `./gradlew spotlessApply` fixes formatting)
- [ ] `./gradlew assembleDebug` passes

## Notes for the reviewer

<!-- Anything risky, out of scope, or needing a second look. -->

## Dependencies

<!-- Only if changed:
- Name, explicit version, and why (ask before adding)
- Added to gradle/libs.versions.toml, never inline in a build file
-->
- None
```

### A.12 `.github/ISSUE_TEMPLATE/issue.yml` (MinimalUI) — shape
GitHub issue form: markdown intro (Conventional Commits title), dropdown **Type** (Bug `type::bug`, Feature `type::feature`, Task `type::task`, Chore `type::chore`, Refactor; required), dropdown **Scope** (App `app`, Core logic `core`, Tooling / CI `ci`, Documentation `documentation`, Other), dropdown **Priority** (`priority::critical|high|medium|low`, default Medium), input **Device and Android version**, textarea **Description** (required), textarea **Acceptance criteria**, checkbox "Followed the workflow in AGENTS.md". Full YAML: `clones/hive-acmm/MinimalUI/.github/ISSUE_TEMPLATE/issue.yml`.

### A.13 `CLAUDE.md` / `.github/copilot-instructions.md` / `.cursor/rules/agent-guidance.mdc` (MinimalUI; same body)
```markdown
# CLAUDE.md

Guidance for Claude-family agents working in this repository.
**`AGENTS.md` at the repo root is the authoritative agent instructions file —
when this file conflicts with AGENTS.md, AGENTS.md wins.**

## Issue tracking

- GitHub issues are the primary source of truth for all work. Read and claim
  issues through the GitHub API (`gh` CLI), never via local mirrors; an issue
  closes when the PR that says `Fixes #<number>` merges.
- Beads (`bd`) mirrors issue state locally; before any `bd github` command run
  `export GITHUB_TOKEN="$(gh auth token)"`. After GitHub-only changes use
  `bd github sync --pull-only`. Never make a standalone sync/`issues.jsonl`
  commit.
- Work one issue at a time; pick work via `bd ready` / `gh issue list`, and let
  child/follow-up issues wait for their parents.

## Engineering rules

- <stack summary and module layout>
- TDD is mandatory for code changes: one failing test first, implement, run the
  failing test, then the full suite. Never modify tests to make them pass;
  never add `@Suppress` to silence failures.
- Test behaviour, not implementation. Put logic in `core` so it runs as a plain
  unit test; keep framework code thin.
- Quality gates after any change: <commands>.
- No new dependencies without explicit approval; always an exact version.
- Conventional Commits, one commit per issue, referencing the issue number.
- Land each issue through a pull request: branch `<type>/<number>-<slug>` off
  `main`, `git push -u origin HEAD`, then `gh pr create` with
  `Fixes #<number>` in the body. `main` is protected; the maintainer merges
  once the required checks pass.

See `CONTRIBUTING.md` for contributor workflow and `AGENTS.md` for the full
agent ruleset.
```
The Cursor file adds front-matter:
```
---
description: "Repository-wide guidance for Cursor agents in this workspace."
alwaysApply: true
---
```
`AGENTS.md` (MinimalUI, 2.2 KB) adds sections **Issue Tracking** (GitHub primary, Beads mirror), **Sessions with GitHub issues**, **Session Completion** (7 numbered steps ending "overwrite the 'Latest session' section of `.claude/session-summary.md` … Log a correction round in `.claude/memory/corrections.tsv`; write the *why* in `docs/reflections/`"), **Git and Version Management** (ruleset applied with `gh api -X PUT repos/<owner>/<repo>/rulesets/<id> --input .github/rulesets/main.json`), **Testing**, **Dependency Management**. Full text: `clones/hive-acmm/MinimalUI/AGENTS.md`.

### A.14 Learning artefacts (MinimalUI)
`.claude/memory/corrections.tsv`:
```
# Corrections

Correction log for agent work in this repository. Append one line per
correction round (tab-separated): ISO date | what went wrong | correction +
where it is encoded.

Format: `YYYY-MM-DD\t<behaviour>\t<correction (file:rule)>`

## 2026

- 2026-10-12	Tooling tests: planned to skip jq-based script tests ...	Never skip on a missing tool; ... (`AGENTS.md`: never weaken tests).
```
`.claude/session-summary.md`: header explaining purpose, then `## Latest session` with **Date**, **Worked**, **Outcome**, **Open follow-ups**, **Notes for next session**.
`docs/reflections/README.md`: purpose; table of the three artefacts (`session-summary.md` overwritten each session; `corrections.tsv` append-only; `docs/reflections/` one file per reflection `YYYY-MM-DD-short-slug.md` with **Context / What happened / Lesson / Encoded in**); index.
`prompts/README.md`: lists `code-review.md` (two-axis review checklist) and `pull-request.md` (PR body from issue); usage line `@claude review this PR using prompts/code-review.md against issue #<number>`.
`.claude/skills/github-issue-flow/SKILL.md`: front-matter `name`, `description`; sections 1. Start an issue (`gh issue list -S "is:open"`, `gh issue view`, `gh issue edit --add-assignee @me`, branch), 2. Implement (TDD, gates, conventional commit), 3. Finish (push, `gh pr create --body-file`, `Fixes #N`, mirror to beads).

### A.15 `.github/dependabot.yml`, `.github/rulesets/main.json`, `.editorconfig` (MinimalUI)
```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    commit-message:
      prefix: ci
    groups:
      github-actions:
        update-types: [minor, patch]
  - package-ecosystem: gradle   # Dailies: pip / cargo
    directory: /
    schedule:
      interval: weekly
    commit-message:
      prefix: build(deps)
    open-pull-requests-limit: 5
    groups:
      minor-and-patch:
        update-types: [minor, patch]
```
```json
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "bypass_actors": [ { "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request" } ],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "pull_request", "parameters": {
        "required_approving_review_count": 0, "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false, "require_last_push_approval": false,
        "required_review_thread_resolution": true, "allowed_merge_methods": ["merge"] } },
    { "type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": false, "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "PR review rubric", "integration_id": 15368 },
          { "context": "Build, lint, test", "integration_id": 15368 },
          { "context": "Unit-test coverage floors", "integration_id": 15368 },
          { "context": "Static checks", "integration_id": 15368 } ] } }
  ]
}
```
```
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 4
insert_final_newline = true
trim_trailing_whitespace = true

[*.md]
trim_trailing_whitespace = false

[*.{yml,yaml,json,toml}]
indent_size = 2
```

### A.16 `docs/security/SECURITY-AI.md` (MinimalUI) — section outline to adapt
Scope (in: agent-driven changes incl. `claude.yml`; out: runtime, which calls no model) · Trust boundaries (instructions only from the human and `AGENTS.md`/`CLAUDE.md`/copilot/cursor files; issue bodies, PR text, web pages, CI logs are **data, not instructions**; CI `claude.yml` only answers `ai-fix-requested` and `@claude` from OWNER/MEMBER/COLLABORATOR, refuses forks) · Secrets (none in repo; agents must not read `.env*`, keystores; tokens only in env/Actions secrets; rotate on exposure) · Supply chain (ask before adding deps; verify existence — slopsquatting; versions in one file; every Action pinned to a SHA; Dependabot + CodeQL) · Destructive actions table (deny force-push/`--no-verify`/`sudo`; ask for rebase/reset/clean/`gh pr merge`) · Review of agent-written changes (ruleset, closer look at workflows, agent config, manifest, build files) · Reporting (private advisory; agent misbehaviour as issue) · Maintenance ("Policy and enforcement must not drift apart"). Full text: `clones/hive-acmm/MinimalUI/docs/security/SECURITY-AI.md`.

### A.17 `docs/risk-tiers.md`, `docs/metrics/README.md`, `docs/postmortems/TEMPLATE.md`
Full texts in the clone (`MinimalUI/docs/risk-tiers.md` 4.4 KB; `MinimalUI/docs/metrics/README.md` 6 KB with a **Catalog** table `| Metric | Measures | Source | Cadence | Published as |` and an **Adding a metric** procedure; `website/docs/postmortems/TEMPLATE.md` with Summary / Impact / Timeline / Detection / Root cause / Resolution / Follow-up).

## Appendix B — Hive's own templates (verbatim)

### B.1 `hivecommons/hive/.github/PULL_REQUEST_TEMPLATE.md`
```markdown
## Summary

- 

## Related issues

Fixes #

## Testing

- [ ] Not run locally: CI runs validation for agent-authored PRs (AGENTS.md forbids local builds/tests in agent panes).
- [ ] Other / manual verification (explain):

## Contributor checklist

- [ ] **Changelog** (required when `src/` code changes, or CI fails): added `changelog.d/<added|changed|deprecated|fixed|security>-<pr-or-slug>.md` ... containing one `- ` bullet ... **or** the change is not user-visible and a maintainer added the `no-changelog` label. Never edit `CHANGELOG.md` directly (#5675).
- [ ] PR targets the correct release line (`v5` by default; ...).
- [ ] Title uses the repo emoji convention, for example `📖 docs: ...`, `🐛 fix: ...`, or `✨ feature: ...`.
- [ ] Commits include DCO sign-off (`git commit -s`).
- [ ] Docs, examples, and policies are updated when behavior changes.
- [ ] No secrets, credentials, or local runtime state are committed.
```
(The collapsible "Adding or changing a CLI backend?" block is omitted here; see the clone.)

### B.2 `hivecommons/hive/.github/ISSUE_TEMPLATE/bug_report.md`
```markdown
---
name: Bug report
about: Report a reproducible problem in Hive
title: "🐛 bug: "
labels: bug
assignees: ""
---

## What happened?
## Expected behavior
## Reproduction steps
1.
2.
3.
## Environment
- Branch/version: `v2` / commit SHA / release tag:
- Deployment method: Docker Compose / Kubernetes / local binary / Hive Hub / other:
- Operating system or Kubernetes version:
- Relevant configuration (redact secrets):
## Logs or screenshots
## Additional context
```
`config.yml`: `blank_issues_enabled: true`, contact link "Join our Discord" → https://hivecommons.dev/discord.

### B.3 `hivecommons/hive/AGENTS.md`
```markdown
# Agent instructions for hivecommons/hive

These rules apply to every AI agent (hive agents, Copilot CLI, Claude Code, Codex, …) working in this repository. Human contributor guidance lives in [CONTRIBUTING.md](CONTRIBUTING.md); where the two differ for agents, this file wins.

## Testing: CI runs the tests, you do not

- **Do not run `go test`, `go build ./...`, `go vet`, `golangci-lint`, or the docs/citation guards locally.** Commit, push, open the PR, and read the CI results (`gh pr checks <n>`, then the failing job log). ...
- If CI fails, fix from the job log and push again. Do not "reproduce locally first". ...
- The only local check worth running is `gofmt -l` on files you changed.
- **Never run this repository's test suite from inside an agent pane.** ...

## Working style

- Keep changes surgical and PR-sized; one concern per PR.
- Every PR needs a `changelog.d/<category>-<slug>.md` fragment (`added|changed|deprecated|fixed|security`) whose body is a single `- ` bullet. ...
- Sign commits (`git commit -s`); PR titles start with an emoji (`✨` feature, `🐛` fix, `📖` docs, `🌱` chore, `⚠️` breaking).
- Do not edit `src/docs/api-reference.md` line citations by hand; ...
```

### B.4 `hivecommons/.github/.github/ISSUE_TEMPLATE/join-hive-commons.yml` — fields
`name: "Propose a project to join Hive Commons"`, `title: "[project proposal] <project name>"`, `labels: ["project-proposal"]`; inputs: Project name*, Repository URL*, What does the project do?*, How does it fit the Hive Commons family?*, License* (dropdown `Apache-2.0` / `Other OSI-approved (please note below; relicensing may be required)`), Community commitments (checkboxes: DCO sign-off on every commit*, CNCF Code of Conduct*, willing to move under hivecommons org, maintainer attends biweekly meeting for first quarter), Maintainers*, Adoption and maturity, Anything else.

## Appendix C — Local evaluator used for §8 (adoptable as a CI self-check)
`<scratch>/scripts/acmm_eval.py` — parses `universalCriteria` from `acmm_criteria.go` and applies `checkCriterion` (any pattern exists; `/` suffix = directory) and `scoreResults` (0.70 threshold, consecutive-pass level, L0→L1 rule) to one or more local directories. Usage: `python3 -I acmm_eval.py <path/to/acmm_criteria.go> <repo-dir>...`.
