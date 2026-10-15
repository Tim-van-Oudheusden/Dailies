---
key: 23
title: chore(github): issue forms (incl. new-game submission form) and PR template
type: Task
labels: milestone::M0, type::chore, priority::high, data, ci
parent: 2
---
> **Risk tier:** high (`.github/**`) · **Size:** S · **ACMM:** `prereq-issue-template`, `prereq-pr-template`

## Why

The brief says "DLEs are added through GitHub issues". From day one the form exists and the maintainer edits `games.json` by hand from submissions. M2 automates the rest (#58, #59) **without changing the form**, so get it right now.

## Files

### `.github/ISSUE_TEMPLATE/new-game.yml`

Start from the copy-ready template in [`data-pipeline.md` §1.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md) and apply these changes:

- `name: Add a game`, `title: "game: "`, `labels: ["game-submission"]`
- **Category** dropdown with exactly the ten labels below, in this order, and **no "Other"**. Each label maps to its enum id in `scripts/validate_submission.py` (#57):

| Label | Enum id |
|---|---|
| Words | `words` |
| Geography | `geography` |
| Music | `music` |
| Movies & TV | `movies-tv` |
| Video Games | `video-games` |
| Numbers & Logic | `numbers-logic` |
| Trivia | `trivia` |
| Pictures & Colors | `visual` |
| Food | `food` |
| Sports | `sports` |

- **Difficulty** dropdown `Easy | Medium | Hard`, with the rubric from [`dle-catalog.md` §2.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md) in the description (easy: most people in under ~3 min; medium: some domain knowledge or 5–10 min; hard: niche knowledge or long sessions)

Fields:

| Field | Required | Notes |
|---|---|---|
| Name | yes | |
| URL | yes | Placeholder `https://`; description says https only |
| Category | yes | Dropdown above |
| Difficulty | yes | Dropdown above |
| Description | yes | `min_length`-style guidance "at least 20 characters". GitHub forms have no min-length validation; the validator enforces it |
| Tags | no | Comma-separated |
| Language | no | Default `en` |
| Checks | yes | Checkboxes: "Publishes a new puzzle every day"; "Playable without an account"; "I am not the author, or I am and I consent to listing" |

- Field `id`s must stay stable (the parser keys on them). Use `name`, `url`, `category`, `difficulty`, `description`, `tags`, `language`, `checks`
- `validations.required` is only enforced on public repos **[V]**. Dailies is public

### `.github/ISSUE_TEMPLATE/issue.yml`

MU's general issue form, with the "Device" input replaced by **"Flatpak version and desktop"** (output of `flatpak info io.github.tim_van_oudheusden.Dailies` + desktop environment).

### `.github/ISSUE_TEMPLATE/config.yml`

`blank_issues_enabled: true`, plus a contact link "Report a broken game link" pointing to the general form with a `data` label.

### `.github/pull_request_template.md`

MU's template ([`hive-acmm.md` Appendix A.11](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)) with the gate commands from #21 and the rubric bullets "Looks like libadwaita / follows HIG", "No new finish-args" and "Catalog change validated". `scripts/pr-review-check.sh` (#29) mechanically checks the **Conventional Commits title** and the **`Fixes #N`** line.

## Acceptance criteria

- [ ] Opening "New issue" shows "Add a game" and the general form
- [ ] A test submission renders all fields; parsing the body with `stefanbuck/github-issue-parser` v3.2.5 (dropdown → string, checkboxes → array, `_No response_` → `""`) yields the ids above. Paste the parser output in the PR
- [ ] `actionlint` / YAML lint passes on all three files

## References

- [`mvp-first.md` §2 tree, §7.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §1.1–§1.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
- [`dle-catalog.md` §2.2, §2.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)
