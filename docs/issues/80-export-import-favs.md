---
key: 80
title: feat(settings): export/import favourites
type: Feature
labels: milestone::M5, type::feature, priority::low, app
parent: 7
blocked_by: 43
---
> **Risk tier:** medium · **Size:** S

## Tasks

- [ ] Primary menu → "Export Favorites…" / "Import Favorites…" use `Gtk.FileDialog`, which goes through the **FileChooser portal**, so no `--filesystem` permission is needed
- [ ] Format: `{"schema_version": 1, "favorites": ["worldle", "connections", …]}`, UTF-8, 2-space JSON
- [ ] Import: validate the file, then **merge** by default (append unknown ids, keep the existing order). An `Adw.AlertDialog` offers "Merge" (default) or "Replace". Ids unknown to the current catalog are kept; they resolve once the catalog has them
- [ ] Toast: "Imported N favorites"
- [ ] Pure-Python parsing and merge logic in `dailies/core/` with unit tests

## Acceptance criteria

- [ ] Export, then reset favourites, then import → identical order
- [ ] A malformed file shows an error toast and changes nothing
- [ ] The manifest still has exactly the same finish-args

## References

- [`mvp-first.md` §6.3, §16 (M5)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
