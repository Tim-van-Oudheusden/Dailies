---
key: 19
title: spike: verify GNOME 51 SDK assumptions (Blueprint skeletons, Adw.Sidebar from Python, runtime versions)
type: Task
labels: spike, milestone::M0, type::task, priority::high, app
parent: 2
---
> **Time box:** 1 day · **Output:** a short findings comment on this issue plus compiled `.blp` files in a throwaway branch

## Why

The UI design rests on facts the research could **not** verify (**[U]** in [`mvp-first.md` §4, §17 risk 7, §19](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)):

- The five Blueprint skeletons in [`libadwaita-ui-patterns.md` Appendix A](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md) (window, game tile, preferences, browser view, shortcuts dialog) were hand-checked against the v0.22 grammar but **never compiled**.
- `Adw.Sidebar` (libadwaita ≥ 1.9) has never been exercised from PyGObject in the research; Cartridges' `rewrite` uses it, and that branch is partly non-functional.
- The Python version in runtime 51 is assumed to be 3.14; only 3.13.15 in runtime 49 was measured.

Settling these before #24 and #41 avoids building on a broken API.

## Tasks

- [ ] `flatpak install --user flathub org.gnome.Sdk//51 org.gnome.Platform//51`
- [ ] Inside the SDK (`flatpak run --command=bash org.gnome.Sdk//51`), run `blueprint-compiler --version` and expect **0.22.2**
- [ ] Copy the five skeletons from `libadwaita-ui-patterns.md` Appendix A.1–A.5 and compile each with `blueprint-compiler compile`. Record and fix every error, and note any grammar differences
- [ ] Write a ~60-line PyGObject script that builds an `Adw.ApplicationWindow` → `Adw.NavigationSplitView` with an `Adw.Sidebar` holding three sections (title-less "Favorites", "This Week" with two items, "Categories" with items appended at runtime). Connect `activated`, and confirm the `selected` property works for restoring the last section
- [ ] Record `python3 --version`, `python3 -c "import gi; print(gi.__version__)"`, GTK, libadwaita and WebKitGTK versions inside Platform 51. Check that `gi.require_version('WebKit', '6.0')` and `from gi.repository import WebKit` succeed
- [ ] Confirm `ghcr.io/flathub-infra/flatpak-github-actions:gnome-51` can be pulled. `flatpak-release-pipeline.md` §1.1 verified it exists; two older reports said only gnome-48 existed
- [ ] Check `Gtk.UriLauncher` and the libadwaita colour variables `--success-bg-color`, `--warning-bg-color`, `--error-bg-color` against the 4.24 / 1.10 docs. Both were cited from memory

## Acceptance criteria

- [ ] All five `.blp` skeletons compile in `org.gnome.Sdk//51`; the corrected versions are attached or pushed to a branch for #24/#41/#42/#46/#47/#48 to start from
- [ ] A findings comment states: Python version, PyGObject version, whether `Adw.Sidebar` works from Python (**go**), or the fallback (`GtkListBox` with `.navigation-sidebar`, as in Cartridges `main`) is needed (**no-go**)
- [ ] If anything forces a design change (e.g. the Sidebar fallback), update #41 before closing

## References

- [`libadwaita-ui-patterns.md` §1, §2.4, §13, Appendix A, open questions](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
- [`stack-crossplatform.md` §1.1, §1.5, §4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/stack-crossplatform.md)
- [`cartridges.md` §5.3, Appendix C.1 (rewrite window with Adw.Sidebar)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)
