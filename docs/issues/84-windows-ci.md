---
key: 84
title: ci: experimental Windows build job
type: Task
labels: milestone::M5, type::task, priority::low, ci
parent: 7
blocked_by: 72
---
> **Risk tier:** high · **Size:** M · **When:** only after Flathub (#72), per proposal §15

## Why

The brief says "If possible also cross-platform". The architecture keeps that door open at no cost: `dailies/core` is pure Python, WebKit is optional (`HAVE_WEBKIT`), there's no `flatpak-spawn` dependency, and Blueprint/Meson build the same way on MSYS2. Two hard limits apply:

- **WebKitGTK does not exist on Windows** (no port since 2.4 in 2014, no MSYS2 package). The built-in browser is Linux-only in every language; Windows uses the default browser only.
- Windows CSD problems (black border, giant shadows, no snapping) **may** be fixed in GTK 4.24, but no post-4.24 report confirms it **[U]**.

## Tasks

- [ ] A `windows` job in `ci.yml` (or a separate workflow) with **`continue-on-error: true`**, modelled on Cartridges' MSYS2 UCRT64 job ([`stack-crossplatform.md` Appendix A.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/stack-crossplatform.md)): `msys2/setup-msys2` (pinned SHA), install `mingw-w64-ucrt-x86_64-{gtk4,libadwaita,python-gobject,blueprint-compiler,meson}`, `meson setup`, `meson install`
- [ ] Add a Meson option `-Ddecorations=no-csd` (Cartero's pattern) and use it on Windows if CSD is still broken
- [ ] i18n/gresources: Cartridges 2.13.1 disables i18n on Windows because gresources and gettext were broken there; test whether that still holds
- [ ] Optional Inno Setup installer from [`stack-crossplatform.md` Appendix A.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/stack-crossplatform.md); `.ico` generated from the 128 px SVG
- [ ] Label the artifact **experimental**. **No GitHub Release asset** until someone has tested it on real hardware
- [ ] macOS (Homebrew + PyInstaller; Apple Silicon bottles only) is a separate, later issue

## Acceptance criteria

- [ ] The job produces an installable artifact that launches, shows the catalog and opens games in the default browser; the built-in option is hidden
- [ ] A failing Windows job never blocks merges

## References

- [`mvp-first.md` §15](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`stack-crossplatform.md` §1.3, §1.4, §3, Appendix A](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/stack-crossplatform.md)
