# Agent task traceability

Every change an agent makes traces back to the GitHub issue that asked for it, and every issue leads forward to the
change that resolved it. GitHub issues are the task records; this directory does not copy them. It describes the chain
of links from an issue to the code on `main`, which links are enforced, and how to follow the chain either way. The
coordination rules behind it are in [`../multi-agent.md`](../multi-agent.md).

## The chain

| Link | Carries the issue number as | Example | Enforced by |
| --- | --- | --- | --- |
| Issue | The task itself, filed by a person, an agent or a workflow; Hive's issues end with `— hive: agent=<name> …` | #303 | — |
| Claim | An assignee, or Hive's `<!-- hive:claim who=<agent> … until=<time> -->` comment with its `hive/claimed-by-<agent>` label | `gh issue edit 303 --add-assignee @me` | Convention ([`multi-agent.md`](../multi-agent.md#the-shared-queue)) |
| Branch | `<type>/<number>-<slug>` for local agents; Hive uses `<agent>/<number>-<slug>` or a topic branch such as `quality/test-…`; Claude Code in CI uses `claude/*` | `craftsman/303-done-today-refresh-doc` | Convention (`AGENTS.md`, "Issue Tracking") |
| Commit | `(#<number>)` at the end of the Conventional Commits subject | `docs(done-today): refresh drops the marks of every other day, not only earlier ones (#303)` | Convention |
| Pull request | `Fixes #<number>` in the body (or `Closes`, `Resolves`, `Refs`); Hive's PRs also end with `— hive: agent=<name> backend=… model=<model> …` | #304 | `PR review rubric` check (`scripts/pr-review-check.sh`), required on `main` for authors that are not `*[bot]` accounts |
| Merge | Merge commit `Merge pull request #<PR> from <owner>/<branch>`, made by the maintainer or, for a low- or medium-risk PR, by the merge queue (`.github/workflows/merge-queue.yml`) or Hive's merge sweep | `ec9291a` | `main` only changes through pull requests (`.github/rulesets/main.json`); `.github/CODEOWNERS` names the maintainer owner of the high-risk paths |
| Close | The merge closes the issue through `Fixes #<number>`; a merge by the queue's token closes nothing by itself, so its `land` job closes the linked issues | #303 closed by #304 | GitHub; `scripts/merge-queue.sh land` |

The required rubric check is what guarantees the chain for pull requests from people: a pull request into `main` from
a person cannot merge without an issue link. Bot authors, including Hive, are exempt (see **Exempt** below).
Branch names and commit subjects carry the number by convention, which makes them quicker to search but not
authoritative: Hive's topic branches and the `claude/*` branches often carry no number. `Refs #<number>` satisfies the
rubric without closing the issue; use it when a PR covers only part of one.

**Exempt:** pull requests from bot accounts (`*[bot]`) need no issue link; the rubric check skips the link for them.
Dependabot's task is the dependency update itself, and the branch `dependabot/<ecosystem>/<package>` names it. Hive's
`hive-worker-bee[bot]` PRs are exempt; by convention their bodies carry `Fixes`/`Refs #N`, but this repository does not
enforce it. The pull requests opened by the
repository's own workflows (`data/popularity`, `ci/checker-pin`, `data/link-status`, …) are named for the workflow that
opened them ([`multi-agent.md`](../multi-agent.md#work-the-workflows-generate)); their task is that workflow's job.

## Beside the issue

An issue records what was asked and what was merged. Two files record what a session learned on the way, and they are
not substitutes for the link to the issue:

- `.claude/session-summary.md` holds the hand-off from the last session, overwritten in the issue's own commit
  (`AGENTS.md`, "Session Completion"). Its first line names the issue and the branch.
- `.claude/memory/corrections.tsv` and [`docs/reflections/`](../reflections/README.md) keep the durable lessons: one
  line per correction round, and the reasoning behind a non-obvious lesson.

## Following the chain

From an issue to the change that resolved it:

```bash
gh issue view <number> --json state,assignees,labels,closedByPullRequestsReferences
gh pr list --state all --search "<number>"
git log --oneline --grep "(#<number>)" origin/main
```

From a line of code back to its issue:

```bash
git blame -L <line>,<line> <file>              # the commit
git log -1 --format=%s <commit>                # its subject ends in (#<number>)
gh pr list --state merged --search "<commit>"  # the PR, whose body links the issue
```

From an agent to everything it did: filter pull requests by author or branch, for example
`gh pr list --state all --author app/hive-worker-bee` for Hive and `gh pr list --state all --search "head:claude/"` for
Claude Code in CI. The `— hive: agent=<name> …` signature at the end of a Hive issue or PR body names the Hive agent,
and the `agent/<name>` label on its issues does too.

## When the chain breaks

- **Work with no issue:** file one (`gh issue create`) before opening the pull request. An agent that finds work outside
  its issue files a new issue rather than widening the PR.
- **A PR that links the wrong issue:** edit the body; the rubric check runs again on the edit.
- **An issue closed with no linked PR:** reopen it, or comment with the PR or commit that resolved it so the record is
  complete.
