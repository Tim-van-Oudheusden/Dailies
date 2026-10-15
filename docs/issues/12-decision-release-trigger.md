---
key: 12
title: Decision: release trigger (tag push vs version-file push to main)
type: Task
labels: decision, milestone::M1, priority::high, ci
parent: 3
---
## Question

What starts a release?

| Option | How | For | Against |
|---|---|---|---|
| **Tag push (proposed)** | Bump `project(..., version:)` in `meson.build` and add a `<release>` to the metainfo in one PR, merge, then push tag `vX.Y.Z`; `release.yml` runs on `push: tags: ['v*']` | A Flatpak release needs the metainfo release entry and the tag to exist together; `v*` tags are what `x-checker-data` (`tag-pattern: ^v([\\d.]+)$`) and the later Flathub manifest consume; Bazaar and Cartridges convention | One extra manual step (pushing the tag) |
| MinimalUI convention | `push: branches: [main] paths: ['meson.build']`; `scripts/release-version.sh` reads the version, creates the tag and release | Same as the owner's other repos; fully automatic | A version bump that forgets the metainfo entry still releases; the tag is created by the bot |

## Proposed default

**Tag push.** `release.yml`'s `verify` job still asserts that tag == Meson version == newest metainfo `<release>` and that the date isn't in the future, so the two cannot drift.

## How to close

Comment and close. #51 implements the chosen trigger.

## References

- [`mvp-first.md` §10, §18.10](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`flatpak-release-pipeline.md` §7, Appendix A.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
- [`scaffolding-repos.md` §8.6](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/scaffolding-repos.md) (the MinimalUI variant)
