---
name: github-issue-flow
description: Complete one GitHub issue end-to-end: claim, branch, implement with TDD, open a pull request. Use when starting or finishing issue-tracked work in this repository.
---

# GitHub Issue Flow

Single-issue loop for `Dailies`. AGENTS.md is authoritative; this skill
encodes its workflow into concrete commands.

## 1. Start an issue

1. `gh issue list -S "is:open"` to find work. Pick one issue; child issues
   wait for their parents.
2. Read the full body: `gh issue view <number>`.
3. Claim it: `gh issue edit <number> --add-assignee @me`.
4. Branch off an up-to-date `main`:
   `git switch main && git pull --rebase && git switch -c <type>/<number>-<slug>`
   (e.g. `feat/12-game-search`).

## 2. Implement

- Follow repo TDD: one failing test first, confirm it fails for the right
  reason, implement, run the test, then the full suite.
- Gates before finishing (`ruff format .` fixes formatting):
  ```sh
  ruff check . && ruff format --check .
  pytest
  meson setup _build -Dprofile=development && meson test -C _build
  flatpak-builder --user --install --force-clean _flatpak build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json
  ```
  After touching `scripts/` or `.github/workflows/`, also run
  `shellcheck -x scripts/*.sh scripts/lib/*.sh` and `actionlint`.
- Conventional Commit per issue, referencing the number:
  `git commit -m "type(scope): summary (#<number>)"`.

## 3. Finish the issue

`main` is protected by the ruleset in `.github/rulesets/main.json`: it only
changes through merged pull requests whose required checks pass, so the issue
branch is what you push.

1. Push: `git push -u origin HEAD`.
2. Open the PR, following `.github/pull_request_template.md`:
   `gh pr create --title "type(scope): summary (#<number>)" --body-file <file>`.
   The body says `Fixes #<number>`; the `PR review rubric` check fails without
   that link or a Conventional Commits title.
3. Confirm `git status` shows up to date with `origin/<branch>`, and hand off
   the PR URL. The maintainer merges it, and the merge closes the issue.
