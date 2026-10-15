---
key: 60
title: feat(scripts): weekly link checker scripts/check_links.py
type: Feature
labels: milestone::M2, type::feature, priority::medium, data, ci
parent: 4
blocked_by: 31, 57
---
> **Risk tier:** high (`scripts/**`) · **Size:** S

## Why

Games die, move and get hijacked. Stale or hijacked links lingering for months is a common weakness of other DLE directories. Dailies checks every active entry weekly with the **same rules** as the submission validator.

## Tasks

- [ ] `scripts/check_links.py --catalog data/v1/games.json --out "$RUNNER_TEMP/links.md"`: for every `status: active` entry, apply the reachability, final-registrable-domain and title-blocklist checks from #57. **Share the code**: extract a `scripts/lib/urlcheck.py` used by both scripts
- [ ] Rate-limit politely (≤ 2 req/s overall, one host at a time) with the descriptive User-Agent
- [ ] Classify each result as `ok`, `redirected-cross-domain`, `blocked-title`, `http-<code>`, `timeout` or `bot-walled` (a Cloudflare challenge counts as a warning, not a failure: 4 seed games are bot-walled but live)
- [ ] Wire it into `scripts/nightly-compliance.sh` (#31) as a row that runs **only on Sundays**. Failures go to the job summary **and** open (or update) **one** issue titled `data: N broken links (week W)` with the label `data`, listing each game with its reason and a suggested `status` change
- [ ] The maintainer flips `status` to `broken` or `retired` by PR and **never deletes** entries. Automating the flip is #81
- [ ] Tests in `tests/scripts/test_check_links.py` with mocked HTTP: graveyard fixtures are reported, live fixtures pass, bot-walled → warning

## Acceptance criteria

- [ ] A manual run of nightly-compliance on a Sunday (or forced with a flag) produces the links row
- [ ] With one fixture entry pointing at a graveyard domain, the run opens the `data: 1 broken links (week W)` issue; a second run updates that issue instead of opening another

## References

- [`mvp-first.md` §7.6, §11 (nightly row), §17 risks 3 and 14](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`dle-catalog.md` §1.4, §5.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)
