---
key: 31
title: ci: supply chain and nightly compliance (Dependabot, actionlint, pinned script deps, ACMM self-check)
type: Task
labels: milestone::M0, type::task, priority::medium, ci
parent: 2
blocked_by: 20
---
> **Risk tier:** high · **Size:** M · **ACMM:** `nightly-compliance`

## Why

Some things go stale without any code change: action versions, CVEs in script dependencies, the GNOME runtime reaching EOL (49 was about to be EOL'd when this was planned; branch N dies when N+2 ships, roughly yearly), and Hive renaming an ACMM path. The nightly job turns each of these into a red row instead of a surprise.

## Tasks

### Dependencies
- [ ] `.github/dependabot.yml` (MU, [`flatpak-release-pipeline.md` Appendix A.6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)): `github-actions` weekly with commit prefix `ci`, grouped minor+patch; `pip` for `/scripts` (`requirements.txt`) weekly with prefix `build(deps)`
- [ ] `scripts/requirements.txt`: the dependencies used **only by CI scripts**, pinned **with hashes** (`--require-hashes`): `check-jsonschema`, `requests`, `tldextract`. Add `Pillow` only when icons arrive (#77). Generate with `pip-compile --generate-hashes`. The app itself has **no** pip dependencies
- [ ] `.github/actionlint.yaml` (MU)

### Nightly compliance
- [ ] `.github/workflows/nightly-compliance.yml`: daily **03:23 UTC** + `workflow_dispatch`; runs `scripts/nightly-compliance.sh`, which prints a Markdown report to the job summary and exits non-zero if any row fails
- [ ] `scripts/nightly-compliance.sh` rows:
  1. Dependabot alerts with severity ≥ high (`gh api repos/{owner}/{repo}/dependabot/alerts`)
  2. `pip-audit -r scripts/requirements.txt`
  3. GNOME runtime EOL: `flatpak remote-info flathub org.gnome.Platform//51` contains no `end-of-life` string. Run inside the `gnome-51` container, or install flatpak on the runner
  4. `python3 scripts/acmm-self-check.py`
  5. *(Added by #60:)* weekly link check on Sundays
- [ ] `scripts/acmm-self-check.py`: a port of the evaluator in [`hive-acmm.md` §9 "Self-check in CI"](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md). It vendors the criteria list from `hivecommons/hive` `src/pkg/dashboard/acmm_criteria.go` (50 entries; the code comment says 43) **with the source commit hash in a header comment**, applies the scoring rules (any listed path exists → pass; a level passes at ≥ 70 %; Codebase Level = highest consecutive level from L0) and fails if the repo scores below **L5**. Add a unit test in `tests/scripts/` with a fake tree

## Acceptance criteria

- [ ] A manual dispatch of `nightly-compliance.yml` is green and its summary lists every row
- [ ] Deleting `docs/reflections/README.md` in a scratch branch makes the ACMM row fail and name the criterion
- [ ] `pip install --require-hashes -r scripts/requirements.txt` succeeds
- [ ] Dependabot opens its first update PR (or shows "up to date") after merge

## References

- [`mvp-first.md` §2 tree (`dependabot.yml`, `requirements.txt`, `acmm-self-check.py`), §11 (nightly-compliance row), §14 (Supply chain), §17 risk 5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`hive-acmm.md` §4, §4.1, §9 Phase 3, Appendix A.6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
- [`flatpak-release-pipeline.md` §5, §8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
