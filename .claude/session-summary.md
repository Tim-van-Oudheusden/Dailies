# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-10-19. #195 on `feat/195-category-badge`: a legible category badge and a Preferences switch to hide it.

- **Outcome:** `.tile-badge` is now a solid `--category-color` disc with a white 16 px glyph (it was 12 px) and an
  opaque card-coloured ring. The cause was `--card-bg-color`, which is translucent (8 % white) in the dark style, so
  both the old disc and the old ring were see-through there. There is a new `show-category-badge` key (default on), an
  "Appearance" switch row in Preferences, and a tile property bound with `GET`. Games without an icon always show the
  glyph. The research is in `docs/research/category-badge.md`.
- **Open follow-ups:** the open questions in the research note: whether yellow at exactly 3.01:1 is enough, and the
  app-wide sentence case vs HIG header capitalisation for switch rows.
- **Gotchas:**
  - Use `--card-bg-color` only for backgrounds that sit on the card. For an opaque card colour, stack it over
    `--window-bg-color`.
  - To render tiles headlessly, use Broadway in `scripts/sandbox.sh` with `GSETTINGS_SCHEMA_DIR` set and no pipe on
    stdout/stderr: `gtk4-broadwayd` inherits stderr and keeps a pipe, and so the container, alive.
    `GtkCssProvider:prefers-contrast` forces the high-contrast media query.
  - The host has no GTK development files: run the Meson gate with `scripts/sandbox.sh` and the Flatpak gate with
    `scripts/dev.sh build-devel`.
