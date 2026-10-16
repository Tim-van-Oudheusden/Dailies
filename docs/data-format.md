# Data format

The reference for the two JSON files Dailies reads: what each field means, which values are allowed, and the rules a
catalog entry has to meet. It is written for contributors adding or changing games and for anyone consuming the files.
The JSON Schemas are the source of truth; where this page and a schema disagree, the schema wins.

| File | What it holds | Schema |
|---|---|---|
| [`data/v1/games.json`](../data/v1/games.json) | The catalog: every daily game, one entry per game, sorted by `id` | [`catalog.schema.json`](../data/v1/schema/catalog.schema.json) |
| [`data/v1/popularity.json`](../data/v1/popularity.json) | The weekly Popular and Trending shelves for one ISO week | [`popularity.schema.json`](../data/v1/schema/popularity.schema.json) |

Both schemas are JSON Schema 2020-12. Validate the files the way CI does:

```sh
check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json
check-jsonschema --schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json
pytest tests/data
```

`tests/data/test_catalog_file.py` also checks the [rules the schemas cannot express](#rules-beyond-the-schemas).

**Where to get them.** Fetch the files from GitHub Pages at `https://tim-van-oudheusden.github.io/Dailies/v1/`, with
`https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/main/data/v1/` as the fallback. Both send an ETag; please
use conditional requests (`If-None-Match`) and fetch at most every few hours.

## `games.json`

### Top level

`additionalProperties` is allowed: consumers must ignore fields they do not know.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | integer, always `1` | yes | Format version. A breaking change publishes `data/v2/` with `schema_version: 2` |
| `generated_at` | string, `date-time` (RFC 3339) | yes | When the file was last written; an app keeps the newer of two copies |
| `games` | array of [game entries](#game-entry), unique | yes | Every game, sorted by `id` |

### Game entry

Unknown fields are allowed here too and must be ignored.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | string matching `^[a-z0-9][a-z0-9-]{1,48}$` | yes | Stable slug, 2 to 49 characters. Never renamed, never reused |
| `name` | string, 1 to 60 characters | yes | The game's name as its site shows it |
| `url` | string, URI starting with `https://` | yes | The page that starts today's puzzle |
| `category` | one of the [ten category ids](#categories) | yes | The single category the game is listed under |
| `difficulty` | `easy`, `medium` or `hard` | yes | See the [difficulty rubric](#difficulty) |
| `description` | string, 20 to 300 characters | yes | One or two sentences: what you guess and how |
| `tags` | array of strings matching `^[a-z0-9-]+$`, unique, at most 10 | no | Lower-kebab-case tags from the [tag vocabulary](#tags) |
| `language` | string matching `^[a-z]{2,3}(-[A-Za-z0-9]+)*$` | no | BCP 47 language of the game, e.g. `en`, `nl`, `pt-BR`. Treated as `en` when absent |
| `free_no_account` | boolean | no | `true` when the daily puzzle can be played in full without an account or subscription |
| `added` | string, `date` (`YYYY-MM-DD`) | yes | The day the entry was added to the catalog |
| `status` | `active`, `broken` or `retired` | yes | `active` games are shown. `broken` (the link fails or leads elsewhere) and `retired` (the game ended) are hidden, but the entry stays so favourites still resolve |
| `domain` | string, a lower-case host name | yes | The registrable domain (eTLD+1) of `url`, e.g. `teuteuf.fr` for `https://worldle.teuteuf.fr/`. Used for redirect checks and popularity lookups |
| `icon` | string matching `^icons/[a-z0-9-]+\.png$` | no | Icon path relative to the catalog base URL. Reserved; no entry has one yet |
| `icon_source` | `site`, `google`, `duckduckgo`, `manual` or `none` | no | Where `icon` came from. Reserved, like `icon` |
| `aliases` | array of strings | no | Other names the game is known by, including former names; used for duplicate detection and search |
| `wikipedia` | string | no | Title of the game's English Wikipedia article, for pageview lookups |
| `source_issue` | integer ≥ 1 | no | Number of the GitHub issue that proposed the game |
| `notes` | string, at most 300 characters | no | Maintainer notes; not shown in the app |
| `history` | array of [history events](#history-event), oldest first | no | Append-only log of what happened to the entry |

### History event

| Field | Type | Required | Meaning |
|---|---|---|---|
| `date` | string, `date` | yes | When it happened |
| `event` | string matching `^[a-z][a-z-]*$` | yes | What happened: `added`, `broken`, `retired`, `restored`, `renamed`, `url-changed`, … |
| `note` | string, at most 300 characters | no | Why, or a reference such as `issue #12` |

### Example

```json
{
  "id": "worldle",
  "name": "Worldle",
  "url": "https://worldle.teuteuf.fr/",
  "category": "geography",
  "difficulty": "easy",
  "description": "Identify a country from its silhouette, with distance and direction hints.",
  "tags": ["teuteuf", "countries", "silhouette"],
  "language": "en",
  "free_no_account": true,
  "added": "2026-10-15",
  "status": "active",
  "domain": "teuteuf.fr",
  "wikipedia": "Worldle",
  "history": [{ "date": "2026-10-15", "event": "added", "note": "seed" }]
}
```

## Categories

Every game has exactly one category. The list is fixed; there is deliberately no `other`, so the sidebar stays short.
A cluster that reaches about 15 games under one tag can become a category of its own.

| id | Display name | What belongs there |
|---|---|---|
| `words` | Words | Letters, words, phrases, crosswords, anagrams, semantic guessing. Any language |
| `geography` | Geography | Countries, flags, maps, borders, Street View, places |
| `music` | Music | Songs, artists, lyrics, instruments, audio clips |
| `movies-tv` | Movies & TV | Film, series, anime, actors, posters, box office |
| `video-games` | Video Games | Games, characters, franchises, esports |
| `numbers-logic` | Numbers & Logic | Arithmetic, sudoku-likes, deduction, chess, dominoes, pure logic |
| `trivia` | Trivia | General knowledge, ranking lists, nature and science, languages, history facts |
| `visual` | Pictures & Colors | Photos, art, colours, shapes; the puzzle is in looking |
| `food` | Food | Dishes, cuisines, grocery prices, food comparisons |
| `sports` | Sports | Players, teams, leagues, grids |

The **Add a game** issue form shows the display names; the submission tooling maps them to the ids.

## Tags

Tags are lower-kebab-case, at most ten per game (a handful is usual). Prefer a tag from this curated vocabulary; a new
tag is fine when none fits, and a tag that keeps coming back is added here in a PR.

| Group | Tags |
|---|---|
| Mechanics | `wordle-like`, `grouping` (Connections-likes), `grid` (Immaculate-Grid-likes), `multi-board`, `semantic`, `word-ladder`, `word-search`, `crossword`, `cryptic`, `deduction`, `estimation`, `higher-lower`, `ranking`, `pathfinding`, `comparison` |
| Media | `audio`, `photos`, `stills`, `clips`, `emoji`, `silhouette`, `street-view` |
| Subject | `history`, `nature`, `colors`, `chess`, `pokemon`, `anime`, `nba`, `nfl`, `soccer`, `countries`, `usa`, `flags` |
| Publisher or family | `nyt`, `merriam-webster`, `teuteuf`, `linkedin`, `puzzmo`, `the-atlantic`, `vulture` |
| Language | `non-english`, plus `dutch`, `french`, `spanish`, `portuguese`, `german` |
| Flags | see below |

Flags are the tags software acts on:

| Flag | Meaning |
|---|---|
| `fan-made` | An unofficial game built on someone else's IP (Pokédle, LoLdle, …). Listed, but these tend to disappear after takedowns |
| `account-required` | The daily puzzle cannot be played without an account. Such a game has `free_no_account: false` |
| `account-for-streaks` | Playable without an account; an account only keeps streaks or stats |
| `subscription-limited` | Part of the game, or of its archive, needs a paid subscription |
| `weekdays-only` | A new puzzle on weekdays only |
| `not-daily` | Not a once-a-day puzzle (endless or on demand); a few seed entries carry it; new submissions must be daily |
| `bot-walled` | The site answers scripts with a bot challenge (HTTP 403 or a Cloudflare page) or never answers them at all, so automated checks cannot prove it is live |
| `low-confidence` | Some details (difficulty, free play, liveness) could not be confirmed |

## Difficulty

Three values. The submitter suggests one and the maintainer adjusts it; no aggregator publishes difficulty, so this is
the one field Dailies curates itself. Judge a typical day for a newcomer:

| Value | Rubric | Examples |
|---|---|---|
| `easy` | Most people solve it in under about 3 minutes with general knowledge | Wordle, Worldle, Flagle, Strands |
| `medium` | Needs some domain knowledge, or 5 to 10 minutes | Connections, Globle, Framed, Nerdle |
| `hard` | Niche knowledge, or long sessions | Quordle, Actorle, Immaculate Grid, Tradle, Semantle |

## `popularity.json`

The weekly Popular and Trending shelves. Unlike the catalog, this schema is closed (`additionalProperties: false` at
every level), so a new field needs a schema change first. `method_version: 0` means the shelves were picked by hand;
from `1` on they are computed by the weekly workflow, and the number goes up whenever the formula changes. The app
reads `week`, `valid_until`, `popular` and `trending`; the rest is there for transparency and for computing the next
week's trend.

### Top level

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | integer, always `1` | yes | Format version |
| `method_version` | integer ≥ 0 | yes | Version of the ranking method; `0` is hand-curated |
| `week` | string matching `^\d{4}-W\d{2}$` | yes | The ISO 8601 week, e.g. `2026-W42` |
| `generated_at` | string, `date-time` | yes | When the shelves were computed |
| `valid_until` | string, `date-time` | yes | `generated_at` plus 10 days. After it the app still shows the shelves, marked "as of" the week |
| `stale` | boolean, default `false` | no | `true` when this week's sources failed and the previous shelves were kept |
| `popular` | array of [ranked items](#ranked-item), 1 to 20 | yes | The Popular shelf, best first |
| `trending` | array of [ranked items](#ranked-item), at most 20 | yes | The Trending shelf, best first; may be empty |
| `scores` | object: game `id` → [score](#score) | no | Per-game detail behind the shelves |
| `sources` | object: source name → [source health](#source-health) | yes | One entry per signal collected this week; `{}` when hand-curated |
| `attribution` | array of strings | yes | Credit lines for every external source used, including its licence; `[]` when none was used |
| `report` | string | no | URL of the week's human-readable report relative to `popularity.json` on GitHub Pages, e.g. `../popularity/2026-W42.md` (`docs/popularity/2026-W42.md` in the repository). Set by the publish job only when a report was written; see [`docs/popularity/`](popularity/README.md) |

### Ranked item

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | string | yes | A game `id` from `games.json` |
| `rank` | integer ≥ 1 | yes | Position on the shelf, starting at 1 |
| `score` | number, 0 to 1 | yes | The score the shelf is sorted by |
| `delta` | number or `null` | no | Change against the trailing four-week mean; Trending only |
| `reason` | `score`, `new` or `carried_forward` | no | Why the game is on the shelf: its score, being newly added (used to fill Trending), or carried over from last week |

### Score

| Field | Type | Required | Meaning |
|---|---|---|---|
| `popularity` | number | yes | The game's popularity score this week |
| `trend` | number or `null` | no | `popularity` minus the mean of the previous four weeks; `null` until two prior weeks exist |
| `tranco_rank` | integer or `null` | no | Tranco rank of the game's `domain` (mean of the last seven daily ranks) |
| `radar_bucket` | integer or `null` | no | Cloudflare Radar popularity bucket, if that source is enabled |
| `wiki_views_7d` | integer or `null` | no | English Wikipedia pageviews over seven days, if enabled |
| `hn_stories_28d` | integer or `null` | no | Hacker News stories over 28 days, if enabled |
| `shared_domain_weight` | number | no | Written only by `method_version: 1`: the share of a shared domain's score given to this game. Since `2` every game gets its domain's full score, so the field is left out |
| `history` | array of numbers, at most 8 | no | Previous weekly `popularity` values, for the trend |

### Source health

| Field | Type | Required | Meaning |
|---|---|---|---|
| `ok` | boolean | yes | Whether the source was usable this week |
| `fetched_at` | string, `date-time` | yes | When it was queried |
| `domains_resolved` | integer | no | Domains the source returned a value for |
| `domains_requested` | integer | no | Domains asked for |
| `error` | string | no | What went wrong, when `ok` is `false` |

### How `method_version: 2` is computed

Two scripts produce the file; every number is deterministic, so the same inputs and `--now` give byte-identical
output:

```sh
python -I scripts/popularity/collect.py --catalog data/v1/games.json --out raw/
python -I scripts/popularity/compute.py --catalog data/v1/games.json --raw raw/ \
    --out data/v1/popularity.json --summary summary.json
```

- `collect.py` asks Tranco once per distinct `domain` of the active games (1 request per second, one retry on a 5xx
  answer, up to three on a 429; about two minutes for the seed catalog) and writes `raw/tranco.json` with each
  domain's daily ranks and the source's health.
- `compute.py` scores each domain `clamp(1 − (log10(rank) − 2) / 4.5, 0, 1)` on the mean of its last seven daily
  ranks (no rank scores 0), and every game gets its domain's full score. A game whose domain could not be fetched
  keeps last week's `popularity` (`reason: "carried_forward"`). `trend` and `history` come from the previous
  `popularity.json` (`--previous`, by default the `--out` file) when its `method_version` is the same; history from
  another version (including `1`) is dropped.
- Shelves hold `N = max(5, min(12, 10 % of active games))` items. Popular is sorted by `popularity`. Trending takes
  games with `trend > 0.02` outside the top five Popular, sorted by `trend` (which is also their `score`); with fewer
  than three, the newest games fill it to three with `reason: "new"` and `score: 0`.
- At most **2** games of one registrable domain go on each shelf; when more qualify, the next games, from other
  domains, take the freed slots. Which two, and every tie, follows `data/v1/domain_weights.json`
  (`{"nytimes.com": {"wordle": 0.35, …}}`): listed games first, highest weight first, then the domain's unlisted
  games, then `id`. The weights only order a domain's games; they no longer split its score. The script rejects the
  file unless each domain's weights are numbers between 0 and 1 that sum to 1 and name existing games on that
  domain. The maintainer edits it by hand (decision #88, which superseded the equal split of #13 used by
  `method_version: 1`).
- If Tranco failed for more than 20 % of the domains, `compute.py` exits 1 and writes nothing. It also writes
  `summary.json` (shelves with names, top movers, source health), the input for the weekly report.

## Rules beyond the schemas

`tests/data/test_catalog_file.py` enforces these on every pull request:

| File | Rule |
|---|---|
| `games.json` | `id`s are unique and the array is sorted by `id` |
| `games.json` | URLs are unique after normalisation (lower-case host, no `www.`, no trailing slash, fragment or `utm_*` parameters) |
| `games.json` | `domain` is the registrable domain of `url`'s host (`foo.github.io` counts as its own site) |
| `games.json` | No entry uses a known dead or hijacked domain |
| `games.json` | `history`, when present, starts with an `added` event dated `added` |
| `games.json` | Every category has at least one active game |
| `games.json` | The file is under 100 KB, 2-space indented, UTF-8 without escaping, with a final newline |
| `popularity.json` | Every `id` on a shelf exists in `games.json`; no `id` appears twice on a shelf |
| `popularity.json` | Ranks run 1, 2, 3, … and scores never increase down a shelf |
| `popularity.json` | `valid_until` is exactly 10 days after `generated_at`, and `week` is the ISO week of `generated_at` |

## Submission rules

New games come in through the **Add a game** issue form; you do not need to edit `games.json` yourself. A game is
accepted when:

- **https only.** The URL starts with `https://` and the host resolves to a public address.
- **Same site at the end of the redirects.** After following redirects, the final registrable domain must match the
  submitted one. Dead DLE domains are regularly bought up and redirected to gambling sites; this rule keeps them out.
- **A daily puzzle.** The game publishes a new puzzle every day (tag `weekdays-only` if it skips weekends).
- **No account.** With `free_no_account: true` the daily puzzle must be playable in full without signing in or paying.
  A game that needs an account or a subscription for today's puzzle is listed only with `free_no_account: false` and
  the `account-required` or `subscription-limited` tag.
- **Not a duplicate** of an existing URL, `id` or alias.
- The submitter is not the author, or is and consents to the listing.

A bot checks every submission when it is opened or edited and comments with the result (labels `validated` or
`needs-changes`). When a maintainer adds `approved`, the checks run once more, and a passing submission becomes a pull
request `data(games): add <name>` that adds the entry to `games.json` (sorted by `id`, with `source_issue` and an
`added` history event) and closes the issue when merged. A submission that no longer passes gets a comment instead.

Maintaining the catalog follows four rules:

- **`id`s are immutable and never reused.** A renamed game keeps its `id`, gets a new `name`, the old name goes into
  `aliases` and a `renamed` event into `history`.
- **Status instead of deletion.** Entries are never removed. A game whose link breaks or that ends gets
  `status: broken` or `retired` and a matching `history` event, so installed apps can still resolve favourites; a game
  that comes back gets `status: active` and a `restored` event.
- **Additive changes stay in v1.** A new optional field, or a new tag, is not a breaking change because consumers
  ignore what they do not know. Dailies maps an unknown `category` to `trivia` and hides an entry whose `status` it
  does not know.
- **Breaking changes go to `data/v2/`.** Renaming, removing or retyping a field publishes a new directory with
  `schema_version: 2`; `data/v1/` keeps being published for at least two app releases.

## Licences

- **Catalog** (`games.json` and the schemas): [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Use it for
  anything, no attribution needed. Game names are trademarks of their owners; the catalog only links to their sites.
- **Popularity data** (`popularity.json`): derived from third-party signals. Reuse it with the credit lines listed in
  its `attribution[]` array, which names each source and its terms. The current hand-picked file
  (`method_version: 0`) uses no external source, so its list is empty.
- The app's code is GPL-3.0-or-later (see [`LICENSE`](../LICENSE)).
