---
key: 57
title: feat(scripts): submission validator scripts/validate_submission.py
type: Feature
labels: milestone::M2, type::feature, priority::high, data
parent: 4
blocked_by: 26, 31
---
> **Risk tier:** high (`scripts/**`) · **Size:** M · **Security:** runs on untrusted input from issue forms

## Why

Every game entering the catalog passes through this script, twice (stage A #58 and stage B #59). Hijacked or dead domains that redirect to gambling sites recur across this genre (`moviedle.app`, `absurdle.online`, `posterdle.com`, `cladder.io`, `cloudle.app`, `foodle.io`), so **the final registrable domain must equal the submitted one**.

## Interface

```sh
python -I scripts/validate_submission.py \
  --parsed "$HOME/issue-parser-result.json" \
  --catalog data/v1/games.json \
  --schema data/v1/schema/catalog.schema.json \
  --issue "$ISSUE_NUMBER" \
  --out "$RUNNER_TEMP/result.json" --report "$RUNNER_TEMP/report.md"
```

Exit code 0 means valid, 1 means invalid (the report explains why), 2 means a usage or internal error.

## Checks (from [`data-pipeline.md` §1.4, Appendix A6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md))

1. **Map form → entry:**
   - `name`
   - `url`
   - category label → enum id (the table in #23)
   - difficulty lower-cased
   - `description` (≥ 20 characters)
   - `tags`: split on commas and slugified
   - `language`: default `en`
2. **URL safety:**
   - parses; scheme must be `https`
   - the host must resolve **only** to public IPs: reject RFC 1918, loopback, link-local, CGNAT and ULA after DNS resolution. This bounds SSRF from the runner
3. **Reachability:**
   - `HEAD`, then `GET` if the HEAD returns 403/405
   - 10 s timeout, at most **5 redirects**
   - descriptive User-Agent; accept 2xx
4. **Final domain:** `tldextract` registrable domain of the **final** URL == that of the submitted URL. Otherwise fail with "redirects to another site (…)"
5. **Blocklist:** fail if the page `<title>` contains gambling keywords (curated list in `scripts/data/title-blocklist.txt`: casino, slot, bet, poker, togel, judi, …)
6. **Duplicates:**
   - normalise the URL (lower-case host, strip `www.`, trailing slash and `utm_*`) and compare host+path with existing `url`s
   - compare the slugified name with existing `id`s and `aliases`
   - fuzzy name match (`difflib.SequenceMatcher` ≥ 0.9) produces a **warning**, not a failure
7. **Candidate entry:**
   - `id` = slug of the name
   - `added` = today
   - `status: "active"`
   - `domain` from `tldextract`
   - `source_issue` = N
   - `history: [{date, event: "added", note: "issue #N"}]`
   - validated against the catalog schema with `check-jsonschema` / `jsonschema`
8. **Outputs:**
   - `result.json`: `{ok, entry, errors[], warnings[]}`
   - `report.md`: starts with the marker `<!-- dailies-submission-check -->` and contains a pass/fail table plus the candidate JSON in a code block

## Rules

- Never `eval` or shell out with form values; read them only from the parsed JSON file
- Dependencies come only from `scripts/requirements.txt` (#31): `requests`, `tldextract`, `check-jsonschema`

## Tests (`tests/scripts/test_validate_submission.py`)

- [ ] Valid submission → ok
- [ ] `http://` URL → fail
- [ ] Private IP (`10.0.0.1`, `127.0.0.1`, `[::1]`) → fail
- [ ] Cross-domain redirect → fail. Use the **graveyard domains as fixtures**, with HTTP mocked (`responses` or a local fixture server); never hit the network in unit tests
- [ ] Gambling title → fail
- [ ] Duplicate URL with `www.` and a trailing slash → fail
- [ ] Duplicate slug → fail
- [ ] Near-duplicate name → warning
- [ ] Unknown category label → fail
- [ ] Description that is too short → fail

## Acceptance criteria

- [ ] `pytest tests/scripts/test_validate_submission.py` passes offline, and `scripts/` coverage stays above its floor (#28)
- [ ] Running it against every active entry of the seed (as if each were newly submitted, with the duplicate check disabled) flags nothing unexpected

## References

- [`mvp-first.md` §7.2, §14 (IssueOps), §17 risk 3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`data-pipeline.md` §1.4, Appendix A6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/data-pipeline.md)
- [`dle-catalog.md` §1.4, §5.3, §5.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/dle-catalog.md)
