# Dailies data pipeline research (key: data-pipeline)

Research date: 2026-10-15. Author: research subagent for the Dailies architecture document.

Legend used throughout: **[verified]** = read from a primary source or observed with `curl`/`gh` on 2026-10-15 (source URL given); **[inferred]** = reasoning or recommendation not directly stated by a source; **[unverified]** = could not be confirmed, treat as a claim to check.

---

## 0. Executive summary and recommendations for Dailies

1. **Submissions via a GitHub Issue Form** (`.github/ISSUE_TEMPLATE/new-game.yml`) with `required` validations, dropdowns for category/difficulty, and an auto-applied `game-submission` label. GitHub's form schema supports `input`, `textarea`, `dropdown` (single or `multiple`), `checkboxes`, `markdown`, `upload`; `validations.required` only works on public repositories, which Dailies is. [verified]
2. **IssueOps automation in two stages**: (a) on `issues: [opened, edited]` parse the form with `stefanbuck/github-issue-parser@v3.2.5`, run a small Python validator (schema, URL reachable, duplicate check) and post the result as a comment plus a `validated` / `needs-changes` label; (b) when a maintainer adds `approved`, generate the JSON entry and open a PR with `peter-evans/create-pull-request@v8.1.1`, body `Closes #N`. Auto-merge is possible (`gh pr merge --auto --squash`, requires the repo setting "Allow auto-merge" and a ruleset with required checks) but I recommend keeping a human merge click for v1; the approval label already is the human gate. [verified for the actions and settings; the two-stage design is inferred]
3. **Catalog = one JSON file in the repo** (`data/v1/games.json`) validated in CI against `data/v1/schema/catalog.schema.json` (JSON Schema 2020-12) with `check-jsonschema`. Stable `id` slugs that are never reused; soft-delete via `status` instead of removal; `schema_version` in the file and `/v1/` in the path for breaking changes; apps must ignore unknown fields.
4. **Distribution**: publish `data/v1/*.json` and icons to **GitHub Pages** (`https://tim-van-oudheusden.github.io/Dailies/v1/games.json`) from an Actions deploy; it returns `ETag` and `Cache-Control: max-age=600` [verified by curl on a Pages site]. Fallback URL: `raw.githubusercontent.com` (`max-age=300`, `ETag` + `If-None-Match` -> 304 [verified]). jsDelivr is a fine third option but caches branches 12 h and `@latest` 7 days [verified]. Release assets redirect to one-hour signed URLs with `Cache-Control: no-cache` [verified], so use releases for app binaries, not the live catalog. The Flatpak bundles a snapshot of the data so first run and offline work.
5. **Popularity sources, ranked for Dailies**: (1) **Tranco** `GET https://tranco-list.eu/api/ranks/domain/{domain}` - no key, 1 request/second, 30 days of daily ranks, covers even small DLE domains (ranks observed between 21,392 and 1,487,156 for eight sample games) [verified]; (2) **Cloudflare Radar** `/radar/ranking/domain/{domain}` and `/radar/ranking/top?rankingType=TRENDING_RISE` - free API token with "Account > Radar: Read", data licensed CC BY-NC 4.0 [verified]; (3) **Wikipedia pageviews** (CC0, no key, strict User-Agent) - great for the ten famous games, 404 for most others [verified]; (4) **HN Algolia** - no key, 10,000 req/h/IP, weak but free "buzz" signal [verified]. Reddit (OAuth + registration), Google Trends (pytrends archived, official API gated alpha) and Similarweb (paid/unverified free tier) are excluded from v1. No in-app telemetry, per the brief.
6. **Weekly job = deterministic Python + optional Claude narrative.** The numbers (popular/trending scores) must be computed by a plain Python script so they are reproducible and testable; Claude (via `anthropics/claude-code-action@v1`, automation mode with `prompt`, or a 20-line Anthropic SDK call) writes the human-readable `docs/popularity/YYYY-Www.md` report and sanity-checks anomalies. The job opens a PR with `create-pull-request`; it never pushes to `main`. Fail closed: if any source fails, the previous `popularity.json` stays in place and the file carries `stale: true` metadata. Cron must not sit at minute 0, and public-repo scheduled workflows are disabled after 60 days without repository activity [verified].
7. **Icons**: fetch at build time into `data/v1/icons/<id>.png` (HTML `<link rel="icon">` / apple-touch-icon -> `/favicon.ico` -> Google `faviconV2` -> DuckDuckGo `ip3`), normalise to 64x64 PNG, serve via Pages, with a runtime fallback to a symbolic placeholder. Icons are the trademarks of their owners; keep them out of the Flatpak payload, publish a takedown note in `CONTRIBUTING.md`, and treat the Google/DDG endpoints as unofficial and unsupported [verified that both are undocumented; licensing stance is inferred].
8. **Weekly rotation**: `popular` = top N by trailing-28-day composite score (Tranco rank dominant); `trending` = largest positive score delta versus the previous 28 days with a minimum-rank floor, excluding items already in `popular`. Both are stored in one `data/v1/popularity.json` keyed by ISO week with `generated_at`, `valid_until`, `method_version`, per-entry `sources`.

---

## 1. GitHub Issue Forms for submitting a DLE

### 1.1 Form schema facts [verified]

Source: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms and https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema

- Top-level keys: `name` (required, unique among templates), `description` (required), `body` (required array), `title` (prefilled issue title), `labels` (array or comma string; labels that do not exist in the repo are skipped silently), `assignees`, `projects`, `type` (org issue type).
- Element types: `markdown` (not submitted), `input`, `textarea` (`render` turns it into a code block), `dropdown` (`options` non-empty and distinct, `multiple`, `default` zero-based index), `checkboxes` (per-option `required`), `upload` (`accept` extension list; images <= 10 MB).
- `id`: alphanumeric, `-` and `_` only; unique; used for URL prefill (`?title=...&<id>=...`).
- `validations.required` and `min_length` exist for `input`/`textarea`; `required` for `dropdown`, `checkboxes`, `upload`. **`required` is enforced on public repositories only.**
- The schema page says it is in public preview and may change.
- The form is rendered into the issue body as Markdown: each field becomes `### <label>` followed by the value, `_No response_` for empty optional fields, `- [x]`/`- [ ]` for checkboxes, and multi-select dropdowns become a comma-separated list (observed in the parser fixture `"browsers": "Chrome, Safari"`). [verified from the parser repo fixtures, see 1.2]

### 1.2 Parsers [verified]

| Action | Latest release (2026-10-15) | Dropdown mapping | Checkbox mapping | Notes |
|---|---|---|---|---|
| `stefanbuck/github-issue-parser` | v3.2.5 (2026-04-22), commit `cb6e97157cbf851e3a393ff8d57c93a484cc323f`; runs on `node24` | string (multi-select = `"A, B"`) | array of checked labels; `[]` if none | Inputs `template-path` (optional, maps labels -> ids), `issue-body` (default `${{ github.event.issue.body }}`); outputs `jsonString` and `issueparser_<id>`; also writes `$HOME/issue-parser-result.json`. `_No response_` becomes `""`. Code blocks are not split into sections. Source: https://github.com/stefanbuck/github-issue-parser (README, `index.js`, `fixtures/full-example`). |
| `issue-ops/parser` (GitHub's IssueOps org) | v5.0.0 (2025-12-04), commit `cb7e2e4e5da701aad0e23e718bc4c91d442ca8ba` | **array** (`["red","blue"]`) | object `{selected:[],unselected:[]}` | Inputs `body`, `issue-form-template`, `workspace`; outputs `json`, `parsed_<key>`. Keys slugified from headings. Source: https://github.com/issue-ops/parser README. `issue-ops/validate` returned 404 for me: it may have been renamed or made private - **do not plan on it** [unverified]. |

Recommendation: `stefanbuck/github-issue-parser` because the owner's other repositories already pin third-party actions by SHA and its output shape is flat; the template-path mapping means our Python validator reads `issueparser_*` keys that equal the form `id`s.

### 1.3 Proposed template `.github/ISSUE_TEMPLATE/new-game.yml` (copy-ready)

```yaml
name: Add a daily game
description: Propose a DLE (daily guessing game) for the Dailies catalog.
title: "game: <name>"
labels: ["game-submission"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for adding a daily! A bot checks this form in a minute (URL reachable,
        not already listed) and a maintainer approves it. Fields marked * are required.
  - type: input
    id: name
    attributes:
      label: Name
      description: The game's name as shown on its site.
      placeholder: e.g. Worldle
    validations:
      required: true
  - type: input
    id: url
    attributes:
      label: URL
      description: The page that starts today's puzzle. https only.
      placeholder: https://worldle.teuteuf.fr/
    validations:
      required: true
  - type: dropdown
    id: category
    attributes:
      label: Category
      options:
        - Words
        - Geography
        - Music
        - Film & TV
        - Video games
        - Sports
        - Trivia & general knowledge
        - Numbers & logic
        - Pictures & art
        - Food & drink
        - Other
    validations:
      required: true
  - type: dropdown
    id: difficulty
    attributes:
      label: Difficulty
      description: How hard is a typical day for a newcomer?
      options:
        - Easy
        - Medium
        - Hard
      default: 1
    validations:
      required: true
  - type: textarea
    id: description
    attributes:
      label: Description
      description: One or two sentences. What do you guess, and how many tries do you get?
      placeholder: Guess the country from its silhouette in six tries; distance and direction hints.
    validations:
      required: true
      min_length: 20
  - type: input
    id: tags
    attributes:
      label: Tags
      description: Optional, comma separated. e.g. countries, maps, six-tries
  - type: input
    id: language
    attributes:
      label: Language
      description: BCP 47 code of the game's language, e.g. en, nl, fr. Default en.
      placeholder: en
  - type: input
    id: icon_url
    attributes:
      label: Icon URL
      description: Optional. Direct link to a square PNG/SVG if the site's favicon is poor.
  - type: checkboxes
    id: checks
    attributes:
      label: Checks
      options:
        - label: The game publishes a new puzzle every day (it is a "daily").
          required: true
        - label: Playing does not require creating an account.
          required: true
        - label: I am not the game's author, or I am and I am happy for it to be listed.
          required: true
```

Also add `.github/ISSUE_TEMPLATE/config.yml` [verified that `blank_issues_enabled` and `contact_links` exist on the GitHub templates docs]:

```yaml
blank_issues_enabled: true
contact_links:
  - name: Report a broken game link
    url: https://github.com/Tim-van-Oudheusden/Dailies/issues/new?template=issue.yml&labels=data
    about: Use the general issue form; mention the game id.
```

Keep the owner's existing generic `issue.yml` (reproduced in Appendix A1) alongside it; its `Type`/`Scope`/`Priority` dropdowns are part of the ACMM scaffolding another agent is covering.

Labels to create: `game-submission`, `validated`, `needs-changes`, `approved`, `duplicate`, `data` (plus the existing `type::*`, `priority::*` set). The form only auto-applies `game-submission`; the rest are set by the workflow or maintainer.

### 1.4 Validation and PR automation

Design (two workflows; the first runs on untrusted input with read-only token):

**Stage A - `.github/workflows/game-submission-check.yml`** on `issues: [opened, edited]` filtered by `contains(github.event.issue.labels.*.name, 'game-submission')`:

1. `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1` (sparse: `data/`, `scripts/`, `.github/ISSUE_TEMPLATE/`).
2. `stefanbuck/github-issue-parser@cb6e97157cbf851e3a393ff8d57c93a484cc323f # v3.2.5` with `template-path: .github/ISSUE_TEMPLATE/new-game.yml`.
3. `actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0` and `python -I scripts/validate_submission.py --parsed "$HOME/issue-parser-result.json" --catalog data/v1/games.json --out "$RUNNER_TEMP/result.json"`. Checks:
   - URL parses, scheme is `https`, host is public (reject RFC1918/loopback/link-local after DNS resolution: an Actions runner performing a request to an attacker-controlled URL is a mild SSRF surface, so bound it) [inferred];
   - `HEAD` then `GET` with a 10 s timeout, max 5 redirects, descriptive User-Agent; accept 2xx (some sites answer 403/405 to HEAD, so fall back to GET) [inferred];
   - duplicate detection: normalise URL (lower-case host, strip `www.`, strip trailing slash and `utm_*`), compare host+path against existing `url` values; also compare slugified name against existing `id`s and `aliases` [inferred];
   - produce the candidate entry (`id` = slug of name, `added` = today, `source_issue` = N) and validate it against `catalog.schema.json` with `check-jsonschema`.
4. Comment with `peter-evans/create-or-update-comment@e8674b075228eee787fea43ef493e45ece1004c9 # v5.0.0` (use `comment-id` lookup to update the same comment on edits), and swap labels `validated` / `needs-changes` with `gh issue edit --add-label/--remove-label`.
5. Permissions: `issues: write`, `contents: read`. Pass every parsed value through `env:` not inline `${{ }}` in `run:` (GitHub's script-injection guidance, also stated in the parser README) [verified].

**Stage B - `.github/workflows/game-submission-approve.yml`** on `issues: [labeled]` where `github.event.label.name == 'approved'` and `contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.sender.author_association)` [the author_association guard mirrors the owner's `claude.yml`; `sender` is the user who applied the label - inferred from the webhook payload shape]:

1. Re-run the parser and validator (never trust the stage-A result; labels can be removed and re-added).
2. `python -I scripts/add_game.py --parsed ... --catalog data/v1/games.json --icons data/v1/icons` appends the entry (sorted by `id`) and fetches the icon (section 6).
3. `peter-evans/create-pull-request@5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1` with `branch: data/add-<slug>`, `title: "data(games): add <name>"`, `body: "Closes #N ..."`, `labels: data, automated`, `delete-branch: true`, `add-paths: data/**`.
4. Optional: `gh pr merge --auto --squash "$PR_URL"` (needs the repository setting Settings > General > Pull Requests > "Allow auto-merge", and a ruleset with required status checks so the PR cannot merge instantly) [verified: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-auto-merge-for-pull-requests-in-your-repository and https://cli.github.com/manual/gh_pr_merge].

Token facts [verified, create-pull-request README]: a PR created with the default `GITHUB_TOKEN` **does not trigger** `on: push`/`on: pull_request` workflows, so CI (schema check) would not run on it. Options: (a) use a fine-grained PAT (`contents`, `pull-requests` write) or a GitHub App token as `token:`; (b) run the schema check inside stage B before opening the PR and accept that the PR shows no checks; (c) use `workflows: write` if the PR could touch `.github/workflows` (it never should). The repository also needs "Allow GitHub Actions to create and approve pull requests" enabled under Settings > Actions > General. Repositories created after 2023-02-02 default `GITHUB_TOKEN` to read-only, so grant `contents: write` and `pull-requests: write` on the job.

Full workflow skeletons are in Appendix A2/A3.

---

## 2. Catalog format and JSON Schema

### 2.1 Layout

```
data/
  v1/
    games.json            # the catalog (single file, sorted by id)
    popularity.json       # weekly popular/trending (section 7)
    icons/<id>.png        # 64x64 PNG, build-time fetched (section 6)
    schema/
      catalog.schema.json
      popularity.schema.json
docs/popularity/2026-W42.md   # human report written by the weekly job
```

Why one file: at tens to low hundreds of entries it stays under 100 KB, one HTTP round-trip, one ETag. Split per category only if it passes ~1 MB [inferred].

### 2.2 `catalog.schema.json` (JSON Schema 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://tim-van-oudheusden.github.io/Dailies/v1/schema/catalog.schema.json",
  "title": "Dailies catalog",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "generated_at", "games"],
  "properties": {
    "schema_version": { "const": 1 },
    "generated_at": { "type": "string", "format": "date-time" },
    "games": {
      "type": "array",
      "items": { "$ref": "#/$defs/game" },
      "uniqueItems": true
    }
  },
  "$defs": {
    "game": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "name", "url", "category", "difficulty", "description", "added", "status"],
      "properties": {
        "id": { "type": "string", "pattern": "^[a-z0-9][a-z0-9-]{1,48}$",
                "description": "Stable slug. Never reused, never renamed." },
        "name": { "type": "string", "minLength": 1, "maxLength": 60 },
        "url": { "type": "string", "format": "uri", "pattern": "^https://" },
        "category": { "enum": ["words", "geography", "music", "film-tv", "video-games",
                                "sports", "trivia", "numbers-logic", "pictures", "food", "other"] },
        "difficulty": { "enum": ["easy", "medium", "hard"] },
        "description": { "type": "string", "minLength": 20, "maxLength": 300 },
        "tags": { "type": "array", "items": { "type": "string", "pattern": "^[a-z0-9-]+$" },
                  "maxItems": 10, "uniqueItems": true },
        "language": { "type": "string", "pattern": "^[a-z]{2,3}(-[A-Za-z0-9]+)*$", "default": "en" },
        "added": { "type": "string", "format": "date" },
        "status": { "enum": ["active", "broken", "retired"],
                    "description": "Soft delete: apps hide broken/retired entries but keep favourites." },
        "icon": { "type": "string", "pattern": "^icons/[a-z0-9-]+\\.png$",
                  "description": "Path relative to the catalog base URL." },
        "icon_source": { "enum": ["site", "google", "duckduckgo", "manual", "none"] },
        "aliases": { "type": "array", "items": { "type": "string" } },
        "domain": { "type": "string", "description": "Registrable domain used for popularity lookups (eTLD+1)." },
        "wikipedia": { "type": "string", "description": "en.wikipedia article title for pageview lookups, if any." },
        "source_issue": { "type": "integer", "minimum": 1 },
        "notes": { "type": "string", "maxLength": 300 }
      }
    }
  }
}
```

Entry example:

```json
{
  "id": "worldle",
  "name": "Worldle",
  "url": "https://worldle.teuteuf.fr/",
  "category": "geography",
  "difficulty": "medium",
  "description": "Guess the country from its silhouette in six tries, with distance and direction hints.",
  "tags": ["countries", "maps", "six-tries"],
  "language": "en",
  "added": "2026-10-15",
  "status": "active",
  "icon": "icons/worldle.png",
  "icon_source": "site",
  "domain": "teuteuf.fr",
  "wikipedia": "Worldle",
  "source_issue": 12
}
```

### 2.3 Versioning and stability rules [inferred, standard practice]

- Additive changes (new optional field, new enum value handled by `other` fallback) do not bump the version. Apps must ignore unknown fields and map unknown `category` to `other`.
- Breaking changes (field renamed/removed/type changed) create `data/v2/` and `schema_version: 2`; keep publishing `v1` for at least two app releases.
- `id` is immutable; a rename changes `name` and appends the old name to `aliases`.
- Never delete entries; set `status` so favourites in installed apps keep resolving.
- CI: `check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json` (pip/pipx package `check-jsonschema`, also a pre-commit hook; https://github.com/python-jsonschema/check-jsonschema) plus a Python test for sorted/unique ids, unique normalised URLs, and every `icon` path existing. [verified that check-jsonschema exists and its CLI form; the extra tests are inferred]

Seed data: "Wordles of the World" (https://rwmpelstilzchen.gitlab.io/wordles/, 780 entries, **CC0**) is a legitimate bulk source for an initial import of names/URLs [verified: license stated on the page]. `rarelygoeshere/wordleweb` has no license, so only use it as a discovery aid, not for copying text [verified: no license text in README].

---

## 3. Fetching the catalog from the app

### 3.1 Measured behaviour (curl, 2026-10-15) [verified]

| Channel | URL shape | Cache-Control observed | ETag / 304 | CORS | Notes |
|---|---|---|---|---|---|
| raw.githubusercontent.com | `https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/main/data/v1/games.json` | `max-age=300`, `via: 1.1 varnish`, `expires` 5 min | Yes; `If-None-Match` returned `304` | `*` | Content-Type is `text/plain`. No documented rate limit; community reports of 429s under heavy polling and of the 5-minute cache being unbypassable (https://github.com/orgs/community/discussions/46691, https://issues.fluidproject.org/browse/FLUID-6626/). |
| GitHub Pages | `https://tim-van-oudheusden.github.io/Dailies/v1/games.json` | `max-age=600` (observed on pages.github.com) | Yes (`etag: "689c7eef-386e"`) | `*` | Served by Fastly (`x-served-by: cache-ams-...`). Limits: 1 GB site, soft 100 GB/month bandwidth, soft 10 builds/hour (not when deployed via Actions), requests may get HTTP 429, no SLA, not for commercial transactions (https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits). Custom headers cannot be set. |
| jsDelivr | `https://cdn.jsdelivr.net/gh/Tim-van-Oudheusden/Dailies@main/data/v1/games.json` | `public, max-age=604800, s-maxage=43200`, `x-jsd-version-type: branch` | Weak ETag | `*` | Documented TTLs: branches 12 h, `@latest`/semver ranges 7 days, exact tags/commits ~permanent; files > 20 MB unsupported; free, no bandwidth caps; purge by email request only (https://github.com/jsdelivr/jsdelivr README). The browser-facing `max-age=604800` means a GLib/libsoup HTTP cache would hold a branch file for a week unless the app revalidates explicitly. |
| GitHub Release asset | `https://github.com/<o>/<r>/releases/latest/download/games.json` | `no-cache`, 302 to `release-assets.githubusercontent.com` with a signed URL valid ~1 h | ETag on final object | n/a | `/releases/latest/download/<name>` is a stable alias (observed 302). Good for immutable snapshots tied to app releases, poor for a mutable weekly feed. Unauthenticated API calls (`api.github.com`) are limited to 60/hour, so never use the REST API from the app (https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api). |

### 3.2 Recommendation [inferred]

- **Primary**: GitHub Pages. Deploy `data/v1/` (and `docs/`) with `actions/upload-pages-artifact` + `actions/deploy-pages` on push to `main`. Benefits: URL independent of repo layout/branch, 10-minute TTL, ETags, can move to a custom domain later with the same path, same place a project website could live. Cost risk: 100 GB/month soft cap. At 50 KB per full fetch and 304s for unchanged data, 1 million fetch attempts/month cost well under 1 GB if 98 % are 304s; fine for the foreseeable scale.
- **Secondary**: `raw.githubusercontent.com` same path; try it if Pages returns 5xx/429.
- **Bundled snapshot**: the Flatpak build copies `data/v1/games.json`, `popularity.json` and icons into `/app/share/dailies/data/v1/`. The app seeds its cache from it on first run and uses it whenever the network is unavailable (also satisfies a Flatpak reviewer that the app is usable offline).
- **Client cache policy**: store `games.json` + `ETag` + `fetched_at` in `$XDG_CACHE_HOME/dailies/`. On startup and at most once per 6 hours send `If-None-Match`; on 304 just refresh `fetched_at`. For `popularity.json` once per 24 hours is enough (it changes weekly). Respect `Retry-After` on 429, back off exponentially, never retry in a loop. Send a descriptive `User-Agent: Dailies/<version> (+https://github.com/Tim-van-Oudheusden/Dailies)`. Validate the downloaded JSON against the bundled schema (or at least `schema_version == 1`) before replacing the cache; keep the previous good copy on failure.
- Flatpak needs `--share=network` in the finish-args (the app fetches data and opens web games anyway).

---

## 4. Popularity data sources

### 4.1 Comparison

| Source | Access | Cost / key | Terms and license | Coverage for DLEs | Signal: popular (absolute) | Signal: trending (relative) | Verdict |
|---|---|---|---|---|---|---|---|
| **Tranco** (https://tranco-list.eu) | `GET https://tranco-list.eu/api/ranks/domain/{domain}` -> `{"ranks":[{"date":"2026-10-14","rank":156},...]}` (>= 30 daily points). Daily list zip at `/top-1m.csv.zip` (and `-incl-subdomains`). List updated daily by 00:00 UTC. [verified: https://tranco-list.eu/api_documentation and live call] | Free; **no key for `/ranks/domain`**; **1 request/second** (429 above); list creation needs an account | License not stated on the site [unverified]; upstream sources include Cloudflare Radar (CC BY-NC 4.0), Majestic (CC BY 3.0), CrUX (CC BY-SA 4.0), Umbrella. Treat as attribution-required, non-commercial-safe. | Excellent: observed ranks for nytimes.com 156, wordleunlimited.org 21,392, teuteuf.fr 40,873, globle-game.com 57,356, nerdlegame.com 62,988, scrandle.com 544,636, semantle.com 723,783, heardle.app 1,487,156 [verified] | Strong. Rank is a 30-day average over four providers so it is stable; use `log10(rank)`. Caveat: ranks are per registrable domain, so `nytimes.com` covers Wordle, Connections, Spelling Bee and the newspaper together. | Medium. 30-day smoothing damps spikes; week-over-week rank deltas are still usable for established domains. | **Primary source.** ~1 call per game per week. |
| **Cloudflare Radar** (https://developers.cloudflare.com/radar/) | `GET https://api.cloudflare.com/client/v4/radar/ranking/domain/{domain}` (rank, bucket, categories, top locations), `GET /radar/ranking/top?rankingType=POPULAR|TRENDING_RISE|TRENDING_STEADY&limit=...&date=...&location=...` (`pctRankChange` only for trending), `GET /radar/ranking/timeseries_groups`, bucket CSVs via `/radar/datasets`. Top-100 is daily; the top-1M buckets are weekly. [verified: Cloudflare API reference and dataset docs; **query parameters of the per-domain endpoint not verified**] | Free; **API token required** (Custom token, permission "Account > Radar > Read"); global limit 1,200 requests/5 min per user | **CC BY-NC 4.0** for API and downloads (radar.cloudflare.com/about) [verified via search of the about pages]; attribution required | Good for anything in the top 1M; small games fall out of the buckets | Good (bucketed: 200/500/1k/...1M, so coarse below the top 100) | Good: the only source with a first-party **trending** ranking, but it covers the whole web, so a DLE will rarely appear in it. | **Secondary**: enrich with bucket + categories; store the token as `CLOUDFLARE_RADAR_TOKEN` secret. Optional in v1. |
| **Wikipedia pageviews** (Wikimedia Analytics API) | `GET https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/{granularity}/{start}/{end}` e.g. `en.wikipedia/all-access/user/Wordle/daily/20261001/20261014` [verified live]. Data from 2015-07-01. Monthly granularity truncates to the requested range (use full months). | Free, no key. **Mandatory descriptive User-Agent** with contact info and the word "bot" for automated clients; generic agents get 403. New 2026 rate-limit classes: 200 req/min for a compliant unauthenticated bot, 10/min for unidentified clients (https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits) | Data **CC0 1.0** (https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/access-policy.html) | Poor: `Wordle` 403k views/month, `Worldle` 2.1k, `Nerdle` 838, `Semantle` 532, `Heardle` 522, `Globle` 98; `Connections_(game)`, `Framed_(game)`, `Scrandle` -> 404 [verified]. Only ~10 games have articles. | Weak except for the famous few | Decent for games that have an article (daily series; detect spikes) | **Tertiary, optional** via the `wikipedia` field. Zero cost, high trust, CC0. |
| **Hacker News (Algolia)** | `GET https://hn.algolia.com/api/v1/search_by_date?query=<name>&tags=story&numericFilters=created_at_i>UNIX,created_at_i<UNIX` -> `nbHits`, hits with `points`, `num_comments` [verified live; URL-encode `>`] | Free, no key, **10,000 requests/hour/IP** (https://hn.algolia.com/api) | Algolia-hosted; no explicit license for counts; HN data is public | Any name, but ambiguous names ("Framed", "Connections") produce noise; restrict to `query="<name> daily"` or the domain in `url:` | Weak | Useful for launches/new-game buzz | Optional, low weight. |
| **Reddit Data API** | OAuth2 required; `r/<sub>/about` subscribers, search | Free for non-commercial use; **100 QPM per OAuth client id**; unauthenticated requests are rejected; app registration at reddit.com/prefs/apps; some sources claim self-service registration is now manual-approval [unverified] (https://www.redditinc.com/policies/data-api-terms could not be fetched; archived rules: https://github.com/reddit-archive/reddit/wiki/API) | Reddit Data API Terms; strict User-Agent format | Many DLEs have subreddits (r/wordle, r/Worldle), most small ones do not | Medium (subscribers) | Medium (posts/week) | **Skip in v1**; revisit if a maintainer registers an app. |
| **Google Trends** | `pytrends` archived 2025-04-17, returns 429/404 [secondary sources]; official **Google Trends API alpha** announced 2025-07-24, application-gated, no GA date (https://developers.google.com/search/blog/2025/07/trends-api) | n/a | ToS forbids scraping | n/a | n/a | n/a | **Skip.** Re-evaluate when the API is GA. |
| **Similarweb** | Paid plans from ~$149/month; a free DigitalRank tier is claimed by one third-party page and denied by others [unverified] | Paid | Commercial license | Good | Good | Good | **Skip.** |
| **Steam** | Not applicable: DLEs are web games | | | | | | Skip |
| **App-internal telemetry** | Prohibited by the brief (no accounts, privacy) | | | | | | **Excluded.** Favourites stay on-device. |

Notes on legality/ToS: the sources selected (Tranco, Radar, Wikimedia, HN Algolia) all publish an API meant for programmatic use and require only attribution (Radar additionally non-commercial; Dailies is GPL-3.0 free software, not a commercial service, so CC BY-NC is compatible, but note it if the project ever sells anything). Record the attribution in `README.md` ("Popularity data: Tranco (tranco-list.eu), Cloudflare Radar (CC BY-NC 4.0), Wikimedia Analytics (CC0)") and in `popularity.json` `attribution`.

### 4.2 Composite score [inferred, proposed]

For each game `g` with registrable domain `d(g)`:

- `tranco_score = clamp(1 - (log10(rank) - 2) / 4.5, 0, 1)` using the mean of the last 7 daily Tranco ranks; rank 100 -> 1.0, rank 1,000,000 -> 0.11; no rank -> 0 and `tranco_missing: true`.
- `wiki_score = clamp(log10(views_7d + 1) / 6, 0, 1)` when `wikipedia` is set (1 M views/week -> 1.0).
- `hn_score = clamp(log10(stories_28d + 1) / 2, 0, 1)` optional.
- `popularity = 0.8 * tranco_score + 0.15 * wiki_score + 0.05 * hn_score` (weights renormalised over sources present).
- **Shared-domain correction**: games sharing a domain (nytimes.com) split a domain's Tranco contribution equally unless an explicit `domain_weight` override exists in `data/v1/domain_weights.json` [inferred; this is the main modelling weakness and should be an open question for the owner].
- `trend = popularity_this_week - mean(popularity of previous 4 weeks)`; require at least 2 prior weeks of history, else `trend = null`.

---

## 5. Weekly scheduled workflow with an agentic step

### 5.1 Facts [verified]

- `schedule` cron: five-field POSIX cron, UTC by default (`timezone` key optional), minimum every 5 minutes, runs on the default branch only, can be delayed under load (especially at the top of the hour), **disabled after 60 days without repository activity in public repos**, `@weekly` shorthand unsupported (https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows).
- `anthropics/claude-code-action`: latest release tag `v1.0.250` = commit `a26b07d8c778b0c43f64618e5fd29fd0f8af72e8` (moving tag `v1` = `89de2884dfb82a6f05363c853c717419cd72bc8a`). Composite action, installs Bun 1.3.14. Inputs include `prompt`, `claude_args`, `anthropic_api_key`, `claude_code_oauth_token`, workload-identity-federation inputs (`anthropic_federation_rule_id`, `anthropic_organization_id`, `anthropic_service_account_id`, requires `id-token: write`), `github_token`, `settings`, `additional_permissions`, `use_commit_signing`, `ssh_signing_key`, `track_progress`, `display_report`, `show_full_output`, `plugins`, `plugin_marketplaces`, `allowed_bots`, `allowed_non_write_users`, `branch_prefix`, `label_trigger`, `trigger_phrase`. Outputs: `conclusion`, `execution_file`, `branch_name`, `github_token`, `structured_output` (when `--json-schema` is passed in `claude_args`), `session_id`. `max_turns`, `model`, `allowed_tools`, `disallowed_tools` inputs are deprecated in favour of `claude_args` (`--max-turns 10`, `--model ...`, `--allowedTools "Read,Write,Edit,Bash(python:*)"`, `--disallowedTools WebSearch`). Mode is auto-detected: a `prompt` on `schedule`/`workflow_dispatch` = automation mode. Security doc: Claude does not create PRs by itself in tag mode (it pushes a branch and links to the PR page); in automation mode it can do whatever `Bash(gh ...)` patterns you allow; keep `show_full_output` off on public repos; prompt-injection risk from issue content; use `use_commit_signing: true` or an `ssh_signing_key` for verified commits. Sources: `action.yml`, `docs/usage.md`, `docs/configuration.md`, `docs/security.md`, `docs/solutions.md` in https://github.com/anthropics/claude-code-action.
- The owner's `MinimalUI/.github/workflows/claude.yml` already uses `claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}`, pins the action by SHA (v1.0.248), restricts triggers to OWNER/MEMBER/COLLABORATOR, and refuses fork PRs. Reuse that file verbatim for interactive `@claude`, and add the scheduled job as a separate workflow (reproduced in Appendix A1).
- Anthropic API pricing (from the bundled `claude-api` skill table, cached 2026-10-06): `claude-opus-5-5` $4 / $20 per MTok (in/out), `claude-sonnet-5-5` $2 / $10, `claude-haiku-5-5` $0.10 / $0.50. The skill's default model recommendation is `claude-opus-5-5`.

### 5.2 Design: deterministic numbers, Claude for prose [inferred]

`.github/workflows/popularity.yml` (full skeleton in Appendix A4):

1. `on: schedule: - cron: '17 4 * * 1'` (Monday 04:17 UTC, off the hour) + `workflow_dispatch` with a `week` input for reruns. `concurrency: popularity`, `timeout-minutes: 30`, `permissions: contents: read` at top.
2. **Collect** (`python -I scripts/popularity/collect.py --catalog data/v1/games.json --out "$RUNNER_TEMP/raw/"`): one Tranco call per unique domain at <= 1 rps (approx. 1-3 minutes for 100 domains), Radar per-domain if the token is present, Wikipedia daily views for games with a `wikipedia` field, HN counts. Each source writes `raw/<source>.json` with HTTP status and timestamp. Upload `raw/` as a workflow artifact (90-day retention) for auditability.
3. **Compute** (`scripts/popularity/compute.py`): applies section 4.2, reads the previous `data/v1/popularity.json` for history, writes the new `popularity.json` and a `summary.json` (top movers, missing sources, anomalies such as a rank jump > 10x). Exit non-zero if Tranco failed for > 20 % of domains; the old file is then left untouched (fail closed).
4. **Narrate** (optional, `if: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN != '' }}` is not allowed in `if`; use a job output from a step that checks the secret): `anthropics/claude-code-action@<sha>` in automation mode with the prompt in Appendix A5. `claude_args: --max-turns 8 --allowedTools "Read,Write(docs/popularity/**)" --disallowedTools "Bash,WebSearch,WebFetch"`. Claude only reads `summary.json`/`popularity.json` and writes `docs/popularity/<week>.md`; it cannot change numbers. Alternative with fewer moving parts: a 30-line `scripts/popularity/narrate.py` using the `anthropic` Python SDK (`client.messages.create(model="claude-opus-5-5", ...)`) with `ANTHROPIC_API_KEY`; this is cheaper to run and easier to unit test, but loses the action's GitHub integration. Either way the step is `continue-on-error: true`: a failed narrative must not block the data PR.
5. **Validate**: `check-jsonschema --schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json`.
6. **PR**: `peter-evans/create-pull-request@<sha>` with `branch: data/popularity`, `title: "data(popularity): week <ISO week>"`, body containing the top-10 table from `summary.json`, labels `data, automated`. A PR instead of a push keeps `main` protected and lets a maintainer eyeball anomalies; enable auto-merge for this branch once the pipeline has been stable for a month (`gh pr merge --auto --squash`).

Cost estimate [inferred from the pricing table]: the narrative step consumes roughly 20-60k input tokens (summary plus system prompt plus a few turns) and 2-4k output tokens per run; at `claude-opus-5-5` prices that is about $0.15-0.35 per week, under $20/year; Sonnet 5.5 roughly halves it and Haiku 5.5 is under a cent. The OAuth token path (`CLAUDE_CODE_OAUTH_TOKEN`) bills against the owner's Claude subscription instead of API credits; the owner already uses it in MinimalUI. GitHub Actions minutes: ~5 minutes/week, free for public repos.

Failure handling checklist:
- Cron delay/drop: `valid_until` in the JSON is 10 days, not 7, so a late run does not make the app treat data as stale; the app shows "updated <date>".
- 60-day inactivity: Dependabot PRs and issue submissions count as activity; add a note in `docs/runbooks/popularity.md` on how to re-enable the workflow from the Actions tab.
- Source outage: per-source `ok: false` in `popularity.json.sources`; compute falls back to the previous week's score for that source with `carried_forward: true`.
- Rate limits: Tranco 1 rps with retry on 429 (sleep 2 s, max 3); Wikimedia 200/min for compliant bots; Radar 1,200/5 min.
- Secrets: `CLOUDFLARE_RADAR_TOKEN` (optional), `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` (optional), optional `DATA_BOT_TOKEN` fine-grained PAT if CI must run on the automated PRs.
- Prompt injection: the narrative model only sees numbers and game names from the catalog (maintainer-approved), never raw issue text or fetched HTML.

---

## 6. Icons / favicons

### 6.1 Facts [verified by curl]

- Google: `https://www.google.com/s2/favicons?domain=nytimes.com&sz=64` -> `301` to `https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://nytimes.com&size=64` -> `200 image/png`, `Cache-Control: public, max-age=604800`. Undocumented by Google; third parties describe it as unofficial with no uptime guarantee; returns the closest available size.
- DuckDuckGo: `https://icons.duckduckgo.com/ip3/nytimes.com.ico` -> `200 image/vnd.microsoft.icon`, `Cache-Control: max-age=2592000`, 1,648 bytes (small 16/32 px ICO). Undocumented.
- Direct: `<link rel="icon">` / `<link rel="apple-touch-icon">` in the page HTML or `/favicon.ico`. Many DLEs are static sites with a 180x180 apple-touch-icon or a `manifest.json` with 192/512 px icons, the best quality source [inferred].

### 6.2 Build time versus runtime [inferred]

| | Build time (repo + Pages) | Runtime (app fetches per game) |
|---|---|---|
| Privacy | App contacts only the Dailies host for icons | App contacts Google/DDG/every game host at list time, leaking the user's full catalog view to third parties before they click |
| Reliability | Deterministic, reviewable in the PR, survives source outages | Depends on unofficial services; Flatpak sandbox network access fine |
| Freshness | Refresh job monthly or on `status` change | Always fresh |
| Repo size | ~5-10 KB per 64 px PNG; 500 games = 5 MB; fine | none |
| Licensing | Icons sit in a public repo; need a takedown process | Same exposure, less visible |

Recommendation: **build time**. `scripts/icons/fetch_icon.py <url> --out data/v1/icons/<id>.png` tries: manifest icons >= 128 px, apple-touch-icon, `<link rel=icon>` largest, `/favicon.ico`, then Google `faviconV2` size=128, then DuckDuckGo; converts with Pillow to 64x64 (and 128x128 for HiDPI as `<id>@2x.png`), records `icon_source`. Run it in stage B of the submission flow and in a monthly `icons-refresh.yml`. The app loads `<base>/icons/<id>.png` via the same cache as the catalog, falls back to a bundled symbolic icon (e.g. a dice/calendar glyph coloured by category) when missing. Do **not** bundle third-party icons inside the Flatpak: the sandboxed app is distributed as a GPL work and Flathub reviewers may ask about trademark material in the payload; fetching from the project's Pages site at runtime keeps the binary clean [inferred; Flathub policy not checked here]. Add to `CONTRIBUTING.md`: icons are the property of their owners, used to identify the linked game; owners can request removal via an issue; the icon then becomes `icon_source: none`.

---

## 7. Weekly category rotation: `popularity.json`

### 7.1 Logic [inferred, proposed]

- Inputs: `games.json` (active games only), raw collector output, previous `popularity.json` (history of up to 8 weeks per game).
- `popular`: top `N = max(5, min(12, 10 % of active games))` by `popularity` score; stable sort by score desc then `id`; shared-domain correction applied.
- `trending`: games with `trend` not null and `trend > 0.02` and `tranco_rank <= 2,000,000`, sorted by `trend` desc, excluding the top 5 of `popular`; top `N` same size; if fewer than 3 qualify, fill with the newest `added` games (flagged `reason: "new"`) so the shelf is never empty.
- Rotation cadence: Monday 04:17 UTC. Each entry stores `week` (ISO 8601 `2026-W42`), `generated_at`, `valid_until` (+10 days), `method_version` (bump when the formula changes so apps can show "methodology changed" and the compute script can skip trend comparison across versions).
- The app shows: Favourites (always first), Popular (`popular[]` ordered), Trending (`trending[]`), then static categories; if `popularity.json` is older than `valid_until` show the lists anyway with an "as of <date>" subtitle.

### 7.2 `popularity.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://tim-van-oudheusden.github.io/Dailies/v1/schema/popularity.schema.json",
  "title": "Dailies weekly popularity",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "method_version", "week", "generated_at", "valid_until", "popular", "trending", "sources", "attribution"],
  "properties": {
    "schema_version": { "const": 1 },
    "method_version": { "type": "integer", "minimum": 1 },
    "week": { "type": "string", "pattern": "^\\d{4}-W\\d{2}$" },
    "generated_at": { "type": "string", "format": "date-time" },
    "valid_until": { "type": "string", "format": "date-time" },
    "stale": { "type": "boolean", "default": false },
    "popular": { "type": "array", "items": { "$ref": "#/$defs/ranked" }, "minItems": 1, "maxItems": 20 },
    "trending": { "type": "array", "items": { "$ref": "#/$defs/ranked" }, "maxItems": 20 },
    "scores": {
      "type": "object",
      "description": "Per-game detail for transparency and next week's trend computation.",
      "additionalProperties": { "$ref": "#/$defs/score" }
    },
    "sources": {
      "type": "object",
      "additionalProperties": {
        "type": "object", "additionalProperties": false,
        "required": ["ok", "fetched_at"],
        "properties": {
          "ok": { "type": "boolean" },
          "fetched_at": { "type": "string", "format": "date-time" },
          "domains_resolved": { "type": "integer" },
          "domains_requested": { "type": "integer" },
          "error": { "type": "string" }
        }
      }
    },
    "attribution": { "type": "array", "items": { "type": "string" } },
    "report": { "type": "string", "description": "Relative URL of the human-readable report, e.g. ../docs/popularity/2026-W42.md" }
  },
  "$defs": {
    "ranked": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "rank", "score"],
      "properties": {
        "id": { "type": "string" },
        "rank": { "type": "integer", "minimum": 1 },
        "score": { "type": "number", "minimum": 0, "maximum": 1 },
        "delta": { "type": ["number", "null"], "description": "Change vs trailing 4-week mean; trending only." },
        "reason": { "enum": ["score", "new", "carried_forward"] }
      }
    },
    "score": {
      "type": "object", "additionalProperties": false,
      "required": ["popularity"],
      "properties": {
        "popularity": { "type": "number" },
        "trend": { "type": ["number", "null"] },
        "tranco_rank": { "type": ["integer", "null"] },
        "radar_bucket": { "type": ["integer", "null"] },
        "wiki_views_7d": { "type": ["integer", "null"] },
        "hn_stories_28d": { "type": ["integer", "null"] },
        "shared_domain_weight": { "type": "number" },
        "history": { "type": "array", "items": { "type": "number" }, "maxItems": 8 }
      }
    }
  }
}
```

Example:

```json
{
  "schema_version": 1,
  "method_version": 1,
  "week": "2026-W42",
  "generated_at": "2026-10-12T04:21:09Z",
  "valid_until": "2026-10-22T04:21:09Z",
  "popular": [
    { "id": "wordle", "rank": 1, "score": 0.91 },
    { "id": "worldle", "rank": 2, "score": 0.44 }
  ],
  "trending": [
    { "id": "scrandle", "rank": 1, "score": 0.21, "delta": 0.06, "reason": "score" }
  ],
  "scores": {
    "wordle": { "popularity": 0.91, "trend": 0.00, "tranco_rank": 156, "wiki_views_7d": 96000, "shared_domain_weight": 0.33, "history": [0.91, 0.91, 0.90] }
  },
  "sources": {
    "tranco": { "ok": true, "fetched_at": "2026-10-12T04:18:00Z", "domains_requested": 84, "domains_resolved": 81 },
    "wikipedia": { "ok": true, "fetched_at": "2026-10-12T04:19:10Z" },
    "radar": { "ok": false, "fetched_at": "2026-10-12T04:19:12Z", "error": "no token" }
  },
  "attribution": [
    "Tranco (https://tranco-list.eu)",
    "Wikimedia Analytics API, CC0 1.0",
    "Cloudflare Radar, CC BY-NC 4.0"
  ],
  "report": "../docs/popularity/2026-W42.md"
}
```

---

## 8. Open questions for the owner

1. Shared domains (nytimes.com hosts Wordle, Connections, Spelling Bee, Strands): accept equal splitting, or maintain manual `domain_weights.json`?
2. Should Cloudflare Radar be in v1 (needs a Cloudflare account + token secret), or Tranco-only first?
3. Narrative step: `claude-code-action` with the existing `CLAUDE_CODE_OAUTH_TOKEN`, or a small SDK script with `ANTHROPIC_API_KEY`? Model choice (`claude-opus-5-5` default per the skill; Haiku 5.5 is far cheaper for a prose summary).
4. Auto-merge of data PRs: on from day one, or after a probation period?
5. Fine-grained PAT (`DATA_BOT_TOKEN`) so CI runs on automated PRs, versus accepting unchecked PRs opened with `GITHUB_TOKEN`.
6. Category taxonomy: the 11 proposed enum values are a guess; the UI agent may want fewer.
7. Should icons live in the repo at all, or only on the Pages branch (keeps git history small)? Could use a `gh-pages` orphan branch written by the workflow.
8. Tranco's license is not stated on its site; e-mail the maintainers or document "used under the terms of its upstream sources" [unverified].

---

## Appendix A - Files

### A1. Owner's existing templates (verbatim, from Tim-van-Oudheusden/MinimalUI, cloned 2026-10-15)

`.github/ISSUE_TEMPLATE/issue.yml`:

```yaml
name: Issue
description: Report a bug, request a feature, or file a task
body:
  - type: markdown
    attributes:
      value: |
        Thanks for contributing! Please keep the title in
        [Conventional Commits](https://www.conventionalcommits.org/) style,
        e.g. `fix(input): ...`, `feat(launcher): ...`, `chore: ...`, and
        apply the labels shown in brackets after filing.
  - type: dropdown
    id: type
    attributes:
      label: Type
      description: What kind of issue is this?
      multiple: false
      options:
        - Bug (type::bug)
        - Feature (type::feature)
        - Task (type::task)
        - Chore (type::chore)
        - Refactor
    validations:
      required: true
  - type: dropdown
    id: scope
    attributes:
      label: Scope
      description: Which part of the repository is affected?
      multiple: false
      options:
        - App (app)
        - Core logic (core)
        - Tooling / CI (ci)
        - Documentation (documentation)
        - Other (no label)
  - type: dropdown
    id: priority
    attributes:
      label: Priority
      multiple: false
      options:
        - Critical (priority::critical)
        - High (priority::high)
        - Medium (priority::medium)
        - Low (priority::low)
      default: 2
  - type: input
    id: device
    attributes:
      label: Device and Android version
      description: For bugs, the phone and Android version you saw it on.
      placeholder: e.g. Unihertz Titan 2, Android 11
  - type: textarea
    id: description
    attributes:
      label: Description
      description: What is the problem, or what should be done?
      placeholder: |
        - What's wrong or what's needed
        - Why it matters
        - Steps to reproduce, if a bug
    validations:
      required: true
  - type: textarea
    id: acceptance
    attributes:
      label: Acceptance criteria
      description: How do we know this issue is done?
      placeholder: |
        - [ ] Behaviour or deliverable that proves completion
        - [ ] Verification steps, if applicable
  - type: checkboxes
    id: checks
    attributes:
      label: Checks
      options:
        - label: Followed the workflow in AGENTS.md (issues via GitHub API, beads sync, Conventional Commits)
          required: false
```

(For Dailies replace the `device` input with e.g. "Flatpak version and desktop".)

`.github/workflows/claude.yml` (MinimalUI; the `website` copy differs only in the toolchain setup and allowed tools):

```yaml
name: Claude Code

# Hands an issue to Claude Code when a maintainer labels it `ai-fix-requested`,
# or when a trusted collaborator mentions @claude on an issue or PR. Claude
# works on a `claude/*` branch and opens a PR; it never pushes to main.
# Needs the CLAUDE_CODE_OAUTH_TOKEN repo secret and the Claude GitHub App.

on:
  issues:
    types: [labeled]
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  pull_request_review:
    types: [submitted]

# Jobs that need more ask for it themselves.
permissions:
  contents: read

concurrency:
  group: >-
    claude-${{ github.event.issue.number || github.event.pull_request.number }}-${{
    (github.event.label.name == 'ai-fix-requested'
    || (contains(format('{0}{1}', github.event.comment.body, github.event.review.body), '@claude')
    && contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.comment.author_association || github.event.review.author_association)))
    && 'queue' || github.run_id }}
  cancel-in-progress: false

jobs:
  claude:
    name: Claude Code
    if: >-
      (github.event_name == 'issues'
        && github.event.label.name == 'ai-fix-requested')
      || (github.event_name == 'issue_comment'
        && contains(github.event.comment.body, '@claude')
        && contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.comment.author_association))
      || (github.event_name == 'pull_request_review_comment'
        && contains(github.event.comment.body, '@claude')
        && contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.comment.author_association))
      || (github.event_name == 'pull_request_review'
        && contains(github.event.review.body, '@claude')
        && contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.review.author_association))
    runs-on: ubuntu-latest
    timeout-minutes: 60
    permissions:
      contents: write
      pull-requests: write
      issues: write
      id-token: write
      actions: read
    steps:
      - name: Refuse fork pull requests
        if: github.event.issue.pull_request || github.event.pull_request
        env:
          GH_TOKEN: ${{ github.token }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.issue.number || github.event.pull_request.number }}
        run: |
          set -euo pipefail
          head_repo="$(gh api "repos/$REPO/pulls/$PR_NUMBER" --jq '.head.repo.full_name // ""')"
          if [ "$head_repo" != "$REPO" ]; then
            echo "::error::Fork pull requests are not supported by the Claude workflow; review them locally."
            exit 1
          fi
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 1
      # (toolchain setup steps omitted; MinimalUI sets up JDK + Gradle, website sets up Bun)
      - name: Run Claude Code
        # Third-party action pinned to a commit SHA (v1.0.248).
        uses: anthropics/claude-code-action@1d6de8cb0c237e7c15e9e1bdf973826ebae490cc
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          label_trigger: ai-fix-requested
          trigger_phrase: '@claude'
          branch_prefix: claude/
          additional_permissions: |
            actions: read
          claude_args: >-
            --allowedTools "Bash(./gradlew test:*),Bash(./gradlew lint:*),Bash(./gradlew assembleDebug:*),Bash(./gradlew check:*),Bash(./gradlew spotlessApply:*),Bash(./gradlew :core:test:*),Bash(./gradlew :app:testDebugUnitTest:*)"
```

Owner's scheduled-workflow style (website `nightly-compliance.yml`): `cron: '23 3 * * *'` (off the hour), `workflow_dispatch`, top-level `permissions: contents: read`, `timeout-minutes`, SHA-pinned actions with `# vX.Y.Z` comments, results to `$GITHUB_STEP_SUMMARY` and an uploaded artifact. The Dailies workflows below follow that style. The owner's `.github/rulesets/main.json` requires a PR with specific status checks and allows only the `merge` method; the data PRs must pass the same checks, so name the schema check job accordingly or add it to the ruleset.

### A2. `.github/workflows/game-submission-check.yml` (skeleton)

```yaml
name: Game submission check

# Validates a "game-submission" issue form: URL reachable, not a duplicate,
# entry conforms to data/v1/schema/catalog.schema.json. Posts one comment
# (updated on edits) and toggles the validated / needs-changes labels.
# Runs with a read-only contents token; nothing from the issue is executed.

on:
  issues:
    types: [opened, edited]

permissions:
  contents: read

concurrency:
  group: submission-${{ github.event.issue.number }}
  cancel-in-progress: true

jobs:
  check:
    name: Validate submission
    if: contains(github.event.issue.labels.*.name, 'game-submission')
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
      issues: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: '3.13'
      - name: Install validator deps
        run: python -m pip install --require-hashes -r scripts/requirements.txt   # check-jsonschema, requests, tldextract, Pillow
      - name: Parse issue form
        id: parse
        uses: stefanbuck/github-issue-parser@cb6e97157cbf851e3a393ff8d57c93a484cc323f # v3.2.5
        with:
          template-path: .github/ISSUE_TEMPLATE/new-game.yml
      - name: Validate
        id: validate
        env:
          PARSED_JSON: ${{ steps.parse.outputs.jsonString }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
        run: |
          set -euo pipefail
          printf '%s' "$PARSED_JSON" > "$RUNNER_TEMP/parsed.json"
          python -I scripts/validate_submission.py \
            --parsed "$RUNNER_TEMP/parsed.json" \
            --catalog data/v1/games.json \
            --schema data/v1/schema/catalog.schema.json \
            --issue "$ISSUE_NUMBER" \
            --report "$RUNNER_TEMP/report.md" \
            --result "$RUNNER_TEMP/result.json" || true
          echo "ok=$(python -I -c 'import json,sys;print(str(json.load(open(sys.argv[1]))["ok"]).lower())' "$RUNNER_TEMP/result.json")" >> "$GITHUB_OUTPUT"
      - name: Find previous comment
        id: fc
        uses: peter-evans/find-comment@v4   # pin by SHA before use
        with:
          issue-number: ${{ github.event.issue.number }}
          comment-author: github-actions[bot]
          body-includes: '<!-- dailies-submission-check -->'
      - name: Comment result
        uses: peter-evans/create-or-update-comment@e8674b075228eee787fea43ef493e45ece1004c9 # v5.0.0
        with:
          comment-id: ${{ steps.fc.outputs.comment-id }}
          issue-number: ${{ github.event.issue.number }}
          body-path: ${{ runner.temp }}/report.md
          edit-mode: replace
      - name: Set labels
        env:
          GH_TOKEN: ${{ github.token }}
          GH_REPO: ${{ github.repository }}
          N: ${{ github.event.issue.number }}
          OK: ${{ steps.validate.outputs.ok }}
        run: |
          if [ "$OK" = true ]; then
            gh issue edit "$N" --add-label validated --remove-label needs-changes
          else
            gh issue edit "$N" --add-label needs-changes --remove-label validated
          fi
```

(`peter-evans/find-comment` exists in the same family of actions; its current version and SHA were not looked up in this session [unverified], so resolve before pinning.)

### A3. `.github/workflows/game-submission-approve.yml` (skeleton)

```yaml
name: Game submission approve

# When a maintainer adds the `approved` label to a validated submission,
# re-validates it, fetches the icon, appends the entry to data/v1/games.json
# and opens a pull request that closes the issue. Never pushes to main.

on:
  issues:
    types: [labeled]

permissions:
  contents: read

jobs:
  add:
    name: Open catalog PR
    if: >-
      github.event.label.name == 'approved'
      && contains(github.event.issue.labels.*.name, 'game-submission')
      && contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), github.event.sender.author_association)
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: write
      pull-requests: write
      issues: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: '3.13'
      - run: python -m pip install --require-hashes -r scripts/requirements.txt
      - uses: stefanbuck/github-issue-parser@cb6e97157cbf851e3a393ff8d57c93a484cc323f # v3.2.5
        id: parse
        with:
          template-path: .github/ISSUE_TEMPLATE/new-game.yml
      - name: Add entry and icon
        id: add
        env:
          PARSED_JSON: ${{ steps.parse.outputs.jsonString }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
        run: |
          set -euo pipefail
          printf '%s' "$PARSED_JSON" > "$RUNNER_TEMP/parsed.json"
          python -I scripts/add_game.py --parsed "$RUNNER_TEMP/parsed.json" --issue "$ISSUE_NUMBER" \
            --catalog data/v1/games.json --icons data/v1/icons --out-meta "$RUNNER_TEMP/meta.json"
          echo "slug=$(python -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["id"])' "$RUNNER_TEMP/meta.json")" >> "$GITHUB_OUTPUT"
          echo "name=$(python -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["name"])' "$RUNNER_TEMP/meta.json")" >> "$GITHUB_OUTPUT"
      - name: Validate catalog
        run: check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json
      - name: Create pull request
        id: cpr
        uses: peter-evans/create-pull-request@5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1
        with:
          # token: ${{ secrets.DATA_BOT_TOKEN }}   # fine-grained PAT if CI must run on this PR
          branch: data/add-${{ steps.add.outputs.slug }}
          delete-branch: true
          add-paths: data/**
          commit-message: "data(games): add ${{ steps.add.outputs.name }}"
          title: "data(games): add ${{ steps.add.outputs.name }}"
          body: |
            Adds **${{ steps.add.outputs.name }}** (`${{ steps.add.outputs.slug }}`) from #${{ github.event.issue.number }}.

            Closes #${{ github.event.issue.number }}
          labels: |
            data
            automated
      - name: Link PR on the issue
        if: steps.cpr.outputs.pull-request-url
        env:
          GH_TOKEN: ${{ github.token }}
          N: ${{ github.event.issue.number }}
          URL: ${{ steps.cpr.outputs.pull-request-url }}
        run: gh issue comment "$N" --body "Opened $URL. It will be merged after review."
```

### A4. `.github/workflows/popularity.yml` (skeleton)

```yaml
name: Weekly popularity

# Every Monday: collect public popularity signals for every active game
# (Tranco; optionally Cloudflare Radar and Wikipedia pageviews), compute the
# popular/trending shelves deterministically, let Claude write the weekly
# report, validate against the schema and open a PR. Fails closed: if the
# collectors fail, data/v1/popularity.json is left untouched.
# Scheduled workflows in public repos are disabled after 60 days without
# activity; re-enable from the Actions tab (docs/runbooks/popularity.md).

on:
  schedule:
    - cron: '17 4 * * 1'
  workflow_dispatch:
    inputs:
      narrate:
        description: Write the Claude report
        type: boolean
        default: true

permissions:
  contents: read

concurrency:
  group: popularity
  cancel-in-progress: false

jobs:
  compute:
    name: Collect and compute
    runs-on: ubuntu-latest
    timeout-minutes: 20
    outputs:
      week: ${{ steps.compute.outputs.week }}
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: '3.13'
      - run: python -m pip install --require-hashes -r scripts/requirements.txt
      - name: Collect signals
        env:
          CLOUDFLARE_RADAR_TOKEN: ${{ secrets.CLOUDFLARE_RADAR_TOKEN }}
          DAILIES_USER_AGENT: "DailiesPopularityBot/1.0 (+https://github.com/Tim-van-Oudheusden/Dailies; data@example.invalid)"
        run: python -I scripts/popularity/collect.py --catalog data/v1/games.json --out "$RUNNER_TEMP/raw"
      - name: Compute shelves
        id: compute
        run: |
          python -I scripts/popularity/compute.py --catalog data/v1/games.json --raw "$RUNNER_TEMP/raw" \
            --previous data/v1/popularity.json --out data/v1/popularity.json --summary "$RUNNER_TEMP/summary.json"
          echo "week=$(python -I -c 'import json;print(json.load(open("data/v1/popularity.json"))["week"])')" >> "$GITHUB_OUTPUT"
      - name: Validate
        run: check-jsonschema --schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json
      - name: Upload raw signals
        if: always()
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: popularity-raw-${{ steps.compute.outputs.week }}
          path: |
            ${{ runner.temp }}/raw
            ${{ runner.temp }}/summary.json
          retention-days: 90
      - name: Stash results for the next job
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: popularity-result
          path: |
            data/v1/popularity.json
            ${{ runner.temp }}/summary.json

  publish:
    name: Narrate and open PR
    needs: compute
    runs-on: ubuntu-latest
    timeout-minutes: 20
    permissions:
      contents: write
      pull-requests: write
      id-token: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: actions/download-artifact@v6   # pin by SHA before use
        with:
          name: popularity-result
          path: ${{ runner.temp }}/result
      - run: |
          cp "$RUNNER_TEMP/result/data/v1/popularity.json" data/v1/popularity.json
          mkdir -p docs/popularity
          cp "$RUNNER_TEMP/result/summary.json" "docs/popularity/${{ needs.compute.outputs.week }}.summary.json"
      - name: Write weekly report with Claude
        if: ${{ inputs.narrate != false }}
        continue-on-error: true
        uses: anthropics/claude-code-action@a26b07d8c778b0c43f64618e5fd29fd0f8af72e8 # v1.0.250
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          prompt: |
            You are writing the weekly popularity report for Dailies, a launcher for daily guessing games.
            Read docs/popularity/${{ needs.compute.outputs.week }}.summary.json and data/v1/popularity.json.
            Write docs/popularity/${{ needs.compute.outputs.week }}.md with: a two-sentence overview,
            the Popular and Trending tables (id, name, score, delta), notable movers, and a "Data quality"
            section listing sources that failed or domains without a rank. Do not change any numbers,
            do not edit any JSON file, do not speculate about causes you cannot see in the data.
            Plain Markdown, no emoji, under 400 words.
          claude_args: >-
            --max-turns 6
            --allowedTools "Read,Write"
            --disallowedTools "Bash,Edit,WebSearch,WebFetch"
      - name: Guard that Claude only touched the report
        run: |
          set -euo pipefail
          changed=$(git status --porcelain | awk '{print $2}')
          for f in $changed; do
            case "$f" in data/v1/popularity.json|docs/popularity/*) ;; *) echo "::error::Unexpected change: $f"; exit 1;; esac
          done
          rm -f "docs/popularity/${{ needs.compute.outputs.week }}.summary.json"
      - name: Create pull request
        uses: peter-evans/create-pull-request@5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1
        with:
          branch: data/popularity
          delete-branch: true
          add-paths: |
            data/v1/popularity.json
            docs/popularity/*.md
          commit-message: "data(popularity): week ${{ needs.compute.outputs.week }}"
          title: "data(popularity): week ${{ needs.compute.outputs.week }}"
          body: |
            Weekly popular/trending shelves. Report: docs/popularity/${{ needs.compute.outputs.week }}.md
            Raw signals are attached to the workflow run as an artifact.
          labels: |
            data
            automated
```

Versions to resolve before use: `actions/download-artifact` and `peter-evans/find-comment` SHAs (not looked up). `actions/upload-artifact@cf430e03... # v7.0.2` is copied from the owner's website repo.

### A5. Alternative narrative step without claude-code-action (Python SDK outline)

```python
# scripts/popularity/narrate.py  (requires ANTHROPIC_API_KEY)
import json, sys, anthropic
summary = json.load(open(sys.argv[1])); week = sys.argv[2]
client = anthropic.Anthropic()
with client.messages.stream(
    model="claude-opus-5-5",            # owner may choose claude-sonnet-5-5 / claude-haiku-5-5 for cost
    max_tokens=4000,
    system="You write a short, factual weekly popularity report for the Dailies launcher. Never alter numbers.",
    messages=[{"role": "user", "content": f"Week {week}. Data:\n{json.dumps(summary)}\nWrite the Markdown report."}],
) as stream:
    msg = stream.get_final_message()
open(f"docs/popularity/{week}.md", "w").write("".join(b.text for b in msg.content if b.type == "text"))
```

(Model ids and pricing from the bundled `claude-api` skill, cached 2026-10-06; verify against https://docs.anthropic.com pricing before committing. Prompt caching is irrelevant at one call per week.)

### A6. `scripts/validate_submission.py` responsibilities (outline)

1. Load parsed JSON; map form ids -> entry (`name`, `url`, `category` label -> enum slug, `difficulty` lower-case, `description`, `tags` split on commas and slugified, `language` default `en`, `icon_url` optional).
2. URL: `urllib.parse` -> scheme must be `https`, host must resolve to a public IP (reject private ranges), fetch with `requests.head` then `get` (timeout 10 s, `allow_redirects=True`, `max_redirects=5`, descriptive UA); record final URL and status.
3. Duplicates: normalise and compare host+path against `games.json`; compare slug against `id` and `aliases`; fuzzy name match (`difflib.SequenceMatcher` >= 0.9) as a warning.
4. Build candidate entry (`id`, `added`, `status: active`, `domain` via `tldextract`, `source_issue`); validate with `jsonschema` against the catalog schema.
5. Write `report.md` with a `<!-- dailies-submission-check -->` marker, a pass/fail table and the candidate JSON in a code block; write `result.json` with `ok` and `entry`.

---

## Sources

Primary documentation and repositories read on 2026-10-15:

- GitHub issue forms syntax: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms
- GitHub form schema: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema
- stefanbuck/github-issue-parser (README, action.yml, index.js, fixtures): https://github.com/stefanbuck/github-issue-parser
- issue-ops/parser README: https://github.com/issue-ops/parser
- peter-evans/create-pull-request README (v8): https://github.com/peter-evans/create-pull-request
- anthropics/claude-code-action: README, action.yml, docs/usage.md, docs/configuration.md, docs/security.md, docs/solutions.md: https://github.com/anthropics/claude-code-action
- GitHub events that trigger workflows (schedule, issues, workflow_dispatch): https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows
- GitHub REST rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- GitHub REST best practices (conditional requests): https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- GitHub Pages limits: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- Auto-merge: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request and https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-auto-merge-for-pull-requests-in-your-repository
- gh pr merge manual: https://cli.github.com/manual/gh_pr_merge
- jsDelivr README (GitHub CDN, caching, restrictions): https://github.com/jsdelivr/jsdelivr
- raw.githubusercontent caching reports: https://github.com/orgs/community/discussions/46691 , https://issues.fluidproject.org/browse/FLUID-6626/
- Wikimedia Analytics API access policy (CC0): https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/access-policy.html ; getting started: https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/getting-started.html ; rate limits: https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits ; User-Agent policy: https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy ; live endpoint: https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/...
- Cloudflare Radar: domain ranking datasets https://developers.cloudflare.com/radar/investigate/domain-ranking-datasets/ ; first request / token https://developers.cloudflare.com/radar/get-started/first-request/ ; ranking API reference https://developers.cloudflare.com/api/resources/radar/subresources/ranking/ and .../methods/top/ ; API limits https://developers.cloudflare.com/fundamentals/api/reference/limits/ ; methodology blog https://blog.cloudflare.com/radar-domain-rankings/ ; license (about pages) https://radar.cloudflare.com/about
- Tranco: https://tranco-list.eu/ and https://tranco-list.eu/api_documentation ; live endpoint https://tranco-list.eu/api/ranks/domain/{domain}
- HN Algolia API: https://hn.algolia.com/api (via search summary) ; live endpoint https://hn.algolia.com/api/v1/search_by_date
- Reddit API rules (archived wiki): https://github.com/reddit-archive/reddit/wiki/API ; 2023 rate-limit announcement via r/redditdev mirrors
- Google Trends API alpha announcement: https://developers.google.com/search/blog/2025/07/trends-api
- pytrends status (secondary): https://dev.to/esteban_ortega/pytrends-is-dead-heres-how-to-get-google-trends-data-in-2026-1a18 , https://apiserpent.com/blog/pytrends-dead-google-trends-data-2026
- Favicon services (secondary): https://blog.jim-nielsen.com/2021/displaying-favicons-for-any-domain/ , https://docs.logo.dev/duckduckgo-favicon-api ; live probes of https://www.google.com/s2/favicons and https://icons.duckduckgo.com/ip3/
- check-jsonschema: https://github.com/python-jsonschema/check-jsonschema
- Wordles of the World (CC0 list): https://rwmpelstilzchen.gitlab.io/wordles/ ; wordleweb list: https://github.com/rarelygoeshere/wordleweb
- Owner's scaffolding (cloned): https://github.com/Tim-van-Oudheusden/MinimalUI , https://github.com/Tim-van-Oudheusden/website , https://github.com/Tim-van-Oudheusden/Dailies
- Claude model ids/pricing: bundled `claude-api` skill table (cached 2026-10-06).
