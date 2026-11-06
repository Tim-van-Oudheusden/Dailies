# Dailies documentation

| Path | What it is | Status |
|---|---|---|
| [`BRIEF.md`](BRIEF.md) | The owner's requirements statement | final |
| [`research/`](research/README.md) | 12 verified research reports feeding the architecture (Hive ACMM, scaffolding, Cartridges, Bazaar, stack, embedded browser, Flatpak pipeline, data pipeline, logo, DLE catalog, Libadwaita UI, category badge) | 11 complete 2026-10-15; category badge 2026-10-19 |
| [`proposals/`](proposals/) | Candidate architectures: only MVP-first was written, and `architecture.md` was trimmed from it | closed |
| [`plans/design-judge-plan.md`](plans/design-judge-plan.md) | The plan for the Design and Judge phases, kept as a record | superseded by [`architecture.md`](architecture.md) |
| [`architecture.md`](architecture.md) | The architecture as shipped: runtime data flow, modules, caching, link opening, data and release pipelines, decisions, measurements | current |
| [`data-format.md`](data-format.md) | Reference for `data/v1/games.json` and `popularity.json`: fields, categories, tags, difficulty rubric, submission rules, licences | current for `data/v1` |
| [`multi-agent.md`](multi-agent.md) | How Hive's agents, Claude Code, CLI agents and the workflows share the issue queue: who does what, claim and stage labels, hand-offs, merging | current |
| [`agent-tasks/`](agent-tasks/README.md) | How an agent's change links back to its issue and the issue forward to the change: branch, commit, PR, merge, close | current |
| [`ai-ops-runbook.md`](ai-ops-runbook.md) | How to watch the agents and workflows, debug them when they stall or misbehave, and pause or stop each one | current |

How the design went: Research → the MVP-first proposal → `architecture.md`, trimmed to the design that shipped. The other two proposals and the Judge phase never ran.
