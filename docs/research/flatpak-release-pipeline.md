# Flatpak build/release pipeline for Dailies (research report)

Research key: `flatpak-release-pipeline`
Date of research: 2026-10-15
Target project: github.com/Tim-van-Oudheusden/Dailies (GTK4/Libadwaita, GPL-3.0, GitHub-hosted)

Legend used throughout: **[V]** = verified against a primary source (URL or cloned file given); **[I]** = inference / recommendation derived from verified facts; **[U]** = could not be verified.

---

## 0. Executive summary

1. **Action to use:** `flatpak/flatpak-github-actions/flatpak-builder@v6.8` (released 2026-08-30, commit `79327416609af08178ad73b352877e51450790b3`) together with the Flathub-provided container image `ghcr.io/flathub-infra/flatpak-github-actions:gnome-51`. The `flathub-infra/flatpak-github-actions` *action* fork is deprecated (issue #17); only the **images** live under `flathub-infra` now (repo `flathub-infra/actions-images`). Cartridges' CI (`bilelmoussaoui/flatpak-github-actions:gnome-47` + `flatpak/flatpak-github-actions/flatpak-builder@v6.5`) is outdated; Bazaar's CI (`ghcr.io/flathub-infra/flatpak-github-actions:gnome-50` + `@v6.7` native arm runner matrix) is the better template. [V]
2. **Architectures:** build natively on `ubuntu-latest` (x86_64) and `ubuntu-24.04-arm` / `ubuntu-26.04-arm` (aarch64). GitHub-hosted arm64 runners are free for public repos; there is **no** `ubuntu-latest-arm` label. QEMU emulation is still documented but no longer needed. [V]
3. **App ID:** `io.github.tim_van_oudheusden.Dailies`. Flathub rule: dashes in the domain part become underscores; the linter demangles `_` back to `-` and lowercases to reach `github.com/tim-van-oudheusden/dailies`. Dev builds: `io.github.tim_van_oudheusden.Dailies.Devel`. [V]
4. **Runtime:** target `org.gnome.Platform//51` (GNOME 51 released 2026-09-16; `gnome-51` CI image exists; Flathub requires the latest runtime at submission). GNOME 48 was EOL'd 2026-03-24, six days after GNOME 50 shipped; GNOME 46 was EOL'd 2025-04-17, four weeks after GNOME 48 shipped. Pattern [I]: branch N is EOL'd within weeks of N+2 shipping, i.e. ~1 year of support. GNOME 49 is not flagged EOL as of 2026-10-15 (checked with `flatpak remote-info`), but expect it any day. [V]/[I]
5. **Releases:** build `.flatpak` bundles for both arches on `v*` tags and attach them with `softprops/action-gh-release@v3.0.3` or `gh release create`. Users install with `flatpak install --user ./Dailies-x86_64.flatpak`; the bundle carries `--runtime-repo=https://flathub.org/repo/flathub.flatpakrepo`, so Flatpak offers to add Flathub for the runtime. Bundles do **not** auto-update. [V]
6. **Self-hosted remote on GitHub Pages:** feasible and documented in the official Flatpak docs (GitLab Pages variant) and by `andyholmes/flatter` (GitHub Pages action, v1.0.0, 2026-03-11). Limits: 1 GB site, 100 GB/month soft bandwidth, 10-minute deploy timeout. Sign with GPG, run `flatpak build-update-repo --generate-static-deltas --prune`, publish `dailies.flatpakrepo` + `io.github.tim_van_oudheusden.Dailies.flatpakref`. [V]
7. **Flathub submission** is the long-term goal, but note two policy risks for Dailies specifically: Flathub rejects "thin wrappers or launchers" and "simple web wrapper applications ... without significant polish, functionality, or meaningful desktop integration", and it requires "a meaningful history, real-world use, and ongoing maintenance" and tagged releases. Also, Flathub's Generative-AI policy says "Flathub manifests must not contain AI-generated or AI-assisted content" and AI tools must not open submission PRs. [V]
8. **Dependency automation:** `flatpak-external-data-checker` (Docker image `ghcr.io/flathub/flatpak-external-data-checker:latest`, weekly cron) for manifest modules; Dependabot `github-actions` ecosystem for workflow pins. Neither Dependabot nor Renovate has a Flatpak manifest manager. [V]

---

## 1. flatpak-github-actions (build on push/PR, bundle artifact, multi-arch, caching)

### 1.1 Which repository/version

| Item | Fact | Status |
|---|---|---|
| Canonical action repo | `flatpak/flatpak-github-actions` | [V] README + issue |
| Latest release | `v6.8`, published 2026-08-30 (`v6.7` 2026-04-06, `v6.6` 2025-10-19) | [V] `gh release list` |
| Commit for `v6.8` | `79327416609af08178ad73b352877e51450790b3` | [V] `gh api git/ref/tags` |
| Node runtime | `node24` (fork is still `node20`) | [V] `action.yml` diff |
| Fork status | `flathub-infra/flatpak-github-actions` README: "This fork is deprecated. Please see this issue." Issue #17 (still OPEN): "This repository will only provide the images ... while the action will be provided by `flatpak/flatpak-github-actions`... The `image` should still point to `ghcr.io/flathub-infra/flatpak-github-actions` namespace." | [V] |
| Images repo | `flathub-infra/actions-images`, built Mon+Fri 02:00 UTC (`cron: "0 2 * * 1,5"`) for `linux/amd64,linux/arm64`; base image is `FROM ghcr.io/flathub/flatpak-builder-lint:latest` with `flathub`, `flathub-beta`, `gnome-nightly` remotes pre-added | [V] `Dockerfile`, `.github/workflows/docker.yml` |
| Available image tags (2026-10-15) | `freedesktop-24.08`, `freedesktop-25.08`, `freedesktop-26.08`, `gnome-49`, `gnome-50`, `gnome-51`, `kde-5.15-25.08`, `kde-6.9`, `kde-6.10`, `kde-6.11` | [V] `actions-images/README.md` |

Because the image is built on top of `ghcr.io/flathub/flatpak-builder-lint`, **`flatpak-builder-lint` is on `PATH` (`/app/bin`) inside the CI container** — no extra install step is needed to lint in CI. [V] (`flatpak-builder-lint/docker/Dockerfile`: `ENV PATH="/app/bin:$PATH"`, `ENTRYPOINT ["/app/bin/flatpak-builder-lint"]`; `actions-images/Dockerfile` resets `ENTRYPOINT []`.) The lint tool "tracks the git commit currently used on the Flathub infrastructure" (its latest commit at research time: `c9c8b75`, 2026-10-15). [V]

### 1.2 Inputs of `flatpak-builder` (v6.8) [V — `flatpak-builder/action.yml` + README]

| Input | Default | Notes |
|---|---|---|
| `manifest-path` | (required) | relative path |
| `stop-at-module` | – | disables bundle generation |
| `bundle` | `app.flatpak` | output file name |
| `build-bundle` | `true` | |
| `build-debug-bundle` | `false` | produces `<bundle>-debug.flatpak` of `<id>.Debug` (new in upstream, absent in fork) |
| `repository-name` / `repository-url` | `flathub` / `https://flathub.org/repo/flathub.flatpakrepo` | used for `--install-deps-from` and bundle `--runtime-repo` |
| `run-tests` | `false` | rewrites manifest to add network + X11; runs under `xvfb-run` |
| `branch` | `master` | `--default-branch` |
| `cache` / `restore-cache` / `save-cache` | `true` | caches `.flatpak-builder` via `@actions/cache`; `--ccache` is added only when `cache` is on |
| `cache-key` | `flatpak-builder-${arch}-${sha256(manifestPath)}` | arch is appended automatically |
| `arch` | `x86_64` | |
| `mirror-screenshots-url` | – | passes `--mirror-screenshots-url` |
| `gpg-sign` | – | passes `--gpg-sign=KEY` to flatpak-builder |
| `build-dir` / `repo-dir` / `state-dir` | `flatpak_app` / `repo` / `.flatpak-builder` | "must be under the same partition" |
| `keep-build-dirs` | `false` | |
| `verbose` | `false` | |
| `upload-artifact` | `true` | |
| `artifact-name` | `app-${arch}.flatpak`-style (bundle name tagged with arch) | |

What the action actually runs [V — `flatpak-builder/index.js`]:

```
xvfb-run --auto-servernum flatpak-builder <build-dir> <manifest> \
  --repo=<repo-dir> --disable-rofiles-fuse --install-deps-from=<repository-name> \
  --force-clean --default-branch=<branch> [--ccache] [--mirror-screenshots-url=..] [--gpg-sign=..]
flatpak build-bundle <repo-dir> <bundle> --runtime-repo=<repository-url> --arch=<arch> <app-id> <branch>
```

So after the step, the job workspace contains the OSTree repo at `repo/` (usable for `flatpak-builder-lint repo repo` and for `build-update-repo`) and the bundle file. [V]

### 1.3 Reference workflows seen in the wild

- **Bazaar** `.github/workflows/build-flatpak.yml` (cloned 2026-08-18 HEAD) — `permissions: {}`, image `gnome-50`, matrix `{x86_64: ubuntu-latest, aarch64: ubuntu-24.04-arm}` with the comment "no latest for ARM :(", manual `actions/cache/restore` + `actions/cache/save` around the action with `cache: true, restore-cache: false` and the comment "caching is broken upstream https://github.com/flatpak/flatpak-github-actions/issues/239 — this is only true because there is no other way to call fb with --ccache". I did not verify issue #239 itself [U]; the workaround pattern is reproduced in Appendix A.
- **Cartridges** `.github/workflows/ci.yml` — single x86_64 job, outdated image (`bilelmoussaoui/flatpak-github-actions:gnome-47`, Docker Hub) and `@v6.5`; `publish-release.yml` on `tags: "*"` downloads the CI artifacts with `dawidd6/action-download-artifact@v9`, extracts the latest `<release>` description from `data/page.kramo.Cartridges.metainfo.xml.in` with a Python regex and publishes with `softprops/action-gh-release@v2.2.2` (`body_path: release_notes`, `fail_on_unmatched_files: true`). Note Cartridges only ships Windows/macOS binaries on GitHub Releases, not the Flatpak (Flathub is the Linux channel). Cartridges README now says the project is no longer actively maintained. [V]

### 1.4 Caching

- Built in: `.flatpak-builder` state dir cached under `flatpak-builder-${arch}-${sha256(manifest)}` (or your `cache-key` + `-${arch}`), restore-keys fall back to `flatpak-builder-${arch}`. [V]
- `--ccache` only when `cache: true`. [V]
- Bazaar's explicit restore/save dance exists because of a reported upstream issue; for a Python/Blueprint app (little compilation) the built-in cache is adequate [I].

### 1.5 Runners [V — docs.github.com "GitHub-hosted runners"]

Public repos, free and unlimited: `ubuntu-latest` (= 24.04 x64), `ubuntu-24.04`, `ubuntu-22.04`, `ubuntu-26.04` (4 vCPU/16 GB/14 GB SSD); arm64: `ubuntu-24.04-arm`, `ubuntu-22.04-arm`, `ubuntu-26.04-arm` (same size); `ubuntu-slim` (1 vCPU, x64 only, 15-minute job timeout — not suitable for flatpak-builder). The flatpak-github-actions README also still documents QEMU (`docker/setup-qemu-action`, latest `v4.4.0`), which installs static Docker binaries into the container — slower and unnecessary now. [V]

---

## 2. Publishing `.flatpak` bundles to GitHub Releases

### 2.1 Tools and versions [V]

- `softprops/action-gh-release` latest `v3.0.3` (2026-08-30), commit `efb35369e0ad2afab669f228072c1b0d510eae64`. Inputs used by Cartridges: `files`, `fail_on_unmatched_files`, `tag_name`, `body_path`.
- `gh release create [<tag>] [<files>...]` flags: `--notes-file/-F`, `--notes`, `--generate-notes`, `--notes-start-tag`, `--notes-from-tag`, `--prerelease`, `--draft`, `--latest`, `--verify-tag`, `--target`, `--fail-on-no-commits`. "If a matching git tag does not yet exist, one will automatically get created from the latest state of the default branch." Immutable-releases note: "Git tags associated with a release cannot be modified or deleted. Release assets cannot be modified or deleted" once published. [V — `gh release create --help`]
- `actions/download-artifact` latest `v8.0.2`, `actions/upload-artifact` `v7.0.2`, `actions/checkout` `v7.0.1`. [V]
- `.github/release.yml` controls GitHub's auto-generated notes (`changelog.categories[].title/labels`, `changelog.exclude.labels/authors`, `"*"` catch-all). [V — docs.github.com]

### 2.2 Install instructions and prerequisites [V]

- Create: `flatpak build-bundle repo Dailies.flatpak io.github.tim_van_oudheusden.Dailies --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo` (the action does this for you with `--arch` too).
- Install: `flatpak install --user ./Dailies-x86_64.flatpak` (docs show `flatpak install dictionary.flatpak`; `--user` avoids polkit). The bundle is "an OSTree static delta against an empty base, plus Flatpak-specific metadata for application icons and AppData".
- Prerequisite: the GNOME 51 runtime. Bundles "don't include dependencies or AppStream data"; `--runtime-repo` is "the URL of a .flatpakrepo file describing the repository that supplies the app's required runtimes", so Flatpak offers to add Flathub if missing. Document `flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo` as the explicit step.
- Updates: a bundle configures an update remote only if built with `--repo-url=URL` ("Installing the bundle configures a remote for this URL"). Without it, users must download the next bundle manually. If the GitHub Pages repo (section 3) exists, pass `--repo-url=https://tim-van-oudheusden.github.io/Dailies/repo` via flatter's `flatpak-build-bundle-args` or by running `flatpak build-bundle` yourself; the stock action does not expose `--repo-url` [V — index.js].
- Architecture: a bundle is arch-specific; name assets `Dailies-x86_64.flatpak` and `Dailies-aarch64.flatpak` [I].

---

## 3. Self-managed Flatpak remote (OSTree repo) on GitHub Pages

### 3.1 Primary sources [V]

- Flatpak docs "Hosting a repository" (`docs/hosting-a-repository.rst` in `flatpak/flatpak-docs`, cloned): archive-z2 ⇒ one HTTP request per file, enable keep-alive; static deltas via `flatpak build-update-repo --generate-static-deltas`; `.flatpakrepo` and `.flatpakref` formats; GPG commands; a complete GitLab Pages `.gitlab-ci.yml` (single and multi-arch) using image `ghcr.io/flathub-infra/flatpak-github-actions:freedesktop-25.08` and:
  ```
  flatpak-builder build --user --install-deps-from=flathub --gpg-sign=${GPG_KEY_ID} --disable-rofiles-fuse --disable-updates --force-clean --repo=repo ${BRANCH:+--default-branch=$BRANCH} ${MANIFEST_PATH}
  flatpak build-bundle --gpg-sign=${GPG_KEY_ID} repo ${BUNDLE} --runtime-repo=${RUNTIME_REPO} ${APP_ID} ${BRANCH}
  flatpak build-update-repo --gpg-sign=${GPG_KEY_ID} --generate-static-deltas --prune repo/
  ```
  Multi-arch: the x86_64 and aarch64 jobs are chained so both land in the same `repo/` before one `build-update-repo` run ("The repo folder must have contents for both arches present"). Install: `flatpak install --user https://.../app_name.flatpakref` — "This will set up a flatpak remote userwide, install the dependencies and the application. Updates will be fetched when running flatpak update".
- `flatpak build-update-repo` options: `--title`, `--comment`, `--description`, `--homepage`, `--icon`, `--default-branch`, `--redirect-url`, `--gpg-sign=KEYID`, `--gpg-homedir`, `--gpg-import=FILE`, `--collection-id`, `--deploy-collection-id`, `--generate-static-deltas`, `--static-delta-jobs`, `--static-delta-ignore-ref`, `--prune`, `--prune-depth=N` (default -1 keeps all). [V — man page]
- GitHub Pages limits: published site ≤ 1 GB; soft 100 GB/month bandwidth; soft 10 builds/hour (not applicable with a custom Actions workflow); 10-minute deployment timeout. `actions/upload-pages-artifact` README: artifact must be a single gzip'd tar, ≤ 10 GB hard (unofficial), recommended < 1 GB, **no symlinks/hardlinks**. [V]
- `andyholmes/flatter` (v1.0.0 2026-03-11, commit `b32437fdafdca87317165f558dbcba78ebb20e1e`): "intended for nightly or development builds for a small project"; generates `index.flatpakrepo` when `upload-pages-artifact: true`; uses `CNAME` file for `Url` else `https://<user>.github.io/<repo>`; built-in repo cache for incremental updates; multi-arch requires `max-parallel: 1` (shared repo cache); GPG via `crazy-max/ghaction-import-gpg` (latest `v7.0.0`); caution: "Projects hosted on Github pages may have download speeds throttled if too many users are subscribed". Its own images are `ghcr.io/andyholmes/flatter/gnome:{48,49,master}` — no `51` yet, but the Flathub `gnome-51` image can be used since flatter only needs `flatpak`/`flatpak-builder` in the container [I]. [V]
- Other projects doing this (search results, not deeply verified): `rmonk/hey-whisper` PR #4 (restores old repo from `gh-pages` before `build-update-repo`, unsigned ⇒ `--no-gpg-verify`), `moosingin3space/guest-info-display` PR #36, `aetherpak/actions` (serves OCI layers from GHCR and only an index from Pages). Alex Larsson's 2017 blog post "Maintaining a flatpak repository" is the origin of the pattern. [V that they exist; contents skimmed only]

### 3.2 OSTree objects and GitHub Pages — practical constraints [I from V facts]

- An OSTree archive-z2 repo has thousands of small files under `objects/`; `.nojekyll` is needed only for the `gh-pages`-branch publishing mode (Jekyll ignores `_`-prefixed paths); with the Actions publishing mode (`actions/deploy-pages`) there is no Jekyll step. Pages serves with HTTP/2 keep-alive, fine for ostree.
- Two update strategies: (a) **rebuild from scratch each release** (the Flatpak docs' GitLab template does this; `--prune` keeps the repo at one commit per ref; clients without a static delta simply fetch objects — correct, just slower), or (b) **incremental** (flatter's cache, or restore the previous `repo/` from Pages/`gh-pages`), which lets `--generate-static-deltas` create from→to deltas and keeps `--prune-depth=N` history. (a) is simplest and size-bounded (one GTK/Python app ≈ a few MB per arch, well under 1 GB).
- `flatpak-builder --repo=repo` *exports* into `repo/` (equivalent to `flatpak build-export`); `flatpak build-export` is only needed if you build without `--repo`. Bazaar's Justfile shows the manual pair: `flatpak build-export repo build-dir` then `flatpak build-bundle repo id.flatpak id`. [V]
- GPG: generate a dedicated key (`gpg --quick-gen-key dailies@tim-van-oudheusden.github.io` or with `--homedir`), store `GPG_PRIVATE_KEY` (ASCII-armored, `gpg --armor --export-secret-key`) and `GPG_PASSPHRASE` as repository secrets; public key goes base64-encoded (`base64 --wrap=0 < key.gpg`) into `GPGKey=` of both `.flatpakrepo` and `.flatpakref`. Skip signing on PRs from forks (`if: github.triggering_actor == github.repository_owner`). [V]

---

## 4. Flathub submission requirements and process

### 4.1 Application ID [V — docs.flathub.org/docs/for-app-authors/requirements + linter source]

- 3–5 components, ≤ 255 chars; components contain only letters, digits, underscores; "A dash is allowed only in the last component"; "The domain portion must be lowercase. Dashes become underscores, and a component with an initial digit gets a leading underscore"; must not end in `.desktop`, `.app`, `.linux`; must equal the MetaInfo `<id>` and the manifest filename (`appid-filename-mismatch`).
- Code-hosting prefixes: GitHub ⇒ `io.github.` (needs ≥ 4 components; `com.github.` is reserved for GitHub's own projects); example given: "`io.github.example_foo.bar` maps to `https://github.com/example-foo/bar`".
- Linter (`flatpak_builder_lint/domainutils.py`): `demangle()` strips a leading `_` before a digit and does `name.replace("_", "-")`, then builds `github.com/{user}/{repo}`.lower() and checks it is reachable (`appid-url-not-reachable` otherwise). `checks/appid.py` requires `io` TLD for `github` (`appid-uses-code-hosting-domain`) and ≥ 4 components (`appid-code-hosting-too-few-components`).
- Real Flathub examples with hyphenated GitHub owners: `io.github.nate_xyz.Resonance` (github.com/nate-xyz), `io.github.celluloid_player.Celluloid`, `io.github.pwr_solaar.solaar`, `io.github.zen_browser.zen`, `io.github.diegoivan.pdf_metadata_editor` (hyphenated *repo* name also underscored). Last component may keep a dash: `io.github.doukutsu_rs.doukutsu-rs`, `io.github.torrent_file_editor.Torrent-file-editor`. [V — `gh search repos --owner flathub`]
- **Therefore for Tim-van-Oudheusden/Dailies: `io.github.tim_van_oudheusden.Dailies`** (lowercase user component; the linter lowercases the URL so `Dailies` casing in the last component is fine — compare `io.github.nate_xyz.Resonance`). Dev ID `io.github.tim_van_oudheusden.Dailies.Devel` (5 components — the maximum for apps). [V]
- Verification: "For GitHub, the authenticated account must be the owner of the repository" — log in to flathub.org with the `Tim-van-Oudheusden` GitHub account, Developer Portal → app → Verification. [V]
- Flathub repo for the app will be `github.com/flathub/io.github.tim_van_oudheusden.Dailies` after acceptance (pattern of all examples above). [I]

### 4.2 Inclusion policy items relevant to Dailies [V — requirements page]

- Rejected: "Minimal submissions: simple scripts, thin wrappers or launchers, or single simple sources"; "Simple web wrapper applications that embed local or remote content in a web engine without providing significant polish, functionality, or meaningful desktop integration will not be accepted"; "Insufficient development history: a meaningful history, real-world use, and ongoing maintenance are needed ... tagged versions"; "Nightly releases, development snapshots, or any software requiring daily updates must not be published to either repo".
- Generative AI: "AI-generated code, documentation, or packaging must be disclosed. Flathub manifests must not contain AI-generated or AI-assisted content. AI tools must not open or automate submission PRs or write their descriptions, commits, or reviews." Linter exceptions page adds that LLM use in exception PRs "can result in a permanent denial".
- Permissions: "Static permissions must be kept to an absolute minimum", portals mandatory where they cover the use case. `--share=network` is normal and not linted; WebKitGTK needs no extra permission. Linter never-granted errors include `finish-args-arbitrary-dbus-access` (`--socket=session-bus`), `finish-args-unnecessary-appid-own-name`, `finish-args-portal-talk-name`, `finish-args-absolute-home-path`, `finish-args-x11-without-ipc`; `finish-args-flatpak-spawn-access` (`--talk-name=org.freedesktop.Flatpak`) only "with sufficient explanation". Dailies needs none of these. [V]
- WebKitGTK availability: `gnome-build-meta/elements/sdk/webkitgtk.bst` builds `webkitgtk-2.54.1` with `-DPORT=GTK -DUSE_GTK4=ON`, splitting `libwebkitgtk-6.0.so` / `libjavascriptcoregtk-6.0.so`, i.e. the GTK4 API `webkitgtk-6.0` ships in `org.gnome.Platform` — no module to build. [V file; "in Platform not only Sdk" is [I] from the devel split rules]
- Build: no network during build; all sources via public URLs or files in the PR; dependency manifests generated with `flatpak-builder-tools` (e.g. `flatpak-pip-generator` for Python deps, which is what Cartridges' `python3-*` modules look like). [V]
- Required files in the submission PR: manifest at top level named `<id>.json|.yml|.yaml`; `flathub.json` only if single-arch (or for `end-of-life`, `require-important-update`, `automerge-flathubbot-prs`, `disable-external-data-checker`, `only-arches`/`skip-arches`). Style: JSON 4-space? — the page says "4-tab indentation" for JSON, 2-space for YAML, LF, trailing newline. [V]
- Runtimes "must be hosted on Flathub and be the latest version at submission". [V]

### 4.3 MetaInfo requirements [V — metainfo-guidelines + quality-guidelines]

- Path `/app/share/metainfo/<id>.metainfo.xml` (`.appdata.xml` deprecated). Validate with `flatpak run --command=flatpak-builder-lint org.flatpak.Builder appstream <file>` (wraps `appstreamcli validate` with Flathub overrides); warnings count as failures.
- Required: `<id>` = Flatpak ID; `<metadata_license>` (CC0-1.0 / FSFAP); `<project_license>` SPDX (`GPL-3.0-or-later`); `<name>`; `<summary>`; `<developer id="io.github.tim_van_oudheusden"><name translate="no">…</name></developer>` (exactly one untranslated name); `<launchable type="desktop-id">io.github.tim_van_oudheusden.Dailies.desktop</launchable>`; `<description>` with at least one non-empty `p`/`ul`/`ol` (only `p ol ul li em code`); `<content_rating type="oars-1.1" />` generated at the OARS site; `<url type="homepage">` minimum, recommended `bugtracker`, `vcs-browser`, `donation`, `contact`, `translate`, `contribute`; `<branding>` with `<color type="primary" scheme_preference="light">` and `dark`; `<screenshots>` with one `type="default"` and `<caption>` — direct image links; "For git-hosted images, link to a tag or commit, not a branch" (linter: `appstream-external-screenshot-url` means Flathub mirrors them to `dl.flathub.org/media`; screenshots don't appear in test builds); `<releases>` required, each `<release version=".." date="YYYY-MM-DD">` with ordered versions (`appstreamcli vercmp`), no future dates, optional `<url type="details">` and `<description>`; `<translation type="gettext">dailies</translation>`; `<requires>/<recommends>/<supports>` with `control` (`keyboard`, `pointing`, `touch`) and `display_length` (desktop ⇒ `ge 768`; adaptive ⇒ `ge 360`). Categories/keywords come from the `.desktop` file (generic `GTK`, `GNOME` are filtered). `<custom><value key="flathub::manifest">` only for apps *not* hosted in the flathub org — not needed.
- Quality guidelines (optional but gate "featured" placement): name ≤ 15 chars ideally (< 20 hard); summary 10–25 chars (≤ 35), sentence case, no period, imperative, no "app/tool/client"; description 3–6 lines; 3–6 screenshots for a medium app, window with shadow, no wallpaper, ≤ 1000×700 (or 2000×1400 HiDPI), captions one sentence no period; icon SVG or ≥ 256×256 PNG, square, no baked shadows, follow GNOME icon guidelines; brand colors colorful, dark variant darker/more muted, contrast with icon; release notes for every release, user-facing, no "bug fixes and improvements".
- Bazaar's metainfo (Appendix C) is a good concrete template; it uses `<description translate="no">` inside releases and `<url type="details">` pointing at the GitHub release.

### 4.4 Submission flow [V — docs.flathub.org/docs/for-app-authors/submission]

1. Build locally with `org.flatpak.Builder`: `flatpak install -y flathub org.flatpak.Builder`; `flatpak run --command=flathub-build org.flatpak.Builder --install <manifest>`; run; lint `manifest` and `repo` (`flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest <manifest>` / `repo repo`).
2. Fork `flathub/flathub` with "Copy the master branch only" **unchecked**; `gh repo fork --clone flathub/flathub && cd flathub && git checkout --track origin/new-pr`; `git checkout -b dailies-submission new-pr`; add manifest (+ `flathub.json` if needed, + generated dependency manifests); push; PR against base **`new-pr`**, title "Add io.github.tim_van_oudheusden.Dailies".
3. Review by volunteers; `bot, build` comment triggers a test build (bundle link valid a few days; remove with `flatpak remove` on the `/test` ref). Screenshots are not shown in test builds.
4. On approval the submission is merged into a new repo in the flathub org (in batches); accept the write invitation within one week; 2FA required; official build publishes within 1–2 h; then verification and `flathub.json` maintenance; Flathub's own external-data-checker runs every 2 h on the default branch; EOL criterion: "persistently behind at least 3 runtime updates". [V]

### 4.5 Linter in CI [V]

- Subcommands: `appstream <metainfo>`, `manifest <manifest>`, `builddir <build-dir>`, `repo <repo>`; flags `--exceptions`, `--exceptions-repo`, `--user-exceptions <json>`, `--appid`, `--ref`, `--gha-format` (GitHub annotations), `--debug`. Local exceptions file format: `{"io.github.tim_van_oudheusden.Dailies.Devel": ["error-name"]}` — useful because the Devel ID is not on Flathub (expect e.g. `appstream-*`/`appid-url-*` noise for the Devel ID [I]).
- Ways to run: (a) inside the `ghcr.io/flathub-infra/flatpak-github-actions:*` container it is already on PATH; (b) `docker run -v $(pwd):/mnt ghcr.io/flathub/flatpak-builder-lint:latest repo /mnt/repo` on a plain runner (cannot nest inside the container job); (c) `flatpak run --command=flatpak-builder-lint org.flatpak.Builder …` locally. Note the README references both `ghcr.io/flathub/flatpak-builder-lint` and `ghcr.io/flathub-infra/flatpak-builder-lint` images.

---

## 5. GNOME runtime version to target

| Branch | Release date | Flathub status (2026-10-15) | Source |
|---|---|---|---|
| GNOME 48 | 2025-03-20 | EOL: "The GNOME 48 runtime is no longer supported as of March 24, 2026" | [V] `flatpak remote-info flathub org.gnome.Platform//48` |
| GNOME 49 | 2025-09-17 | no EOL flag yet; last build 49.10 on 2026-10-03 | [V] `remote-info` |
| GNOME 50 | 2026-03-18 | "old stable" upstream; builds 50.5 on 2026-10-03 | [V] release.gnome.org + remote-info |
| GNOME 51 | 2026-09-16 | current stable; 51.0 build on 2026-10-14; CI image `gnome-51` available | [V] |
| GNOME 52 | 2027-03-17 (tarballs 2027-03-13; 52.alpha 2027-01-09, beta 2027-01-30, rc 2027-02-27) | future | [V] release.gnome.org/calendar |

Policy text (docs.flathub.org/docs/for-app-authors/runtimes): GNOME "branch is usually supported for about one year and reaches EOL when a newer stable version is released"; Freedesktop SDK branches get 2 years, new major every August (25.08, 26.08 exist). Observed practice: 45 EOL 2024-09-18 (= GNOME 47 day), 46 EOL 2025-04-17 (28 days after 48), 48 EOL 2026-03-24 (6 days after 50). [V] ⇒ **Expect GNOME 49 EOL imminently and GNOME 51 EOL around GNOME 53 (Sept 2027).** [I] Point releases of 51 land 51.1 (2026-10-10), 51.2 (2026-11-21), 51.3 (2027-01-09), 51.4 (2027-01-30), 51.5 (2027-03-13). [V]

Recommendation: `runtime-version: "51"` now; bump every March/September within a few weeks of the GNOME release (Flathub nags via website "EOL runtime" banner, and EOL ≥3 behind risks delisting). Bazaar's Flathub manifest is already on `'51'`; Cartridges' is on `49`. [V]

---

## 6. Nightly / dev builds with `.Devel`

- GNOME developer docs: "Suffix the ID with `.Devel`, such as `org.gnome.TextEditor.Devel`, so it can be installed alongside the stable build." [V — developer.gnome.org application-id tutorial]
- Cartridges implementation [V — `meson_options.txt`, `meson.build`, `data/meson.build`, `build-aux/flatpak/page.kramo.Cartridges.Devel.json`]: `option('profile', type: 'combo', choices: ['release','development'], value: 'release')`; `meson.build` sets `app_id = 'page.kramo.Cartridges.Devel'` and `prefix = '/page/kramo/Cartridges/Devel'` for development; `.desktop.in`, `.metainfo.xml.in`, `.gschema.xml.in`, gresource and icons are `configure_file`'d with `@APP_ID@`; the CI manifest is named `<id>.Devel.json`, uses `"type": "dir", "path": "../.."` source, `"config-opts": ["-Dprofile=development"]`, `"run-tests": true`, and bundles as `page.kramo.Cartridges.Devel.flatpak`. The Flathub manifest (`flathub/page.kramo.Cartridges`) is the release ID with the same modules.
- Bazaar implementation [V]: `-Ddevelopment=true` meson option; manifest keys `"tags": ["nightly"]` and `"desktop-file-name-suffix": " (Nightly)"` (flatpak-builder manifest keys that tag the ref and rename the desktop entry without changing the app ID).
- Flathub: never submit the Devel/nightly ID ("Nightly releases, development snapshots ... must not be published to either repo"); GNOME Nightly (`nightly.gnome.org`) is for GNOME-hosted projects. Distribute Devel through CI artifacts, GitHub pre-releases, or your own Pages repo (flatter's stated use case). [V]
- Typical conventions [I]: Devel icon gets the "stripes" overlay (GNOME HIG dev-profile style); `.Devel` builds can use `--default-branch=devel` in the repo so stable and devel coexist in one remote.

---

## 7. Versioning, tagging, changelog, metainfo release notes

- GNOME core style [V — handbook.gnome.org "Making a release"]: version = GNOME major (`51.0`, `51.1`), pre-releases `51.alpha/beta/rc` written as `51~alpha` in AppStream; annotated/signed tags named exactly the version (`git tag -s 51.0`), message "GNOME Foo 51.0"; NEWS file for packagers; `<release>` entry in metainfo per release (dev snapshots may be omitted). GNOME Circle / third-party apps commonly use SemVer-ish: Cartridges `2.13.1` (tags `2.13.1`, no `v`), Bazaar `0.9.5` (tags `v0.9.4`, single `version.sh` as source of truth, `meson.build` reads `version.sh get-vcs` which appends `git describe` info, `<url type="details">https://github.com/bazaar-org/bazaar/releases/tag/v0.9.4</url>`). [V]
- AppStream tooling [V — appstreamcli(1)]: `appstreamcli news-to-metainfo [--format text|markdown|yaml] [--limit N] [--translatable-count N] NEWS_FILE MI_FILE [OUT_FILE]` (NEWS → `<releases>`), `appstreamcli metainfo-to-news MI_FILE NEWS_FILE` (reverse; `--format` required for stdout), `appstreamcli vercmp V1 [eq|ne|lt|gt|le|ge] V2` (exit non-zero on failed comparison), `appstreamcli validate [--pedantic] [--no-net] FILE`. Cartridges' meson test runs `appstreamcli validate --no-net --explain`. [V]
- `git-cliff-action` latest `v4.9.1` exists if a conventional-commits changelog is desired [V version only]. GitHub auto-generated notes via `.github/release.yml` + `gh release create --generate-notes`. [V]
- Flathub: `<release>` dates must not be in the future; versions must sort; linter `appstream-latest-release-is-prerelease` exists (pre-release tags like `~beta` as the latest entry are flagged — confirm behaviour before shipping betas [U]).

Recommendation [I]: SemVer `MAJOR.MINOR.PATCH` with tags `v1.2.3` (matches Bazaar and the owner's MinimalUI convention `v<versionName>`); single source of truth `project(version:)` in `meson.build`; metainfo `<release>` is the human changelog and the GitHub Release body is derived from it (Cartridges' regex or `appstreamcli metainfo-to-news --format markdown`), with `.github/release.yml` PR-category notes appended via `--generate-notes` for contributors' credit. CI guard: tag == meson version == newest `<release version>`, date ≤ today.

---

## 8. Dependency automation for the manifest and workflows

- `flatpak-external-data-checker` [V — README in `flathub-infra/flatpak-external-data-checker`]: image `ghcr.io/flathub/flatpak-external-data-checker:latest`; custom workflow runs `docker://ghcr.io/flathub/flatpak-external-data-checker:latest` with `args: --update --never-fork <manifest>`, `GITHUB_TOKEN`, author `41898282+github-actions[bot]@users.noreply.github.com`; options `--require-important-update` (+ `"is-important": true` / `is-main-source` in `x-checker-data`); checkers: `rotating-url`, `html`, `git` (`tag-pattern`, `version-scheme: semantic`, `versions` constraints), `json` (jq `version-query`, `url-query`, `tag-query`, `timestamp-query`), `anitya` (`project-id`, `url-template`/`tag-template`, `stable-only`), `pypi` (`name`, `versions` — seen in Bazaar's manifest), `debian-repo`, `gnome`; the main source with `is-main-source` also gets its version appended to `<releases>`. Flathub's own instance runs every 2 h on the default branch of `flathub/<id>`; docs say custom workflows should run "at reasonable intervals, such as weekly". Bazaar runs daily (`0 0 * * *`). The Flatpak docs' GitLab template also runs it (`--update --commit-only`). [V]
- Dependabot: `package-ecosystem: github-actions` (directory `/` scans `.github/workflows`), `docker`, `pip`; no Flatpak ecosystem. The owner's MinimalUI `dependabot.yml` uses weekly cadence, `commit-message.prefix: ci`, `groups: github-actions: update-types: [minor, patch]` — reuse verbatim for Dailies. [V]
- Renovate: `github-actions` manager and `custom.regex` manager exist; no `flatpak` manager. [V — docs.renovatebot.com/modules/manager]
- Python deps inside the manifest: regenerate with `flatpak-pip-generator` (flatpak-builder-tools) — Flathub requires "Dependency manifest ... generated with community tools such as flatpak-builder-tools"; the checker's `pypi` type can then bump them. [V]

---

## 9. Recommendations for Dailies

1. **IDs & names**: `io.github.tim_van_oudheusden.Dailies` (release) and `io.github.tim_van_oudheusden.Dailies.Devel` (CI/nightly). Desktop file `io.github.tim_van_oudheusden.Dailies.desktop`; GSettings path `/io/github/tim_van_oudheusden/Dailies/`; D-Bus name same as app ID. Meson `profile` option exactly like Cartridges.
2. **Repo layout**: `build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json` (dir source, `-Dprofile=development`, `run-tests: true`) for CI; `build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json` (git tag+commit source, `x-checker-data` type `git`/`json`) kept in-tree as the Flathub-submission copy and for release/Pages builds. `data/io.github.tim_van_oudheusden.Dailies.metainfo.xml.in`, `.desktop.in`, `.gschema.xml.in`, icons `data/icons/hicolor/scalable/apps/<id>.svg` + `symbolic/apps/<id>-symbolic.svg` (Cartridges layout).
3. **Runtime**: `org.gnome.Platform//51`, CI image `gnome-51`; `python3` from the SDK; `webkitgtk-6.0` from the Platform (no module). Finish-args: `--share=network --share=ipc --socket=wayland --socket=fallback-x11 --device=dri` only. Browser-opening preference goes through the OpenURI portal (Gtk.UriLauncher), no extra permission.
4. **Workflows** (Appendix A): `ci.yml` (push/PR; x86_64 + aarch64 native; lint manifest+repo with `--gha-format`; Devel bundle artifacts), `release.yml` (on `v*` tag; builds release manifest for both arches; verifies versions; publishes GitHub Release with both bundles, `.flatpakref`, notes from metainfo), `pages-repo.yml` (on release or `workflow_dispatch`; GPG-signed OSTree repo for both arches → `actions/deploy-pages`; emits `dailies.flatpakrepo` and `<id>.flatpakref`), `external-data-checker.yml` (weekly cron, `--require-important-update`), `dependabot.yml` (github-actions weekly). Pin every action to a commit SHA with a `# vX.Y.Z` comment (MinimalUI convention; all SHAs listed in Appendix A) and set `permissions: contents: read` at top level.
5. **Releases**: assets `Dailies-x86_64.flatpak`, `Dailies-aarch64.flatpak`, `io.github.tim_van_oudheusden.Dailies.flatpakref`, `SHA256SUMS`. README install block: Flathub remote → `flatpak install --user ./Dailies-x86_64.flatpak`, or `flatpak install --user https://tim-van-oudheusden.github.io/Dailies/io.github.tim_van_oudheusden.Dailies.flatpakref` for auto-updates. Add the Flathub badge later.
6. **Pages remote**: start with the simple rebuild-from-scratch repo (one commit per ref, `--prune`, `--generate-static-deltas`), signed. Expect < 50 MB. Re-evaluate bandwidth if the user base grows (100 GB/month soft cap). Add `Url=https://tim-van-oudheusden.github.io/Dailies/repo/` to `.flatpakrepo`, `RuntimeRepo=https://dl.flathub.org/repo/flathub.flatpakrepo` to `.flatpakref`.
7. **Flathub readiness checklist**: ≥ 3 tagged releases before submitting (history requirement; no user-count gate, decided in #190); substantial native UX (favorites, categories, popularity, search, offline catalog) to clear the "launcher/web wrapper" bar; human-authored manifest and submission PR (AI policy); screenshots linked to a tag/commit; OARS rating (consider that embedded third-party web games are "content a user can reach by normal navigation" — rate accordingly); brand colours; `appstreamcli validate` + `flatpak-builder-lint appstream` clean; runtime at the latest GNOME at submission time; set `require-important-update` in `flathub.json` for the Flathub copy.
8. **Cross-platform note** (out of scope here but observed): Cartridges' CI builds Windows (MSYS2 UCRT64 + Inno Setup) and macOS (Homebrew + PyInstaller) and publishes those on GitHub Releases — a proven path for a Python/GTK4 app if cross-platform is pursued later. [V]

---

## 10. Open questions

1. Will Flathub treat Dailies as a "thin wrapper/launcher" or "simple web wrapper"? Nothing in the written policy gives a bright line; reviewers decide case by case. Build native value (favorites, categories, popularity feed, search provider) before submitting.
2. Exact GNOME 49 EOL date — not yet flagged in Flathub's summary as of 2026-10-15 though 51 shipped 2026-09-16; monitor `flatpak remote-info flathub org.gnome.Platform//49` and Flathub Discourse.
3. flatpak-github-actions issue #239 ("caching is broken upstream", per Bazaar's workflow comment) — not read; decide whether to copy Bazaar's manual `actions/cache` restore/save pattern or rely on the built-in cache.
4. Whether `andyholmes/flatter` works unmodified inside the `ghcr.io/flathub-infra/flatpak-github-actions:gnome-51` image (it only needs `flatpak`/`flatpak-builder`, but untested here).
5. `appstream-latest-release-is-prerelease` linter behaviour for `~beta` versions if pre-releases are ever published to Flathub beta.
6. Flathub docs JSON style says "4-tab indentation" — ambiguous (4 spaces vs tabs); Flathub's own repos (Cartridges, Bazaar) use 2-space JSON/YAML, and the external-data-checker honours `.editorconfig`. Pick 2 spaces and add `.editorconfig`.
7. Hive/ACMM requirements for the repo scaffolding are outside this task (separate research key); MinimalUI's `.github/` (rulesets, actionlint, dependabot, labeler, policies) was listed as the source to copy.

---

## Appendix A — Copy-paste workflow YAML (pinned to SHAs resolved 2026-10-15)

Resolved pins: `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`, `actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2`, `actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333 # v8.0.2`, `actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0`, `flatpak/flatpak-github-actions/flatpak-builder@79327416609af08178ad73b352877e51450790b3 # v6.8`, `softprops/action-gh-release@efb35369e0ad2afab669f228072c1b0d510eae64 # v3.0.3`, `actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d # v6.0.0`, `actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0`, `actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346 # v5.0.1`, `crazy-max/ghaction-import-gpg@2dc316deee8e90f13e1a351ab510b4d5bc0c82cd # v7.0.0`, `andyholmes/flatter@b32437fdafdca87317165f558dbcba78ebb20e1e # v1.0.0`, `docker/setup-qemu-action@99012661954931238ded8c8b007157a8430204e1 # v4.4.0`.

### A.1 `.github/workflows/ci.yml` — build + lint on push/PR, both arches

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    paths-ignore:
      - "**.md"
      - "docs/**"
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.sha }}
  cancel-in-progress: true

env:
  APP_ID: io.github.tim_van_oudheusden.Dailies
  MANIFEST: build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json

jobs:
  flatpak:
    name: Flatpak (${{ matrix.variant.arch }})
    runs-on: ${{ matrix.variant.runner }}
    timeout-minutes: 60
    container:
      image: ghcr.io/flathub-infra/flatpak-github-actions:gnome-51
      options: --privileged
    strategy:
      fail-fast: false
      matrix:
        variant:
          - arch: x86_64
            runner: ubuntu-latest
          - arch: aarch64
            runner: ubuntu-24.04-arm   # free native arm64 runner for public repos; no ubuntu-latest-arm exists
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      # flatpak-builder-lint is on PATH in this image (image is FROM ghcr.io/flathub/flatpak-builder-lint)
      - name: Lint manifest
        run: flatpak-builder-lint --gha-format --user-exceptions build-aux/flatpak/lint-exceptions.json manifest "$MANIFEST"

      - name: Lint metainfo
        run: flatpak-builder-lint --gha-format appstream data/${APP_ID}.metainfo.xml.in || true  # .in has @APP_ID@ placeholders; prefer linting the built repo below

      - name: Build Flatpak
        uses: flatpak/flatpak-github-actions/flatpak-builder@79327416609af08178ad73b352877e51450790b3 # v6.8
        with:
          manifest-path: ${{ env.MANIFEST }}
          bundle: ${{ env.APP_ID }}.Devel-${{ matrix.variant.arch }}.flatpak
          arch: ${{ matrix.variant.arch }}
          cache-key: flatpak-builder-${{ hashFiles(env.MANIFEST) }}
          run-tests: true
          verbose: true

      - name: Lint exported repo
        run: flatpak-builder-lint --gha-format --user-exceptions build-aux/flatpak/lint-exceptions.json repo repo
```

`build-aux/flatpak/lint-exceptions.json` (local exceptions for the Devel ID only; keep the release ID exception-free):

```json
{
  "io.github.tim_van_oudheusden.Dailies.Devel": [
    "appid-url-not-reachable"
  ]
}
```
(Which exceptions are actually needed must be discovered by running the linter once — the list above is a guess [I].)

Optional Bazaar-style explicit cache (only if the built-in cache misbehaves):

```yaml
      - name: Restore cache
        uses: actions/cache/restore@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0
        with:
          path: .flatpak-builder
          key: flatpak-builder-${{ matrix.variant.arch }}-${{ github.run_id }}
          restore-keys: |
            flatpak-builder-${{ matrix.variant.arch }}-
      # ... flatpak-builder step with `cache: true` and `restore-cache: false` ...
      - name: Save cache
        uses: actions/cache/save@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0
        with:
          path: .flatpak-builder
          key: flatpak-builder-${{ matrix.variant.arch }}-${{ github.run_id }}
```

### A.2 `.github/workflows/release.yml` — on tag `v*`: build release manifest, publish bundles to GitHub Releases

```yaml
name: Release

on:
  push:
    tags: ["v*"]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

env:
  APP_ID: io.github.tim_van_oudheusden.Dailies
  MANIFEST: build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json

jobs:
  verify:
    name: Verify version metadata
    runs-on: ubuntu-latest
    timeout-minutes: 5
    outputs:
      version: ${{ steps.v.outputs.version }}
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Tag == meson version == newest metainfo release
        id: v
        run: |
          tag="${GITHUB_REF_NAME#v}"
          meson_ver=$(sed -nE "s/^\s*version: '([^']+)',/\1/p" meson.build | head -1)
          mi_ver=$(grep -oE '<release version="[^"]+"' data/${APP_ID}.metainfo.xml.in | head -1 | sed -E 's/.*"([^"]+)"/\1/')
          mi_date=$(grep -oE 'date="[0-9-]+"' data/${APP_ID}.metainfo.xml.in | head -1 | sed -E 's/.*"([^"]+)"/\1/')
          echo "tag=$tag meson=$meson_ver metainfo=$mi_ver date=$mi_date"
          [ "$tag" = "$meson_ver" ] && [ "$tag" = "$mi_ver" ] || { echo "::error::version mismatch"; exit 1; }
          [ "$(date -d "$mi_date" +%s)" -le "$(date +%s)" ] || { echo "::error::release date is in the future"; exit 1; }
          echo "version=$tag" >> "$GITHUB_OUTPUT"

  build:
    name: Build (${{ matrix.variant.arch }})
    needs: verify
    runs-on: ${{ matrix.variant.runner }}
    timeout-minutes: 60
    container:
      image: ghcr.io/flathub-infra/flatpak-github-actions:gnome-51
      options: --privileged
    strategy:
      fail-fast: true
      matrix:
        variant:
          - { arch: x86_64,  runner: ubuntu-latest }
          - { arch: aarch64, runner: ubuntu-24.04-arm }
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Lint release manifest
        run: flatpak-builder-lint --gha-format manifest "$MANIFEST"
      - name: Build Flatpak
        uses: flatpak/flatpak-github-actions/flatpak-builder@79327416609af08178ad73b352877e51450790b3 # v6.8
        with:
          manifest-path: ${{ env.MANIFEST }}
          bundle: Dailies-${{ matrix.variant.arch }}.flatpak
          artifact-name: Dailies-${{ matrix.variant.arch }}
          arch: ${{ matrix.variant.arch }}
          branch: stable
          cache-key: flatpak-builder-release-${{ hashFiles(env.MANIFEST) }}
      - name: Lint repo (Flathub rules, no exceptions)
        run: flatpak-builder-lint --gha-format repo repo

  publish:
    name: Publish GitHub Release
    needs: [verify, build]
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333 # v8.0.2
        with:
          pattern: Dailies-*
          path: dist
          merge-multiple: true
      - name: Release notes from metainfo (newest <release>)
        shell: python
        run: |
          import re, textwrap, pathlib
          xml = pathlib.Path("data/io.github.tim_van_oudheusden.Dailies.metainfo.xml.in").read_text(encoding="utf-8")
          body = re.findall(r"<release[^>]*>\s*(?:<url[^>]*>.*?</url>\s*)?<description[^>]*>\n([\s\S]*?)\s*</description>\s*</release>", xml)[0]
          body = re.sub(r"</?(p|ul|ol)>", "", textwrap.dedent(body))
          body = re.sub(r"\s*<li>(.*?)</li>", r"\n- \1", body)
          pathlib.Path("release_notes.md").write_text(body.strip() + "\n", encoding="utf-8")
      - name: Checksums
        run: (cd dist && sha256sum *.flatpak > SHA256SUMS)
      - name: Publish
        uses: softprops/action-gh-release@efb35369e0ad2afab669f228072c1b0d510eae64 # v3.0.3
        with:
          tag_name: ${{ github.ref_name }}
          name: Dailies ${{ needs.verify.outputs.version }}
          body_path: release_notes.md
          generate_release_notes: true   # appends PR-based notes (.github/release.yml) under the metainfo text
          fail_on_unmatched_files: true
          files: |
            dist/Dailies-x86_64.flatpak
            dist/Dailies-aarch64.flatpak
            dist/SHA256SUMS
            build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.flatpakref
```

Equivalent `gh` CLI alternative for the last step (needs `GH_TOKEN: ${{ github.token }}`):
`gh release create "$GITHUB_REF_NAME" dist/Dailies-x86_64.flatpak dist/Dailies-aarch64.flatpak dist/SHA256SUMS --title "Dailies $VERSION" --notes-file release_notes.md --verify-tag`.

### A.3 `.github/workflows/pages-repo.yml` — GPG-signed OSTree remote on GitHub Pages (hand-rolled, rebuild-from-scratch)

Settings → Pages → Source = "GitHub Actions". Secrets: `GPG_PRIVATE_KEY` (armored), `GPG_PASSPHRASE`. Repository variable `PAGES_URL=https://tim-van-oudheusden.github.io/Dailies`.

```yaml
name: Flatpak repository (GitHub Pages)

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: pages-repo
  cancel-in-progress: false

env:
  APP_ID: io.github.tim_van_oudheusden.Dailies
  MANIFEST: build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json
  BRANCH: stable
  RUNTIME_REPO: https://dl.flathub.org/repo/flathub.flatpakrepo
  PAGES_URL: ${{ vars.PAGES_URL }}

jobs:
  build:
    name: Build repo (${{ matrix.variant.arch }})
    runs-on: ${{ matrix.variant.runner }}
    timeout-minutes: 60
    container:
      image: ghcr.io/flathub-infra/flatpak-github-actions:gnome-51
      options: --privileged
    strategy:
      fail-fast: true
      matrix:
        variant:
          - { arch: x86_64,  runner: ubuntu-latest }
          - { arch: aarch64, runner: ubuntu-24.04-arm }
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Import GPG key
        id: gpg
        uses: crazy-max/ghaction-import-gpg@2dc316deee8e90f13e1a351ab510b4d5bc0c82cd # v7.0.0
        with:
          gpg_private_key: ${{ secrets.GPG_PRIVATE_KEY }}
          passphrase: ${{ secrets.GPG_PASSPHRASE }}
      - name: Build and export signed repo
        uses: flatpak/flatpak-github-actions/flatpak-builder@79327416609af08178ad73b352877e51450790b3 # v6.8
        with:
          manifest-path: ${{ env.MANIFEST }}
          arch: ${{ matrix.variant.arch }}
          branch: ${{ env.BRANCH }}
          gpg-sign: ${{ steps.gpg.outputs.fingerprint }}
          build-bundle: false
          upload-artifact: false
          repo-dir: repo
          cache-key: flatpak-builder-pages-${{ hashFiles(env.MANIFEST) }}
      - name: Upload repo
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: repo-${{ matrix.variant.arch }}
          path: repo
          retention-days: 1

  merge:
    name: Merge arches, update repo, upload Pages artifact
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 20
    container:
      image: ghcr.io/flathub-infra/flatpak-github-actions:gnome-51
      options: --privileged
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Import GPG key
        id: gpg
        uses: crazy-max/ghaction-import-gpg@2dc316deee8e90f13e1a351ab510b4d5bc0c82cd # v7.0.0
        with:
          gpg_private_key: ${{ secrets.GPG_PRIVATE_KEY }}
          passphrase: ${{ secrets.GPG_PASSPHRASE }}
      - uses: actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333 # v8.0.2
        with:
          pattern: repo-*
          path: arches
      - name: Combine into one OSTree repo
        run: |
          ostree init --repo=site/repo --mode=archive
          for d in arches/repo-*; do
            ostree pull-local --repo=site/repo "$d"
          done
          flatpak build-update-repo \
            --gpg-sign="${{ steps.gpg.outputs.fingerprint }}" \
            --title="Dailies" \
            --comment="Dailies releases" \
            --homepage="https://github.com/Tim-van-Oudheusden/Dailies" \
            --default-branch="$BRANCH" \
            --generate-static-deltas --prune site/repo
      - name: Write .flatpakrepo / .flatpakref / index
        run: |
          KEY=$(gpg --export "${{ steps.gpg.outputs.fingerprint }}" | base64 --wrap=0)
          cat > site/dailies.flatpakrepo <<EOF
          [Flatpak Repo]
          Title=Dailies
          Url=${PAGES_URL}/repo/
          Homepage=https://github.com/Tim-van-Oudheusden/Dailies
          Comment=Daily guessing games in one place
          Description=Official Flatpak repository for Dailies
          Icon=${PAGES_URL}/icon.svg
          GPGKey=${KEY}
          EOF
          cat > site/${APP_ID}.flatpakref <<EOF
          [Flatpak Ref]
          Title=Dailies
          Name=${APP_ID}
          Branch=${BRANCH}
          Url=${PAGES_URL}/repo/
          SuggestRemoteName=dailies
          Homepage=https://github.com/Tim-van-Oudheusden/Dailies
          Icon=${PAGES_URL}/icon.svg
          RuntimeRepo=${RUNTIME_REPO}
          IsRuntime=false
          GPGKey=${KEY}
          EOF
          cp data/icons/hicolor/scalable/apps/${APP_ID}.svg site/icon.svg
          cp docs/pages/index.html site/index.html   # optional landing page
      - uses: actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0
        with:
          path: site

  deploy:
    name: Deploy to GitHub Pages
    needs: merge
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346 # v5.0.1
```

Notes: `ostree pull-local` into an `archive` repo and the merge-before-`build-update-repo` step follow the official multi-arch GitLab template (which chains jobs on a shared `repo/` artifact instead) [I adaptation of V]. The upload-pages artifact must contain no symlinks; OSTree archive repos do not use symlinks in `objects/` [I — verify once on first run]. If signing is dropped (not recommended), users need `flatpak remote-add --no-gpg-verify`.

Users: `flatpak install --user https://tim-van-oudheusden.github.io/Dailies/io.github.tim_van_oudheusden.Dailies.flatpakref` or `flatpak remote-add --user --if-not-exists dailies https://tim-van-oudheusden.github.io/Dailies/dailies.flatpakrepo && flatpak install --user dailies io.github.tim_van_oudheusden.Dailies`.

### A.4 Alternative: `andyholmes/flatter` (incremental, less YAML)

```yaml
name: Flatter
on:
  push:
    tags: ["v*"]
  workflow_dispatch:
permissions:
  contents: read
jobs:
  flatter:
    name: Flatter (${{ matrix.arch }})
    runs-on: ${{ matrix.arch == 'aarch64' && 'ubuntu-24.04-arm' || 'ubuntu-latest' }}
    container:
      image: ghcr.io/andyholmes/flatter/gnome:49   # no 51 image yet; try ghcr.io/flathub-infra/flatpak-github-actions:gnome-51
      options: --privileged
    strategy:
      matrix:
        arch: [x86_64, aarch64]
      fail-fast: false
      max-parallel: 1          # shared repo cache
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - name: Setup GPG
        if: ${{ github.triggering_actor == github.repository_owner }}
        id: gpg
        uses: crazy-max/ghaction-import-gpg@2dc316deee8e90f13e1a351ab510b4d5bc0c82cd # v7.0.0
        with:
          gpg_private_key: ${{ secrets.GPG_PRIVATE_KEY }}
          passphrase: ${{ secrets.GPG_PASSPHRASE }}
      - uses: andyholmes/flatter@b32437fdafdca87317165f558dbcba78ebb20e1e # v1.0.0
        with:
          files: build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json
          arch: ${{ matrix.arch }}
          gpg-sign: ${{ steps.gpg.outputs.fingerprint }}
          upload-bundles: true
          upload-pages-artifact: ${{ matrix.arch == 'aarch64' }}
          upload-pages-includes: |
            index.html
          flatpak-builder-args: |
            --default-branch=stable
          flatpak-build-bundle-args: |
            --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo
            --repo-url=https://tim-van-oudheusden.github.io/Dailies
  deploy:
    needs: flatter
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346 # v5.0.1
```
Flatter writes `index.flatpakrepo` itself (Url from `CNAME` or `https://<user>.github.io/<repo>`). [V README]

### A.5 `.github/workflows/external-data-checker.yml` — weekly (Bazaar's file, cadence changed)

```yaml
name: Check for Flatpak dependency updates
on:
  schedule:
    - cron: "0 6 * * 1"   # weekly, Monday 06:00 UTC (Flathub docs: weekly is a "reasonable interval")
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  flatpak-external-data-checker:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          ref: main
      - uses: docker://ghcr.io/flathub/flatpak-external-data-checker:latest
        env:
          GIT_AUTHOR_NAME: Flatpak External Data Checker
          GIT_COMMITTER_NAME: Flatpak External Data Checker
          GIT_AUTHOR_EMAIL: 41898282+github-actions[bot]@users.noreply.github.com
          GIT_COMMITTER_EMAIL: 41898282+github-actions[bot]@users.noreply.github.com
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          args: --update --never-fork --require-important-update build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json
```
(`GITHUB_TOKEN`-created PRs do not trigger `pull_request` workflows unless a PAT/GitHub App token is used — standard GitHub Actions limitation [I, well known, not re-verified here].)

### A.6 `.github/dependabot.yml` (from MinimalUI, trimmed)

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    commit-message:
      prefix: ci
    groups:
      github-actions:
        update-types: [minor, patch]
```

### A.7 `.github/release.yml`

```yaml
changelog:
  exclude:
    labels: [ignore-for-release]
    authors: [dependabot, github-actions]
  categories:
    - title: New games and catalogue changes
      labels: [game, catalogue]
    - title: Features
      labels: [enhancement]
    - title: Fixes
      labels: [bug]
    - title: Other changes
      labels: ["*"]
```

---

## Appendix B — Manifest skeletons

### B.1 `build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json` (CI / local dev; modelled on Cartridges)

```json
{
  "id": "io.github.tim_van_oudheusden.Dailies.Devel",
  "runtime": "org.gnome.Platform",
  "runtime-version": "51",
  "sdk": "org.gnome.Sdk",
  "command": "dailies",
  "tags": ["devel"],
  "desktop-file-name-suffix": " (Devel)",
  "finish-args": [
    "--share=network",
    "--share=ipc",
    "--socket=fallback-x11",
    "--socket=wayland",
    "--device=dri"
  ],
  "cleanup": [
    "/include",
    "/lib/pkgconfig",
    "/man",
    "/share/doc",
    "/share/gtk-doc",
    "/share/man",
    "/share/pkgconfig",
    "*.la",
    "*.a"
  ],
  "modules": [
    "python3-requirements.json",
    {
      "name": "dailies",
      "buildsystem": "meson",
      "builddir": true,
      "run-tests": true,
      "config-opts": ["-Dprofile=development"],
      "sources": [
        {
          "type": "dir",
          "path": "../.."
        }
      ]
    }
  ]
}
```
`python3-requirements.json` is generated with `flatpak-pip-generator` (flatpak-builder-tools) from `requirements.txt` and contains `pip3 install --no-index --find-links="file://${PWD}" --prefix=${FLATPAK_DEST} ...` modules exactly like Cartridges' `python3-pyyaml`/`python3-requests` modules. Add `"x-checker-data": {"type": "pypi", "name": "<pkg>"}` to each source so the external-data-checker can bump them (Bazaar does this). Note Flathub says sub-manifests are acceptable "only when generated by external tooling" — a pip-generated file qualifies. [V]

### B.2 `build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json` (release / Flathub submission copy)

```json
{
  "id": "io.github.tim_van_oudheusden.Dailies",
  "runtime": "org.gnome.Platform",
  "runtime-version": "51",
  "sdk": "org.gnome.Sdk",
  "command": "dailies",
  "finish-args": [
    "--share=network",
    "--share=ipc",
    "--socket=fallback-x11",
    "--socket=wayland",
    "--device=dri"
  ],
  "cleanup": [
    "/include",
    "/lib/pkgconfig",
    "/man",
    "/share/doc",
    "/share/gtk-doc",
    "/share/man",
    "/share/pkgconfig",
    "*.la",
    "*.a"
  ],
  "modules": [
    "python3-requirements.json",
    {
      "name": "dailies",
      "buildsystem": "meson",
      "builddir": true,
      "config-opts": ["-Dprofile=release"],
      "sources": [
        {
          "type": "git",
          "url": "https://github.com/Tim-van-Oudheusden/Dailies.git",
          "tag": "v0.1.0",
          "commit": "<full 40-char sha of the tag>",
          "x-checker-data": {
            "type": "git",
            "tag-pattern": "^v([\\d.]+)$",
            "version-scheme": "semantic",
            "is-main-source": true,
            "is-important": true
          }
        }
      ]
    }
  ]
}
```
Flathub linter requires `tag` **with** `commit` (never `branch`: `module-<name>-source-git-branch`). Within the Flathub repo, the checker bumps `tag`+`commit` and (because of `is-main-source`) can append the version to `<releases>`. [V]

Optional `flathub.json` for the Flathub repo: `{ "require-important-update": true }` (Bazaar). [V]

### B.3 `meson_options.txt` / `meson.build` profile switch (Cartridges pattern) [V]

```meson
option('profile', type: 'combo', choices: ['release', 'development'], value: 'release')
```
```meson
profile = get_option('profile')
if profile == 'development'
  app_id = 'io.github.tim_van_oudheusden.Dailies.Devel'
  prefix = '/io/github/tim_van_oudheusden/Dailies/Devel'
else
  app_id = 'io.github.tim_van_oudheusden.Dailies'
  prefix = '/io/github/tim_van_oudheusden/Dailies'
endif
conf.set('APP_ID', app_id)
conf.set('PREFIX', prefix)
conf.set('VERSION', meson.project_version())
conf.set('PROFILE', profile)
```
`data/meson.build` then `configure_file`s `<id>.desktop.in`, `<id>.metainfo.xml.in`, `<id>.gschema.xml.in` with `@APP_ID@`, merges translations with `i18n.merge_file`, and adds tests `desktop-file-validate`, `appstreamcli validate --no-net --explain`, `glib-compile-schemas --strict --dry-run` (all from Cartridges' `data/meson.build`). [V]

---

## Appendix C — Reproduced reference files

### C.1 Bazaar `data/io.github.kolunmi.Bazaar.metainfo.xml.in` (head) [V — clone 2026-08-18]

```xml
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>io.github.kolunmi.Bazaar</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>

  <name>Bazaar</name>
  <summary>Discover and install apps</summary>
  <description>
    <p>
      A fast and modern app store for Linux with a focus on discovering
      and installing Flatpak apps and add-ons, particularly from Flathub.
    </p>
    <ul>
      <li>Queue multiple installs and keep browsing</li>
      <li>Easily view app permissions</li>
      <li>Sign in to Flathub to view and manage your favorites</li>
      <li>Search apps directly from GNOME Shell</li>
    </ul>
  </description>

  <supports>
    <control>pointing</control>
    <control>keyboard</control>
    <control>touch</control>
  </supports>
  <requires>
    <display_length compare="ge">360</display_length>
  </requires>

  <developer id="io.github.kolunmi">
    <name>The Bazaar Contributors</name>
  </developer>

  <url type="homepage">https://usebazaar.org/</url>
  <url type="vcs-browser">https://github.com/bazaar-org/bazaar</url>
  <url type="bugtracker">https://github.com/bazaar-org/bazaar/issues</url>
  <url type="translate">https://l10n.gnome.org/module/bazaar/</url>
  <url type="faq">https://github.com/bazaar-org/bazaar/blob/master/README.md</url>
  <url type="help">https://github.com/bazaar-org/bazaar/discussions</url>
  <url type="donation">https://github.com/sponsors/kolunmi</url>
  <url type="contact">https://github.com/kolunmi</url>
  <url type="contribute">https://github.com/bazaar-org/bazaar</url>

  <translation type="gettext">bazaar</translation>
  <launchable type="desktop-id">io.github.kolunmi.Bazaar.desktop</launchable>
  <content_rating type="oars-1.1" />

  <branding>
    <color type="primary" scheme_preference="light">#ffbe6f</color>
    <color type="primary" scheme_preference="dark">#c11c2b</color>
  </branding>

  <screenshots>
    <screenshot type="default">
      <image>https://github.com/user-attachments/assets/e67f35f0-9566-4068-93f5-cb814db0aedd</image>
      <caption>The home page displaying Flathub apps</caption>
    </screenshot>
    ...
  </screenshots>

  <releases>
    <release version="0.9.4" date="2026-08-14">
      <url type="details">https://github.com/bazaar-org/bazaar/releases/tag/v0.9.4</url>
      <description translate="no">
        <p><em>Changes</em></p>
        <ul>
          <li>Added shortcuts for zoom actions in the screenshot viewer</li>
          <li>Clicking other app tiles on an app page now creates a new page</li>
          <li>Fixed keyboard navigation on the "Curated" page</li>
        </ul>
        <p>Thanks for reading, and have a great day!</p>
      </description>
    </release>
    ...
  </releases>
</component>
```

### C.2 Cartridges `data/page.kramo.Cartridges.metainfo.xml.in` (head) [V — clone 2026-09-03]

```xml
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>@APP_ID@</id>
  <replaces>
    <id>hu.kramo.Cartridges</id>
  </replaces>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <name>Cartridges</name>
  <summary>Launch all your games</summary>
  <description>
    <p>Cartridges is a simple game launcher for all of your games. ...</p>
  </description>
  <url type="homepage">https://apps.gnome.org/Cartridges/</url>
  <url type="bugtracker">https://git.kramo.page/cartridges/issues</url>
  <url type="translate">https://hosted.weblate.org/engage/cartridges/</url>
  <url type="contact">https://www.kramo.page/about/</url>
  <url type="vcs-browser">https://git.kramo.page/cartridges</url>
  <url type="contribute">https://git.kramo.page/cartridges/blob/main/CONTRIBUTING.md</url>
  <developer id="page.kramo">
    <name translate="no">kramo</name>
  </developer>
  <launchable type="desktop-id">@APP_ID@.desktop</launchable>
  <translation type="gettext">cartridges</translation>
  <branding>
    <color type="primary" scheme_preference="light">#d5b0e7</color>
    <color type="primary" scheme_preference="dark">#501a5c</color>
  </branding>
  <supports>
    <control>pointing</control>
    <control>keyboard</control>
    <control>touch</control>
  </supports>
  <requires>
    <display_length compare="ge">360</display_length>
  </requires>
  <screenshots>
    <screenshot type="default">
      <image>https://codeberg.org/kramo/cartridges/raw/branch/main/data/screenshots/1.png</image>
      <caption>Cartridges</caption>
    </screenshot>
    ...
```
(Note: Cartridges links screenshots to a *branch*, which the Flathub guidelines now advise against — link to a tag/commit.)

### C.3 Cartridges `.github/workflows/publish-release.yml` [V]

```yaml
name: Publish Release
on:
  push:
    tags: "*"

concurrency:
  group: release-${{ github.sha }}

jobs:
  publish-release:
    name: Publish Release
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download workflow artifact
        uses: dawidd6/action-download-artifact@v9
        with:
          workflow: ci.yml
          commit: ${{ github.sha }}

      - name: Get release notes
        shell: python
        run: |
          import re, textwrap
          open_file = open("./data/page.kramo.Cartridges.metainfo.xml.in", "r", encoding="utf-8")
          string = open_file.read()
          open_file.close()
          string = re.findall("<release.*>\s*<description.*>\n([\s\S]*?)\s*</description>\s*<\/release>", string)[0]
          string = textwrap.dedent(string)
          open_file = open("release_notes", "w", encoding="utf-8")
          open_file.write(string)
          open_file.close()

      - name: Get tag name
        id: get_tag_name
        run: echo tag_name=${GITHUB_REF#refs/tags/} >> $GITHUB_OUTPUT

      - name: Publish release
        uses: softprops/action-gh-release@v2.2.2
        with:
          files: |
            Windows Installer/Cartridges Windows.exe
            macOS Application/Cartridges macOS.zip
          fail_on_unmatched_files: true
          tag_name: ${{ steps.get_tag_name.outputs.tag_name }}
          body_path: release_notes
```

### C.4 Bazaar `.github/workflows/build-flatpak.yml` [V]

```yaml
on:
  push:
    branches: [main]
  pull_request:
    paths-ignore:
      - "**.md"
      - "docs/*"
      - "screenshots/*"
      - "translators.sh"
      - ".github/ISSUE_TEMPLATE/**"
  workflow_dispatch:

permissions: {}

name: CI Build Flatpak
jobs:
  flatpak:
    name: "Flatpak"
    container:
      image: ghcr.io/flathub-infra/flatpak-github-actions:gnome-50
      options: --privileged
    strategy:
      matrix:
        variant:
          - arch: x86_64
            runner: ubuntu-latest
          # no latest for ARM :(
          - arch: aarch64
            runner: ubuntu-24.04-arm
    runs-on: ${{ matrix.variant.runner }}
    steps:
    - name: Git Checkout
      uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
      with:
        submodules: recursive
        persist-credentials: false
    - name: Restore cache
      uses: actions/cache/restore@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0
      with:
        path: .flatpak-builder
        key: flatpak-builder-046f9ec-${{ matrix.variant.arch }}-${{ github.run_id }}
        restore-keys: |
          flatpak-builder-046f9ec-${{ matrix.variant.arch }}-
    - name: Build Flatpak
      uses: flatpak/flatpak-github-actions/flatpak-builder@401fe28a8384095fc1531b9d320b292f0ee45adb # v6.7
      with:
        bundle: Bazaar.flatpak
        manifest-path: build-aux/flatpak/io.github.kolunmi.Bazaar.json
        # caching is broken upstream
        # https://github.com/flatpak/flatpak-github-actions/issues/239
        # this is only true because there is no other way to call fb with --ccache
        cache: true
        restore-cache: false
        arch: ${{ matrix.variant.arch }}
        verbose: true
    - name: Write new cache
      uses: actions/cache/save@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0
      with:
        path: .flatpak-builder
        key: flatpak-builder-046f9ec-${{ matrix.variant.arch }}-${{ github.run_id }}
```

### C.5 Flathub `.flatpakrepo` example (from Flatpak docs) [V]

```
[Flatpak Repo]
Title=Flathub
Url=https://dl.flathub.org/repo/
Homepage=https://flathub.org/
Comment=Central repository of Flatpak applications
Description=Central repository of Flatpak applications
Icon=https://dl.flathub.org/repo/logo.svg
GPGKey=mQINBFlD2sABEADsiUZUO...
```

### C.6 `.flatpakref` template (from Flatpak docs) [V]

```
[Flatpak Ref]
Title=<A pretty application or repo name>
Name=<Application id in tld.vendor.app_name format>
Branch=< branch of generated ostree refs, defaults to master>
Url=<Url of Gitlab page>
SuggestRemoteName=<A name for the flatpak remote>
Homepage=<URL of the homepage>
Icon=<Direct link to an icon>
RuntimeRepo=< Link to repo where runtime and other dependencies are eg. https://dl.flathub.org/repo/flathub.flatpakrepo>
IsRuntime=false
GPGKey=<base64 encoded GPG key>
```

### C.7 GPG command set (Flatpak docs + flatter README) [V]

```sh
gpg --quick-gen-key dailies-repo@tim-van-oudheusden.github.io          # or: gpg --homedir ./keyring --quick-gen-key ...
gpg --list-secret-keys --keyid-format=long                             # keyid (sec line, algorithm/ID)
gpg --list-secret-keys --with-keygrip                                  # keygrip (only needed for gpg-preset-passphrase)
gpg --output private.pgp --armor --export-secret-key <keyid>          # -> secret GPG_PRIVATE_KEY
gpg --export <keyid> > dailies.gpg && base64 --wrap=0 < dailies.gpg    # -> GPGKey= value
```

---

## Sources

Primary documentation
- https://docs.flathub.org/docs/for-app-authors/requirements (inclusion policy, app ID rules, dashes→underscores, AI policy, required files)
- https://docs.flathub.org/docs/for-app-authors/submission (new-pr branch, linter commands, `bot, build`)
- https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines (required tags, screenshots, releases, branding, OARS)
- https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines/quality-guidelines (icon, name/summary limits, screenshot sizes, brand colours)
- https://docs.flathub.org/docs/for-app-authors/linter (exceptions, error catalogue)
- https://docs.flathub.org/docs/for-app-authors/maintenance (flathub.json keys, external-data-checker cadence, test builds)
- https://docs.flathub.org/docs/for-app-authors/verification (GitHub owner must match)
- https://docs.flathub.org/docs/for-app-authors/runtimes (runtime support policy)
- https://docs.flatpak.org/en/latest/hosting-a-repository.html and source https://github.com/flatpak/flatpak-docs/blob/main/docs/hosting-a-repository.rst (GitLab Pages template, .flatpakrepo/.flatpakref, GPG)
- https://docs.flatpak.org/en/latest/single-file-bundles.html
- https://man.archlinux.org/man/flatpak-build-update-repo.1.en ; https://man.archlinux.org/man/flatpak-build-bundle.1.en ; https://man.archlinux.org/man/appstreamcli.1.en
- https://release.gnome.org/calendar/ (GNOME 48/49/50/51 dates, 52 schedule)
- https://handbook.gnome.org/maintainers/making-a-release.html (GNOME versioning/tagging)
- https://developer.gnome.org/documentation/tutorials/application-id.html (`.Devel` suffix)
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/master/elements/sdk/webkitgtk.bst (WebKitGTK 6.0 in GNOME SDK)
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners (runner labels, arm64 free for public repos)
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits (1 GB, 100 GB/month, 10-min timeout)
- https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes (`.github/release.yml`)
- https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference
- https://docs.renovatebot.com/modules/manager/ (no flatpak manager)
- https://raw.githubusercontent.com/actions/upload-pages-artifact/main/README.md (artifact constraints)
- https://discourse.flathub.org/t/org-gnome-platform-branch-46-is-end-of-life/9675 (GNOME 46 EOL 2025-04-17)

Repositories cloned/inspected (shallow clones under `<scratch>/clones/flatpak-release-pipeline/`)
- https://github.com/flatpak/flatpak-github-actions (README, `flatpak-builder/action.yml`, `flatpak-builder/index.js`; tags v6.8 2026-08-30)
- https://github.com/flathub-infra/flatpak-github-actions (deprecated fork README) and https://github.com/flathub-infra/flatpak-github-actions/issues/17
- https://github.com/flathub-infra/actions-images (README image table, `Dockerfile`, `.github/workflows/docker.yml`)
- https://github.com/flathub-infra/flatpak-builder-lint (README, `docker/Dockerfile`, `flatpak_builder_lint/checks/appid.py`, `flatpak_builder_lint/domainutils.py`)
- https://github.com/flathub-infra/flatpak-external-data-checker (README: checkers, workflow template)
- https://github.com/kra-mo/cartridges (ci.yml, publish-release.yml, Devel manifest, meson profile, metainfo, data/meson.build)
- https://github.com/bazaar-org/bazaar (build-flatpak.yml, flatpak-external-data-checker.yml, manifest, metainfo, version.sh, Justfile)
- https://github.com/flathub/page.kramo.Cartridges and https://github.com/flathub/io.github.kolunmi.Bazaar (Flathub-side manifests, flathub.json)
- https://github.com/flathub/io.github.nate_xyz.Resonance and `gh search repos --owner flathub` (underscore IDs)
- https://github.com/andyholmes/flatter (README, action.yml; v1.0.0 2026-03-11)
- https://github.com/Tim-van-Oudheusden/MinimalUI (`.github/workflows/release.yml`, `ci.yml`, `dependabot.yml` conventions)

Local verification
- `flatpak remote-info --user flathub org.gnome.Platform//{48,49,50,51}` on this machine (Flatpak 1.18.4), 2026-10-15
- `gh api repos/<owner>/<repo>/git/ref/tags/<tag>` for all SHA pins; `gh release list` for action versions; `gh release create --help`

Secondary (search results, existence verified only)
- https://github.com/rmonk/hey-whisper/pull/4 ; https://github.com/moosingin3space/guest-info-display/pull/36 ; https://github.com/aetherpak/actions ; https://blogs.gnome.org/alexl/2017/02/10/maintaining-a-flatpak-repository/
- https://discourse.ubuntu.com/t/the-gnome-48-runtime-is-no-longer-supported-as-of-march-24-2026-ubuntu-24-04-4-lts-flatpak/80598 (GNOME 48 EOL wording, also confirmed locally)
