---
key: 59
title: ci(data): stage B — approved submission → PR (add_game.py + game-submission-approve.yml)
type: Task
labels: milestone::M2, type::task, priority::high, ci, data
parent: 4
blocked_by: 57, 58
---
> **Risk tier:** high · **Size:** M

## `scripts/add_game.py`

- [ ] `python -I scripts/add_game.py --entry "$RUNNER_TEMP/result.json" --catalog data/v1/games.json` inserts the validated entry **sorted by `id`**, bumps the catalog's `generated_at`, and preserves formatting (2-space JSON, trailing newline). The output must be byte-stable so diffs show only the new entry
- [ ] Refuses if the id already exists (a race between two approvals)
- [ ] No icon fetching in the MVP (decision #17; `scripts/icons/fetch_icon.py` comes later, in #77)
- [ ] Tests in `tests/scripts/test_add_game.py`: insertion order, stable formatting, duplicate refusal

## Workflow `.github/workflows/game-submission-approve.yml`

Use the skeleton in [`data-pipeline.md` Appendix A3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md).

- **Trigger:** `issues: [labeled]`, with `if: github.event.label.name == 'approved' && contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.sender.author_association)` (the same guard as `claude.yml`)
- **Permissions:** `contents: write`, `pull-requests: write`, `issues: write`
- **Steps:**
  1. Re-run the parser **and** the validator. Never trust stage A, because labels can be removed and re-added
  2. Run `add_game.py`
  3. Re-validate the whole file with `check-jsonschema` and run `pytest tests/data`
  4. `peter-evans/create-pull-request@5f6978fa… # v8.1.1` with `branch: data/add-<slug>`, `title: data(games): add <name>`, a body containing `Closes #N` plus the candidate JSON, `labels: data, automated`, `add-paths: data/v1/games.json`, `delete-branch: true`
- **Merge:** a human clicks merge. PRs opened with `GITHUB_TOKEN` **do not trigger** `pull_request` workflows **[V]**, so the required checks never appear and the maintainer merges with the ruleset's admin bypass (#35). That is accepted because stage B already validated the entry. #79 adds `DATA_BOT_TOKEN` later
- Requires the repository setting "Allow GitHub Actions to create and approve pull requests" (#18)

## Acceptance criteria

- [ ] End-to-end: submit → `validated` → maintainer adds `approved` → a PR `data(games): add <name>` appears with only `games.json` changed → merge → the issue closes → Pages updates (#56) → the app shows the game after a refresh
- [ ] Adding `approved` from a non-collaborator account does nothing
- [ ] Approving a submission that has become invalid since stage A (edited afterwards) fails stage B with a comment and opens no PR
- [ ] **Milestone exit:** two real games added this way (record their issue numbers in #65)

## References

- [`mvp-first.md` §7.3, §7.4, §17 risk 12](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §1.4, Appendix A3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
