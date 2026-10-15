<!--
Title must follow Conventional Commits, e.g. `feat(library): ...`, `fix(opener): ...`, `docs(agents): ...`.
-->
## Summary

**What:** <!-- one or two sentences: the change -->

**Why:** <!-- the problem it solves; link the GitHub issue -->

Fixes #<!-- issue number -->

## Testing

<!-- Evidence, not claims. Paste failing-before/passing-after output for the changed path. -->

- [ ] New/changed behaviour covered by a test written first (TDD); test confirmed failing before implementation
- [ ] Test asserts observable behaviour, never implementation internals
- [ ] UI changes checked in the Devel Flatpak (keyboard-only navigation and a narrow window included)

## Quality gates

- [ ] `ruff check . && ruff format --check .` passes (`ruff format .` fixes formatting)
- [ ] `pytest` passes
- [ ] `meson setup _build -Dprofile=development && meson test -C _build` passes
- [ ] `flatpak-builder --user --install --force-clean _flatpak build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json` passes

## Review rubric

- [ ] Looks like libadwaita / follows HIG (stock widgets and style classes, no colour-only information)
- [ ] No new finish-args (or the new permission is justified under "Notes for the reviewer")
- [ ] Catalog change validated (`data/v1/` edits pass the schema check), or no catalog change

## Notes for the reviewer

<!-- Anything risky, out of scope, or needing a second look. -->

## Dependencies

<!-- Only if changed:
- Name, explicit version, and why (ask before adding)
- Python tooling pinned with hashes in scripts/requirements.txt; app dependencies as a module in the Flatpak manifest
-->
- None
