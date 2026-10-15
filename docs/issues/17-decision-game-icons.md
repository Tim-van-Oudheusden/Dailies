---
key: 17
title: Decision: game icons strategy (none / build-time / runtime favicons)
type: Task
labels: decision, milestone::M5, priority::low, data
parent: 7
---
## Question

Tiles show bundled **category glyphs** in the MVP. Should individual games get icons later, and from where?

| Option | How | For | Against |
|---|---|---|---|
| (a) none (MVP) | Category glyph in a tinted square | No trademark or redistribution question; zero network | Less recognisable tiles |
| (b) build-time favicons | `scripts/icons/fetch_icon.py` in stage B fetches manifest icon / apple-touch-icon / `link rel=icon` → `/favicon.ico` → (unofficial) Google faviconV2 / DuckDuckGo ip3; served from **Pages**, kept out of the Flatpak; takedown note ([`data-pipeline.md` §6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)) | Fast, cached, one origin | Dailies **redistributes** third-party marks; Flathub policy on trademark icons unchecked **[U]** |
| (c) runtime favicons | The app fetches each game's favicon from its own domain and caches it locally; never redistributed ([`dle-catalog.md` §4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)) | No redistribution | Leaks the user's catalog view to every game host; many requests |

Remote images must be decoded with glycin (`GlyGtk4-2`, 2.2.1 in Platform 51), which GTK recommends for untrusted images ([`libadwaita-ui-patterns.md` §9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)).

## Proposed default

**(a) now. Decide between (b) and (c) at M5 after asking on the issue tracker.** If (b) is chosen, also decide whether icons live in the main repo or on an orphan branch to keep history small (open question in [`data-pipeline.md` §8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)).

## How to close

Comment and close. #77 implements it.

## References

- [`mvp-first.md` §8 (Icons), §18.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
