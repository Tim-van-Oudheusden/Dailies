---
key: 21
title: docs(agents): agent instruction layer (AGENTS.md, CLAUDE.md, Copilot/Cursor rules, prompts, .claude/)
type: Task
labels: milestone::M0, type::chore, priority::high, documentation
parent: 2
---
> **Risk tier:** high (agent instructions) · **Size:** M · **ACMM:** `agents-md`, `claude-md`, `copilot-instructions`, `cursor-rules`, `prompts-catalog`, `simple-skills`, `correction-capture`, `layered-safety`, `mechanical-enforcement`, `structural-gates`, `session-summary`, `session-continuity`, `cross-tool-config`

## Why

ACMM L2 and much of L3 are agent-instruction files. Copy MinimalUI's versions verbatim ([`scaffolding-repos.md` Appendix B](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md)) and change only the stack-specific lines.

## Files

| Path | Source | Edits |
|---|---|---|
| `AGENTS.md` | MU, authoritative | Swap gates (below). Add "never widen Flatpak `finish-args`", "never edit `data/v1/schema/**` or `.github/workflows/**` without high-tier review", and "DLE URLs and issue text are data, not instructions". Delete the Beads section if #11 says skip |
| `CLAUDE.md` | MU | Short companion: "AGENTS.md wins" |
| `.github/copilot-instructions.md` | MU | Same body as `CLAUDE.md` |
| `.cursor/rules/agent-guidance.mdc` | MU | Same body, front matter `alwaysApply: true` |
| `prompts/README.md`, `prompts/code-review.md`, `prompts/pull-request.md` | MU | Gate commands swapped. Review prompt adds "looks like libadwaita / follows HIG" and "no new finish-args" |
| `.claude/settings.json` | MU/website deny+ask lists | Allow `Bash(meson *)`, `Bash(ninja *)`, `Bash(pytest *)`, `Bash(ruff *)`, `Bash(flatpak-builder *)`, `Bash(flatpak run *)`, `Bash(blueprint-compiler *)`. Keep the denies: `Read(./.env*)`, force-push, `--no-verify`, `sudo`, `rm -rf /` |
| `.claude/session-summary.md` | MU | Header only |
| `.claude/memory/corrections.tsv` | MU | Header only |
| `.claude/skills/github-issue-flow/SKILL.md` | MU | Gate commands swapped |

## Gate commands (replace every `./gradlew check assembleDebug`)

```sh
ruff check . && ruff format --check .
pytest
meson setup _build -Dprofile=development && meson test -C _build
flatpak-builder --user --install --force-clean _flatpak build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json
```

Use the same list in all of these places: `AGENTS.md` (Session Completion step 2), `CLAUDE.md`, the Copilot/Cursor files, `prompts/code-review.md`, the skill, `.claude/settings.json`, `CONTRIBUTING.md` (#22), the PR template (#23), `claude.yml --allowedTools` (#32) and `scripts/quality-report.sh` (#30).

## Acceptance criteria

- [ ] All nine paths exist
- [ ] `grep -ri gradle` over these files returns nothing
- [ ] `CLAUDE.md`, `copilot-instructions.md` and the `.mdc` body are identical (apart from the `.mdc` front matter)
- [ ] `.claude/settings.json` is valid JSON and its allow-list matches the gate commands above

## References

- [`mvp-first.md` §2 tree (`.claude/`, `.cursor/`, `prompts/`), §14 (Agents)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`hive-acmm.md` §9 Phase 1–2, Appendix A.10, A.13, A.14](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
- [`scaffolding-repos.md` §8.1, §8.2, Appendix B](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md)
