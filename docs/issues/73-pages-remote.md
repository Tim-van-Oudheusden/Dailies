---
key: 73
title: ci(flatpak): fallback GPG-signed OSTree remote on GitHub Pages + .flatpakref
type: Task
labels: milestone::M4, type::task, priority::medium, ci, flatpak
parent: 6
blocked_by: 71
---
> **Risk tier:** high · **Size:** M · **When:** Flathub rejects Dailies (#72), **or** a third release exists and users ask for automatic updates

## Why

Release bundles don't self-update. A self-hosted, signed OSTree repository on GitHub Pages gives users `flatpak update` without Flathub.

## Approach (pick one; record the choice in `docs/architecture.md`)

| Option | For | Against |
|---|---|---|
| Hand-rolled `pages-repo.yml` ([`flatpak-release-pipeline.md` Appendix A.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)) | No third-party action; rebuilds from scratch (one commit per ref, `--prune`, `--generate-static-deltas`) | The `ostree pull-local` merge of both arches was **untested** in the research **[U]** |
| `andyholmes/flatter` v1.0.0 (Appendix A.4) | Incremental, less YAML, generates `index.flatpakrepo` | Needs `max-parallel: 1`; it is **[U]** whether it runs inside the `gnome-51` image |

## Tasks

- [ ] Generate a dedicated GPG signing key (not the owner's personal key). Store the private key and passphrase as repository secrets, and import them with `crazy-max/ghaction-import-gpg@… # v7.0.0` (pin the SHA)
- [ ] Build both arches with `flatpak-builder --gpg-sign`, merge them into one repo, then `flatpak build-update-repo --gpg-sign --generate-static-deltas --prune`
- [ ] Publish to Pages under `/repo/` **next to** the existing `/v1/` data (#56). Both workflows deploy to the same Pages site, so merge the artifact assembly into one deploy job, or the second deploy overwrites the first
- [ ] Emit `dailies.flatpakrepo` (`Url=https://tim-van-oudheusden.github.io/Dailies/repo/`, base64 `GPGKey=`) and `io.github.tim_van_oudheusden.Dailies.flatpakref` (`RuntimeRepo=https://dl.flathub.org/repo/flathub.flatpakrepo`). Attach the `.flatpakref` to each GitHub Release (extend #51)
- [ ] Budget: GitHub Pages has a 1 GB site limit, 100 GB/month soft bandwidth and a 10-minute deploy limit; the repo is expected to stay under 50 MB
- [ ] README install section gains: `flatpak install --user https://tim-van-oudheusden.github.io/Dailies/io.github.tim_van_oudheusden.Dailies.flatpakref`

## Acceptance criteria

- [ ] On a clean machine, `flatpak install --user <flatpakref URL>` installs Dailies, and after the next release `flatpak update` upgrades it
- [ ] Signature verification is on (no `--no-gpg-verify` anywhere)
- [ ] `/v1/games.json` is still served after a repo deploy

## References

- [`mvp-first.md` §10 (Pages remote), §16 (M4)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`flatpak-release-pipeline.md` §3, §9 item 6, Appendix A.3, A.4, C.5–C.7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
