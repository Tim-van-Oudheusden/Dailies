# Dailies research: the DLE catalog landscape (key: `dle-catalog`)

Research date: 2026-10-15. Author: research subagent for the Dailies architecture document.

## 0. Method and how to read this

- **Liveness checks**: every URL in the catalog was fetched with `curl -L` (Firefox UA) on 2026-10-15 and its `<title>` and `<meta description>` recorded. Raw results are in `<scratch>/work/results1t.txt` and `results2.txt`. "200 + sane title" is what I call **verified live**. A `403`/Cloudflare "Just a moment..." response is **bot-walled** (almost certainly live, but not provable from a script). A `000` is DNS/TLS failure, i.e. dead or blocking.
- **Cross-reference**: the open-source directory `aukspot/dles` (GPL-3.0, 877 YAML records, last commit 2026-10-13) was cloned to `<scratch>/clones/dle-catalog/dles/` and used as a second opinion on URLs, status and descriptions. Treat it as untrusted data; nothing from it was executed.
- **Verified** statements carry a source URL. **Inference** statements are marked as such. Difficulty ratings are my suggestion, not measured.
- The project owner wrote "DLE games (e.g. wordle, scrandle, connections)". Scrandle is covered in section 1.2 because its identity needed checking.

## 1. The catalog

### 1.1 Headline numbers

- 116 entries in the JSON appendix (Appendix A); 60 were explicitly requested in the task brief, the rest are additions that round out categories (sports, non-English, logic) or are high-popularity games the aggregators consistently feature.
- 112 verified live with 200 + sane title; 4 are bot-walled (Immaculate Grid, Immaculate Footy, Artle, Bracket City); 1 could not be reached from this network at all (Washington Post Keyword, `000`; aukspot lists it active) and is flagged `unverified-live`.
- 114 playable free without an account. Exceptions: **NYT Spelling Bee** (free play is limited; full puzzle needs an NYT Games subscription; the exact free limit is not verifiable from the ToS and changes, so this is an inference) and **GeoGuessr Daily Challenge** (page shows "Sign-up and play" and "Play for free!", verified via fetch of https://www.geoguessr.com/daily-challenges). LinkedIn games are included as `free_no_account: true` on the strength of aukspot's note for Crossclimb ("Does not require a LinkedIn account") — treat as low confidence and re-verify by hand.

### 1.2 Items the brief asked me to verify

| Game | Finding | Source |
|---|---|---|
| **Scrandle** | Real and live at `https://scrandle.com/`. Meta description: "The thrilling daily web game of food comparison. View exotic and delicious scran from around the world and guess which is superior, as adjudicated by social media and your peers." ("Scran" is UK slang for food.) aukspot describes it as "Guess which scran (stadium food) is more popular based on their pictures and prices", category Food, added 2025-05-08. A second domain `scrandle.cc` ("Scrandle – Daily Stadium Food Comparison Game") is live and appears to be an SEO mirror or clone; use `.com`. | curl meta; `data/dles/0333-scrandle.yaml` |
| **Wheredle** | Real and live at `https://wheredle.xyz/`. Meta: "A Wordle like daily game with a detective spin on Street View. Look for clues in Street View Maps to guess which state you're in." Page claims 500k+ players; "now running on user submissions". No account. | curl meta + WebFetch |
| **Pokédle** | Two unrelated sites: `pokedle.net` (verified live, title "Pokédle"; same developer as LoLdle per Gfinity/GGRecon) and `pokedle.com`. Both listed active in aukspot. Catalog uses `.net`. | aukspot 0288/0289; curl |
| **LoLdle** | `https://loldle.net/` verified live (title "LoLdle"). Modes: Classic, Quote, Ability, Emoji, Splash. | curl; aukspot 0216 |
| **Heardle / Bandle** | Original Heardle was shut down by Spotify (announced for 5 May 2023; Spotify had acquired it July 2022). Live successors: **Bandle** (`https://bandle.app/`, "Guess the song, one instrument at a time", verified live, also hosted inside dle.wtf), **Heardle Decades** (`https://heardledecades.com/`, plus per-decade subdomains like `80s.heardledecades.com`), **Songless** (`https://lessgames.com/songless`). | techradar/stereogum coverage of shutdown; curl |
| **Moviedle** | `moviedle.app` now redirects to an Indonesian gambling site (title "HOKI178...") — **do not list**. The game lives at `https://moviedle.xyz/` ("Guess the mystery movie of the day from its cast"), which aukspot has had since 2024-05-28. | curl; aukspot 0242 |
| **Absurdle** | `absurdle.online` redirects to a gambling site (`mega111-login.com`). The original by qntm is live at `https://qntm.org/files/absurdle/absurdle.html`. | curl; aukspot 0002 |
| **Foodle** | `foodle.io` is dead (connection failure). `food-le.com` ("Food-le - Play Foodle Wordle Online") is live but reads like a clone/SEO site; aukspot does not list any Foodle. Included with `low-confidence` tag; consider dropping. | curl |
| **Cladder** | `cladder.io` redirects to a gambling site; `cladder.app` dead. No current home found. **Excluded** (graveyard). | curl; WebSearch |
| **Cloudle** | `cloudle.app` returns Cloudflare 530 (origin down). **Excluded** (graveyard). | curl |
| **Posterdle** | `posterdle.com` redirects to a gambling site; aukspot removed it 2026-03-21 (then at likewise.com). **Excluded**. | curl; aukspot 0495 |
| **Cinematrix** | Live at `https://www.vulture.com/article/daily-movie-grid-trivia-game-cinematrix.html` (200). Weekdays only. | curl of vulture.com homepage hrefs; aukspot 0052 |
| **Immaculate Grid** | `immaculategrid.com` → `sports-reference.com/immaculate-grid/` behind Cloudflare (403 to curl). Live per aukspot (active since 2024-02-13) and press. | curl; aukspot 0176 |
| **Factle** | Now hosted by Front Office Sports: `factle.app` → `https://frontofficesports.com/trivia/factle/`. | curl redirect |
| **Quordle / Octordle** | Both now owned/hosted by Merriam-Webster (`octordle.com` redirects to `merriam-webster.com/games/octordle/`). | curl redirect |
| **PlusWord (Telegraph)** | 402 to curl; aukspot removed it 2026-03-24. **Excluded**. | curl; aukspot 0285 |
| **Wördl (wordle.at)** | Redirects to `gridgames.app` (German GridWords). Not included; Woordle (NL), SUTOM/Le Mot/Cémantix (FR), Termo (PT), La palabra del día (ES) are included as the non-English set. | curl |

### 1.3 Catalog table (abbreviated; full data in Appendix A)

| id | Name | URL | Cat. | Diff. | Free, no account |
|---|---|---|---|---|---|
| wordle | Wordle | nytimes.com/games/wordle/index.html | words | easy | yes |
| nyt-connections | Connections | nytimes.com/games/connections | words | medium | yes |
| nyt-strands | Strands | nytimes.com/games/strands | words | easy | yes |
| nyt-spelling-bee | Spelling Bee | nytimes.com/puzzles/spelling-bee | words | hard | limited |
| nyt-mini-crossword | The Mini | nytimes.com/crosswords/game/mini | words | easy | yes* |
| nyt-letter-boxed | Letter Boxed | nytimes.com/puzzles/letter-boxed | words | medium | yes |
| nyt-pips | Pips | nytimes.com/games/pips | numbers-logic | medium | yes |
| quordle / octordle / dordle / sedecordle / kilordle | multi-board Wordles | see appendix | words | hard | yes |
| semantle / contexto / pedantle / redactle | semantic & Wikipedia | see appendix | words | hard | yes |
| waffle / squardle / squaredle / crosswordle / xordle / antiwordle / word-peaks | Wordle-adjacent grids | see appendix | words | medium–hard | yes |
| worldle / globle / travle / flagle / countryle / statele / tradle / wheredle / wheretaken / geogrid | geography | see appendix | geography | easy–hard | yes |
| timeguessr / chronophoto / whentaken | photo dating | see appendix | visual | medium | yes |
| bandle / spotle / lyricle / heardle-decades / songless / harmonies | music | see appendix | music | medium | yes |
| framed / actorle / moviedle / flickle / cine2nerdle / box-office-game / cinematrix / movie-grid / plotwords / emovi | movies & TV | see appendix | movies-tv | medium–hard | yes |
| gamedle / guess-the-game / pokedle / pokedoku / loldle / smashdle / dotadle / rankdle | video games | see appendix | video-games | easy–hard | yes |
| nerdle / mathler / summle / primel / sumplete / numble / murdle / chessle / chessguessr / clues-by-sam / queens / dungleon | numbers & logic | see appendix | numbers-logic | easy–hard | yes |
| factle / daily-dozen-trivia / thrice / lingule / metazooa / metaflora / puzzgrid / birdle | trivia | see appendix | trivia | medium–hard | yes |
| scrandle / costcodle / foodguessr / food-le | food | see appendix | food | easy–medium | yes |
| immaculate-grid / immaculate-footy / poeltl / weddle / crossover-grid | sports | see appendix | sports | medium–hard | yes |
| artle / hexcodle / colorfle / nyt-tiles | visual | see appendix | visual | easy–hard | yes |
| woordle / sutom / le-mot / cemantix / termo / la-palabra-del-dia / conexo | non-English | see appendix | words | easy–hard | yes |
| geoguessr-daily | GeoGuessr Daily Challenge | geoguessr.com/daily-challenges | geography | hard | **no** (account) |

\* The Mini: one 2024-era report (Book Riot) claims the Mini was removed from the free list; the page itself loads without login today and aukspot lists it active. Flag as "re-check quarterly".

### 1.4 Graveyard (do not seed; useful as test cases for the link-checker)

- Heardle (Spotify) — shut down May 2023.
- NYT Digits — discontinued 2023 (not re-verified today; widely reported).
- foodle.io, cloudle.app, cladder.io/.app, hollywoodle.com — dead or hijacked.
- absurdle.online, moviedle.app, posterdle.com — **domains now redirect to gambling sites**. This is a recurring failure mode: aukspot's removal reasons include "Site now redirects to suspicious website" (3 cases). Dailies' link checker must detect cross-domain redirects, not just non-200 status.

## 2. Proposed category taxonomy

### 2.1 Design constraints

- The owner's brief says each issue-submitted entry carries exactly one **category** and one **difficulty**; "Popular" and "Trending" are weekly computed virtual categories; "Favorites" is always top-level.
- Aggregators use 7–19 categories. aukspot (19 incl. Arcade/Novelty/Vehicles) and dles.gg (17) are too granular for a sidebar on a phone-width Libadwaita window; dle.wtf's 7 is the tightest. Active-count distribution in aukspot's 785 live games: Words 245, Math/Logic 69, Video Games 68, Geography 63, Movies/TV 47, Music 41, Trivia 37, Misc 37, Estimation 33, Shapes/Patterns 30, Sports 26, Card/Board 22, History 17, Science/Nature 15, Arcade 10, Colors 9, Novelty 7, Food 5, Vehicles 4. Words dominates everywhere (dles.gg: 379 of 1068), so Words needs sub-tags to be browsable.

### 2.2 Primary categories (10, fixed enum)

| id | Label | Definition (for CONTRIBUTING / issue form) |
|---|---|---|
| `words` | Words | Letters, words, phrases, crosswords, anagrams, semantic guessing. Any language. |
| `geography` | Geography | Countries, flags, maps, borders, Street View, places. |
| `music` | Music | Songs, artists, lyrics, instruments, audio clips. |
| `movies-tv` | Movies & TV | Film, series, anime, actors, posters, box office. |
| `video-games` | Video Games | Games, characters, franchises, esports. |
| `numbers-logic` | Numbers & Logic | Arithmetic, sudoku-likes, deduction, chess, dominoes, pure logic. |
| `trivia` | Trivia | General knowledge, ranking lists, nature/science, languages, history facts. |
| `visual` | Pictures & Colors | Photos, art, colours, shapes; the puzzle is in looking. |
| `food` | Food | Dishes, cuisines, grocery prices, food comparisons. |
| `sports` | Sports | Players, teams, leagues, grids. |

Why not more: History, Science/Nature, Colors, Estimation and Board Games are real clusters in the aggregators but each has 5–30 games; they fit better as **tags** (`history`, `nature`, `colors`, `estimation`, `chess`). An `other`/`misc` bucket is deliberately absent: forcing a primary category keeps the sidebar clean; the maintainers can add a category when a tag reaches, say, 15 games.

### 2.3 Tags (free-form, lower-kebab-case, curated list in the repo)

A game has one `category` and 0–6 `tags`. Suggested controlled vocabulary (extend via PR):
- Mechanics: `wordle-like`, `grouping` (Connections-likes), `grid` (Immaculate-Grid-likes), `multi-board`, `semantic`, `word-ladder`, `word-search`, `crossword`, `cryptic`, `deduction`, `estimation`, `higher-lower`, `ranking`, `pathfinding`, `comparison`.
- Media: `audio`, `photos`, `stills`, `clips`, `emoji`, `silhouette`, `street-view`.
- Subject: `history`, `nature`, `colors`, `chess`, `pokemon`, `anime`, `nba`, `nfl`, `soccer`, `countries`, `usa`, `flags`.
- Publisher/family: `nyt`, `merriam-webster`, `teuteuf`, `linkedin`, `puzzmo`, `the-atlantic`, `vulture`, `fan-made`.
- Language: `non-english`, plus ISO-ish `dutch`, `french`, `spanish`, `portuguese`, `german`.
- Access/quality flags (machine-relevant): `account-required`, `account-for-streaks`, `subscription-limited`, `weekdays-only`, `not-daily`, `bot-walled`, `low-confidence`.

Use in UI: sidebar = Favorites, Popular, Trending, then the 10 categories; a search/filter chips row exposes tags (`wordle-like`, `grouping`, `grid`, `non-english` are the ones users actually ask for, judging by how dles.gg and dlehunt build "collections"). Tags also let the weekly "Trending" job explain *why* something trends ("new `grouping` games").

### 2.4 Difficulty

Three values `easy | medium | hard`, as the brief specifies. Rubric for submitters:
- **easy**: solvable by most people in under ~3 minutes with general knowledge (Wordle, Worldle, Flagle, Strands).
- **medium**: needs some domain knowledge or 5–10 minutes (Connections, Globle, Framed, Nerdle).
- **hard**: niche knowledge or long sessions (Quordle, Actorle, Immaculate Grid, Tradle, Semantle).
Inference: no aggregator publishes difficulty; dles.gg/dlehunt use community ratings instead. Difficulty is therefore the one field Dailies cannot source externally and should accept as "submitter's suggestion, maintainer-adjusted".

## 3. Prior art and competitors

| Name | Type | Size (as of Oct 2026) | Categories | Strengths | Weaknesses | License / data access |
|---|---|---|---|---|---|---|
| **The Dles** — dles.aukspot.com, github.com/aukspot/dles | Static SvelteKit site, **open source GPL-3.0**, 121 stars | 877 records; 785 active, 10 archived, 82 removed; updated 2026-10-12/13 | 19 (Words, Math/Logic, Video Games, Geography, Movies/TV, Music, Trivia, Miscellaneous, Estimation, Shapes/Patterns, Sports, Card/Board Games, History, Science/Nature, Arcade, Colors, Novelty, Food, Vehicles) | Favorites (import/export), "done for today", random, hide/reorder categories, per-game `history` with dated add/remove reasons, Tally forms + GitHub issue template for suggestions, Discord testing | Web only; counts per category are lopsided; no popularity signal; no difficulty | **One YAML file per game** under `data/dles/NNNN-slug.yaml` (schema in Appendix B). GPL-3.0 means Dailies (GPL-3.0) could legally import the data with attribution, but see §5 recommendation. |
| **DLES.gg** — dles.gg | Commercial directory | 1068 games, "latest update 15 Oct 2026" | 17 (Words 379, Numbers and Logic 125, Video Games 81, Geography 77, Trivia 68, Movies and Series 65, Sports 52, Music 44, Visual 43, Guessing 29, Tabletop 28, History 23, Nature 16, Misc 14, Colors 13, Transport 6, Food 5) | "Build Your Ritual" (personal daily set), bookmarks, random, pick-of-the-week, reviews, **Graveyard** section | No API; closed | Proprietary; no license stated |
| **Dle Hunt** — dlehunt.com | Community directory with accounts | 859 games | 11 (Word, Geography, Music, Movies, TV, Gaming, Sports, Math, Trivia, Higher/Lower, Other) | Ratings, "Most played / most favorited" leaderboards, cross-game streak, curated collections, "Your dailies" playlist | Rating/favorites need an account; closed | Proprietary |
| **Alldle** — alldle.net | SEO-heavy directory | 1606 games (2026-10-14) | 17 (Words, Music, Geography, Sports, Transport, Movies & TV, Colors, Food, Logic & Math, Trivia, History, Video Games, Guessing, Tabletop Games, Visual, Nature & Science, Misc) | A–Z index, creator sign-in | Quantity over curation | Proprietary |
| **Dle Games** — dlegames.org | Directory with paid ad-free tier | 600+ | 18 (Word, Geography, History, Science & Nature, Music, TV, Movies, Gaming, Sports, Math, Logic, Color, Visual, Estimation, Board & Card, Quiz & Trivia, Higher or Lower, Other) | Local favorites, Popular/Featured/Fresh sections | Ads; $2.9/mo to remove | Proprietary |
| **playdle / dle.wtf** | Hub that **hosts 12 games itself** and links 22 others | 34 | 7 (Words & letters, Estimation, Logic & numbers, Geography, Music & sound, Movies & TV, Trivia & more) | No account; favorites/progress/streaks in browser; footer "Games belong to their respective creators"; linked games open on creator sites | Tiny | Proprietary |
| **Puzzmo** — puzzmo.com | Publisher platform (Zach Gage), own games only | ~10 games | n/a | Polished; cross-game daily ritual | Not an aggregator; Puzzmo Plus paywall for archive | Proprietary |
| **NYT Games app** | Publisher app | 7 games | n/a | Streaks, leaderboards with friends | NYT only; subscription for archive and full Spelling Bee/Crossword | Proprietary |
| **Daily Games Tracker** (Chrome extension) | Browser extension | ~39 users | n/a | Remembers which dailies you've done | Chrome-only, tiny | unknown |
| **DLEs - Daily Games & Puzzles** (iOS, released June 2026), **Daily Puzzles** (iOS, Norman Basham), **Sportsdle** (web + mobile, sports only) | Mobile apps | small | n/a | Native mobile | Host their own mini-games rather than launching third-party ones | Proprietary |
| **GNOME / Flathub** | — | — | — | Only single-game Wordle clones exist: **Blurble** (`app.drey.Blurble`, GPL-3.0-or-later, GTK4/libadwaita, Vala; last release 0.4.0, 2023), **Puzzled** (`de.til7701.Puzzled`, tile-placement puzzles), **GNOME Crosswords**. Flathub search for "daily puzzle" returns only Puzzled and Crossword Editor. | **No DLE launcher/aggregator exists on Flathub or as a GTK app** — Dailies would be first. | — |

What they do well that Dailies should copy:
1. **Favorites + "done today" + random** (aukspot, dle.wtf, dles.gg "Ritual") — the trio every directory converges on; "done today" is the one most relevant to a launcher.
2. **Dated add/remove history with reasons** (aukspot) — makes the catalog auditable and powers a Graveyard view.
3. **"New this week" / pick of the week** (dles.gg, dlegames.org "Fresh finds") — complements Popular/Trending.
4. **Local-only state, no accounts** (aukspot, dle.wtf) — matches the brief exactly.

What they do poorly:
1. Category sprawl (17–19 buckets, half with <20 games).
2. Zero link hygiene: hijacked domains persist for months (moviedle.app, absurdle.online, posterdle.com are still linked on several directories). aukspot removes them manually.
3. No difficulty signal anywhere.
4. Popularity is either absent or gated behind an account (dlehunt).

### 3.1 Embedding/framing caveats for the "built-in browser" mode

The brief's preference order (configured browser → built-in WebView → external browser) implies loading third-party pages inside a WebKitGTK view. Facts:
- **NYT ToS §2.2** (fetched 2026-10-15 from help.nytimes.com): "You may not modify, publish, transmit, participate in the transfer or sale of, reproduce (except as provided in Section 2.3 of these Terms of Service), create new works from, distribute, perform, display (**including framing and inline linking**), communicate to the public or in any way exploit, any of the Content..." It also prohibits using "robots, spiders, scripts... to data mine or scrape the Content... or otherwise use, access, or collect the Content... using automated means".
- Inference: a full-page WebView that navigates to the page (like a browser tab) is not "framing" in the HTML-`<iframe>` sense and is how Obsidian/Electron-style in-app browsers work; but NYT's clause is broad enough that the design doc should (a) never embed games in an `<iframe>` of a Dailies-owned page, (b) never inject scripts or strip ads, (c) send a normal browser UA, (d) keep "open in external browser" one click away, and (e) make the WebView the *fallback*, as the brief already does.
- Many sites set `X-Frame-Options`/CSP `frame-ancestors`; irrelevant for a top-level WebView navigation but fatal for iframes — another reason not to iframe.
- Fan-made games built on others' IP (Pokédle, LoLdle, Smashdle, Dotadle, Onepiecedle, Narutodle, Harry-Potter-dle etc.) are listed by every aggregator; Dailies only links, but these are the entries most likely to disappear (IP takedowns) — tag them `fan-made` and expect churn.

## 4. Trademark and attribution

Verified:
- The New York Times filed US trademark application **serial 97510050** for the word mark WORDLE (filed 2022-07-19 per TrademarkElite; status shown as "suspended" as of 2026-07-23). Not confirmed as registered; verify on USPTO TSDR. An unrelated earlier WORDLE registration (2625340, 2002) was cancelled in 2013.
- In March 2024 NYT sent DMCA notices to GitHub against Wordle clones, including the **Reactle** repo and its ~1,900 forks, asserting rights over the name and over "look and feel" elements such as the 5×6 grid and green/yellow/grey tiles (404 Media, 2024-03-07; Engadget; Gizmodo). NYT stated it "has no issue with similar word games that don't infringe its Wordle trademarks or copyrighted gameplay" (AP, 2024-03).
- NYT filed a USPTO opposition against Kory McDonald's **WORLDLE** application (2024); outcome not found. A German court in July 2024 rejected NYT's claim against Stefan Heine's German WORDLE mark (Euronews 2024-07-21).
- Spotify shut down Heardle in May 2023.

Implications for Dailies (inference):
1. Dailies **links/launches**; it does not reproduce gameplay, so the Reactle-style copyright exposure does not apply. Nominative use of a game's name to identify where a link goes is the classic fair-use case for trademarks.
2. **Do not ship third-party logos/icons** in the catalog. Use (a) the app's own generic category icons, or (b) a favicon fetched at runtime from the game's own domain and cached locally, never redistributed in the repo or Flatpak. aukspot/dles ships no icons for this reason (inference from the repo: no icon field in the schema).
3. Avoid Wordle's trade dress (green/yellow/grey 5×6 tiles) in the Dailies logo and screenshots. Use a calendar/sun/"daily" motif instead.
4. Add a one-line disclaimer in README and About dialog: "Dailies is not affiliated with The New York Times, Merriam-Webster, or any game listed. All game names are trademarks of their respective owners. Dailies only opens their public websites."
5. Mark `nyt`, `merriam-webster`, `linkedin` as publisher tags so a future "hide subscription games" filter is trivial.
6. The word **"Dailies"** has no collision with an existing DLE launcher (search 2026-10-15 found none); closest names are "DLEs - Daily Games & Puzzles" (iOS, 2026) and "Daily Puzzles" (iOS). An app-id like `io.github.tim_van_oudheusden.Dailies` or a custom domain reverse-DNS is unaffected.

## 5. Recommendations for Dailies

1. **Seed the catalog with Appendix A (116 games)** but run every entry through the link checker in CI on day one; drop `food-le` and `birdle` unless a human confirms them.
2. **Store the catalog as one YAML/JSON file per game** (aukspot pattern, Appendix B) in `data/games/<id>.yaml`, built into a single `catalog.json` by CI. Pros: PR diffs are per-game, GitHub issue → PR automation is trivial, `history` is auditable. Fields: `id, name, url, category, difficulty, description, tags, free_no_account, status (active|archived|removed), added, history[]`.
3. **Issue form → PR bot**: a GitHub Issue Form (`.github/ISSUE_TEMPLATE/add-game.yml`) with dropdowns for the 10 categories and 3 difficulties, and a required URL; an action validates (HEAD/GET 200, same-domain final URL, no `<title>` containing gambling keywords) and opens a PR adding the YAML.
4. **Link hygiene job (weekly)**: fail on non-2xx, on cross-registrable-domain redirects (moviedle.app → gambling), on titles matching a blocklist. Set `status: removed` with a `reason` instead of deleting — keeps the Graveyard and lets the app hide stale favorites gracefully.
5. **Popularity/Trending sources** (for the sibling research task): aggregator "most played/favorited" (dlehunt), dles.gg "pick of the week", aukspot `history.added` dates for "new", plus the number of directories listing a game (a cheap proxy for popularity — being in all five directories above is a strong signal). Avoid scraping NYT.
6. **Categories**: ship the 10 primaries above as a fixed enum; tags as a curated list; Favorites, Popular, Trending as computed sections. Store `free_no_account` and surface it as a badge; default-filter nothing.
7. **Access mode**: default to the user's configured browser via `Gtk.UriLauncher`/portal; make the WebKitGTK built-in view opt-in per game or global, with "Open externally" always visible; no iframes, no script injection; honour the NYT ToS wording in §3.1.
8. **Legal copy**: README/About disclaimer (§4.4), no bundled third-party icons, favicon caching at runtime only.
9. **Non-English**: the owner is Dutch; keep Woordle and friends with a `non-english` tag and a language tag so a Settings toggle "show games in other languages" can hide them by default for non-matching locales.
10. **Treat aukspot/dles as a reference, not a dependency**: its license (GPL-3.0) is compatible with Dailies, but its 19-category scheme and 877 entries would swamp a desktop launcher. Import selectively and credit it in README ("Catalog seeded with help from The Dles by aukspot, GPL-3.0").

## 6. Open questions

1. Exact free-play limit of NYT Spelling Bee and whether The Mini is still free; needs a logged-out manual check in a browser (automated fetch of nytimes.com is blocked for WebFetch and the ToS forbids scraping).
2. Whether LinkedIn games really play without a LinkedIn account (aukspot says yes for Crossclimb; not re-verified).
3. Washington Post Keyword reachability (curl `000` from this network).
4. Outcome of NYT v. Worldle USPTO opposition (not found).
5. Whether to include fan-made IP games (Pokédle, LoLdle…) by default given takedown risk.
6. Birdle (birdlegame.com) and Food-le content/provenance.

## Sources

Primary (fetched 2026-10-15):
- https://github.com/aukspot/dles (GPL-3.0; cloned; `README.md`, `data/dles/*.yaml`) and https://dles.aukspot.com/
- https://dles.gg/ ; https://dlehunt.com/ ; https://www.alldle.net/all-dles ; https://dlegames.org/ ; https://dle.wtf/
- https://help.nytimes.com/hc/en-us/articles/115014893428-Terms-of-Service (§1.1, §2.2, §2.3; fetched via curl)
- https://www.geoguessr.com/daily-challenges ; https://scrandle.com/ ; https://scrandle.cc/ ; https://wheredle.xyz/ ; https://moviedle.xyz/ ; https://qntm.org/files/absurdle/absurdle.html ; https://www.vulture.com/article/daily-movie-grid-trivia-game-cinematrix.html
- https://flathub.org/api/v2/appstream/app.drey.Blurble ; https://flathub.org/api/v2/search
- All catalog URLs (curl results in scratchpad `work/results1t.txt`, `work/results2.txt`)

Secondary:
- 404 Media, "NYTimes Files Copyright Takedowns Against Hundreds of Wordle Clones" https://www.404media.co/nytimes-files-copyright-takedowns-against-hundreds-of-wordle-clones/
- Engadget https://www.engadget.com/the-new-york-times-is-cracking-down-on-wordle-clones-100004668.html ; Gizmodo https://gizmodo.com/nyt-dmca-takedown-request-wordle-clones-reactle-1851320538
- AP via WJLA, "NYT fighting off Wordle copycats with several takedown notices" https://wjla.com/news/offbeat/nyt-fighting-off-wordle-copycats-with-several-takedown-notices-word-guessing-game-new-york-times-look-alikes-digital-millenium-copycat-act-github-trademark-battle
- TrademarkElite WORDLE serial 97510050 https://www.trademarkelite.com/trademark/trademark-detail/97510050/WORDLE ; Justia older mark https://trademark.justia.com/753/00/wordle-75300387.html
- Techdirt on Worldle opposition https://www.techdirt.com/tag/wordle/ ; Goodmans IP https://www.goodmans.ca/insights/post/goodmans-ip-blog/worldle--faces-a-wordle-hurdle ; Euronews German ruling https://www.euronews.com/business/2024/07/21/new-york-times-unable-to-push-germanys-wordle-out-of-puzzle-market
- Heardle shutdown: https://www.techradar.com/news/spotify-just-killed-the-best-wordle-like-game-for-music-fans ; https://www.stereogum.com/?p=2220401
- Bracket City / Atlantic games: https://www.niemanlab.org/2025/06/wordle-who-the-atlantic-launches-a-suite-of-new-daily-puzzles-and-games/
- Pokédle/LoLdle developer link: https://www.ggrecon.com/word-games/pokedle-answers-hints-today/ ; https://10015.io/product/pokedle
- Daily Games Tracker extension https://www.chromeboard.com/extension/daily-games-tracker-lilhdhmnjimhilmalbhfbdkdockefoja
- Blurble on LinuxPhoneApps https://linuxphoneapps.org/games/app.drey.blurble/ ; Puzzled https://www.linuxlinks.com/puzzled-solving-daily-tile-placement-puzzles/
- Book Riot on the Mini https://ohayou.bookriot.com/the-new-york-times-mini-crossword-is-no-longer-free-to-play/ (unverified claim)

## Appendix A — Catalog JSON (116 entries)

Schema: `{id, name, url, category, difficulty, description, tags, free_no_account}`. `category` ∈ {words, geography, music, movies-tv, video-games, numbers-logic, trivia, visual, food, sports}; `difficulty` ∈ {easy, medium, hard}. Validated with `python3 -I -c "json.load(...)"` on 2026-10-15; also saved as `<scratch>/work/catalog.json`.

```json
[
{"id":"wordle","name":"Wordle","url":"https://www.nytimes.com/games/wordle/index.html","category":"words","difficulty":"easy","description":"Guess the five-letter word in six tries; the game that started the -dle wave.","tags":["nyt","wordle-like","five-letter"],"free_no_account":true},
{"id":"nyt-connections","name":"Connections","url":"https://www.nytimes.com/games/connections","category":"words","difficulty":"medium","description":"Group 16 words into four hidden categories with at most four mistakes.","tags":["nyt","grouping"],"free_no_account":true},
{"id":"nyt-strands","name":"Strands","url":"https://www.nytimes.com/games/strands","category":"words","difficulty":"easy","description":"Themed word search where every letter is used exactly once, with a spangram spanning the board.","tags":["nyt","word-search"],"free_no_account":true},
{"id":"nyt-spelling-bee","name":"Spelling Bee","url":"https://www.nytimes.com/puzzles/spelling-bee","category":"words","difficulty":"hard","description":"Make as many words as possible from seven letters, always using the centre letter.","tags":["nyt","anagram","subscription-limited"],"free_no_account":false},
{"id":"nyt-mini-crossword","name":"The Mini Crossword","url":"https://www.nytimes.com/crosswords/game/mini","category":"words","difficulty":"easy","description":"A 5x5 crossword meant to be solved in a minute or two.","tags":["nyt","crossword"],"free_no_account":true},
{"id":"nyt-letter-boxed","name":"Letter Boxed","url":"https://www.nytimes.com/puzzles/letter-boxed","category":"words","difficulty":"medium","description":"Chain words around a square of twelve letters, never using two letters from the same side in a row.","tags":["nyt","word-chain"],"free_no_account":true},
{"id":"nyt-pips","name":"Pips","url":"https://www.nytimes.com/games/pips","category":"numbers-logic","difficulty":"medium","description":"Place dominoes on a board so each region satisfies its numeric rule; NYT's 2025 logic game.","tags":["nyt","dominoes","logic"],"free_no_account":true},
{"id":"nyt-sudoku","name":"NYT Sudoku","url":"https://www.nytimes.com/puzzles/sudoku","category":"numbers-logic","difficulty":"medium","description":"Daily sudoku at easy, medium and hard levels.","tags":["nyt","sudoku"],"free_no_account":true},
{"id":"nyt-tiles","name":"Tiles","url":"https://www.nytimes.com/puzzles/tiles","category":"visual","difficulty":"easy","description":"Match layered patterns on tiles to clear the board in one long combo.","tags":["nyt","matching","relaxing"],"free_no_account":true},
{"id":"quordle","name":"Quordle","url":"https://www.merriam-webster.com/games/quordle/","category":"words","difficulty":"hard","description":"Solve four Wordle boards at once with nine shared guesses.","tags":["merriam-webster","wordle-like","multi-board"],"free_no_account":true},
{"id":"octordle","name":"Octordle","url":"https://www.merriam-webster.com/games/octordle/","category":"words","difficulty":"hard","description":"Eight simultaneous Wordle boards and thirteen guesses.","tags":["merriam-webster","wordle-like","multi-board"],"free_no_account":true},
{"id":"dordle","name":"Dordle","url":"https://zaratustra.itch.io/dordle","category":"words","difficulty":"medium","description":"Two Wordle boards solved with the same guesses; the original multi-board variant.","tags":["wordle-like","multi-board","itch.io"],"free_no_account":true},
{"id":"sedecordle","name":"Sedecordle","url":"https://sedecordle.com/","category":"words","difficulty":"hard","description":"Sixteen Wordle boards, 21 guesses.","tags":["wordle-like","multi-board"],"free_no_account":true},
{"id":"absurdle","name":"Absurdle","url":"https://qntm.org/files/absurdle/absurdle.html","category":"words","difficulty":"hard","description":"Adversarial Wordle that changes its secret word to dodge your guesses; not strictly daily but endless.","tags":["wordle-like","adversarial","not-daily"],"free_no_account":true},
{"id":"semantle","name":"Semantle","url":"https://semantle.com/","category":"words","difficulty":"hard","description":"Guess the secret word by semantic similarity scores from a word-embedding model.","tags":["semantic","word-embeddings"],"free_no_account":true},
{"id":"contexto","name":"Contexto","url":"https://contexto.me/","category":"words","difficulty":"medium","description":"Semantle-style: each guess is ranked by how contextually close it is to the secret word.","tags":["semantic"],"free_no_account":true},
{"id":"waffle","name":"Waffle","url":"https://wafflegame.net/","category":"words","difficulty":"medium","description":"Swap letters on a waffle-shaped grid to form six words in 15 swaps or fewer.","tags":["swap","grid"],"free_no_account":true},
{"id":"squardle","name":"Squardle","url":"https://fubargames.se/squardle/","category":"words","difficulty":"hard","description":"Wordle in two dimensions: fill a 5x5 grid of six intersecting words.","tags":["wordle-like","grid"],"free_no_account":true},
{"id":"squaredle","name":"Squaredle","url":"https://squaredle.app/","category":"words","difficulty":"medium","description":"Boggle-style daily word search: find every word by connecting adjacent letters.","tags":["word-search","boggle"],"free_no_account":true},
{"id":"redactle","name":"Redactle","url":"https://redactle.net/","category":"words","difficulty":"hard","description":"Un-redact a Wikipedia article one guessed word at a time to identify its title.","tags":["wikipedia","redaction"],"free_no_account":true},
{"id":"pedantle","name":"Pedantle","url":"https://pedantle.certitudes.org/","category":"words","difficulty":"hard","description":"English sibling of the French pedantix: reveal a redacted Wikipedia page by guessing words, with semantic hints.","tags":["wikipedia","redaction","semantic"],"free_no_account":true},
{"id":"weaver","name":"Weaver","url":"https://wordwormdormdork.com/","category":"words","difficulty":"easy","description":"Word ladder: change one letter at a time to get from the start word to the end word.","tags":["word-ladder"],"free_no_account":true},
{"id":"phrazle","name":"Phrazle","url":"https://solitaired.com/phrazle","category":"words","difficulty":"medium","description":"Wordle for whole phrases; two puzzles a day.","tags":["wordle-like","phrases"],"free_no_account":true},
{"id":"betweenle","name":"Betweenle","url":"https://betweenle.com/","category":"words","difficulty":"medium","description":"Find the secret word by narrowing it down alphabetically between your guesses.","tags":["alphabetical","bisection"],"free_no_account":true},
{"id":"crosswordle","name":"Crosswordle","url":"https://crosswordle.vercel.app/","category":"words","difficulty":"medium","description":"Reverse Wordle: given the coloured grid of a finished game, reconstruct the guesses.","tags":["wordle-like","deduction"],"free_no_account":true},
{"id":"xordle","name":"Xordle","url":"https://xordle.org/","category":"words","difficulty":"hard","description":"Two secret words share one board and one set of colour clues.","tags":["wordle-like","deduction"],"free_no_account":true},
{"id":"antiwordle","name":"Antiwordle","url":"https://www.antiwordle.com/","category":"words","difficulty":"medium","description":"Try NOT to guess the word; letters you reveal become mandatory.","tags":["wordle-like","inverted"],"free_no_account":true},
{"id":"kilordle","name":"Kilordle","url":"https://jonesnxt.github.io/kilordle/","category":"words","difficulty":"hard","description":"One thousand Wordle boards at once; a marathon rather than a puzzle.","tags":["wordle-like","multi-board","marathon"],"free_no_account":true},
{"id":"minute-cryptic","name":"Minute Cryptic","url":"https://www.minutecryptic.com/","category":"words","difficulty":"medium","description":"One cryptic crossword clue per day with a video explanation.","tags":["cryptic","crossword"],"free_no_account":true},
{"id":"blossom","name":"Blossom","url":"https://www.merriam-webster.com/games/blossom-word-game","category":"words","difficulty":"easy","description":"Spelling Bee-style: build words from seven petals, scoring bonus for the highlighted letter.","tags":["merriam-webster","anagram"],"free_no_account":true},
{"id":"twofer-goofer","name":"Twofer Goofer","url":"https://www.merriam-webster.com/games/twofer-goofer","category":"words","difficulty":"easy","description":"Guess a rhyming two-word phrase from a clue.","tags":["merriam-webster","rhymes"],"free_no_account":true},
{"id":"jumblie","name":"Jumblie","url":"https://jumblie.com/","category":"words","difficulty":"easy","description":"Find four themed words hidden in a jumble of letters.","tags":["word-search","themed"],"free_no_account":true},
{"id":"conexo","name":"Conexo","url":"https://conexo.ws/","category":"words","difficulty":"medium","description":"Connections-style grouping game available in several languages.","tags":["grouping","multilingual"],"free_no_account":true},
{"id":"bracket-city","name":"Bracket City","url":"https://www.theatlantic.com/games/bracket-city/","category":"words","difficulty":"medium","description":"Solve nested bracketed clues until a single sentence about a historic event remains (The Atlantic).","tags":["the-atlantic","clues","history"],"free_no_account":true},
{"id":"keyword","name":"Keyword","url":"https://www.washingtonpost.com/games/keyword/","category":"words","difficulty":"medium","description":"Find the target word by guessing the final letter of six vertical words (Washington Post).","tags":["washington-post","letter-reveal","unverified-live"],"free_no_account":true},
{"id":"puzzmo","name":"Puzzmo","url":"https://www.puzzmo.com/","category":"words","difficulty":"medium","description":"Daily puzzle hub (Crossword, SpellTower, Typeshift, Really Bad Chess, Pile-Up Poker and more) by Zach Gage.","tags":["hub","crossword","multi-game","account-optional"],"free_no_account":true},
{"id":"woordle","name":"Woordle","url":"https://woordle.nl/","category":"words","difficulty":"easy","description":"Dutch daily word game in the Wordle mould.","tags":["wordle-like","dutch","non-english"],"free_no_account":true},
{"id":"sutom","name":"SUTOM","url":"https://sutom.nocle.fr/","category":"words","difficulty":"medium","description":"French Motus-style daily word game with the first letter given.","tags":["wordle-like","french","non-english"],"free_no_account":true},
{"id":"le-mot","name":"Le Mot","url":"https://wordle.louan.me/","category":"words","difficulty":"easy","description":"Wordle in French.","tags":["wordle-like","french","non-english"],"free_no_account":true},
{"id":"cemantix","name":"Cémantix","url":"https://cemantix.certitudes.org/","category":"words","difficulty":"hard","description":"French semantic word-guessing game (the original behind Pedantle/Pedantix).","tags":["semantic","french","non-english"],"free_no_account":true},
{"id":"termo","name":"Termo","url":"https://term.ooo/","category":"words","difficulty":"easy","description":"Brazilian Portuguese Wordle, with dueto/quarteto multi-board modes.","tags":["wordle-like","portuguese","non-english"],"free_no_account":true},
{"id":"la-palabra-del-dia","name":"La palabra del día","url":"https://lapalabradeldia.com/","category":"words","difficulty":"easy","description":"Spanish Wordle.","tags":["wordle-like","spanish","non-english"],"free_no_account":true},
{"id":"linkedin-pinpoint","name":"Pinpoint","url":"https://www.linkedin.com/games/pinpoint/","category":"words","difficulty":"easy","description":"Guess the category that links five words revealed one at a time (LinkedIn).","tags":["linkedin","grouping","account-for-streaks"],"free_no_account":true},
{"id":"linkedin-queens","name":"Queens","url":"https://www.linkedin.com/games/queens/","category":"numbers-logic","difficulty":"medium","description":"Place one crown per row, column and colour region with no two touching (LinkedIn).","tags":["linkedin","logic","account-for-streaks"],"free_no_account":true},
{"id":"clues-by-sam","name":"Clues By Sam","url":"https://cluesbysam.com/","category":"numbers-logic","difficulty":"medium","description":"Deduce which characters in a grid are innocent or criminal from chained clues.","tags":["deduction","logic"],"free_no_account":true},
{"id":"worldle","name":"Worldle","url":"https://worldle.teuteuf.fr/","category":"geography","difficulty":"easy","description":"Identify a country from its silhouette, with distance and direction hints.","tags":["teuteuf","countries","silhouette"],"free_no_account":true},
{"id":"globle","name":"Globle","url":"https://globle-game.com/","category":"geography","difficulty":"medium","description":"Find the mystery country on a globe; guesses get hotter colours the closer they are.","tags":["countries","globe"],"free_no_account":true},
{"id":"travle","name":"Travle","url":"https://travle.earth/","category":"geography","difficulty":"medium","description":"Get from one country to another in as few bordering-country guesses as possible.","tags":["countries","borders","pathfinding"],"free_no_account":true},
{"id":"flagle","name":"Flagle","url":"https://www.flagle.io/","category":"geography","difficulty":"easy","description":"Guess the country from a flag revealed one tile at a time.","tags":["flags","countries"],"free_no_account":true},
{"id":"countryle","name":"Countryle","url":"https://countryle.com/","category":"geography","difficulty":"medium","description":"Guess the country using hemisphere, continent, temperature and population hints.","tags":["countries","hints"],"free_no_account":true},
{"id":"statele","name":"Statele","url":"https://statele.teuteuf.fr/","category":"geography","difficulty":"medium","description":"Worldle for US states.","tags":["teuteuf","usa","silhouette"],"free_no_account":true},
{"id":"tradle","name":"OEC Tradle","url":"https://games.oec.world/en/tradle/","category":"geography","difficulty":"hard","description":"Guess the country from a treemap of its exports (Observatory of Economic Complexity).","tags":["economics","countries","oec"],"free_no_account":true},
{"id":"wheredle","name":"Wheredle","url":"https://wheredle.xyz/","category":"geography","difficulty":"hard","description":"Detective-style Street View game: find clues to guess which US state you are in.","tags":["street-view","usa"],"free_no_account":true},
{"id":"wheretaken","name":"WhereTaken","url":"https://wheretaken.teuteuf.fr/","category":"geography","difficulty":"medium","description":"Guess the country where a photo was taken, with distance and direction hints.","tags":["teuteuf","photos","countries"],"free_no_account":true},
{"id":"geogrid","name":"GeoGrid","url":"https://www.geogridgame.com/","category":"geography","difficulty":"hard","description":"Immaculate-Grid-style 3x3 where each cell needs a country matching row and column criteria.","tags":["grid","countries","trivia"],"free_no_account":true},
{"id":"timeguessr","name":"TimeGuessr","url":"https://timeguessr.com/","category":"visual","difficulty":"medium","description":"Guess the year and location of five historical photos.","tags":["photos","history","geography"],"free_no_account":true},
{"id":"chronophoto","name":"Chronophoto","url":"https://www.chronophoto.app/","category":"visual","difficulty":"medium","description":"Guess the year five photographs were taken.","tags":["photos","history"],"free_no_account":true},
{"id":"whentaken","name":"WhenTaken","url":"https://whentaken.com/","category":"visual","difficulty":"medium","description":"Guess when and where a photo was taken (teuteuf).","tags":["teuteuf","photos","history","geography"],"free_no_account":true},
{"id":"geoguessr-daily","name":"GeoGuessr Daily Challenge","url":"https://www.geoguessr.com/daily-challenges","category":"geography","difficulty":"hard","description":"Five Street View rounds that refresh daily; requires a free GeoGuessr account.","tags":["street-view","account-required"],"free_no_account":false},
{"id":"metazooa","name":"Metazooa","url":"https://metazooa.com/","category":"trivia","difficulty":"medium","description":"Guess the mystery animal; each guess shows where it sits on the tree of life relative to the answer.","tags":["nature","taxonomy","animals"],"free_no_account":true},
{"id":"metaflora","name":"Metaflora","url":"https://flora.metazooa.com/","category":"trivia","difficulty":"hard","description":"Metazooa for plants.","tags":["nature","taxonomy","plants"],"free_no_account":true},
{"id":"foodguessr","name":"FoodGuessr","url":"https://www.foodguessr.com/","category":"food","difficulty":"medium","description":"Guess the country a dish comes from in three rounds.","tags":["geography","cuisine"],"free_no_account":true},
{"id":"scrandle","name":"Scrandle","url":"https://scrandle.com/","category":"food","difficulty":"easy","description":"Daily food-comparison game: pick which 'scran' (stadium food) is rated higher by the crowd.","tags":["comparison","uk","higher-lower"],"free_no_account":true},
{"id":"costcodle","name":"Costcodle","url":"https://costcodle.com/","category":"food","difficulty":"easy","description":"Guess the price of a Costco product within six tries.","tags":["estimation","prices","shopping"],"free_no_account":true},
{"id":"food-le","name":"Food-le","url":"https://food-le.com/","category":"food","difficulty":"easy","description":"Wordle with five-letter food words; successor site after the original foodle.io went offline (low confidence on provenance).","tags":["wordle-like","low-confidence"],"free_no_account":true},
{"id":"bandle","name":"Bandle","url":"https://bandle.app/","category":"music","difficulty":"medium","description":"Guess the song as it is rebuilt one instrument at a time.","tags":["songs","audio"],"free_no_account":true},
{"id":"spotle","name":"Spotle","url":"https://spotle.io/","category":"music","difficulty":"medium","description":"Guess the artist from attribute hints (debut year, group size, genre, popularity).","tags":["artists","hints"],"free_no_account":true},
{"id":"lyricle","name":"Lyricle","url":"https://www.lyricle.app/","category":"music","difficulty":"medium","description":"Guess the song from lyrics revealed one line at a time.","tags":["lyrics","songs"],"free_no_account":true},
{"id":"heardle-decades","name":"Heardle Decades","url":"https://heardledecades.com/","category":"music","difficulty":"medium","description":"Community-run Heardle successors: guess the song from its opening seconds, by decade.","tags":["audio","songs","heardle"],"free_no_account":true},
{"id":"songless","name":"Songless","url":"https://lessgames.com/songless","category":"music","difficulty":"medium","description":"Heardle-style: identify a song from a very short clip, with more time per skip.","tags":["audio","songs","heardle"],"free_no_account":true},
{"id":"harmonies","name":"Harmonies","url":"https://harmonies.io/","category":"music","difficulty":"medium","description":"Connections for music: group 16 songs into four categories.","tags":["grouping","songs"],"free_no_account":true},
{"id":"framed","name":"Framed","url":"https://framed.wtf/","category":"movies-tv","difficulty":"medium","description":"Guess the movie from up to six stills.","tags":["movies","stills"],"free_no_account":true},
{"id":"actorle","name":"Actorle","url":"https://actorle.com/","category":"movies-tv","difficulty":"hard","description":"Guess the actor from a redacted filmography with years, genres and ratings.","tags":["actors","filmography"],"free_no_account":true},
{"id":"moviedle","name":"Moviedle","url":"https://moviedle.xyz/","category":"movies-tv","difficulty":"medium","description":"Guess the movie from its cast revealed one actor at a time (note: moviedle.app is no longer the game).","tags":["movies","cast"],"free_no_account":true},
{"id":"flickle","name":"Flickle","url":"https://flickle.app/","category":"movies-tv","difficulty":"medium","description":"Guess the movie from short clips.","tags":["movies","clips"],"free_no_account":true},
{"id":"cine2nerdle","name":"Cine2Nerdle","url":"https://www.cinenerdle2.app/","category":"movies-tv","difficulty":"hard","description":"Connect two movies through shared cast and crew; also has a battle mode.","tags":["movies","connections","graph"],"free_no_account":true},
{"id":"box-office-game","name":"Box Office Game","url":"https://boxofficega.me/","category":"movies-tv","difficulty":"hard","description":"Identify the top five films at the box office for a given weekend from clues.","tags":["movies","trivia","box-office"],"free_no_account":true},
{"id":"cinematrix","name":"Cinematrix","url":"https://www.vulture.com/article/daily-movie-grid-trivia-game-cinematrix.html","category":"movies-tv","difficulty":"hard","description":"Vulture's 3x3 movie grid: name films matching each row and column criterion; new puzzle every weekday.","tags":["vulture","grid","movies","weekdays-only"],"free_no_account":true},
{"id":"movie-grid","name":"Movie Grid","url":"https://moviegrid.io/","category":"movies-tv","difficulty":"hard","description":"Independent Immaculate-Grid-style movie trivia grid.","tags":["grid","movies"],"free_no_account":true},
{"id":"plotwords","name":"Plotwords","url":"https://plotwords.com/","category":"movies-tv","difficulty":"medium","description":"Guess the movie from plot keywords revealed one by one.","tags":["movies","keywords"],"free_no_account":true},
{"id":"emovi","name":"Emovi","url":"https://emovi.teuteuf.fr/","category":"movies-tv","difficulty":"easy","description":"Guess the movie from an emoji summary (teuteuf).","tags":["teuteuf","emoji","movies"],"free_no_account":true},
{"id":"gamedle","name":"Gamedle","url":"https://www.gamedle.wtf/","category":"video-games","difficulty":"medium","description":"Guess the video game from covers, characters, artwork or keywords; several modes.","tags":["covers","multi-mode"],"free_no_account":true},
{"id":"guess-the-game","name":"GuessThe.Game","url":"https://guessthe.game/","category":"video-games","difficulty":"medium","description":"Framed for video games: guess the title from up to six screenshots.","tags":["screenshots"],"free_no_account":true},
{"id":"pokedle","name":"Pokédle","url":"https://pokedle.net/","category":"video-games","difficulty":"easy","description":"Guess the Pokémon from attribute hints, silhouettes, cries or descriptions; multiple modes.","tags":["pokemon","fan-made","multi-mode"],"free_no_account":true},
{"id":"pokedoku","name":"PokeDoku","url":"https://pokedoku.com/","category":"video-games","difficulty":"hard","description":"3x3 grid where each cell needs a Pokémon matching two criteria.","tags":["pokemon","grid","fan-made"],"free_no_account":true},
{"id":"loldle","name":"LoLdle","url":"https://loldle.net/","category":"video-games","difficulty":"medium","description":"Guess the League of Legends champion from attributes, quotes, abilities, emoji or splash art.","tags":["league-of-legends","fan-made","multi-mode"],"free_no_account":true},
{"id":"smashdle","name":"Smashdle","url":"https://smashdle.net/","category":"video-games","difficulty":"medium","description":"LoLdle-style guessing for Super Smash Bros. fighters.","tags":["smash-bros","fan-made"],"free_no_account":true},
{"id":"dotadle","name":"Dotadle","url":"https://dotadle.net/","category":"video-games","difficulty":"medium","description":"Guess the Dota 2 hero from attributes and abilities.","tags":["dota","fan-made"],"free_no_account":true},
{"id":"onepiecedle","name":"Onepiecedle","url":"https://onepiecedle.net/","category":"movies-tv","difficulty":"medium","description":"Guess the One Piece character from attribute hints.","tags":["anime","fan-made"],"free_no_account":true},
{"id":"narutodle","name":"Narutodle","url":"https://narutodle.net/","category":"movies-tv","difficulty":"medium","description":"Guess the Naruto character from attribute hints.","tags":["anime","fan-made"],"free_no_account":true},
{"id":"dungleon","name":"Dungleon","url":"https://www.dungleon.com/","category":"numbers-logic","difficulty":"medium","description":"Wordle-like deduction with dungeon-crawler icons instead of letters.","tags":["deduction","wordle-like","pixel-art"],"free_no_account":true},
{"id":"chessle","name":"Chessle","url":"https://chessle.net/","category":"numbers-logic","difficulty":"hard","description":"Guess the chess opening sequence move by move with Wordle-style feedback.","tags":["chess","openings"],"free_no_account":true},
{"id":"chessguessr","name":"Chessguessr","url":"https://www.chessguessr.com/","category":"numbers-logic","difficulty":"hard","description":"Guess the next five moves of a real master game.","tags":["chess"],"free_no_account":true},
{"id":"nerdle","name":"Nerdle","url":"https://nerdlegame.com/","category":"numbers-logic","difficulty":"medium","description":"Wordle with equations: find the eight-character calculation in six tries.","tags":["math","wordle-like"],"free_no_account":true},
{"id":"mathler","name":"Mathler","url":"https://www.mathler.com/","category":"numbers-logic","difficulty":"medium","description":"Find the hidden calculation that equals the given number.","tags":["math","wordle-like"],"free_no_account":true},
{"id":"summle","name":"Summle","url":"https://summle.net/","category":"numbers-logic","difficulty":"medium","description":"Combine given numbers with arithmetic to hit a target (Countdown-style).","tags":["math","arithmetic"],"free_no_account":true},
{"id":"primel","name":"Primel","url":"https://converged.yt/primel/","category":"numbers-logic","difficulty":"hard","description":"Wordle for five-digit prime numbers.","tags":["math","primes","wordle-like"],"free_no_account":true},
{"id":"sumplete","name":"Sumplete","url":"https://sumplete.com/","category":"numbers-logic","difficulty":"easy","description":"Delete numbers from a grid so each row and column sums to its target.","tags":["math","grid","logic"],"free_no_account":true},
{"id":"numble","name":"Numble","url":"https://numble.wtf/","category":"numbers-logic","difficulty":"medium","description":"Reach the target number using six given numbers and basic operators.","tags":["math","arithmetic"],"free_no_account":true},
{"id":"murdle","name":"Murdle","url":"https://murdle.com/","category":"numbers-logic","difficulty":"medium","description":"Daily whodunit logic puzzle by G. T. Karber: deduce suspect, weapon and location.","tags":["deduction","mystery"],"free_no_account":true},
{"id":"factle","name":"Factle","url":"https://frontofficesports.com/trivia/factle/","category":"trivia","difficulty":"hard","description":"Rank the top five answers to a factual prompt in five guesses (now hosted by Front Office Sports).","tags":["ranking","lists"],"free_no_account":true},
{"id":"daily-dozen-trivia","name":"The Dozen: Daily Trivia","url":"https://dailydozentrivia.com/","category":"trivia","difficulty":"medium","description":"Twelve general-knowledge questions a day.","tags":["quiz","general-knowledge"],"free_no_account":true},
{"id":"thrice","name":"Thrice","url":"https://thrice.geekswhodrink.com/","category":"trivia","difficulty":"medium","description":"Pub-quiz style: each answer has three progressively easier clues (Geeks Who Drink).","tags":["quiz","clues"],"free_no_account":true},
{"id":"lingule","name":"Lingule","url":"https://lingule.xyz/","category":"trivia","difficulty":"medium","description":"Guess the language from a sample sentence, with geographic hints.","tags":["languages","geography"],"free_no_account":true},
{"id":"puzzgrid","name":"PuzzGrid","url":"https://puzzgrid.com/","category":"trivia","difficulty":"medium","description":"User-made Only Connect-style walls; endless rather than one-a-day.","tags":["grouping","user-generated","not-daily"],"free_no_account":true},
{"id":"rankdle","name":"Rankdle","url":"https://rankdle.com/","category":"video-games","difficulty":"medium","description":"Watch a gameplay clip and guess the player's competitive rank.","tags":["esports","clips"],"free_no_account":true},
{"id":"artle","name":"Artle","url":"https://www.nga.gov/artle.html","category":"visual","difficulty":"hard","description":"Guess the artist from up to four works in the National Gallery of Art collection.","tags":["art","museum","bot-walled"],"free_no_account":true},
{"id":"hexcodle","name":"Hexcodle","url":"https://hexcodle.com/","category":"visual","difficulty":"hard","description":"Guess the hex colour code of the shown colour.","tags":["colors","hex"],"free_no_account":true},
{"id":"colorfle","name":"Colorfle","url":"https://colorfle.com/","category":"visual","difficulty":"medium","description":"Mix three colours to match the target colour.","tags":["colors","mixing"],"free_no_account":true},
{"id":"birdle","name":"Birdle","url":"https://www.birdlegame.com/","category":"trivia","difficulty":"medium","description":"Daily bird guessing game (content not verified beyond the live title).","tags":["nature","birds","low-confidence"],"free_no_account":true},
{"id":"immaculate-grid","name":"Immaculate Grid","url":"https://www.immaculategrid.com/","category":"sports","difficulty":"hard","description":"Fill a 3x3 grid with players matching team/achievement criteria; baseball plus football, basketball and hockey editions (Sports Reference).","tags":["grid","baseball","nfl","nba","nhl","bot-walled"],"free_no_account":true},
{"id":"immaculate-footy","name":"Immaculate Footy","url":"https://www.immaculatefooty.com/","category":"sports","difficulty":"hard","description":"Immaculate Grid for football (soccer).","tags":["grid","soccer","bot-walled"],"free_no_account":true},
{"id":"poeltl","name":"Poeltl","url":"https://poeltl.nbpa.com/","category":"sports","difficulty":"medium","description":"Guess the NBA player from team, conference, position, height, age and number hints (NBPA).","tags":["nba","basketball"],"free_no_account":true},
{"id":"weddle","name":"Weddle","url":"https://www.weddlegame.com/","category":"sports","difficulty":"medium","description":"Poeltl for the NFL.","tags":["nfl","american-football"],"free_no_account":true},
{"id":"crossover-grid","name":"Crossover Grid","url":"https://crossovergrid.com/","category":"sports","difficulty":"hard","description":"Daily sports trivia grids across several leagues.","tags":["grid","multi-sport"],"free_no_account":true},
{"id":"word-peaks","name":"Word Peaks","url":"https://vegeta897.github.io/word-peaks/","category":"words","difficulty":"medium","description":"Wordle variant where tiles show whether each letter is alphabetically higher or lower.","tags":["wordle-like","alphabetical"],"free_no_account":true}
]
```

## Appendix B — aukspot/dles record schema (reproduced, GPL-3.0, for reference)

`data/dles/0263-nyt-wordle.yaml`:

```yaml
id: 263
name: NYT Wordle
url: https://www.nytimes.com/games/wordle/index.html
description: Guess the 5-letter word in six or fewer attempts.
category: Words
themes:
- Wordle-likes
status: active
history:
- date: '2024-02-13'
  event: added
```

A removed record (`data/dles/0023-birdle-like-wordle.yaml`) shows the removal pattern Dailies should copy:

```yaml
id: 23
name: Birdle (like Wordle)
url: https://birdle.escism.net
description: Guess the 5-letter bird name in 6 guesses or less.
category: Science/Nature
status: removed
history:
- date: '2025-06-11'
  event: added
- date: '2026-02-07'
  event: removed
  reason: Page gives 404 error.
```

Observed `status` values: `active` (785), `archived` (10), `removed` (82). Most frequent removal reasons: "Site no longer loads." (16), "No longer available." (5), "Site now redirects to suspicious website." (3), "No new puzzles. Archive still available." (3), "No daily puzzle." (3), "Contains AI-generated images." (3). Their README says suggestions come in via a Tally form or a GitHub issue template labelled `dles suggestion`.

## Appendix C — Proposed Dailies record (draft for the architecture doc)

```yaml
# data/games/worldle.yaml
id: worldle
name: Worldle
url: https://worldle.teuteuf.fr/
category: geography          # one of 10 enum values
difficulty: easy             # easy | medium | hard
description: Identify a country from its silhouette, with distance and direction hints.
tags: [teuteuf, countries, silhouette]
free_no_account: true
status: active               # active | archived | removed
history:
  - { date: 2026-10-15, event: added, source: "issue #1" }
```
