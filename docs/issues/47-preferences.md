---
key: 47
title: feat(ui): Preferences dialog (opening games, website data, catalog)
type: Feature
labels: milestone::M1, type::feature, priority::medium, app
parent: 3
blocked_by: 38, 39, 45, 46
---
> **Risk tier:** medium · **Size:** M · **Brief:** "Must be configurable."

## Dialog (`data/ui/preferences.blp`, `dailies/ui/preferences.py`)

`Adw.PreferencesDialog` with `search-enabled: true` (it defaults to false). One page, **"General"**. Start from the skeleton #19 compiled ([`libadwaita-ui-patterns.md` Appendix A.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)).

### Group "Opening games"
- `Adw.ComboRow` **"Open games"**, model `Gtk.StringList` ["Built-in browser", "Default browser", "Custom command"]
  - "Built-in browser" is **hidden** when `HAVE_WEBKIT` is false
  - "Custom command" is **hidden** until #63 detects host access (in M1 it is always hidden)
  - Map `selected` ↔ enum string **by hand in Python**; PyGObject has no closure mapping for this
- `Adw.EntryRow` **"Command"** (`show-apply-button: true`, monospace) is visible only in custom mode (lands with #63)
- Group description, dimmed: "Games open inside Dailies by default. You can always open the current game in your browser from its menu."

### Group "Built-in browser" (hidden when `HAVE_WEBKIT` is false)
- `Adw.SwitchRow` **"Clear website data on exit"**, bound to `clear-web-data-on-exit` with `Gio.Settings.bind`
- `Adw.ButtonRow` **"Clear website data…"** with style `destructive-action`. It opens a confirmation `Adw.AlertDialog`: "Clear website data?" / "You will be signed out of games and lose saved progress and streaks." / [Cancel] [Clear (destructive)]. On confirm, call `BrowserPage.clear_all()` (#46) and toast "Website data cleared"

### Group "Catalog"
- `Adw.ActionRow` with the `property` style, **"Last updated"**: the date of the last successful fetch (#39), or "Never (using built-in list)"; plus a flat refresh button that triggers `app.refresh`
- *(M2, #64:)* `Adw.SwitchRow` "Show games in other languages"

## Acceptance criteria

- [ ] Ctrl+, opens the dialog; typing "clear" in its search finds both clear rows
- [ ] Switching "Open games" to "Default browser" makes the next tile activation open externally, and the setting persists
- [ ] "Clear website data…" asks for confirmation; after confirming, a previously logged-in NYT game is logged out
- [ ] With the WebKit typelib absent (simulated), the built-in options and group are not shown
- [ ] No deprecated widgets (`AdwPreferencesWindow` is deprecated since 1.6)

## References

- [`mvp-first.md` §4.6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`libadwaita-ui-patterns.md` §5, §11.3, Appendix A.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
- [`cartridges.md` §5.5, Appendix D](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)
- [`embedded-browser.md` §9.5 item 9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)
