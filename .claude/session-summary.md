# Session summary

Hand-off notes for agent work in this repository, so the next session starts from where the last one stopped instead
of cold (AGENTS.md "Session Completion" step 7). Keep it short: overwrite the "Latest session" section at the end of
each session, in the issue's own commit; durable lessons belong in `.claude/memory/corrections.tsv` or
`docs/reflections/`, not here.

Format: date, issue/PR worked, outcome, open follow-ups, gotchas for next time.

## Latest session

2026-11-02. #313 / PR #326 on `feat/313-catalog-candidates`.

- **Outcome:** `scripts/catalog_candidates.py --commit SHA [--since DAY]` downloads aukspot/dles at one commit (GitHub
  tarball, urlcheck's public-https `fetch`, 32 MiB cap and a whole-body deadline), reads its `data/dles/*.yaml`
  records with ruamel.yaml from the scripts' lock, and prints the `active` ones whose registrable domain the catalog
  lacks, newest first. Review round: merged `main` (kept #314's catalog-guard row in `docs/testing.md`), each record
  is now refused above `MAX_RECORD` (64 KiB, from the tar header) before it is decompressed, and the quality lane's
  mutant-killing tests are in. Run at 31afcb9 with `--since 2026-10-16`: 10 of the 11 games the issue names; Tagline
  is left out because merriam-webster.com is already in the catalog.
- **Open follow-ups:** a scheduled workflow that files the list as a monthly issue is the owner's call (needs a
  workflow file); not filed.
- **Gotchas:**
  - The Dles' descriptions are GPL-3.0 and the catalog is CC0: never copy one into a submission.
  - Host Python 3.11 cannot import `dailies/core`; a host jq older than 1.7 fails 13 `pr-metrics`/`auto-qa-tuner`/
    `quality-report` tests that pass in CI.
