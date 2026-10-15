# Dailies data, version 1

The app downloads these files; GitHub Pages publishes this directory as `https://tim-van-oudheusden.github.io/Dailies/v1/`.
The full format reference will live in [`docs/data-format.md`](../../docs/data-format.md).

| File | What it holds | Schema |
|---|---|---|
| `games.json` | The catalog: every daily game, one entry per game, sorted by `id`. Entries are never deleted; `status` becomes `broken` or `retired` instead, and `history` records why. | `schema/catalog.schema.json` |
| `popularity.json` | The weekly Popular and Trending shelves for one ISO week, valid for ten days. `method_version: 0` means the lists were picked by hand. | `schema/popularity.schema.json` |
| `domain_weights.json` | Maintainer-set order of the games on a shared registrable domain (`{"nytimes.com": {"wordle": 0.35, …}}`, weights in [0, 1] summing to 1 per domain). `scripts/popularity/compute.py` uses it to pick the two games of a domain a shelf may hold; the app does not read it. | checked by `compute.py` (see `docs/data-format.md`) |

`schema/` holds the JSON Schema 2020-12 files. Apps ignore fields they do not know, so adding an optional field is not
a breaking change; a breaking change goes to `data/v2/`.

Check the files locally with:

```sh
check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json
check-jsonschema --schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json
pytest tests/data
```
