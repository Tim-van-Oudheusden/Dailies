---
key: 32
title: ci: claude.yml — hand `ai-fix-requested` issues to Claude Code
type: Task
labels: milestone::M0, type::task, priority::medium, ci
parent: 2
blocked_by: 18, 21
---
> **Risk tier:** high · **Size:** S · **ACMM:** `ai-fix-workflow`, `github-actions-ai` (also part of L5)

## Why

A solo maintainer hands well-specified issues, like the ones in this backlog, to Claude Code by adding a label. The agent works on a `claude/*` branch and opens a PR; it never pushes to `main`.

## Tasks

- [ ] `.github/workflows/claude.yml`: copy MU's file ([`hive-acmm.md` Appendix A.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)):
  - Triggers: an issue labelled `ai-fix-requested`, or an `@claude` mention in an issue/PR comment
  - Guard: the sender's `author_association` ∈ {OWNER, MEMBER, COLLABORATOR}; **fork PRs are refused**
  - `anthropics/claude-code-action`: MU pins `1d6de8cb… # v1.0.248`; **bump to v1.0.250 `a26b07d8…`** (full SHAs in [`data-pipeline.md` §5.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md) / [`hive-acmm.md` §9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md))
  - `claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}`
  - `--allowedTools "Bash(meson *),Bash(ninja *),Bash(pytest *),Bash(ruff *),Bash(flatpak-builder *),Bash(blueprint-compiler *)"`
  - Toolchain step: `pip install ruff pytest pytest-cov`. **No** `python3-gi` is needed (core tests are pure Python). Flatpak builds are left to CI
- [ ] Per-job permissions are the minimum the action documents (`contents: write`, `pull-requests: write`, `issues: write`, `id-token: write`); top level is `contents: read`

## Acceptance criteria

- [ ] Labelling a trivial test issue `ai-fix-requested` produces a `claude/*` branch and a PR whose title passes `PR review rubric`
- [ ] An `@claude` comment from a non-collaborator account does nothing (the job is skipped)
- [ ] actionlint passes; `tests/tooling/test_workflows.py` (#33) passes

## References

- [`mvp-first.md` §11 (claude.yml row), §14 (Agents)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`hive-acmm.md` §9 Phase 3, Appendix A.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
