# AI operations runbook

How to watch the agents working in this repository and how to debug and stop them when they misbehave.
[`multi-agent.md`](multi-agent.md) is the coordination contract that says what each agent is supposed to do,
[`metrics/`](metrics/README.md) catalogues what is measured, and [`security/SECURITY-AI.md`](security/SECURITY-AI.md)
covers trust boundaries. This page is the day-to-day side: where to look, what a healthy state looks like, and what to
do when something is stuck.

There is no alerting backend. Every signal below is a GitHub Actions run, a label or an issue, read with `gh` or on the
Actions tab. The exception is the nightly compliance run: after each run on `main`, `auto-issues.yml` opens, updates or
closes the `ci: nightly compliance: N failing checks` issue on its own.

The launcher itself runs no AI and sends nothing anywhere. For a bad release see
[`runbooks/bad-release.md`](runbooks/bad-release.md), and for the weekly data files
[`runbooks/popularity.md`](runbooks/popularity.md) and [`runbooks/re-enable-cron.md`](runbooks/re-enable-cron.md).

## The automations

| Automation | Runs as | Starts on | Stop it with |
| --- | --- | --- | --- |
| Claude Code in CI (`claude.yml`) | `GITHUB_TOKEN`, plus the Claude GitHub App and the `CLAUDE_CODE_OAUTH_TOKEN` secret | An `ai-fix-requested` label a person applies, or `@claude` from an `OWNER`, `MEMBER` or `COLLABORATOR` | [Stopping the agents](#stopping-the-agents) |
| Merge queue (`merge-queue.yml`, `scripts/merge-queue.sh`) | `GITHUB_TOKEN` | A required check succeeds, a draft is marked ready, a person removes `hold`, `blocked`, `sentinel-alert` or `automated`, or a manual run | The same table |
| Apply review suggestions (`auto-review.yml`) | `GITHUB_TOKEN` | A `/apply-suggestions` comment on a PR from an `OWNER`, `MEMBER` or `COLLABORATOR` | The same table |
| Hive agents | The `hive-worker-bee` GitHub App (formerly `hive-forge-app`), outside this repository | Hive's own scheduler and the Hive dashboard | The same table |
| Weekly reports (`pr-metrics.yml`, `strategy-report.yml`, `ai-audit.yml`, `quality-report.yml`) | `GITHUB_TOKEN`, read-only | Mondays at 06:17 UTC, and a manual run | They only read; no need to stop them |
| Nightly compliance (`nightly-compliance.yml`) and `auto-issues.yml` | `GITHUB_TOKEN`; the `link-status` and `checker-pin` jobs use the `bot` environment's App | 03:23 UTC nightly, Sunday link check | The same table |
| Dependabot (`.github/dependabot.yml`) | `app/dependabot` | Its schedule | Close its PRs; turn off version updates in the repository's settings |

## Where to look

| Question | Signal | Command |
| --- | --- | --- |
| What are agents working on? | Open PRs by head branch: `claude/*` (Claude Code in CI), `<type>/<N>-…` or `<agent>/…` (CLI agents, Hive), `dependabot/*` | `gh pr list --json number,title,headRefName,author,labels` |
| Who holds an issue? | Assignee, a Hive `hive:claim` comment, or a `hive/claimed-by-<agent>` label | `gh issue view <N> --json assignees,labels,comments` |
| What is queued for Claude Code? | Issues labelled `ai-fix-requested` | `gh issue list --label ai-fix-requested` |
| Did Claude Code run, and how did it end? | `Claude Code` workflow runs | `gh run list --workflow claude.yml` |
| Why is a PR not merging? | Merge queue runs and their `::notice` lines, the `hold`, `blocked`, `sentinel-alert` and `automated` labels, the merge state | `gh run list --workflow merge-queue.yml`, `gh pr view <N> --json mergeStateStatus,isDraft,labels` |
| How risky is a PR? | The `Risk tier` job summary of the `Change classification` workflow; the rules are in `.github/risk-assessment.yml` | `git diff -z --name-only --no-renames origin/main...<branch> \| scripts/tier-classify.sh -z` |
| What may each workflow's token do? | `.github/policies/workflow-permissions.yml`, checked by `tests/tooling/test_workflows.py` | `pytest tests/tooling/test_workflows.py` |
| Who must review a PR? | `.github/CODEOWNERS` names the maintainer for every high-risk path | `gh pr view <N> --json reviewRequests` |
| Are agent PRs being accepted? | Weekly `PR metrics` job summary | `gh workflow run pr-metrics.yml -f days=28` |
| Is the backlog shrinking? Which ACMM gaps are open? | Weekly `Strategy report` job summary | `gh workflow run strategy-report.yml -f days=28` |
| What did each agent merge, and with which model? | Weekly `AI audit trail` job summary and `ai-audit` artifact (kept 90 days) | `gh workflow run ai-audit.yml -f days=7` |
| Is `main` healthy? | `Quality report` (every push to `main`), `Nightly compliance`, the open `ci: nightly compliance: …` issue | `gh run list --branch main --limit 20`, `gh issue list --label ci` |
| How does an issue link to its change? | The issue → branch → commit → PR chain in [`agent-tasks/`](agent-tasks/README.md) | `gh issue view <N> --json closedByPullRequestsReferences` |
| Have agents been corrected before? | `.claude/memory/corrections.tsv`, [`reflections/`](reflections/README.md) | — |

## Routine checks

- **Every Monday**, after 06:17 UTC: read the `PR metrics`, `Strategy report`, `AI audit trail` and `Quality report`
  job summaries. Look for an agent acceptance rate that keeps falling, a `stage/*` label where issues pile up, merges
  whose source you cannot account for, and a coverage floor proposal (the `auto-qa-tuning` artifact) waiting to be
  committed.
- **When a PR you expect to merge has not merged within a day**, work through
  [A PR does not merge](#a-pr-does-not-merge).
- **When the nightly compliance issue opens**, fix it like any other issue; the next fully green run on `main` closes
  it.

## Playbooks

### Claude Code did not pick up an `ai-fix-requested` issue

`gh run list --workflow claude.yml` lists one run per label, comment or review event:

- **`skipped`** is expected for every other event. Only an `ai-fix-requested` label that a person applies passes the
  job's `if`; a comment or review passes only when it mentions `@claude` and its author is an `OWNER`, `MEMBER` or
  `COLLABORATOR`.
- **`skipped` on the `issues` event that labelled the issue** means a bot added the label (the Hive ACMM evaluation
  files its issues already labelled `ai-fix-requested`, as `hive-worker-bee`). The job answers only a person's label;
  `claude-code-action` would refuse a bot sender anyway ("Workflow initiated by non-human actor"). To hand the issue
  over, first check that no one holds it (no assignee, no `hive/claimed-by-<agent>` or `hive/in-progress` label, no
  open PR), then a maintainer removes the label and adds it again:
  `gh issue edit <N> --remove-label ai-fix-requested && gh issue edit <N> --add-label ai-fix-requested`.
- **`failure` at "Refuse fork pull requests"**: the PR comes from a fork. Review it locally; the workflow never runs
  fork code.
- **`failure` at any other step**: read the log (`gh run view <run-id> --log-failed`). An authentication error means
  the `CLAUDE_CODE_OAUTH_TOKEN` secret has expired or is missing.

### A PR does not merge

The merge queue only picks a PR that meets every condition in [`multi-agent.md`](multi-agent.md#merge-queue). Check
them in order:

1. **Draft or a keep-out label:** `gh pr view <N> --json isDraft,labels`. `hold` is the maintainer's stop sign, Hive
   sets it on its own PRs too, and the queue sets it on a PR that failed verification. `blocked` waits on something
   outside the repository. `sentinel-alert` is Hive's flag on a sensitive change: review the diff against the findings
   in its comment and remove the label (`gh pr edit <N> --remove-label sentinel-alert`) only once you are satisfied.
   `automated` marks a PR a workflow opened; the queue leaves it to its own policy, so the maintainer merges it (the
   weekly popularity PR merges itself).
2. **Required checks:** `gh pr view <N> --json mergeStateStatus` must be `CLEAN`. `BLOCKED` means one of the required
   checks (`PR review rubric`, `Build, lint, test`, `Unit-test coverage floors`, `Static checks`, `Flatpak (x86_64)`;
   `.github/rulesets/main.json`) failed or has not run, or a review thread is unresolved. `BEHIND` and `DIRTY` mean the
   branch needs a rebase or a conflict fixed.
3. **High risk:** the queue leaves high-risk PRs for the maintainer and logs `#<N> is high risk` as a notice in its
   run. The tier comes from `.github/risk-assessment.yml` ([`risk-tiers.md`](risk-tiers.md)), and `.github/CODEOWNERS`
   has requested the maintainer's review on them. Dependabot's PRs change workflow or script-lock files, so they are
   high risk too.
4. **Fork:** the queue never picks a PR from a fork.

If the PR meets every condition and still sits there, no event has started the queue since it became ready (a label a
bot removed starts no run). Drain the queue by hand with `gh workflow run merge-queue.yml`.

### The merge queue put `hold` on a PR

The queue merged the PR onto the latest `main` and the `Build, lint, test` commands (lint, format check, the unit,
script, tooling and data tests, the schema validation) failed on the result; its comment on the PR links the failed
run. Most often a PR that merged in the meantime conflicts with this one. Rebase on `main`, fix it, push, then remove
the label (`gh pr edit <N> --remove-label hold`) to queue the PR again.

### `main` shows no CI run after a queued merge

A merge made with `GITHUB_TOKEN` starts no push workflows and closes no issue, so after each merge the queue closes the
issues the PR links with `Fixes #N` and starts the push workflows on `main` itself. If those runs are missing, look at
the queue's `Merge` job (`land`), then start them by hand:
`for w in ci.yml coverage-gate.yml pages.yml quality-report.yml windows.yml; do gh workflow run "$w" --ref main; done`.
Close any issue the merged PR linked that is still open.

### The PR review rubric fails

`scripts/pr-review-check.sh` has two requirements: a Conventional Commits title, and a body that links the issue
(`Fixes #<N>`, or `Refs #<N>` for partial work). Bot authors (`*[bot]`) are exempt from the link. Edit the PR title or
body and the check runs again; no push is needed. The rest of the rubric (TDD evidence, scope, dependencies,
`finish-args`) is the reviewer's checklist in that run's job summary.

### A workflow fails with a permissions error

Every workflow's `permissions:` blocks must equal its rule in `.github/policies/workflow-permissions.yml`; a mismatch
fails `tests/tooling/test_workflows.py` in CI. Widening a grant is a change to that file and to the workflow. Both are
high risk, so the maintainer reviews and merges it; an agent never widens a grant on its own.

### Two agents worked the same issue

Agents claim an issue by assigning it, or with a Hive claim comment and `hive/claimed-by-<agent>` label
([the shared queue](multi-agent.md#the-shared-queue)). Find the competing PRs with
`gh pr list --state all --search "<N>"`, keep the one from the agent holding the claim, and close the other with a
comment linking it. If an agent ignored a claim it could see, treat it as agent misbehaviour (below).

### An agent acted outside its instructions

Ignored rules, an injection attempt that got through, changes outside the issue's scope. Stop the agent
([stopping the agents](#stopping-the-agents)), then follow
[SECURITY-AI.md § Reporting](security/SECURITY-AI.md#reporting): a vulnerability or leaked secret goes to the
private report in [`SECURITY.md`](../SECURITY.md) after rotating the
credential; other misbehaviour is a GitHub issue. Add a line to `.claude/memory/corrections.tsv` saying where the fix
is encoded, and if the lesson needs context, write a reflection in [`reflections/`](reflections/README.md). A change
the agent already merged is traced through [`agent-tasks/`](agent-tasks/README.md) and the `AI audit trail`, and fixed
forward like any other; a bad release follows [`runbooks/bad-release.md`](runbooks/bad-release.md).

## Stopping the agents

To pause agent work, for example during an incident or while a bad instruction gets fixed, stop each entry point:

| Stop | Command | Undo |
| --- | --- | --- |
| Claude Code in CI | `gh workflow disable claude.yml` | `gh workflow enable claude.yml` |
| Claude Code in CI, hard stop | Delete its credential: `gh secret delete CLAUDE_CODE_OAUTH_TOKEN`, or uninstall the Claude GitHub App in the repository's settings | Set the secret again (`gh secret set CLAUDE_CODE_OAUTH_TOKEN`), or reinstall the App |
| Automatic merges | `gh workflow disable merge-queue.yml` | `gh workflow enable merge-queue.yml`, then `gh workflow run merge-queue.yml` |
| One PR | `gh pr edit <N> --add-label hold` | `gh pr edit <N> --remove-label hold` |
| `/apply-suggestions` | `gh workflow disable auto-review.yml` | `gh workflow enable auto-review.yml` |
| Weekly popularity PR, which merges itself | `gh workflow disable popularity.yml` | `gh workflow enable popularity.yml` |
| Workflow-opened PRs and issues | `gh workflow disable nightly-compliance.yml` stops the link-status and checker-pin PRs and the compliance report; `gh workflow disable game-submission-approve.yml` stops the catalog PR a submission's `approved` label opens | `gh workflow enable <file>` |
| Hive | Pause it from the Hive dashboard; it runs outside this repository. To cut it off, revoke the `hive-worker-bee` GitHub App's access in the repository's GitHub App settings | Resume it there, or reinstall the App |
| The repository's bot App (the `bot` environment) | Delete its key under the App's settings, **Private keys** ([SECURITY-AI.md § Secrets](security/SECURITY-AI.md#secrets)) | Generate a new key and replace the `BOT_APP_PRIVATE_KEY` secret |
| A local CLI agent | End the session; `.claude/settings.json` already denies force pushes, `--no-verify` commits and reads of `.env*`, and asks before `gh pr merge` | — |

Never disable `ci.yml`, `coverage-gate.yml` or `review.yml` to pause agents: CI keeps running on every PR either way,
so nothing lands on `main` without passing the ruleset's required checks. GitHub disables a scheduled workflow after 60
days without repository activity; a workflow you disabled by hand stays disabled until you enable it, so write down
what you paused ([`runbooks/re-enable-cron.md`](runbooks/re-enable-cron.md) covers the inactivity case).
