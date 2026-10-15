---
key: 14
title: Decision: weekly narrative report — model and execution path
type: Task
labels: decision, milestone::M3, priority::medium, ci
parent: 5
---
## Question

How does the weekly popularity report get written? Claude writes prose only and never changes numbers.

| Option | Auth / billing | Shape | Cost per week |
|---|---|---|---|
| **`anthropics/claude-code-action` v1.0.250 (proposed)** | Existing `CLAUDE_CODE_OAUTH_TOKEN` secret (already used in MinimalUI), so it bills the subscription, not API credits | Automation mode with `prompt`; `claude_args: --max-turns 6 --allowedTools "Read,Write" --disallowedTools "Bash,Edit,WebSearch,WebFetch"` | ≈ $0 extra on the subscription; ≈ $0.15–0.35 at `claude-opus-5-5` API prices |
| ~30-line SDK script `scripts/popularity/narrate.py` | `ANTHROPIC_API_KEY` secret, API billing | Single Messages call on Claude Haiku 5.5 (`claude-haiku-5-5`) | Under a cent |

Prices are from the research's pricing table, cached 2026-10-06 **[U]**. Re-check them before deciding.

## Proposed default

**claude-code-action with the existing OAuth token.**

## How to close

Comment with the path and model and close. #66 implements it.

## References

- [`mvp-first.md` §8 (Agentic report, Cost), §18.8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §5, Appendix A4, A5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
