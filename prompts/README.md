# Prompts Catalog

Reusable prompt templates for this repository. They encode the conventions from
`AGENTS.md` (authoritative) and `CONTRIBUTING.md` so agent and human reviews stay
consistent.

## Templates

- [`code-review.md`](./code-review.md) — two-axis review checklist (standards +
  spec) matching the repo's quality gates and the `PR review rubric`.
- [`pull-request.md`](./pull-request.md) — PR body prepared from an issue and its
  commit, following `.github/pull_request_template.md`.

Quality gates both templates refer to:

```sh
ruff check . && ruff format --check .
pytest
meson setup _build -Dprofile=development && meson test -C _build
flatpak-builder --user --install --force-clean _flatpak build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json
```

After touching `scripts/` or `.github/workflows/`, also `shellcheck -x scripts/*.sh scripts/lib/*.sh` and `actionlint`.

Usage: copy a template into your prompt, fill the bracketed fields, and follow
`AGENTS.md` for issue tracking and the session-completion workflow. On a pull
request, ask Claude Code for a review with a comment such as:

```text
@claude review this PR using prompts/code-review.md against issue #<number>
```
