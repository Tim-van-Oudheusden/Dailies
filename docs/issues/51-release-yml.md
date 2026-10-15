---
key: 51
title: ci(release): release.yml — verify, build x86_64 + aarch64 bundles, publish GitHub Release
type: Task
labels: milestone::M1, type::task, priority::high, ci, flatpak
parent: 3
blocked_by: 12, 25, 27
---
> **Risk tier:** high · **Size:** M · **Brief:** "Releases set up so Flatpaks can be downloaded (or install instructions given) until a remote is configured later."

## Trigger

Per #12. Default: `on: push: tags: ['v*']`. Pre-release tags such as `v0.2.0-beta.1` set `prerelease: true`.

## Jobs (`.github/workflows/release.yml`, from [`flatpak-release-pipeline.md` Appendix A.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md))

1. **`verify`** (ubuntu-latest): assert that the tag without its `v` == `version:` in `meson.build` == the newest `<release version>` in the metainfo, and that the release `date` is not in the future. Fail with a clear message otherwise
2. **`build`**: matrix of `x86_64` on `ubuntu-latest` and `aarch64` on **`ubuntu-24.04-arm`** (free native runner for public repos; there is no `ubuntu-latest-arm`), in container `ghcr.io/flathub-infra/flatpak-github-actions:gnome-51` with `--privileged`:
   - `flatpak-builder-lint manifest build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json`, with **no exceptions** for the release ID
   - `flatpak/flatpak-github-actions/flatpak-builder@v6.8` with the **release** manifest, `arch: ${{ matrix.arch }}`, `bundle: Dailies-${{ matrix.arch }}.flatpak`
   - `flatpak-builder-lint repo repo`
   - Upload the bundle artifact
3. **`publish`** (`permissions: contents: write`): download both bundles, write `SHA256SUMS`, extract the newest release notes from the metainfo (Cartridges' regex, [`flatpak-release-pipeline.md` Appendix C.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)), and publish with `softprops/action-gh-release@efb35369… # v3.0.3` (full SHA in Appendix A.2) using `generate_release_notes: true`
   - Assets: `Dailies-x86_64.flatpak`, `Dailies-aarch64.flatpak`, `SHA256SUMS`

### Release body (prepended to the generated notes)

```sh
# Prerequisite: the Flathub remote, for the GNOME 51 runtime
flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user ./Dailies-x86_64.flatpak     # or Dailies-aarch64.flatpak
```

Add the note: "Bundles do not update themselves. Watch this repository's Releases for new versions."

## Also

- [ ] Before merging this, update the release manifest's `git` source to the real `tag` + `commit` as part of the release PR. Document this in `CONTRIBUTING.md` §Releasing (#22)
- [ ] `.github/release.yml`: auto-notes categories "Games / catalogue" (label `data`), "Features" (`type::feature`), "Fixes" (`type::bug`), and "Other" ([`flatpak-release-pipeline.md` Appendix A.7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md))
- [ ] The workflow passes `tests/tooling/test_workflows.py` (#33)

## Acceptance criteria

- [ ] A pre-release tag on a scratch fork (e.g. `v0.0.1-test.1`) produces a pre-release with both bundles and `SHA256SUMS`, and `sha256sum -c SHA256SUMS` passes
- [ ] Installing the downloaded x86_64 bundle on a clean user installation works with only the Flathub remote added
- [ ] A tag that doesn't match `meson.build` fails `verify` and publishes nothing

## References

- [`mvp-first.md` §10, §11 (release row)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`flatpak-release-pipeline.md` §1.5, §2, §7, §9, Appendix A.2, A.7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
