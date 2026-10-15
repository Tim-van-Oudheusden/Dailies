---
key: 25
title: build(flatpak): Devel and release manifests, lint exceptions, dev script
type: Task
labels: milestone::M0, type::task, priority::high, flatpak
parent: 2
blocked_by: 24
---
> **Risk tier:** high (`build-aux/**`) · **Size:** S

## Why

Two manifests are needed. The **Devel** one is what CI builds on every push. The **release** one is what `release.yml` builds, and it is the copy Flathub will receive later. **No pip modules:** Dailies has zero third-party Python runtime dependencies, so there is no `flatpak-pip-generator` and no `python3-requirements.json`.

## Tasks

- [ ] `build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json` (release). Copy it **exactly** as given in [`mvp-first.md` §9](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md):
  - `runtime` `org.gnome.Platform`, `runtime-version` `"51"`, `sdk` `org.gnome.Sdk`, `command` `dailies`
  - `finish-args`, exactly these five: `--share=network`, `--share=ipc`, `--socket=fallback-x11`, `--socket=wayland`, `--device=dri`
  - The cleanup list from the proposal
  - One `meson` module, `builddir: true`, `config-opts: ["-Dprofile=release"]`, with a `git` source (`tag` + 40-char `commit`) and `x-checker-data` `{type: git, tag-pattern: "^v([\\d.]+)$", version-scheme: semantic, is-main-source: true, is-important: true}`. Until v0.1.0 exists, pin `tag` and `commit` to the current `main` commit and leave a comment in the PR
- [ ] `build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json`: same, but `"id": "...Dailies.Devel"`, `"tags": ["devel"]`, `"desktop-file-name-suffix": " (Devel)"`, `"run-tests": true` on the `dailies` module (a module property, so `meson test` runs during the build), `"config-opts": ["-Dprofile=development"]`, `"sources": [{"type": "dir", "path": "../.."}]` ([`flatpak-release-pipeline.md` Appendix B.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md))
- [ ] `build-aux/flatpak/lint-exceptions.json`: exceptions for the **Devel ID only**. The exact set (probably `appid-url-not-reachable`) is discovered on the first CI run **[U]**. The release ID gets **no** exceptions
- [ ] `scripts/dev.sh`: a shell script, chosen over a Justfile to avoid a `just` dependency, with subcommands `build-devel`, `run`, `bundle` (→ `Dailies-Devel-x86_64.flatpak`) and `lint` (`flatpak-builder-lint manifest` + `repo`). Model the recipes on Bazaar's Justfile ([`bazaar.md` Appendix F](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/bazaar.md)); the script must pass shellcheck

## Never

- No `--filesystem=*`, no `--talk-name=*`, no `--socket=pulseaudio` (that is decision #16 / #69), and **never** `--talk-name=org.freedesktop.Flatpak` (a documented sandbox escape; the custom-command mode in #63 relies on the user granting it themselves)

## Permission justifications (put these in the PR and later in the Flathub PR)

| finish-arg | Why |
|---|---|
| `--share=network` | Catalog fetch + web games |
| `--share=ipc` + `--socket=fallback-x11` | X11 fallback (`finish-args-x11-without-ipc` is never granted) |
| `--socket=wayland` | Wayland display |
| `--device=dri` | WebKitGTK ≥ 2.46 renders with Skia on the GPU and shares DMA-BUFs ([`embedded-browser.md` §1.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)) |

WebKit's own subprocess sandbox uses `flatpak-spawn --sandbox` through the always-available portal, so it needs no extra permission.

## Acceptance criteria

- [ ] `scripts/dev.sh build-devel && scripts/dev.sh run` opens the M0 window on a developer machine
- [ ] `flatpak-builder-lint manifest build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json` reports no errors
- [ ] `flatpak-builder-lint --user-exceptions build-aux/flatpak/lint-exceptions.json manifest …Devel.json` reports no errors
- [ ] Both manifests are 2-space JSON and match `.editorconfig`

## References

- [`mvp-first.md` §9, §14 (Sandbox)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`flatpak-release-pipeline.md` §4.5, §6, Appendix B](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/flatpak-release-pipeline.md)
- [`stack-crossplatform.md` Appendix D](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/stack-crossplatform.md)
