---
key: 39
title: feat(data): catalog/popularity fetcher with ETag cache and bundled offline snapshot
type: Feature
labels: milestone::M1, type::feature, priority::high, app, data
parent: 3
blocked_by: 24, 37
---
> **Risk tier:** medium · **Size:** M · **Deps:** libsoup 3 via GI only, so no pip dependencies

## Why

The brief says popularity "is sourced online and saved in GitHub; the application retrieves it". The app must also work completely offline: a fresh install with no network still shows the full catalog from the bundled snapshot.

## Tasks

### Bundled snapshot
- [ ] Install `data/v1/games.json` and `data/v1/popularity.json` into `PKGDATADIR/data/v1/` (Meson `install_data`)

### `dailies/data/fetcher.py`
- [ ] One `Soup.Session` with `User-Agent: Dailies/<VERSION> (+https://github.com/Tim-van-Oudheusden/Dailies)` and no identifiers
- [ ] `refresh(name, urls, max_age)`:
  - skip if `now - fetched_at < max_age`
  - otherwise send a conditional GET with `If-None-Match: <etag>` to `urls[0]`
  - on 5xx, 429 or a network error, fall through to the next URL, honouring `Retry-After`; **never retry in a loop**
  - **304**: only bump `.fetched`
  - **200**: validate with `core.catalog.parse` / `core.popularity.parse` **before** touching the cache, then atomically replace (`write tmp → rename`) `<name>.json`, `<name>.etag`, `<name>.fetched`
  - on any failure, log and keep the last good copy
- [ ] Max age: catalog **6 h**, popularity **24 h**. Measured upstream cache headers: raw `max-age=300` + ETag; Pages `max-age=600` + ETag
- [ ] Use async Soup calls (`send_and_read_async`); never block the main loop
- [ ] Skip the refresh when `Gio.NetworkMonitor` reports `network-metered` (Bazaar pattern)

### Cache
- [ ] `$XDG_CACHE_HOME/dailies/v1/` (inside the Flatpak: `~/.var/app/<id>/cache/dailies/v1/`). Files: `games.json`, `games.etag`, `games.fetched`, and the same for `popularity`

### `dailies/data/store.py`
- [ ] `Store.load_initial()`: read the cache; if a file is missing or doesn't parse, copy the bundled file into the cache. Populate the `Gio.ListStore(GameObject)` **before the window is shown** (tens of KB, so no spinner except on a cold first run)
- [ ] `Store.reload(catalog, popularity)`: **diff by id** (update the properties of existing `GameObject`s, insert or remove only what changed) so the GridView keeps its scroll position
- [ ] Apply popularity ranks (`popular_rank`, `trending_rank`) and favourite state to each `GameObject`. The `GameObject` class itself lives in `ui/game_object.py` (#42); define it here first if #42 isn't ready, then move it
- [ ] `Fetcher.refresh_all()` runs **after the window maps**

### UI hooks (exposed for #41/#42/#47)
- [ ] Signals or properties: `last_success` (datetime), `popularity_week`, `popularity_stale`
- [ ] Banner rule: reveal an `Adw.Banner` "Showing the game list from <date>" **only** when the last successful fetch is older than **14 days** *and* the app is online, so a fresh offline install stays quiet
- [ ] `app.refresh` (#48) calls `refresh_all(force=True)` and toasts the outcome ("Game list updated", "Already up to date", "Couldn't update — showing saved list")

## Acceptance criteria

- [ ] Offline first run (`flatpak run --unshare=network …`) shows the full bundled catalog
- [ ] A second run within 6 h makes no catalog request (verify with `G_MESSAGES_DEBUG=all` or a logging line)
- [ ] With a valid ETag, the server answers 304 and nothing in the cache except `.fetched` changes
- [ ] A corrupt response (hand-served truncated JSON) leaves the cache untouched
- [ ] Unit tests for the cache-decision logic (age, ETag, fall-through ordering) live in pure Python with Soup mocked behind an interface, or as a Meson test

## References

- [`mvp-first.md` §3.1 (fetcher/store rows, diagram), §3.2, §3.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §3.1, §3.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
- [`bazaar.md` §6.2, §6.3, §12.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/bazaar.md)
