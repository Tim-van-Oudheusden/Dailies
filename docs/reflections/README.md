# Reflections

Cross-session knowledge for agent work in this repository: short write-ups of what a session learned that the next one
should not have to rediscover. Read the newest few before starting work; add one when a session uncovers something
non-obvious about the repo, its tooling, or the environment agents run in.

## How this fits with the other learning artifacts

| Artifact | Holds | Lifetime |
| --- | --- | --- |
| `.claude/session-summary.md` | Hand-off from the last session only | Overwritten each session |
| `.claude/memory/corrections.tsv` | One line per correction round | Append-only log |
| `docs/reflections/` | The *why* behind a lesson, with context | One file per reflection, kept |

If a lesson becomes a rule, encode it where agents already look (`AGENTS.md`, `CLAUDE.md`, a skill, or a test under
`tests/`) and link that from the reflection.

## Format

One Markdown file per reflection, named `YYYY-MM-DD-short-slug.md`, with:

- **Context** — issue/PR and what was being attempted.
- **What happened** — the surprise, failure, or discovery.
- **Lesson** — what to do differently, stated as guidance.
- **Encoded in** — where the lesson now lives, or "not yet" with a follow-up issue.

## Index

- No reflections yet.
