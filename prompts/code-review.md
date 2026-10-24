# Code Review Prompt

Review the diff between `<FIXED_POINT>` and `<HEAD>` in the `Dailies` repository
(GTK4/libadwaita launcher in Python 3 + PyGObject: `dailies/core` pure Python
logic, `dailies/data` and `dailies/ui` GTK code, Blueprint UI, Meson, Flatpak).

Check two axes and report them separately:

## Standards
- TDD compliance: tests were written for the behaviour being changed, assert
  observable outputs (not private state or widget internals), and the full
  suite passes (`pytest`).
- Logic that needs no GTK lives in `dailies/core` (never imports `gi`) with
  plain pytest tests; `dailies/data` and `dailies/ui` stay a thin shell.
- No test weakened, deleted, skipped or marked `xfail` to make CI pass; no
  `# noqa` added to silence failures or lint.
- No new dependency without approval: zero third-party Python runtime
  dependencies, script dependencies pinned with hashes in
  `scripts/requirements.txt`, no new Flatpak modules.
- Looks like libadwaita and follows the GNOME HIG: stock widgets and style
  classes over custom CSS, and every changed screen fully usable with the
  keyboard alone.
- No new or widened `finish-args` in `build-aux/flatpak/*.json`.
- `data/v1/schema/**` and `.github/workflows/**` changed only when the issue
  asks for it, flagged for high-tier review.
- Gates green (plus `shellcheck -x scripts/*.sh scripts/lib/*.sh build-aux/windows/*.sh` and
  `actionlint` when `scripts/` or `.github/workflows/` changed):
  ```sh
  ruff check . && ruff format --check .
  pytest
  meson setup _build -Dprofile=development && meson test -C _build
  flatpak-builder --user --install --force-clean _flatpak build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json
  ```
- Conventional Commits, one commit per issue, issue number referenced.

## Spec
- Every acceptance criterion named in `<ISSUE>` is implemented and tested.
- No unrequested behaviour (scope creep); no partially implemented criteria.

Quote the offending line and source rule for each finding. Under 400 words.
