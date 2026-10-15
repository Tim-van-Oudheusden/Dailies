# Dailies — Implementation stack & cross-platform research (key: `stack-crossplatform`)

Research date: 2026-10-15. All version numbers were checked on that date unless stated otherwise.
Legend: **[V]** = verified against a primary source (URL given), **[I]** = inference / judgement, **[U]** = could not be verified.

---

## 0. Executive summary

* **Recommendation: Python 3 + PyGObject, Blueprint UI files, Meson build, Flatpak on `org.gnome.Platform//51`, WebKitGTK 6.0 for the built-in browser on Linux only.** This is exactly the stack of Cartridges (the UI reference the owner named), which already ships Flatpak + Windows (MSYS2 + Inno Setup) + macOS (Homebrew + PyInstaller `.app`) from one `meson.build` and one GitHub Actions workflow that Dailies can copy almost verbatim (reproduced in Appendix A). [V]
* **Fallback / alternative: Rust (gtk4-rs 0.11.5 + libadwaita-rs 0.9.2).** Cartero and Rnote prove the same Flatpak + Windows (MSYS2, x64 **and** arm64) + macOS (jhb/gtk-osx DMG) story for Rust with a GNOME-native look. Choose Rust if startup time, single-binary distribution or static typing turn out to matter more than contributor accessibility and development speed. [V for the examples, I for the trade-off]
* **Cross-platform is feasible but second-class.** libadwaita 1.10.0 and GTK 4.24.1 are packaged for Windows (MSYS2) and macOS (Homebrew) today, dark/light + accent colour follow the OS, but there are no native window controls, Windows has GPU-driver and shadow/snapping caveats, and GTK developers themselves say stability is lower. [V]
* **The built-in browser cannot be cross-platform with this toolkit.** WebKitGTK has no Windows build since 2.4 (2014) and the Homebrew `webkitgtk` formula is Linux-only; there is no MSYS2 package at all. Dailies' browser preference chain must therefore be: *configured command → embedded WebKitGTK view (Linux/Flatpak builds only) → `Gtk.UriLauncher` external browser*; on Windows/macOS the middle step is compiled out. [V]
* **Exact targets:** GNOME runtime **51** (GTK **4.24.0**, libadwaita **1.10.0**, WebKitGTK **2.54.1** (`webkitgtk-6.0` API), PyGObject **3.58.0**, GJS 1.90.0, blueprint-compiler 0.22.2 pinned in the SDK). Keep `meson.build` minimums at `gtk4 >= 4.24`, `libadwaita-1 >= 1.10`, `webkitgtk-6.0 >= 2.54` (optional dependency). GNOME **50** (GTK 4.22, libadwaita 1.9, WebKitGTK 2.54.1) is the one-step fallback; GNOME 48 is EOL on Flathub since 2026-03-24 and 49 will be EOL'd imminently. [V]

---

## 1. Platform facts that frame the decision

### 1.1 Current GTK / libadwaita / WebKitGTK versions

| Component | Latest stable | Date | Source |
|---|---|---|---|
| GTK | 4.24.1 (4.24.0 = GNOME 51) | 2026-10-01 (4.24.0: 2026-09-11) | GTK `NEWS` [V] |
| GTK (GNOME 50) | 4.22.0 | 2026-03-06 | GTK `NEWS` [V] |
| GTK (GNOME 49) | 4.20.0 / 4.20.1 | 2025-08-29 / 2025-09-08 | GTK `NEWS` [V] |
| libadwaita | 1.10.0 (GNOME 51) | tag 2026-09-14 | libadwaita tags API [V] |
| libadwaita | 1.9.4 / 1.8.8 maintenance | tags 2026-09-14 | same [V] |
| libadwaita 1.10 requires | GTK ≥ 4.23.1 (1.10.alpha), GLib 2.89.3 | — | libadwaita `NEWS` [V] |
| WebKitGTK | 2.54.1 (stable), 2.54.0 2026-09-16 | 2026-10-02 | webkitgtk.org/news [V] |
| blueprint-compiler | 0.22.2 | 2026-07-10 | GitLab tags [V] |
| PyGObject | 3.58.1 (requires Python ≥ 3.10, **sdist only, no wheels**) | 2026-10-09 | PyPI JSON [V] |
| gtk4-rs `gtk4` crate | 0.11.5 (features up to `v4_24`) | 2026-09-20 | crates.io / docs.rs [V] |
| libadwaita-rs crate | 0.9.2 (features `v1_1`..`v1_10`, `gtk_v4_24`) | 2026-07-07 | crates.io / docs.rs [V] |
| gvsbuild | 2026.8.0 (ships `GTK4_Gvsbuild_2026.8.0_x64.zip`; has `libadwaita.py`, `pygobject.py` projects) | 2026-08-08 | `gh api repos/wingtk/gvsbuild/releases/latest` [V] |

libadwaita 1.8 (GNOME 49, Sept 2025) added `AdwShortcutsDialog`, full CSS media-query support and the `.document` style; 1.9 (GNOME 50) added `AdwSidebar`/`AdwViewSwitcherSidebar` and reduced-motion support; 1.10 (GNOME 51) added `AdwCssClassBinding`, `:prefix`/`:suffix` on `AdwSidebar`, swapped appstream for "ministream", and — relevant here — *"resolves the locale directory at runtime on Windows"* and added an Android settings backend. [V: libadwaita NEWS, linuxiac/phoronix coverage]

### 1.2 Flathub GNOME runtimes (checked with `flatpak --user remote-ls/remote-info flathub` on 2026-10-15) [V]

| Runtime | Status | Pinned contents (gnome-build-meta branch) |
|---|---|---|
| `org.gnome.Platform//48` | **EOL**: "The GNOME 48 runtime is no longer supported as of March 24, 2026" | — |
| `org.gnome.Platform//49` | still published (build 49.10, 2026-10-03), **no EOL flag yet** | GTK 4.20.4, libadwaita 1.8.8, WebKitGTK 2.54.1 |
| `org.gnome.Platform//50` | published (50.5, 2026-10-03) | GTK 4.22.x [I], libadwaita 1.9.x [I], WebKitGTK 2.54.1 [V] |
| `org.gnome.Platform//51` | published (51.0-14, 2026-10-14) | GTK 4.24.0, libadwaita 1.10.0, WebKitGTK 2.54.1, PyGObject 3.58.0, GJS 1.90.0, blueprint-compiler 0.22.2, vala, pygobject all in `elements/sdk/` |

Sources: `https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/{gtk,libadwaita,webkitgtk-6.0,blueprint-compiler,pygobject,gjs}.bst` and `webkitgtk.inc`; `gnome-49` and `gnome-50` branches for the fallback rows. The GNOME 51 SDK `elements/sdk/` listing (59 elements) includes `blueprint-compiler.bst`, `gjs.bst`, `vala.bst`, `pygobject.bst`, `libadwaita.bst`, `gtk.bst`, `webkitgtk-6.0.bst`, `webkit2gtk-4.1.bst` — i.e. **Blueprint, Vala, PyGObject and GJS are all in the SDK; no SDK extension is needed for Python, Vala, C or GJS**. Rust needs `org.freedesktop.Sdk.Extension.rust-stable//26.08`; TypeScript needs `org.freedesktop.Sdk.Extension.typescript//26.08` (TypeScript 5.9.3, pulls `node26`). [V]

Flathub policy: runtimes are "usually supported for a year and EOL-ed upon the release of a new stable version"; submissions must use the latest runtime available at submission time; apps "persistently behind at least 3 runtime updates" can be marked EOL after a one-month notice. [V: docs.flatpak.org available-runtimes, docs.flathub.org requirements + maintenance]. GNOME 48 was EOL'd six days after GNOME 50.0 shipped, so **expect 49 to be EOL'd any day now** (51.0 shipped 2026-09-16; 52.0 is scheduled 2027-03-17) [V dates, I on timing].

### 1.3 Libadwaita on Windows and macOS (status 2025-2026)

Verified facts:
* MSYS2 packages `mingw-w64-libadwaita` **1.10.0-2**, `mingw-w64-gjs` 1.90.1-2, `mingw-w64-vala` 0.56.19-3, `mingw-w64-blueprint-compiler` **0.18.0-3** (page notes "newer upstream version 0.22.2"), `mingw-w64-ucrt-x86_64-python-gobject` **3.58.1-1** (Python 3.14) — all updated 2026-10-15; variants ucrt64 / clang64 / clangarm64 / mingw64. [V: packages.msys2.org]
* Homebrew: `libadwaita` 1.10.0 (deps gtk4 4.24.1, glib 2.90.1), `gjs` 1.90.1, `vala` 0.56.19, `blueprint-compiler` 0.22.2, `pygobject3` 3.58.1 (python@3.14). **Bottles are listed only for Apple Silicon (sequoia/tahoe/"golden gate")**; Intel builds from source (Gaphor still runs `macos-15-intel` runners with brew, so it works, just slower). [V: formulae.brew.sh]
* libadwaita has native (non-portal) implementations of dark-mode, accent colour and high-contrast detection on Windows and macOS. [V: GNOME Discourse 18497, Jason Francis 2023-12-10; NEWS entries]
* No platform-native window-control styles exist: "There is no built in styles for those, but you can create a custom style for other platforms." [V: Discourse 18497]
* GNOME Discourse 29181 (May 2025): "It will work on Windows, but from experience, I'd say that the stability you can expect is less" (Jamie Gravendeel); "gigantic shadows that block clicks on objects behind them", "lacks native Windows features such as snapping and tiling", occasional DnD freezes, "font rendering is suboptimal", suggestion to publish via MSYS2 (gwillems). [V]
* Rnote README (Rust/libadwaita, Windows installer): "On Windows: the application window is surrounded by a black border instead of a shadow … a bug with the underlying UI toolkit GTK4". GTK `NEWS` says 4.23.0 "fixed black borders around windows (#7567)", and GTK 4.19.2 moved Windows to DirectX 11/12 + DirectComposition; 4.21.5 added win32 session-end/inhibit, 4.21.6 fixed the native file chooser. macOS: 4.19.2 window snapping + native menu, 4.21.5 reliable native window-control location, 4.24.0 default Edit menu entries. So **GTK 4.24 is the first series where the known Windows CSD complaints are addressed** — but no post-4.24 user report confirms this. [V on NEWS; I on the conclusion]
* Cartero (Rust) builds its Windows version with `-Ddecorations=no-csd` — i.e. it turns off client-side decorations on Windows and lets Windows draw the title bar. This is a pragmatic pattern Dailies should copy (a meson/runtime switch for `AdwHeaderBar` vs. server-side decorations). [V: cartero/.github/workflows/build.yaml]
* libadwaita-rs issue #30: STATUS_STACK_OVERFLOW with libadwaita 1.4 built by gvsbuild under MSVC (old; status today [U]).

### 1.4 WebKitGTK availability off Linux (critical for the built-in browser)

* "The last version of WebKitGTK to support Windows was 2.4, from 2014" (WebKitGTK maintainer, webkit-gtk list). [V]
* GNOME Discourse 28611 (Apr–May 2025), Michael Catanzaro (WebKitGTK maintainer): "WebKit does support Windows, but WebKitGTK does not … The ongoing maintenance required to keep WebKitGTK working on Windows will surely be more expensive." Emmanuele Bassi: "Chromium already supports GTK4". No one in the thread recommends a working cross-platform GTK4 webview. [V]
* MSYS2: **no `webkitgtk` package of any variant**. Homebrew `webkitgtk` 2.54.1 exists but **"requires Linux"**, bottles for Linux only (depends on gtk+3, systemd, wayland, mesa). [V]
* 2025 FOSDEM WebKitGTK/WPE talk and 2026 release notes talk only about Linux (and Android). [V]
* Consequence [I]: the embedded-browser feature is **Linux/Flatpak-only**, in **every** language. On Windows/macOS the only realistic options are an external browser (`Gtk.UriLauncher`, GTK ≥ 4.10) or a separate non-GTK webview (WebView2 on Windows, WKWebView on macOS) embedded via a foreign window — the latter is unproven with GTK4 and not recommended for v1.

### 1.5 Blueprint

* Blueprint is a markup language + compiler (`blueprint-compiler`) that converts `.blp` into GtkBuilder XML at build time; "The compiler's only dependency is Python, and it can be included as a meson subproject"; it needs `Gtk-4.0.typelib` (and any other imported namespace's typelib, e.g. `Adw-1`) at compile time. It is therefore **language-agnostic** — Cartridges (Python), Cartero (Rust), Bazaar (C, 59 `.blp` files) all use it. [V: blueprint docs setup/packaging pages; the three repos]
* Version skew: SDK 51 and Homebrew ship 0.22.2, **MSYS2 ships 0.18.0** → use the Meson wrap subproject pinned to a tag so every platform compiles with the same version (Appendix C). [V versions, I recommendation]

### 1.6 Flatpak CI tooling

* `flathub-infra/flatpak-github-actions` was archived 2025-04-24; the action is back upstream as `flatpak/flatpak-github-actions/flatpak-builder@v6`, while **images stay at `ghcr.io/flathub-infra/flatpak-github-actions:<tag>`** (built from `flathub-infra/actions-images`). Gaphor uses `gnome-50`; README shows `gnome-48`; a `gnome-51` tag was **not verified** [U] — check `https://github.com/flathub-infra/actions-images` before pinning. [V]
* `flatpak/flatpak-builder-tools` (latest commit 2026-09-30) provides `pip/flatpak-pip-generator` (`--runtime org.freedesktop.Sdk//26.08 --requirements-file requirements.txt --output pypi-dependencies`, prefers universal wheels > sdists, `--prefer-wheels=` for binary wheels), `cargo/flatpak-cargo-generator.py Cargo.lock -o cargo-sources.json`, `node/flatpak-node-generator`. Note the GitHub org is **`flatpak`**, not `flathub`. [V]
* Flathub app-ID rule for GitHub projects: `io.github.<user>.<Project>` with ≥ 4 components, domain part lower-case with dashes → underscores → **`io.github.tim_van_oudheusden.Dailies`**; manifest file must be named after the ID (`io.github.tim_van_oudheusden.Dailies.json|yml`). [V: docs.flathub.org requirements]

---

## 2. Language comparison

Scores: ● good · ◐ workable with caveats · ○ poor/unverified.

| Criterion | Python + PyGObject | Rust + gtk4-rs/libadwaita-rs | Vala | C | GJS (+TypeScript) |
|---|---|---|---|---|---|
| Libadwaita 1.10 API coverage | ● (GI, immediate) | ● (`libadwaita` 0.9.2 has `v1_10`) | ● (vapi in SDK) | ● | ● (GI) |
| Blueprint | ● | ● | ● | ● | ● |
| Flatpak packaging | ● PyGObject in SDK; pip deps via `flatpak-pip-generator` (or zero deps by using `Soup`/`Gio` through GI) | ● `rust-stable` ext + `flatpak-cargo-generator`; offline build ~minutes | ● valac in SDK, no extension | ● | ● gjs in Platform; TS needs `typescript` + `node26` extensions and a bundler |
| Windows build | ● MSYS2 pacman (`python-gobject`, `libadwaita`) + Inno (Cartridges, Varia) **or** gvsbuild + PyInstaller + NSIS (Gaphor); winget via `wingetcreate` | ● MSYS2 `rust` + Inno (Rnote, Cartero incl. **arm64 via clangarm64**) or MSVC + gvsbuild | ◐ MSYS2 `vala` exists; no verified shipping libadwaita Vala app found (Dino README says "for Linux") | ◐ same toolchain as Vala | ○ MSYS2 `gjs` exists, but no verified GJS app shipping a Windows installer; would need to bundle `gjs.exe`+mozjs |
| macOS build | ● Homebrew + PyInstaller `BUNDLE` (Cartridges), + create-dmg + signing/notarization (Gaphor) | ● jhb/gtk-osx-based relocatable SDK + DMG (Cartero; Rnote via dehesselle) | ◐ brew `vala`; same bundling problem as C | ◐ gtk-mac-bundler still maintained (commits 2026-07-10) | ○ brew `gjs` exists; no bundling precedent |
| Shipping examples with libadwaita on Win+mac | Cartridges (Win+mac), Gaphor (Win+mac, signed+notarized), Varia (Win + experimental mac) | Cartero (Win x64/arm64 + mac x64/arm64), Rnote (Win; mac by 3rd party) | none verified | Bazaar is C but Linux-only | none verified |
| Maintenance cost | low: small code, no compile step, PyInstaller/gi hooks mature | medium: compile times, two crate versions to bump in lock-step, GNOME Rust crates release ~2×/yr | medium: small community, fewer examples | high for app-level code | medium; TS toolchain adds moving parts |
| Startup time | ◐ interpreter + `gi` import on top of GTK/Adw init [I] | ● native binary [I] | ● | ● | ◐ JS engine init [I] |
| Contributor accessibility (issue-driven open source) | ● | ◐ | ◐ | ○ | ◐ |

Notes:
* GNOME Discourse reports of "2–3 s" libadwaita startup refer to GNOME 42-era icon/CSS loading and are not language-specific; no public Python-vs-Rust launch benchmark exists. Measure Dailies with `sysprof`/`hyperfine` in the Flatpak before deciding it matters. [V on the lack of data, I on expectations]
* PyGObject ships **no wheels** → on Windows/macOS it comes from MSYS2 / Homebrew / gvsbuild's `wheels/` folder, never from `pip install`. Gaphor notes "gtksourceview5 and libadwaita are not available as anaconda packages". [V]
* Cartridges `meson.build` disables i18n on Windows: "Translations are broken on Windows for multiple reasons: gresources don't work and MSYS2 seems to have also broken the gettext package" (comment in file). libadwaita 1.10 fixed its own locale-dir lookup on Windows; the gresource/gettext issue for Python apps is still something to test. [V quote, U current status]

---

## 3. Recommendation for Dailies

### 3.1 Primary stack (recommended)

| Layer | Choice | Version / id |
|---|---|---|
| Language | Python 3 (SDK's Python; 3.14 in MSYS2/Homebrew) | PyGObject 3.58.x |
| UI | GTK 4 + libadwaita, Blueprint `.blp` → gresource | `gtk4 >= 4.24`, `libadwaita-1 >= 1.10`, blueprint-compiler 0.22.2 (meson wrap) |
| Build | Meson + `gnome` module (`compile_resources`, `compile_schemas`, `post_install`) | meson ≥ 1.4 |
| Flatpak | `org.gnome.Platform` / `org.gnome.Sdk` **51**; no SDK extensions | manifest `io.github.tim_van_oudheusden.Dailies.json` (+ `.Devel` variant) |
| HTTP (popularity/DLE list from GitHub) | `Soup 3` / `Gio.File` via GI → **zero pip dependencies** | in runtime; avoids `flatpak-pip-generator` entirely and keeps Windows/macOS deps to `python-gobject` |
| Built-in browser | `WebKit 6.0` via GI, imported lazily behind `try/except`, enabled only when `gi.require_version('WebKit','6.0')` succeeds | WebKitGTK 2.54.1 in runtime; absent on Windows/macOS |
| External browser | `Gtk.UriLauncher` (portal-aware in Flatpak) | GTK ≥ 4.10 |
| Configured browser | `Gio.Subprocess` with user command, or `flatpak-spawn --host` under Flatpak (needs `--talk-name=org.freedesktop.Flatpak`) [I] | — |
| Windows | MSYS2 UCRT64 `pacman` + `meson install` + Inno Setup 6 → `.exe`; optional portable zip; later `wingetcreate` | copy Cartridges `ci.yml`/`Cartridges.iss.in` |
| macOS | Homebrew (`pygobject3 libadwaita adwaita-icon-theme pyinstaller`) + `pyinstaller dailies.spec` → `Dailies.app` zip; signing/notarization later (Gaphor pattern) | copy `cartridges.spec` |
| Rust alternative | gtk4 0.11.5 (`v4_24`) + libadwaita 0.9.2 (`v1_10`), `org.freedesktop.Sdk.Extension.rust-stable//26.08`, `flatpak-cargo-generator` | only if §3.3 triggers |

Rationale:
1. **Reference parity.** The owner's own UI reference (Cartridges) is Python + Blueprint + Meson with working Flatpak/Windows/macOS automation; copying a proven pipeline minimises risk for a one-maintainer project. Bazaar (C, 59 `.blp` files, GNOME 50 runtime, `llvm20` extension) demonstrates the look but is not a sensible model for an app this small.
2. **Workload fit.** Dailies is a data-driven launcher (fetch JSON → list/grid → favourites → open URL). There is no CPU-bound work that would justify Rust's compile/maintenance cost; Python keeps the agentic/GitHub-Actions tooling (popularity report) and the app in the same language.
3. **Flatpak simplicity.** With `Soup`/`Gio`/`Json` from the runtime, the manifest has a single `meson` module and no generated dependency JSON; no SDK extension; builds in seconds.
4. **Cross-platform at low marginal cost.** Two extra CI jobs (≈ 60 lines each, Appendix A) produce an Inno installer and a `.app`. Unsigned builds are acceptable for "best effort" status; signing can be added later (Gaphor shows SignPath/Apple notarization).
5. **Contributor-friendliness.** DLE submissions through issues imply a broad contributor base; Python lowers the bar for fixes to parsers/data code.

### 3.2 What to decide now about the browser chain

* Preference order stays as the brief says, but the middle step is **conditional on `WebKit 6.0` being importable**. Settings UI should hide the "built-in browser" option when unavailable (Windows/macOS/non-Flatpak Linux without webkitgtk6.0).
* Flatpak permissions needed: `--share=network`, `--share=ipc`, `--socket=wayland`, `--socket=fallback-x11`, `--device=dri`; WebKitGTK inside Flatpak needs no extra permission (it uses bubblewrap internally; `dummy-gbm` is part of the runtime). For "configured external browser" prefer the portal (`Gtk.UriLauncher`) rather than `--talk-name=org.freedesktop.Flatpak` unless users demand arbitrary commands. [I, grounded in Cartridges/Bazaar finish-args]
* Treat the embedded browser as a *WebKitGTK* feature, not a *Dailies* feature: the game pages are third-party websites; cookies/local-storage persistence should use `WebKit.NetworkSession` with a data dir under `GLib.get_user_data_dir()` so streaks survive restarts (API present in 6.0). [I]

### 3.3 Fallback plan

| Trigger | Fallback |
|---|---|
| PyInstaller/gi hooks or MSYS2 Python packaging breaks repeatedly, or startup in Flatpak measured > ~1 s on a modern laptop | Port to **Rust** (same `.blp`, same Meson layout, same manifest apart from `sdk-extensions: [org.freedesktop.Sdk.Extension.rust-stable]`, `append-path: /usr/lib/sdk/rust-stable/bin`, `cargo-sources.json`). Cartero's `build.yaml` is the template for Win x64/arm64 + macOS. |
| Windows/macOS maintenance exceeds appetite | Declare Flatpak the only supported channel; keep CI jobs as `continue-on-error`, publish unsigned artifacts labelled "experimental", exactly as Varia does for macOS. |
| GNOME 51 runtime causes a regression | Drop to `runtime-version: "50"` (GTK 4.22, libadwaita 1.9, same WebKitGTK 2.54.1) and lower meson minimums to `gtk4 >= 4.22`, `libadwaita-1 >= 1.9`; avoid `AdwCssClassBinding`. |
| Users want the embedded browser on Windows | Out of scope for GTK; the only verified route is a non-GTK engine (CEF/WebView2) — treat as a research spike, not a roadmap item. |

### 3.4 Things explicitly NOT recommended
* **GJS/TypeScript**: excellent inside Flatpak (gjs 1.90 in the Platform, `typescript` 5.9.3 extension, `@girs/gjs`/`@girs/gtk-4.0` typings from ts-for-gir), but no verified GJS app ships Windows/macOS bundles; bundling SpiderMonkey + `gjs.exe` is uncharted.
* **Vala / C**: fully supported in the SDK and MSYS2/Homebrew, but Dailies gains nothing from them and no cross-platform libadwaita app written in either could be verified.
* **MSIX / Microsoft Store**: no GTK4/libadwaita app using MSIX could be found; all verified projects use Inno Setup (Cartridges, Rnote, Cartero) or NSIS (Gaphor) and publish to winget with `wingetcreate` (Gaphor, Cartero) or Scoop (Cartero). [V on absence of examples]
* **gvsbuild (MSVC) for a Python app**: works (Gaphor), but requires re-installing PyGObject/pycairo wheels from `C:\gtk\wheels` into every venv and maintaining `INCLUDE`/`LIB`/`GI_TYPELIB_PATH`; MSYS2 is simpler for a Meson project.

---

## 4. Open questions (for the architecture doc / first spikes)

1. Does `ghcr.io/flathub-infra/flatpak-github-actions:gnome-51` exist yet? If not, use `gnome-50` image with `runtime-version: "51"` (the image only needs flatpak-builder; runtimes are downloaded) — unverified whether that works offline-cache-wise.
2. Are the Windows CSD problems (black border, giant shadows) gone with GTK 4.24 in MSYS2? Need a smoke test; otherwise ship with server-side decorations on Windows (`Gtk.Window.set_decorated(True)` + no `AdwHeaderBar`) like Cartero's `-Ddecorations=no-csd`.
3. Do gresources + gettext work for a Python app on MSYS2 today (Cartridges says no as of its last release 2.13.1)? Dailies can ship English-only on Windows initially.
4. Intel macOS: Homebrew bottles are Apple-Silicon-only for libadwaita/pygobject3 → decide whether to support x86_64 macOS (slow from-source CI) or Apple Silicon only.
5. Python version inside GNOME 51 / freedesktop 26.08 runtime not verified (likely 3.14); pin nothing below 3.12 in code.
6. Startup-time budget: measure `flatpak run` cold/warm with `hyperfine` once the skeleton exists.
7. Whether `--talk-name=org.freedesktop.Flatpak` (host command execution for "configured browser") is acceptable for Flathub review; Cartridges has it, but Flathub prefers portals.

---

## Appendix A — Cartridges (Python) files to copy (verbatim from `kra-mo/cartridges`, commit d56323e, 2026-09-03)

### A.1 Flatpak manifest `build-aux/flatpak/page.kramo.Cartridges.Devel.json` (trimmed to the parts relevant for Dailies)
```json
{
  "id": "page.kramo.Cartridges.Devel",
  "runtime": "org.gnome.Platform",
  "runtime-version": "49",
  "sdk": "org.gnome.Sdk",
  "command": "cartridges",
  "finish-args": [
    "--share=network",
    "--share=ipc",
    "--socket=fallback-x11",
    "--device=dri",
    "--socket=wayland",
    "--talk-name=org.freedesktop.Flatpak"
  ],
  "cleanup": ["/include", "/lib/pkgconfig", "/man", "/share/doc", "/share/gtk-doc",
              "/share/man", "/share/pkgconfig", "*.la", "*.a"],
  "modules": [
    {
      "name": "python3-requests",
      "buildsystem": "simple",
      "build-commands": [
        "pip3 install --verbose --exists-action=i --no-index --find-links=\"file://${PWD}\" --prefix=${FLATPAK_DEST} \"requests\" --no-build-isolation"
      ],
      "sources": [
        {"type": "file",
         "url": "https://files.pythonhosted.org/packages/1e/db/4254e3eabe8020b458f1a747140d32277ec7a271daf1d235b70dc0b4e6e3/requests-2.32.5-py3-none-any.whl",
         "sha256": "2462f94637a34fd532264295e186976db0f5d453d1cdd31473c85a6a161affb6"}
      ]
    },
    {
      "name": "cartridges",
      "builddir": true,
      "buildsystem": "meson",
      "run-tests": true,
      "config-opts": ["-Dprofile=development"],
      "sources": [{"type": "dir", "path": "../.."}]
    }
  ]
}
```
(The `python3-*` modules are exactly what `flatpak-pip-generator` emits; Dailies can drop them by using `Soup`.)

### A.2 `meson.build` (head) — platform switches
```meson
project('cartridges', version: '2.13.1', meson_version: '>= 0.59.0',
  default_options: ['warning_level=2', 'werror=false'])

dependency('gtk4', version: '>= 4.15.0')
dependency('libadwaita-1', version: '>= 1.6.beta')

# Translations are broken on Windows for multiple reasons
# gresources don't work and MSYS2 seems to have also broken the gettext package
if host_machine.system() != 'windows'
  i18n = import('i18n')
endif

gnome = import('gnome')
python = import('python')
py_installation = python.find_installation('python3')
...
if host_machine.system() == 'windows'
  subdir('build-aux/windows')
else
  subdir('search-provider')
  subdir('po')
endif
```
`data/meson.build` compiles Blueprint with `find_program('blueprint-compiler')` (no wrap — relies on the SDK/MSYS2/brew copy):
```meson
blueprints = custom_target('blueprints',
  input: files('gtk/details-dialog.blp', 'gtk/game.blp', 'gtk/preferences.blp',
               'gtk/shortcuts-dialog.blp', 'gtk/window.blp'),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)
```

### A.3 `.github/workflows/ci.yml`
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
concurrency:
  group: release-${{ github.sha }}
jobs:
  flatpak:
    name: Flatpak
    runs-on: ubuntu-latest
    container:
      image: bilelmoussaoui/flatpak-github-actions:gnome-47   # Dailies: ghcr.io/flathub-infra/flatpak-github-actions:gnome-51 (verify tag) 
      options: --privileged
    steps:
      - uses: actions/checkout@v4
      - uses: flatpak/flatpak-github-actions/flatpak-builder@v6.5
        with:
          bundle: page.kramo.Cartridges.Devel.flatpak
          manifest-path: build-aux/flatpak/page.kramo.Cartridges.Devel.json

  windows:
    name: Windows
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup MSYS2
        uses: msys2/setup-msys2@v2
        with:
          msystem: UCRT64
          update: true
          install: mingw-w64-ucrt-x86_64-gtk4 mingw-w64-ucrt-x86_64-libadwaita mingw-w64-ucrt-x86_64-python-gobject mingw-w64-ucrt-x86_64-python-yaml mingw-w64-ucrt-x86_64-python-requests mingw-w64-ucrt-x86_64-python-pillow mingw-w64-ucrt-x86_64-desktop-file-utils mingw-w64-ucrt-x86_64-ca-certificates mingw-w64-ucrt-x86_64-meson git
      - name: Compile
        shell: msys2 {0}
        run: |
          meson setup _build
          ninja -C _build install
          pacman --noconfirm -Rs mingw-w64-ucrt-x86_64-desktop-file-utils mingw-w64-ucrt-x86_64-meson git
      - name: Test
        shell: msys2 {0}
        run: |
          set +e
          timeout 2 cartridges; [ "$?" -eq "124" ]
      - name: Inno Setup
        run: iscc ".\_build\build-aux\windows\Cartridges.iss"
      - uses: actions/upload-artifact@v4
        with:
          name: Windows Installer
          path: _build/build-aux/windows/Output/Cartridges Windows.exe

  macos:
    name: macOS
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Homebrew/actions/setup-homebrew@master
      - name: Install Dependencies
        run: |
          brew install meson pygobject3 libadwaita adwaita-icon-theme desktop-file-utils pyinstaller pillow
          pip3 install --break-system-packages requests PyYAML
      - name: Meson Build
        run: |
          meson setup _build -Dtiff_compression=jpeg
          ninja install -C _build
      - name: PyInstaller
        env:
          PYTHONPATH: /opt/homebrew/opt/homebrew/lib/python3.12/site-packages
        run: |
          cd build-aux/macos
          pyinstaller ./cartridges.spec
      - name: Zip
        run: |
          cd build-aux/macos/dist
          zip -yr Cartridges\ macOS.zip Cartridges.app
      - uses: actions/upload-artifact@v4
        with:
          path: build-aux/macos/dist/Cartridges macOS.zip
          name: macOS Application
```
`publish-release.yml` (on tag push) downloads the `ci.yml` artifacts with `dawidd6/action-download-artifact@v9`, extracts the latest `<release>` body from `data/page.kramo.Cartridges.metainfo.xml.in` with a small Python regex, and publishes with `softprops/action-gh-release@v2.2.2` (`files: Windows Installer/Cartridges Windows.exe`, `macOS Application/Cartridges macOS.zip`, `fail_on_unmatched_files: true`, `body_path: release_notes`). The Flatpak bundle is *not* attached to releases; add the `.flatpak` bundle artifact for Dailies.

### A.4 `build-aux/windows/Cartridges.iss.in` (Inno Setup; `[Files]` shows exactly which MSYS2 pieces are shipped)
```ini
#define MyAppName "Cartridges"
#define MyAppVersion "@VERSION@"
#define MyAppPublisher "kramo"
#define MyAppURL "https://apps.gnome.org/Cartridges/"
#define MyAppExeName "pythonw.exe"

[Setup]
AppId={{BC3F8D32-4BDC-4715-B149-D79F589CD7F0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=https://git.kramo.page/cartridges/issues
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf64}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\..\LICENSE
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=Cartridges Windows
SetupIconFile=..\..\..\build-aux\windows\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "D:\a\_temp\msys64\ucrt64\bin\cartridges"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\bin\pythonw.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\bin\python.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\bin\gdbus.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\bin\gspawn-win64-helper.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\bin\gspawn-win64-helper-console.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\bin\*.dll"; DestDir: "{app}\bin"; Flags: recursesubdirs ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\etc\ssl\*"; DestDir: "{app}\etc\ssl"; Flags: recursesubdirs ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\lib\gdk-pixbuf-2.0\*"; DestDir: "{app}\lib\gdk-pixbuf-2.0"; Flags: recursesubdirs ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\lib\girepository-1.0\*"; DestDir: "{app}\lib\girepository-1.0"; Flags: recursesubdirs ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\lib\python@PYTHON_VERSION@\*"; DestDir: "{app}\lib\python@PYTHON_VERSION@"; Excludes: "__pycache__"; Flags: recursesubdirs ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\share\cartridges\*"; DestDir: "{app}\share\cartridges"; Excludes: "__pycache__"; Flags: recursesubdirs ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\share\icons\*"; DestDir: "{app}\share\icons"; Excludes: "*.png,cursors\*"; Flags: recursesubdirs ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\share\glib-2.0\*"; DestDir: "{app}\share\glib-2.0"; Flags: recursesubdirs ignoreversion
Source: "D:\a\_temp\msys64\ucrt64\share\gtk-4.0\*"; DestDir: "{app}\share\gtk-4.0"; Flags: recursesubdirs ignoreversion
Source: "..\..\..\build-aux\windows\icon.ico"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\bin\{#MyAppExeName}"; Parameters: """{app}\bin\cartridges"""; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\bin\{#MyAppExeName}"; Parameters: """{app}\bin\cartridges"""; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\bin\{#MyAppExeName}"; Parameters: """{app}\bin\cartridges"""; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall
```
`build-aux/windows/meson.build` is just `configure_file(input: './Cartridges.iss.in', output: 'Cartridges.iss', configuration: conf, install: true, install_dir: '.')`.

### A.5 `build-aux/macos/cartridges.spec` (PyInstaller)
```python
a = Analysis(
    ["../../_build/cartridges/cartridges"],
    pathex=[], binaries=[],
    datas=[("../../_build/data/cartridges.gresource", "Resources")],
    hiddenimports=[], hookspath=[],
    hooksconfig={"gi": {"module-versions": {"Gtk": "4.0"}}},
    runtime_hooks=[], excludes=[], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Cartridges", debug=False,
          bootloader_ignore_signals=False, strip=False, upx=True, console=False,
          disable_windowed_traceback=False, argv_emulation=False, target_arch=None,
          codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name="Cartridges")
app = BUNDLE(coll, name="Cartridges.app", icon="./icon.icns",
             bundle_identifier="page.kramo.Cartridges",
             info_plist={"LSApplicationCategoryType": "public.app-category.games"})
```
PyInstaller's `gi` hook options are `module-versions` (applies to `Gtk`, `Gdk`, `GtkSource`), `icons`, `themes`, `languages` (PyInstaller hooks-config docs). [V]

---

## Appendix B — Rust reference pipelines (fallback)

### B.1 Rnote `build-aux/com.github.flxzt.rnote.Devel.yaml` (head)
```yaml
id: com.github.flxzt.rnote.Devel
runtime: org.gnome.Platform
runtime-version: "50"
sdk: org.gnome.Sdk
sdk-extensions:
    - org.freedesktop.Sdk.Extension.rust-stable
command: rnote
finish-args:
    - "--socket=wayland"
    - "--socket=fallback-x11"
    - "--device=dri"
    - "--share=ipc"
build-options:
    append-path: "/usr/lib/sdk/rust-stable/bin"
    build-args:
        - "--share=network"
modules:
    - name: rnote
      buildsystem: meson
      run-tests: true
      config-opts: ["-Dprofile=devel", "-Dcli=true"]
```
Rnote `Cargo.toml`: `adw = { version = "0.9.2", package = "libadwaita", features = ["v1_9"] }`, `gtk4 = { version = "0.11.5", features = ["v4_22"] }`, `rust-version = "1.89"`.

Rnote `build_win_installer.yml` (on release): `runs-on: windows-2025`, installs Inno Setup 6.4.3 via `winget install -e --id JRSoftware.InnoSetup`, `msys2/setup-msys2` with `msystem: UCRT64`, `dtolnay/rust-toolchain` `toolchain: 1.95-gnu`, then `just ci=true prerequisites-win / setup-win-installer / build / build-win-installer`, uploads `_mesonbuild/rnote-win-installer-<ver>-x86_64.exe` with `gh release upload`.

### B.2 Cartero (Rust; Windows x64 + arm64, macOS x64 + arm64) — `.github/workflows/build.yaml` excerpts
```yaml
  win32:
    strategy:
      matrix:
        platform:
          - { runs-on: windows-latest,  name: x64,   msystem: ucrt64 }
          - { runs-on: windows-11-arm,  name: arm64, msystem: clangarm64 }
    defaults: { run: { shell: msys2 {0} } }
    steps:
      - uses: msys2/setup-msys2@v2
        with:
          update: true
          install: git zip
          pacboy: blueprint-compiler desktop-file-utils gcc gettext gtk4 gtksourceview5 jq libadwaita librsvg libxml2 meson pkgconf rust
          msystem: ${{ matrix.platform.msystem }}
      - name: Build Windows version
        run: |
          meson setup build -Dprofile=default -Ddecorations=no-csd -Dwin32-installer=enabled --prefix=\\
          DESTDIR=$PWD/build/cartero-win32 ninja -C build install
      - uses: Minionguyjpro/Inno-Setup-Action@v1.2.2
        with:
          path: build/packaging/win32/installer.iss
          options: /DSOURCE_DIR=${{ github.workspace }}/build/cartero-win32 /O+
```
macOS: `packaging/macos/jhbuild/main.sh` clones `https://gitlab.com/dehesselle/jhb`, sets `MACOSX_DEPLOYMENT_TARGET=11.0`, runs `jhb bootstrap && jhb configure modulesets/gnome-sdk.modules && jhb build gnome-sdk`, relocates Mach-O rpaths with `install_name_tool`, then `meson setup -Dmacos-app=enabled` + DMG + `codesign`. Cartero `Cargo.toml`: `adw = { version = "0.8.1", package = "libadwaita", features = ["v1_7"] }`, `gtk = { package = "gtk4", version = "0.10.3", features = ["v4_18"] }`; README: "Cartero requires GNOME SDK 48 or greater". Distribution: Flathub, Snap, Scoop (`scoop install extras/cartero`), Homebrew cask tap, winget (`winget-announce.yaml`).

### B.3 gtk-rs book commands
* `cargo add libadwaita --rename adw --features v1_8` ("keep gtk4 and libadwaita crate versions in sync").
* Windows MSVC: `rustup default stable-msvc`, `gvsbuild build gtk4`, `gvsbuild build libadwaita librsvg`, env `PKG_CONFIG_PATH=C:\gtk-build\gtk\x64\release\lib\pkgconfig`, `Lib=C:\gtk-build\gtk\x64\release\lib`, add `...\bin` to `Path`.
* Windows GNU: `pacman -S mingw-w64-x86_64-gtk4 mingw-w64-x86_64-gettext mingw-w64-x86_64-libxml2 mingw-w64-x86_64-librsvg mingw-w64-x86_64-pkgconf mingw-w64-x86_64-gcc`, `rustup default stable-gnu`.
* macOS: `brew install libadwaita`.

### B.4 `flatpak-cargo-generator` manifest skeleton (from `flatpak-builder-tools/cargo/README.md`)
```yaml
sdk-extensions:
  - org.freedesktop.Sdk.Extension.rust-stable
modules:
  - name: my_app
    buildsystem: simple
    build-options:
      append-path: /usr/lib/sdk/rust-stable/bin
      env:
        CARGO_HOME: /run/build/my_app/cargo
        CARGO_NET_OFFLINE: 'true'
    build-commands:
      - cargo --offline fetch --manifest-path Cargo.toml --verbose
      - cargo build --offline --release --all-features
      - install -Dm0755 target/release/my_app ${FLATPAK_DEST}/bin/my_app
    sources:
      - type: archive ...
      - cargo-sources.json
```
Generate with `python3 flatpak-cargo-generator.py /path/to/Cargo.lock -o cargo-sources.json` (needs `tomlkit`, `aiohttp`; flatpak-builder ≥ 1.2).

---

## Appendix C — Blueprint via Meson wrap (recommended for version parity)

`subprojects/blueprint-compiler.wrap` (from the Blueprint "Setup" page; pin `revision` to `v0.22.2` instead of `main`):
```ini
[wrap-git]
directory = blueprint-compiler
url = https://gitlab.gnome.org/GNOME/blueprint-compiler.git
revision = v0.22.2
depth = 1

[provide]
program_names = blueprint-compiler
```
`.gitignore`: `/subprojects/blueprint-compiler`

`data/meson.build`:
```meson
blueprints = custom_target('blueprints',
  input: files('ui/window.blp', 'ui/game-card.blp', 'ui/preferences.blp'),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '--minify', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)
gnome.compile_resources('dailies', 'dailies.gresource.xml',
  gresource_bundle: true, install: true, install_dir: pkgdatadir,
  dependencies: blueprints)
```
Compile-time requirement: `Gtk-4.0.typelib` and `Adw-1.typelib` present (true in the SDK, MSYS2 `gtk4`/`libadwaita`, Homebrew).

---

## Appendix D — Proposed Dailies Flatpak manifest skeleton (Python, zero pip deps) [I, built from verified pieces]

`io.github.tim_van_oudheusden.Dailies.json`:
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
  "cleanup": ["/include", "/lib/pkgconfig", "/share/pkgconfig", "/share/man", "*.la", "*.a"],
  "modules": [
    {
      "name": "dailies",
      "buildsystem": "meson",
      "builddir": true,
      "config-opts": ["-Dprofile=release"],
      "sources": [{"type": "git", "url": "https://github.com/Tim-van-Oudheusden/Dailies.git", "tag": "v0.1.0"}]
    }
  ]
}
```
Development variant `build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json` uses `"sources": [{"type": "dir", "path": "../.."}]` and `-Dprofile=development`, as Cartridges does. If `requests`/`PyYAML` are ever needed: `flatpak-pip-generator --runtime org.freedesktop.Sdk//26.08 --requirements-file requirements.txt --output pypi-dependencies` and add `"pypi-dependencies.json"` to `modules`.

Python side of the browser chain (sketch):
```python
import gi
gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio
try:
    gi.require_version("WebKit", "6.0")
    from gi.repository import WebKit
    HAS_WEBKIT = True
except (ValueError, ImportError):
    HAS_WEBKIT = False  # Windows / macOS / non-Flatpak without webkitgtk-6.0
```

---

## Appendix E — Other verified reference data

* **Gaphor** (Python, GNOME 50 Devel manifest, Windows via gvsbuild 2026.8.0 zip → `C:\gtk`, `PKG_CONFIG=C:\gtk\bin\pkgconf.exe`, PyInstaller + NSIS + 7-Zip portable + SignPath signing, VirusTotal scan, `wingetcreate update Gaphor.Gaphor`; macOS runners `macos-15-intel` + `macos-15`, `brew install gtksourceview5 libadwaita adwaita-icon-theme gobject-introspection graphviz create-dmg`, workaround for broken Homebrew gdk-pixbuf SVG loader (`install_name_tool` + `codesign`), signed & notarized DMG; `ghcr.io/flathub-infra/flatpak-github-actions:gnome-50` + `flatpak/flatpak-github-actions/flatpak-builder@master`).
* **Varia** (Python, GTK4/libadwaita): official Windows amd64 installer + portable (MSYS2 `windows/build.sh`), "macOS version is brand new and still experimental" (Apple Silicon + Intel). [V: README]
* **Komikku** (Python): Flatpak-only, no Windows/macOS. **Bazaar** (C, GNOME 50, `org.freedesktop.Sdk.Extension.llvm20`, moved to gitlab.gnome.org/World/bazaar 2026-08-18): Linux-only. **Dino** README: "for Linux" — Windows builds not confirmed. Fractal/Loupe/Pika Backup/Workbench/Amberol/Letterpress/Pitivi: no cross-platform builds verified in this research [U].
* **gtk-mac-bundler**: still receives commits (2026-07-10 "Update python launcher program to use Python 3.14, the current version in gtk-osx"), so the jhbuild/gtk-osx route is alive, but none of the Python examples above use it — they use PyInstaller.
* **TypeScript SDK extension** manifest (`branch/26.08`): `"sdk-extensions": ["org.freedesktop.Sdk.Extension.node26"]`, `"prefix": "/usr/lib/sdk/typescript"`, TypeScript 5.9.3. ts-for-gir quick start: `npx @ts-for-gir/cli create my-app`; types `npm install @girs/gjs @girs/gtk-4.0` (+ `@girs/adw-1`, not shown on README [I]).
* **GNOME schedule**: 51.0 2026-09-16, 51.1 2026-10-10, 51.2 2026-11-21, 52.alpha 2027-01-09, 52.beta 2027-01-30, 52.rc 2027-02-27, 52.0 2027-03-17.

---

## Sources

Primary (fetched 2026-10-15):
* https://gitlab.gnome.org/GNOME/libadwaita/-/raw/main/NEWS
* https://gitlab.gnome.org/api/v4/projects/GNOME%2Flibadwaita/repository/tags?per_page=10
* https://gitlab.gnome.org/GNOME/gtk/-/raw/main/NEWS
* https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-51/elements/sdk/{gtk,libadwaita,webkitgtk-6.0,blueprint-compiler,pygobject,gjs}.bst and webkitgtk.inc; gnome-49/gnome-50 `gtk.bst`, `libadwaita.bst`, `webkitgtk.inc`
* https://gitlab.gnome.org/api/v4/projects/GNOME%2Fgnome-build-meta/repository/tree?ref=gnome-51&path=elements/sdk
* https://webkitgtk.org/news.html
* https://docs.flatpak.org/en/latest/available-runtimes.html
* https://docs.flathub.org/docs/for-app-authors/requirements ; https://docs.flathub.org/docs/for-app-authors/maintenance
* Local: `flatpak --user remote-ls flathub --runtime`, `flatpak --user remote-info flathub org.gnome.Platform//{48,49,50,51}` (Flatpak 1.18.4)
* https://github.com/flatpak/flatpak-builder-tools (clone; `pip/readme.md`, `cargo/README.md`, `node/README.md`)
* https://github.com/flatpak/flatpak-github-actions ; https://github.com/flathub-infra/flatpak-github-actions/issues/17
* https://github.com/kra-mo/cartridges (clone, commit d56323e): `build-aux/flatpak/page.kramo.Cartridges.Devel.json`, `build-aux/windows/Cartridges.iss.in`, `build-aux/windows/meson.build`, `build-aux/macos/cartridges.spec`, `.github/workflows/ci.yml`, `.github/workflows/publish-release.yml`, `meson.build`, `data/meson.build`
* https://github.com/bazaar-org/bazaar (clone, commit 3d347d5): `build-aux/flatpak/io.github.kolunmi.Bazaar.json`, `src/`
* https://github.com/gaphor/gaphor (clone, commit 78ef52d): `.github/workflows/full-build.yml`, `org.gaphor.Gaphor.json`, `_packaging/`; https://docs.gaphor.org/en/latest/_sources/windows.md.txt ; https://docs.gaphor.org/en/latest/_sources/macos.md.txt
* https://github.com/flxzt/rnote (clone): `Cargo.toml`, `build-aux/com.github.flxzt.rnote.Devel.yaml`, `.github/workflows/build_win_installer.yml`, `README.md`
* https://github.com/danirod/cartero (clone, commit 990b5b9): `Cargo.toml`, `meson.build`, `.github/workflows/build.yaml`, `packaging/win32/`, `packaging/macos/jhbuild/main.sh`, `README.md`
* https://codeberg.org/valos/Komikku (clone)
* https://github.com/giantpinkrobots/varia ; https://github.com/dino/dino
* https://gnome.pages.gitlab.gnome.org/blueprint-compiler/ ; /setup.html ; /packaging.html ; https://gitlab.gnome.org/api/v4/projects/GNOME%2Fblueprint-compiler/repository/tags
* https://gtk-rs.org/gtk4-rs/stable/latest/book/installation_windows.html ; https://gtk-rs.org/gtk4-rs/stable/latest/book/libadwaita.html
* https://crates.io/api/v1/crates/gtk4 ; https://crates.io/api/v1/crates/libadwaita ; https://docs.rs/crate/gtk4/0.11.5/features ; https://docs.rs/crate/libadwaita/0.9.2/features
* https://pypi.org/pypi/PyGObject/json ; https://pygobject.gnome.org/guide/deploy.html ; https://pyinstaller.org/en/stable/hooks-config.html
* https://github.com/wingtk/gvsbuild ; `gh api repos/wingtk/gvsbuild/releases/latest` ; `gh api repos/wingtk/gvsbuild/contents/gvsbuild/projects`
* https://packages.msys2.org/search?t=pkg&q=libadwaita ; …q=webkitgtk ; …q=gjs ; https://packages.msys2.org/base/mingw-w64-vala ; /base/mingw-w64-blueprint-compiler ; https://packages.msys2.org/package/mingw-w64-ucrt-x86_64-python-gobject
* https://formulae.brew.sh/formula/{libadwaita,webkitgtk,gjs,pygobject3,vala,blueprint-compiler}
* https://gitlab.gnome.org/api/v4/projects/GNOME%2Fgtk-mac-bundler/repository/commits
* https://raw.githubusercontent.com/flathub/org.freedesktop.Sdk.Extension.typescript/branch/26.08/org.freedesktop.Sdk.Extension.typescript.json ; https://github.com/gjsify/ts-for-gir
* https://discourse.gnome.org/t/using-libadwaita-on-linux-windows-apps/29181 ; https://discourse.gnome.org/t/is-libadwaita-suitable-for-multiplatform-apps/18497 ; https://discourse.gnome.org/t/webview-for-gtk4-cross-platform-lin-win-mac-cef-or-webkit/28611
* https://lists.webkit.org/pipermail/webkit-gtk/2024-February/003968.html (WebKitGTK Windows support ended at 2.4)
* https://release.gnome.org/calendar/
Secondary: https://linuxiac.com/libadwaita-1-8-arrives-alongside-gnome-49/ ; https://www.phoronix.com/news/libadwaita-1.8-Released ; https://gitlab.gnome.org/World/Rust/libadwaita-rs/-/issues/30 ; https://gitlab.gnome.org/GNOME/gtk/-/issues/5263
