---
key: 48
title: feat(app): application actions, accelerators, About and Shortcuts dialogs
type: Feature
labels: milestone::M1, type::feature, priority::medium, app
parent: 3
blocked_by: 24, 41
---
> **Risk tier:** medium · **Size:** S

## Actions and accelerators (`dailies/application.py`, `dailies/window.py`)

| Action | Accelerator | Notes |
|---|---|---|
| `app.quit` | Ctrl+Q | |
| `app.preferences` | Ctrl+, | Opens #47 |
| `app.about` | — | |
| `app.shortcuts` | Ctrl+? | **Automatic:** `Adw.Application` wires it when the gresource contains `shortcuts-dialog.ui` with id `shortcuts_dialog` |
| `app.refresh` | Ctrl+R (library page) | #39; toasts the outcome |
| `win.search` | Ctrl+F | #44 |
| `win.toggle-favorite` | Ctrl+D | #43 |
| `win.show-section` (s) | — | Used by empty states |
| Browser: reload | Ctrl+R (browser page) | #46. Scope it to the browser page so it doesn't clash with `app.refresh` |
| Browser: back / forward | Alt+Left / Alt+Right | #46 |
| Browser: focus URL | Ctrl+L | #46 |
| Browser: open in browser | Ctrl+Shift+O | #46 |
| Primary menu | F10 | |

This is the HIG reference set ([`libadwaita-ui-patterns.md` §12](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)).

## Shortcuts dialog

`data/ui/shortcuts-dialog.blp` → `shortcuts-dialog.ui`, using **`Adw.ShortcutsDialog`** (libadwaita ≥ 1.8) and **not** `GtkShortcutsWindow`, which has been deprecated since GTK 4.18. Sections: General, Library, Built-in Browser. Base it on [`libadwaita-ui-patterns.md` Appendix A.5 / B.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md).

## About dialog

- `Adw.AboutDialog.new_from_appdata(f"{PREFIX}/{APP_ID}.metainfo.xml", VERSION)` reads the name, icon, developer, version, URLs, licence and the newest `<release>` notes from the metainfo bundled in the gresource (#24/#50)
- Also call `set_developers`, `set_designers` and `set_translator_credits(_("translator-credits"))`
- `add_legal_section("Trademarks", None, Gtk.License.CUSTOM, …)` with the non-affiliation text:

> Dailies is not affiliated with The New York Times, Merriam-Webster, LinkedIn or any game listed. Game names are trademarks of their owners; Dailies only opens their public websites.

## Acceptance criteria

- [ ] Every accelerator in the table works and appears in the Shortcuts dialog
- [ ] About shows version 0.1.0, the GPL-3.0-or-later licence, the release notes and the Trademarks section
- [ ] There is no Quit item in the primary menu (HIG), but Ctrl+Q works

## References

- [`mvp-first.md` §3.1 (application.py row), §4.3 (Keyboard), §4.7, §14 (Trademarks)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`libadwaita-ui-patterns.md` §6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
- [`cartridges.md` §5.6–§5.8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)
