---
key: 66
title: ci(popularity): Claude-written weekly report with change guard
type: Task
labels: milestone::M3, type::task, priority::medium, ci, data
parent: 5
blocked_by: 14, 18, 62
---
> **Risk tier:** high · **Size:** S · **Principle:** the model writes prose; it never changes a number

## Tasks

- [ ] Add a step to the `publish` job of `popularity.yml` (#62), on the path chosen in #14. Default: `anthropics/claude-code-action@a26b07d8… # v1.0.250` in automation mode:
  - `claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}`
  - `prompt:` "Read `summary.json` and `data/v1/popularity.json`. Write `docs/popularity/<week>.md` with: Overview (3–5 sentences), a Popular table, a Trending table, Movers (biggest rises and falls), and Data quality (source health, carried-forward domains). Use only numbers present in the inputs. Do not edit any other file."
  - `claude_args: --max-turns 6 --allowedTools "Read,Write" --disallowedTools "Bash,Edit,WebSearch,WebFetch"`
  - `continue-on-error: true`, so a failed narrative never blocks the numbers PR
  - Runs on the schedule, and on `workflow_dispatch` when `narrate` is true
- [ ] **Guard** (after the step): `git status --porcelain` may only show `data/v1/popularity.json` and `docs/popularity/*.md`. Anything else fails the job. Also diff `popularity.json` against the `compute` artifact; it must be byte-identical
- [ ] Set `popularity.json.report` to the report path (`popularity/<week>.md` on Pages)
- [ ] `pages.yml` (#56) already publishes `docs/popularity/`
- [ ] `docs/popularity/README.md`: format and index (MU docs convention)
- [ ] **Prompt-injection surface:** the model sees **only** numbers and maintainer-approved game names. It never sees issue text or fetched HTML. State this in `docs/security/SECURITY-AI.md` (#22)
- [ ] ~400 words target. Prose is English only

## Cost (record actuals in the PR after the first run)

The estimate is ~20–60k input + 2–4k output tokens per run: about $0 extra on the OAuth subscription path, about $0.15–0.35 per week at `claude-opus-5-5` API prices, and under a cent on Haiku 5.5. Prices were cached 2026-10-06 **[U]**.

## Acceptance criteria

- [ ] A dispatched run with `narrate: true` produces a PR containing `docs/popularity/2026-Wxx.md` and an unchanged-by-the-model `popularity.json`
- [ ] A test where the prompt is tampered with to "edit games.json" (in a scratch branch) is caught by the guard
- [ ] **Milestone exit:** at least one report merged

## References

- [`mvp-first.md` §8 (Agentic report, Cost), §14 (Agents), §18.8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §5, Appendix A4, A5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
