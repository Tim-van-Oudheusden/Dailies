---
key: 11
title: Decision: Hive enrolment details (hosted vs self-hosted, checkouts_dir, Beads)
type: Task
labels: decision, milestone::M0, priority::medium
parent: 2
---
## Questions

1. Is the owner's hive (id `hive-tall-slug`, GitHub App `hive-forge-app`) **hosted** on hive.hivecommons.dev or **self-hosted**? This decides whether Dailies is added through the dashboard **Settings → Repos** (works for both) or by editing `hive.yaml` `project.repos`. **[U]**
2. Should `project.checkouts_dir` be configured on the spoke so Dailies' `AGENTS.md` is actually injected into Hive agent prompts? Without it, `AGENTS.md` only serves CLI agents (Claude Code, Copilot, Cursor) ([`hive-acmm.md` §6.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)).
3. Keep the Beads convention (`.beads/`, `bd`)? Both reference repos have it, but it is **not** an ACMM criterion. If kept, run `bd init` fresh; never copy MinimalUI's `.beads/`, which carries its `project_id` and Dolt remote ([`scaffolding-repos.md` §9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md)).
4. Is the Hive Forge App installed account-wide, or does Dailies need an explicit `hivectl enroll Tim-van-Oudheusden/Dailies`? **[U]**

## Proposed defaults

- Add Dailies through dashboard **Settings → Repos**.
- **Configure `checkouts_dir`.**
- **Skip Beads** unless the owner uses it daily. If skipped, delete the Beads section from the copied `AGENTS.md` (#21).
- Run the hive at operational **L2–L3** at first. The advisor wants coverage ≥ 40 % and a green streak of 3 before suggesting L3 ([`hive-acmm.md` §3.2, §9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)).

## How to close

Answer the four questions in a comment and close. #36 carries out the registration.

## References

- [`mvp-first.md` §11 (Hive paragraph), §18.9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`hive-acmm.md` §6, §9 "Registering Dailies"](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
