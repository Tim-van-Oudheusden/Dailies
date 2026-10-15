---
key: 18
title: chore(repo): configure repository settings, labels, secrets and apps
type: Task
labels: milestone::M0, type::chore, priority::high, ci
parent: 2
---
> **Risk tier:** n/a (GitHub settings, not files) · **Size:** S · **Who:** owner (needs admin rights; agents cannot do this)

## Why

The copied workflows assume repository settings that Dailies does not have yet. As verified with `gh`, the repo currently allows squash/rebase, has no ruleset, has no security-policy flag and has only the default labels. Several later tickets fail without these settings: stage A/B need labels, `claude.yml` needs a secret and an app, and Pages needs its source set to Actions.

## Tasks

### General → Pull Requests
- [ ] Allow **merge commits only**; disable squash and rebase merging
- [ ] **Automatically delete head branches**
- [ ] Leave "Allow auto-merge" **off** for now (#79 turns it on later)

### Code security
- [ ] CodeQL **default setup** with languages `actions` and `python`
- [ ] Dependabot **alerts** + **security updates** on
- [ ] **Private vulnerability reporting** on (referenced by `SECURITY.md`, #22)

### Actions → General
- [ ] Workflow permissions: read-only `GITHUB_TOKEN` by default (jobs ask for more themselves)
- [ ] Enable **"Allow GitHub Actions to create and approve pull requests"** (needed by stage B #59 and `popularity.yml` #62 via `peter-evans/create-pull-request`)

### Pages
- [ ] Source: **GitHub Actions** (used by #56)

### Secrets
- [ ] `CLAUDE_CODE_OAUTH_TOKEN`, the same token MinimalUI uses (needed by #32 and #66)
- [ ] Later: `DATA_BOT_TOKEN` (#79), `CLOUDFLARE_RADAR_TOKEN` (#78). Do **not** create these now.

### Apps
- [ ] Install the **Claude GitHub App** on the repo (needed by #32)
- [ ] Install/authorise **`hive-forge-app`**, unless #11 shows it is already installed account-wide (#36)

### Labels (Hive creates its own; these must exist by hand)

| Label | Use |
|---|---|
| `game-submission`, `validated`, `needs-changes`, `approved` | IssueOps (#23, #58, #59) |
| `data`, `automated` | Bot PRs (#59, #62) |
| `ai-fix-requested` | `claude.yml` trigger (#32) |
| `type::bug`, `type::feature`, `type::task`, `type::chore` | MinimalUI convention |
| `priority::critical`, `priority::high`, `priority::medium`, `priority::low` | MinimalUI convention |
| `app`, `data`, `flatpak`, `ci`, `documentation` | Path labels applied by `labeler.yml` (#29); must match `.github/labeler.yml` |

`docs/issues/create_issues.py` already creates the labels with colours and descriptions (`gh label create --force`). Rerunning it is idempotent.

## Acceptance criteria

- [ ] `gh repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed,deleteBranchOnMerge` shows `true,false,false,true`
- [ ] Every label above exists (`gh label list`)
- [ ] `CLAUDE_CODE_OAUTH_TOKEN` is listed under repository secrets
- [ ] Pages source shows "GitHub Actions"
- [ ] The ruleset is **not** applied yet. It needs the four check contexts to have run once on `main` (#35)

## References

- [`mvp-first.md` §7 (Labels), §11 (Repository settings, Hive)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`scaffolding-repos.md` §2.4, §5, §8.7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md)
- [`data-pipeline.md` §1.4 (token facts)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
