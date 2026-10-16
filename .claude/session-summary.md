# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-10-16 (fifth session). #103 on `ci/103-wikipedia-signal`: `wikipedia` titles for the 11 more games with an
English article about the game, `popularity.yml` collects with `--wikipedia`, HN stays off, docs record why.

- **Outcome:** the first v3 week is `method_version: 3` with Tranco and Wikipedia. Dry-run shelf diff (live data of
  2026-10-16): Wordle, Connections and Quordle leave Popular for Mini Crossword, Pips and Blossom, because an article
  scores below Tranco and every game on a shared domain ties on Tranco.
- **Open follow-ups:**
  - #136 (decision): Wikipedia demoting games with an article; the maintainer may want it settled before merging #103.
  - #137 (owner): `CLOUDFLARE_RADAR_TOKEN`, Radar's 404 rate, then `--radar`.
- **Gotchas:**
  - Check Wikipedia titles with `action=query&redirects=1&prop=pageprops` (`disambiguation`): `Globle (game)` is a
    redirect into `Wordle`; `Murdle` redirects to its author; `Framed (video game)` and `Numble` are other games.
  - HN Algolia matches title prefixes even with `typoTolerance=false` ("Statele" hits "Stateless", "Queens" hits
    "Queensland").
  - The host has Python 3.11 and `jaq` as `jq`: pytest needs 3.12 (`uv python install 3.12`), and 13 shell-script tests
    fail under `jaq` on `main` too.
