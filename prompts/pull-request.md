# Pull Request Prompt

Create a PR body for `<ISSUE>` (title: `<TITLE>`) implemented by commits
`<COMMIT_RANGE>` in `Dailies`.

Rules: Conventional Commits title, one commit per issue, issue referenced in
commits, body says `Fixes #<number>`. Fill in `.github/pull_request_template.md`:

## Summary

- **What:** one or two sentences: what changes for the user.
- **Why:** the issue's goal; note any verified deviations from the ticket
  (stale premises, review-driven changes).

## Testing

- Failing-before / passing-after output for the changed path.
- For UI changes: the desktop used (GNOME version, Wayland or X11) and that
  keyboard-only navigation was checked.

## Quality gates

- The exact commands run and their results:
  ```sh
  ruff check . && ruff format --check .
  pytest
  meson setup _build -Dprofile=development && meson test -C _build
  flatpak-builder --user --install --force-clean _flatpak build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json
  ```
  plus `shellcheck -x scripts/*.sh scripts/lib/*.sh build-aux/windows/*.sh` and `actionlint` after
  touching `scripts/` or `.github/workflows/`.

## Notes for the reviewer

- Documented tradeoffs, harness limitations, or pre-existing issues touched.
- Any change to `finish-args`, `data/v1/schema/**` or `.github/workflows/**`,
  and why the issue asks for it.

## Dependencies

- Only if changed: package, exact version (hash-pinned in
  `scripts/requirements.txt`), why, and the approval.
