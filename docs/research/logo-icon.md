# Dailies — App icon, logo, brand colors and store screenshots (research key: `logo-icon`)

Research date: 2026-10-15. Author: research subagent for the Dailies architecture/design document.

Scope: GNOME HIG app-icon rules (GNOME 40+ style, with the 2024–2026 state of the HIG, template repo, tooling and GTK symbolic-icon changes), required deliverables and install paths for a Flatpak/Meson project, tooling, palette, benchmarks (Cartridges, Bazaar), Flathub icon/branding/screenshot quality rules, and three concrete icon concepts for Dailies.

Conventions in this document:
- **[V]** = verified against a primary source (URL or cloned file given).
- **[I]** = inference/recommendation by the researcher, not stated by a source.
- Clones used (read only, never executed): `<scratch>/clones/logo-icon/{cartridges,bazaar,app-icon-preview,hig-www,hig-app-icons,icon-development-kit,raw}`.

---

## 1. Executive summary

1. GNOME app icons are a **single 128×128 full-color SVG** named after the app ID, plus a **16×16 monochrome `-symbolic.svg`**; nothing else is needed for GNOME/Flathub. Both are installed into the `hicolor` theme (`share/icons/hicolor/scalable/apps/` and `share/icons/hicolor/symbolic/apps/`). A third, auto-generated **`.Devel.svg`** (striped "nightly" variant) is strongly recommended for development builds. [V — HIG + Flatpak conventions + Cartridges/Bazaar repos]
2. Style rules (HIG "App Icons", page last substantively edited 2024-08-10): simple geometric metaphor related to the name/function; drawn inside the 128 canvas without filling it; not flat — a darker "front profile"/chin at the bottom; flat colors on straight surfaces, gradients only on curves; no shadows outside the silhouette; GNOME palette; follow the template's 2 px grid; avoid detail that dies at 32 px; no mascots/characters/third-party logos. [V]
3. Tooling: **App Icon Preview 3.5.1** (Flathub `org.gnome.design.AppIconPreview`, released 2025-04-23) generates the project template, previews at 128/64/32 and 16 px on light/dark, and exports the three SVGs. Companion: **HIG-app-icons** repo (`template.svg`, `GNOME HIG.gpl` palette, sketch templates; last commit 2026-05-26), **Color Palette 3.0.0**, **Symbolic Preview 0.0.9**, **Icon Library 0.0.23**, Flathub `app-icon-grid.svg`. [V]
4. 2024–2026 changes that matter: (a) no *new* full-color style refresh was found — the GNOME 3.32/40 style is still current; (b) GTK 4.22 (2026-03-06) introduced a new SVG-based **stateful/animated symbolic icon format** (`gpa:` namespace, `.gpa`, `org.gtk.Shaper` editor) and the **GtkSvg** renderer; this affects UI symbolics, is optional, and classic `-symbolic.svg` files keep working. [V, see §4]
5. Flathub quality guidelines (optional but required for featuring): SVG or ≥256 px PNG, reasonable footprint (use their grid), good contrast on light *and* dark, no baked-in shadows, no tiny details/small text, contemporary style; **brand colors** (`<branding>`, light + dark) with contrast against the icon; **screenshots**: window only with native shadow/rounded corners, ≤1000×700 window (2000×1400 HiDPI), 3–6 for a medium app, default settings (dark-mode shots only as extras), one-sentence captions. [V]
6. "No text in icons": **not a written rule** in the current HIG; Flathub says "avoid … small text"; GNOME's own design-team practice avoids words (localisation, legibility at 32 px). Treat it as a strong convention, not a hard requirement. [V for sources; I for the convention]
7. Recommendation: go with **Concept A "Daily Grid"** (tear-off calendar card whose page is a guess-feedback tile grid), palette Blue 3/4 + Green 4 + Yellow 4 + Light 2/3/4, brand colors Blue 1 `#99c1f1` (light) / Blue 5 `#1a5fb4` (dark); draft SVGs are in Appendix F. App ID (Flathub rule: hyphen → underscore, lowercase domain part): **`io.github.tim_van_oudheusden.Dailies`** → files `io.github.tim_van_oudheusden.Dailies.svg`, `….Dailies.Devel.svg`, `….Dailies-symbolic.svg`. [V for ID rule; I for concept]

---

## 2. GNOME HIG — App Icons (verified rules)

Source: https://developer.gnome.org/hig/guidelines/app-icons.html (reStructuredText source `source/guidelines/app-icons.rst` in https://gitlab.gnome.org/Teams/Design/hig-www; full text reproduced in Appendix A). Commit history of that page (GitLab API, project 15144): 2021-04-28 "restructure and rewrite", 2021-05-21 "nightly icons", 2023-10-28 "Update icon images", **2024-08-10 "app symbolics: no longer used for HC"** (latest). So the rules below are the current (GNOME 47–50 era) rules. [V]

### 2.1 Metaphor
- "Each app icon should have a simple, recognizable metaphor. Ideally this should have a clear and obvious relationship with the app name."
- Accepted metaphor types: physical objects directly related to the function (speaker → music); physical objects somewhat related or an analog ancestor (cassette → podcasts); domain symbols (play triangle); a simplified, stylized version of a distinctive UI.
- Avoid: metaphors unrelated to name/function, "characters or mascots", "logos which rely on a specific visual style".
- "App icons should be unique to each and every app. Reusing existing icons for app identities is strongly discouraged."

### 2.2 Size & shape
- "App icons are drawn within a 128×128px area, but shouldn't fill this space." Follow the guides of the app icon template (https://gitlab.gnome.org/Teams/Design/HIG-app-icons/blob/master/template.svg) and keep a visual weight similar to other GNOME app icons.
- "Avoid extreme aspect ratios"; "The bottom of the icon should be aligned against the standard baseline, which is indicated in the template."
- Template geometry measured from `template.svg` (layer "App Icon" is translated by `(0,-172)`, so canvas coordinates are y−172) [V, measured]:
  - Base shapes (hairline guides, 0.1 opacity): **square 104×104 at (12,12)–(116,116), rx 8**; **wide 112×88 at (8,28)–(120,116), rx 8**; **tall 88×112 at (20,8)–(108,120), rx 8**; **circle Ø120 centred (64,64)**.
  - **Baseline**: a 2 px blue (`#62a0ea`) horizontal line at **y = 117** (so object bottoms sit at ≈116).
  - Inkscape guides every 4 px around the margins (0, 8, 12, 24, 104, 116, 120, 128) plus two 45° guides.
  - The hicolor artboard is a 128×128 rect at (0,172) and the symbolic artboard a 16×16 rect at (160,172) in document units; layers: `App Icon` (draw here), `baseplate`, `icons` (base shapes), `hairlines`.

### 2.3 Perspective
- "While the app icon style is simple, it is not 'flat'. Depth is introduced by combining the 'top' and 'front' of the object, so that each icon has an additional profile at the bottom of the object. This 'front' profile is shaded darker than the top surface."
- "In most cases the profile is subtle, not taller than 2 detail units (4 nominal pixels)." [V] (1 nominal px = the 64 px viewing size = 2 canvas px, so ≈8 canvas px; Cartridges and Bazaar both use a ~12 canvas-px chin — the HIG explicitly allows exceptions. [I])

### 2.4 Material & lighting
- Skeuomorphic materials (wood, metal, glass) allowed "if required. Otherwise, simple colors and textures are recommended. Use the standard color palette as a base for colors."
- "Straight surfaces should have flat colors, with gradients being reserved for curved surfaces."
- "Shadows should be avoided if possible … the light source should point straight down from above. Do not draw shadows outside the main silhouette of the icon, as these are generated programmatically based on the context."

### 2.5 Detail
- "App icons are defined at 128×128px, but are typically viewed at 64×64px, and can be scaled down to 32×32px … avoid adding too much detail."
- "The template includes a 2px grid which should be followed."

### 2.6 Symbolic app icon
- "Each app should have an additional symbolic version of its app icon, which is used to represent the app icon at smaller sizes, and in some special contexts." Same metaphor where possible; can live in the same SVG as the full-size icon; App Icon Preview exports both.
- Symbolic style (HIG "UI Icons", https://developer.gnome.org/hig/guidelines/ui-icons.html) [V]: nominal **16×16 px** including margin; shown at 16/32/64/128 only; orthogonal view, no perspective; **2 px strokes for main features, avoid 1 px where possible**; monochrome, recolored programmatically; pixel-grid aligned; must work when colors are inverted (negative space).
- Tobias Bernard's tutorial adds: "Leave the outermost 1px empty", "Most strokes should be 2px, but they can be 1px in some cases", "Alignment to the pixel grid is very important here if you don't want the icon to end up a blurry mess." [V]

### 2.7 Nightly/Devel variant
- "If you provide a nightly or beta build of your app, it is recommended to create a specific version of the app icon … App Icon Preview is able to generate a nightly variant of the icon automatically." [V]
- Mechanism (verified in `app-icon-preview/src/common.rs`): the exported `<name>.Devel.svg` is the hicolor icon rendered at 128 px with `resources/templates/stripes.svg` composited over it (`render_stripes`). Cartridges' `page.kramo.Cartridges.Devel.svg` instead hand-edits colors (adds Yellow 1 `#f9f06b`/Yellow 4 `#f5c211`); Bazaar's `.Devel.svg` swaps the red/white awning for yellow/dark (`#f5c517`, `#f8e351`, `#212121`, `#2a2a2a`). Either approach is accepted. [V]

### 2.8 Text/letters in icons
- Current HIG app-icons page: **no statement about text** (verified by reading the full source). Tobias Bernard's post: not discussed. Flathub quality guidelines: "Avoid too many tiny details and **small text**". [V]
- Rationale usually given by the design team (not a quoted rule): words don't localise, fail at 32 px, and glyph-only icons violate Flathub's "avoid single-color glyphs" contrast rule. **Recommendation: no letters/words in the Dailies icon.** [I]

### 2.9 Tobias Bernard, "Designing an icon for your app" (2019-12-30)
https://blogs.gnome.org/tbernard/2019/12/30/designing-an-icon-for-your-app/ — still the canonical walkthrough. Verified points: brainstorm physical objects + thesaurus; sketch many candidates; "The canvas is 128x128px (for legacy reasons)" but design for 64 and check 32; **each grid square is 8×8 px** — put edges on grid lines or simple fractions; standard base shapes for wide/tall/square/circular; perspective "folds" top and front into a darker "chin"; keep objects not too tall; "Straight surfaces have flat colors", curved surfaces may use gradients, add a horizontal highlight gradient to chin corners of rounded shapes; "Do not use drop shadows that affect the app outline though, because GTK renders such a shadow automatically"; work on the **icons** layer, "Don't change, hide, rename, or delete" the **template** layer, hide **grid**/**baseplate** when previewing; use the "GNOME HIG Colors" palette in Inkscape; symbolic: one color, same metaphor, 1 px empty border, 2 px strokes; "Don't overthink it for the first version." [V]

---

## 3. Palette (GNOME HIG)

Source: https://developer.gnome.org/hig/reference/palette.html ("intended for use in app icons and illustrations"); GIMP/Inkscape palette file `GNOME HIG.gpl` in https://gitlab.gnome.org/Teams/Design/HIG-app-icons (reproduced in Appendix B). Also available via Flathub **Color Palette** (`org.gnome.design.Palette`, v3.0.0) and Inkscape's bundled "GNOME HIG Colors" palette. [V]

| Hue | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Blue | #99c1f1 | #62a0ea | #3584e4 | #1c71d8 | #1a5fb4 |
| Green | #8ff0a4 | #57e389 | #33d17a | #2ec27e | #26a269 |
| Yellow | #f9f06b | #f8e45c | #f6d32d | #f5c211 | #e5a50a |
| Orange | #ffbe6f | #ffa348 | #ff7800 | #e66100 | #c64600 |
| Red | #f66151 | #ed333b | #e01b24 | #c01c28 | #a51d2d |
| Purple | #dc8add | #c061cb | #9141ac | #813d9c | #613583 |
| Brown | #cdab8f | #b5835a | #986a44 | #865e3c | #63452c |
| Light | #ffffff | #f6f5f4 | #deddda | #c0bfbc | #9a9996 |
| Dark | #77767b | #5e5c64 | #3d3846 | #241f31 | #000000 |

Usage pattern seen in GNOME icons (Cartridges: top Purple 2 `#c061cb`, chin gradient Purple 3/5; Bazaar: wood Brown 2/4/5, awning Red 2 + Light 2): **top surface = shade N, chin = shade N+1/N+2 of the same hue, highlights = shade N−1**. [V for the two icons; I for the pattern]

---

## 4. What changed 2024–2026 (and what did not)

| Item | Status | Source |
|---|---|---|
| Full-color app-icon style | **Unchanged** since the 3.32/40 redesign; HIG page last edited 2024-08-10 (removed the note that app symbolics are used for High Contrast). No 2025/2026 "refresh" announcement found in web searches, GNOME blogs or the HIG repo. | GitLab API commits for `source/guidelines/app-icons.rst`; searches |
| HIG-app-icons template repo | Maintained: 2025-07-26 "Clean up Figma file" (Hylke Bons), 2026-05-26 "Krita sketch template" (Jakub Steiner). Contains `template.svg` (Inkscape 1.4.2), `GNOME HIG.fig/.gpl/.scss/.css`, sketch templates for A4 PDF, Krita, MyPaint, Procreate. | clone `hig-app-icons`, GitLab API |
| App Icon Preview | 3.5.1 (2025-04-23, "Fixed blurry icons on the preview"); repo active (last commit 2026-10-11); GTK4/Rust, uses librsvg to render; template `empty_project.svg` is a **192×152** document with the 128×128 artboard (`id="hicolor"`) at (8,16) and the 16×16 artboard (`id="symbolic"`) at (168,16); layers `App Icon`, `template`, `baseplate`, `icons`, `grid`. A file is recognised as an icon *project* only if it contains elements with ids `hicolor` **and** `symbolic`; otherwise a plain 128×128 SVG opens in *preview* mode. | clone `app-icon-preview` (`src/project.rs`, `src/common.rs`, `data/resources/templates/`) |
| Symbolic icons in GTK | GTK 4.20 (2025): hand-rolled parser for the symbolic SVG subset (fill **and** stroke). GTK 4.21 dev → **GTK 4.22 stable, 2026-03-06**: new SVG-based stateful/animated symbolic format (namespace `gpa:` — "GTK path animation", pronounced "Grappa"; `gpa:fill`/`gpa:stroke` take `foreground`, `success`, `warning`, `error`, `accent` or a fixed color; up to 64 states; transitions `none/animate/morph/fade`; MIME `image/x-gtk-path-animation`, extension `.gpa`) plus **GtkSvg** paintable; editor **Shaper** (`org.gtk.Shaper`, gnome-nightly remote). Icons looked up by name from the theme still go through the simple parser; full switch planned for the next cycle. Legacy `class="foreground|success|warning|error"` and plain fills still work. | https://docs.gtk.org/gtk4/icon-format.html; https://discourse.gnome.org/t/animated-icons-for-gtk/31564 (2025-09-19); https://blogs.gnome.org/gtk/2026/02/25/an-update-on-svg-in-gtk/; Phoronix 2026-03-06 |
| Icon Development Kit | Repo says "New powerful rendering system for symbolic icons is in the making (and its initial revision already shipping with gtk)" and points to Shaper docs (pad.gnome.org). 1107 CC0 symbolic icons. | clone `icon-development-kit/README.md` |
| Fonts | GNOME 48 replaced Cantarell as default font (irrelevant to icons, relevant to screenshots: use defaults). | search result (secondary) |

**Impact on Dailies** [I]: produce the classic three SVGs; the app-icon symbolic should stay a plain `-symbolic.svg` (paths/rects/circles only, no `<defs>`/filters/masks — the GTK parser ignores them). The animated `.gpa` format is an *optional* later enhancement for in-app UI icons (e.g. an animated favorite star), not for the app identity icon.

---

## 5. Deliverables, naming and install paths

### 5.1 Files (verified against Flatpak conventions, Flathub linter, Cartridges and Bazaar)
| Deliverable | Canvas | Path in repo (Cartridges/Bazaar convention) | Installed to |
|---|---|---|---|
| Full-color icon | 128×128 SVG | `data/icons/hicolor/scalable/apps/<APP_ID>.svg` | `$datadir/icons/hicolor/scalable/apps/<APP_ID>.svg` |
| Devel/nightly icon | 128×128 SVG | `data/icons/hicolor/scalable/apps/<APP_ID>.Devel.svg` | same dir; Bazaar installs it **renamed** to `<APP_ID>.svg` when `-Ddevelopment=true` |
| Symbolic icon | 16×16 SVG | `data/icons/hicolor/symbolic/apps/<APP_ID>-symbolic.svg` | `$datadir/icons/hicolor/symbolic/apps/<APP_ID>-symbolic.svg` |
| Source project (optional) | 192×152 App Icon Preview project | Bazaar: `data/icons/<APP_ID>.Source.svg` (248 KB, not installed) | — |

Rules [V]:
- Flatpak conventions (https://docs.flatpak.org/en/latest/conventions.html#application-icons): icons follow the freedesktop icon-theme spec, named after the app ID, PNG in `/app/share/icons/hicolor/<size>x<size>/apps/` or SVG in `/app/share/icons/hicolor/scalable/apps/`; square; max 512×512; Flatpak only **exports** icons named `$FLATPAK_ID`, `$FLATPAK_ID.foo` or `$FLATPAK_ID-foo` (optionally `.png/.svg`), so the host cannot see other names.
- Flathub requirements (https://docs.flathub.org/docs/for-app-authors/requirements#icons): "Graphical applications must provide, preferably a SVG icon or at least a 256x256 PNG icon, properly named and installed."
- Flathub linter (https://docs.flathub.org/docs/for-app-authors/linter): `appstream-missing-icon-file` — "A 128px png icon was not generated by `appstreamcli compose`. This is generated automatically provided atleast a 128px png icon or a SVG icon is installed to the correct location" (exception never granted); `non-svg-icon-in-scalable-folder`; `non-png-icon-in-hicolor-size-folder`; `desktop-file-icon-key-wrong-value` (Icon= must be `$FLATPAK_ID`, `$FLATPAK_ID.foo` or `$FLATPAK_ID-foo`, extension only `svg/svgz/png`); `no-exportable-icon-installed`; `desktop-file-icon-not-installed`.
- `appstreamcli compose` generates 64×64 and 128×128 catalog icons from a PNG ≥64 px or an installed SVG (Flathub MetaInfo guidelines).
- MetaInfo must have `<launchable type="desktop-id"><APP_ID>.desktop</launchable>` so compose can find the icon via the desktop file's `Icon=` key.
- App ID for this project (Flathub rules: `io.github.` prefix, ≥4 components, domain portion lowercase, `-` → `_`): **`io.github.tim_van_oudheusden.Dailies`** (Flathub derives the repo URL `https://github.com/Tim-van-Oudheusden/Dailies` from it; GitHub usernames are case-insensitive, so the lowercase form resolves). [V for rules; the exact ID choice is a project decision]

### 5.2 Meson snippets (copy-ready; sources reproduced in Appendix C)
Cartridges `data/icons/meson.build` (Python app, `app_id` set in root `meson.build`):
```meson
scalable_dir = join_paths('hicolor', 'scalable', 'apps')
install_data(
  join_paths(scalable_dir, ('@0@.svg').format(app_id)),
  install_dir: join_paths(get_option('datadir'), 'icons', scalable_dir),
)

symbolic_dir = join_paths('hicolor', 'symbolic', 'apps')
install_data(
  join_paths(symbolic_dir, ('@0@-symbolic.svg').format(app_id)),
  install_dir: join_paths(get_option('datadir'), 'icons', symbolic_dir),
)
```
Bazaar `data/icons/meson.build` (adds the Devel switch — recommended for Dailies):
```meson
application_id = 'io.github.kolunmi.Bazaar'

scalable_dir = 'hicolor' / 'scalable' / 'apps'
if get_option('development')
  icon_file = '@0@.Devel.svg'.format(application_id)
else
  icon_file = '@0@.svg'.format(application_id)
endif

install_data(
  scalable_dir / icon_file,
  install_dir: get_option('datadir') / 'icons' / scalable_dir,
  rename: '@0@.svg'.format(application_id)
)

symbolic_dir = 'hicolor' / 'symbolic' / 'apps'
install_data(
  symbolic_dir / ('@0@-symbolic.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / symbolic_dir
)
```
Note: with Bazaar's approach the Devel build keeps the *same* app ID and only swaps the artwork; GNOME's own apps instead use a different app ID (`<APP_ID>.Devel`) for nightly builds, in which case the symbolic must be installed renamed to `<APP_ID>.Devel-symbolic.svg` (App Icon Preview's `data/icons/meson.build` does exactly this: `rename: '@0@-symbolic.svg'.format(application_id)` from `base_id`). Cartridges ships both `page.kramo.Cartridges.Devel.svg` and `page.kramo.Cartridges.Devel-symbolic.svg` in-tree. [V]

### 5.3 Desktop file & MetaInfo bits that reference the icon
```ini
[Desktop Entry]
Name=Dailies
Icon=io.github.tim_van_oudheusden.Dailies
```
(`Icon=` = app ID without extension — Flathub linter rule.) MetaInfo needs `<launchable>`; no `<icon>` tag is needed for desktop apps (compose takes it from the desktop file). [V]

---

## 6. Tooling and workflow (verified versions)

| Tool | ID / URL | Version & date | Role |
|---|---|---|---|
| App Icon Preview | `org.gnome.design.AppIconPreview`, https://gitlab.gnome.org/World/design/app-icon-preview | 3.5.1, 2025-04-23 | New project from template, live preview (128/64/32 light+dark, symbolic 16), export regular/nightly/symbolic (Ctrl+E) |
| HIG app icon template repo | https://gitlab.gnome.org/Teams/Design/HIG-app-icons | last commit 2026-05-26 | `template.svg`, `GNOME HIG.gpl`, `.fig`, sketch templates (A4 PDF, Krita, MyPaint, Procreate) |
| Inkscape | https://inkscape.org | template saved with 1.4.2 (2025-05-08) | Vector editing; ships "GNOME HIG Colors" palette |
| Color Palette | `org.gnome.design.Palette`, https://gitlab.gnome.org/World/design/palette | 3.0.0 | Palette picker |
| Symbolic Preview | `org.gnome.design.SymbolicPreview`, https://gitlab.gnome.org/World/design/symbolic-preview/ | 0.0.9 (~3 years old) | Template + preview for UI symbolics |
| Icon Library | `org.gnome.design.IconLibrary`, https://gitlab.gnome.org/World/design/icon-library | 0.0.23 (Sept/Oct 2026) | Browse GTK + Icon Development Kit symbolics (e.g. favorites star, calendar) for in-app use |
| Icon Development Kit | https://gitlab.gnome.org/Teams/Design/icon-development-kit | last commit 2026-09-23 | 1107 CC0 symbolic icons + Shaper docs |
| Shaper | `org.gtk.Shaper` (gnome-nightly) | announced 2025-09-19 | Editor for the new stateful/animated symbolic format (optional) |
| Flathub icon grid | https://docs.flathub.org/img/app-icon-grid.svg (reproduced in Appendix D) | — | 128×128 overlay with square (rx≈8) and circle base shapes to check footprint |
| Flathub banner preview | https://docs.flathub.org/banner-preview | — | Preview brand colors behind the icon (light/dark) |
| Validation | `appstreamcli validate`, `desktop-file-validate`, `flatpak-builder-lint` (`flathub-infra/flatpak-builder-lint`) | — | Catches icon/launchable/screenshot errors |

Recommended workflow [I, assembled from verified tool behaviour]:
1. In App Icon Preview: *New App Icon* → name it `io.github.tim_van_oudheusden.Dailies` → saves `….Dailies.Source.svg` (keep it in `data/icons/`, like Bazaar).
2. Open in Inkscape; draw on layer **App Icon** inside the 128 artboard (`id="hicolor"`) and the 16 artboard (`id="symbolic"`); do not touch layer `template`; snap to the 2 px/8 px grid; use the GNOME HIG palette.
3. Export (Ctrl+E) → `<id>.svg`, `<id>.Devel.svg`, `<id>-symbolic.svg` into `data/icons/hicolor/{scalable,symbolic}/apps/`.
4. Optional: optimise with `svgo`/`scour` (Cartridges' 2.7 KB icon has no Inkscape metadata; Bazaar's 4.3 KB export is similarly clean).
5. **KDE/Qt compatibility**: Bazaar PR #895 (2026-01-03, "make current Bazaar icons compatible with KDE Plasma") replaced the icons "with versions without clipping masks in order to ensure compatibility with KDE's QT SVG renderer" (KDE bug 448234). → Avoid `clipPath`, `mask`, filters and `mix-blend-mode` in the exported icon; bake shapes instead. [V]
6. Check footprint against `app-icon-grid.svg`, run `appstreamcli validate`, `flatpak-builder-lint`, and look at the icon in GNOME Software/Bazaar's preview and on Flathub's banner-preview with the chosen brand colors.

---

## 7. Benchmarks: Cartridges and Bazaar icons

### 7.1 Cartridges (`page.kramo.Cartridges`) — https://github.com/kra-mo/cartridges (canonical: codeberg.org/kramo/cartridges)
- Designer: kramo (About dialog `about.set_designers(("kramo https://kramo.page",))`, `cartridges/main.py:274`). Icon history: "Update icon" 2023-01-13/29, "Update icons" 2023-01-31, renamed with the app-ID change on 2024-04-07. [V]
- Metaphor: a purple game cartridge seen from the top with label window and connector details — object directly related to the function (game launcher). [V by reading SVG]
- Geometry: wide base shape; top surface `#C061CB` (Purple 2) from y 29 to ≈103, front profile to y 115 in a horizontal gradient `#613583→#9141AC→#613583` (Purple 5/3 — the "highlight gradient on chin corners" trick from the tutorial); details in Dark 3 `#3D3846`; label uses two off-palette colors (`#BDD0D5`, `#305749`) — so small deviations are tolerated. 128×128, 2 716 bytes, `fill="none"` root, no Inkscape metadata. [V]
- Symbolic (16×16, `fill="black"`, `fill-rule="evenodd"`): rounded-rect cartridge outline with inner window and two dots — same metaphor reduced to 2 px strokes. Reproduced in Appendix E. [V]
- Devel variant: same drawing with hand-changed colors (adds Yellow 1/4). Ships extra `build-aux/windows/icon.ico` and `build-aux/macos/icon.icns` for cross-platform packaging (Inno Setup `SetupIconFile`, PyInstaller `icon=`), generation method not in repo. [V]
- Brand colors: light `#d5b0e7`, dark `#501a5c` (lighter/darker purples than the icon, per Flathub guidance; both off-palette). Screenshots: `data/screenshots/1-4.png`, 1146×698, 1146×698, 602×727, 482×812 (window+shadow, light theme, captions "Cartridges", "Game Details", "Edit Game Details", "Preferences"; hosted at `https://codeberg.org/kramo/cartridges/raw/branch/main/...`). [V]

### 7.2 Bazaar (`io.github.kolunmi.Bazaar`) — https://github.com/bazaar-org/bazaar
- Designer: **Tobias Bernard** (GNOME design team), PR #864 "App icon: new market stall metaphor", merged 2025-12-31; earlier iterations reportedly went basket → price tag → market stall (secondary source, not verified). A later PR #895 by M. Gopal (2026-01-03) removed clip masks for KDE. [V for PRs]
- Metaphor: a wooden market stall (wide base shape, Brown 2 `#b5835a` top planks, Brown 4/5 structure, legs 20–32/96–108 × 98–117) with a red-and-white striped awning (Red 2 `#ed333b`, Red 1 `#f66151`, Light 2 `#f6f5f4`, Light 3 `#deddda`) and goods on the counter: a Blue 5→Green 1 gradient box, a Purple 1/Blue 5 radial sphere, a Red 3 triangle with Yellow 2 radial glow. Shows how gradients are used only on curved/rounded "goods", flat colors on planks. 4 293 bytes. [V]
- Source project: `data/icons/io.github.kolunmi.Bazaar.Source.svg` (248 KB) is an App Icon Preview project (layers `App Icon`, `template` with `#hicolor`/`#symbolic` rects, `baseplate`, `icons`, `grid` hidden). [V]
- Symbolic: stall outline (awning as three semicircles + roof bar, counter with three goods) — same metaphor; note it still contains an unused `<filter>`/`<mask>`/`<clipPath>` block with a stray green path from the export — GTK's symbolic parser ignores `defs`-like content, but it is a good reminder to clean exports. [V]
- Brand colors: light Orange 1 `#ffbe6f`, dark `#c11c2b` (near Red 4). Screenshots in `screenshots/`: `bazaar-light.png` and `bazaar-dark.png` (1123×950), plus HiDPI shots 2136–2456 × 1600–1816 (window+shadow at 2×), 5 screenshots in MetaInfo hosted on `github.com/user-attachments/...` with captions like "The home page displaying Flathub apps". [V]

### 7.3 Lessons for Dailies [I]
- Both use the **wide** base shape and a ~12 px chin; both keep every straight surface flat; both pick 1–2 hues + neutrals; both ship a Devel variant and a symbolic that repeats the metaphor; both set brand colors derived from the icon's dominant hue.
- Cartridges proves a hobbyist-made icon can pass Flathub quality; Bazaar shows the value of a design-team iteration (three metaphors before shipping).

---

## 8. Brand colors (MetaInfo `<branding>`)

AppStream spec (https://www.freedesktop.org/software/appstream/docs/chap-Metadata.html#tag-branding): `<branding>` may contain `<color type="primary" scheme_preference="light|dark">#rrggbb</color>`; each type/scheme pair once; "An accent color may for example be used as the background behind the logo/icon." [V]

Flathub quality rules [V]: two colors (light + dark); "colorful" — no white/very light grey, no black/very dark grey; dark variant = darker, more muted version of the light color, never the same; good contrast against the icon ("a lighter/darker version of the primary color used in the icon … or a complementary color"); "consider the brand colors an extension of the app icon, and have the icon designer choose them". Preview: https://docs.flathub.org/banner-preview.

Snippet for Dailies (Concept A):
```xml
<branding>
  <color type="primary" scheme_preference="light">#99c1f1</color> <!-- Blue 1 -->
  <color type="primary" scheme_preference="dark">#1a5fb4</color>  <!-- Blue 5 -->
</branding>
```

---

## 9. Screenshots for Flathub (and the README)

Flathub quality guidelines (https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines/quality-guidelines#screenshots) [V]:
- At least one, in English; **3–6 for medium apps**, 6–10 for very large; best one first (`type="default"`); tag language (`xml:lang="de"`) for translated shots.
- "Use the 'window screenshot' feature in your native system screenshot tool to get just the app window and its shadow. Do not include the wallpaper … Do not edit the screenshot, crop it, add text, or include promotional graphics." Take them on Linux.
- "Use the platform default configuration for all settings … including window controls, interface font, large text, high contrast, dark style, accent color … Having some screenshots to show off that e.g. dark style is supported is fine, but these should not be the only screenshots."
- "Screenshots must include the native decoration such as any title bar, window shadows, and rounded corners … Don't maximize your app window."
- "the window size should be **1000x700 pixels or smaller (2000x1400 for HiDPI)**" (window size; the PNG is larger because of the shadow — Cartridges' 1146×698 PNGs and App Icon Preview's 1086×679 are examples).
- Captions: one sentence, no full stop, don't start with a number. Show real content, not empty states; update when the UI changes (including when the desktop's default window-button layout changes).
- MetaInfo guidelines: `<image>` must be a direct URL; if hosted in git, "link to a tag or commit rather than a branch" (Cartridges links to `raw/branch/main`, which Flathub tolerates but discourages). SVG screenshots are rejected (`metainfo-svg-screenshots`). Flathub mirrors images to `dl.flathub.org/media`.
- GNOME HIG itself has **no screenshot-guidance page** (verified by grepping `hig-www/source`); the Flathub rules are the reference. GNOME Circle's membership guide only asks to "check compliance with the HIG" and keep metadata up to date. [V]

Plan for Dailies [I]: 4–5 shots at a 960×640 window on a default GNOME session (light, default accent, default font): (1) Favorites view with a few DLE cards, (2) Popular/Trending categories, (3) the built-in browser showing a game (choose a game whose page you may screenshot), (4) Preferences with the browser choice, (5) same as 1 in dark style. Store them in `data/screenshots/` like Cartridges, reference them by **tag** URL (`https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/v0.1.0/data/screenshots/1.png`) once releases exist, and reuse 1 and 5 in the README (Cartridges embeds `data/icons/.../<id>.svg` at 128 px and `data/screenshots/1.png` in its README).

---

## 10. Three icon concepts for Dailies

Design constraints applied to all three [V-derived]: 128×128 canvas, standard base shape, bottom on the baseline (y≈116), one ~8–12 px darker chin, flat colors on straight surfaces, gradients only on curves, GNOME palette, no words/letters, no outer shadow, works at 32 px, matching 16×16 symbolic, Devel variant via App Icon Preview stripes, no clip masks. Metaphor rationale per HIG: must relate to the **name** ("Dailies" = things you do every day → calendar/day/sunrise) **and purpose** (launcher for daily guessing games → guess-feedback tile grid, tray of games, favorites star).

### Concept A — "Daily Grid" (recommended)
- **Metaphor**: a tear-off desk-calendar card (today's page) whose page *is* a guessing-game feedback grid. Name (daily page) + purpose (the ubiquitous green/yellow/grey feedback tiles of Wordle-style games) in one object; no mascots, no logos.
- **Shape**: square base shape 104×104 at (12,12)–(116,116), rx 8. Two binder rings protrude 8 px above the top edge (allowed "small protruding elements").
- **Construction (8 px grid)**: header band y 12–36 in **Blue 3 `#3584e4`**, 4 px darker edge y 36–40 in **Blue 4 `#1c71d8`** (reads as the header's own front profile); page face y 40–108 in **Light 2 `#f6f5f4`**; chin y 108–116 in **Light 4 `#c0bfbc`** (8 canvas px = the HIG's "4 nominal px"); rings 8×20 rx 4 at x 32 and x 88 in **Dark 2 `#5e5c64`**; tiles 20×20 rx 3, columns x 26/54/82, rows y 50 and 78: row 1 = **Green 4 `#2ec27e`**, **Yellow 4 `#f5c211`**, Green 4; row 2 = **Light 3 `#deddda`** ×3 (today's unsolved row — a nod to "come back daily").
- **Why it passes**: colorful, high contrast on light and dark (blue header + colored tiles, light edges only at the bottom), 6 tiles and 2 rings are the only details (survives 32 px), flat colors everywhere, chin present, palette-only.
- **Symbolic (16×16)**: filled header bar with rounded top (1,1)–(15,4), then 2 rows × 3 tiles of 4×3 px (x 1/6/11; y 6–9 and 11–14), 1 px outer margin kept. Distinct from GNOME Calendar's symbolic (which shows a full month grid under a header) because of the 3-wide "guess row" rhythm; still, review side by side before shipping.
- **Brand colors**: light Blue 1 `#99c1f1`, dark Blue 5 `#1a5fb4` (lighter/darker versions of the header hue; the light tiles and white page keep contrast). Draft SVGs: Appendix F.
- **Risk/open question**: green/yellow feedback tiles are strongly associated with Wordle (NYT). The *pattern* is generic to the DLE genre and we use GNOME palette hues, not NYT's `#6aaa64/#c9b458`; still, avoid a 5×6 grid that would look like a Wordle screenshot (hence 3×2).

### Concept B — "Sunrise Board"
- **Metaphor**: a new day (rising sun) over a slate game board with one row of guess tiles — "every morning, a new puzzle".
- **Shape**: wide base shape 112×88 at (8,28)–(120,116), rx 8, in **Dark 3 `#3d3846`** with a 12 px chin in **Dark 4 `#241f31`** (y 104–116). A sun disc Ø48 centred (64,36) in **Yellow 3 `#f6d32d`**, radial highlight to **Yellow 2 `#f8e45c`** (gradient allowed: curved surface), half hidden behind the board's top edge so only the upper half (y 12–28) shows above the board. On the board: 5 tiles 16×16 rx 2 at y 56, x 20/40/60/80/100: Green 4, Yellow 4, Light 3, Green 4, Light 3; second row of 5 **Light 5 `#9a9996`** tiles at y 80 (unsolved).
- **Contrast**: the dark board gives the Flathub "dark colors near the edges" warning on dark backgrounds — mitigate with a 2 px **Dark 1 `#77767b`** rim or by lightening the board to Dark 2. Needs a check in App Icon Preview's dark pane.
- **Symbolic**: half-circle (sun) above a 2 px horizon line at y 7, three 3×3 squares below (x 2/6.5→ use 2/7/12, y 10–13). Simple and unique.
- **Brand colors**: light Yellow 1 `#f9f06b` would clash with the sun; use complementary **Blue 2 `#62a0ea`** (light) / **Blue 5 `#1a5fb4`** (dark), or Orange 1 `#ffbe6f` / Orange 5 `#c64600`.

### Concept C — "Game Tray"
- **Metaphor**: a tray holding four colorful game tiles, one marked with a star — "all your dailies in one place, favorites on top". Emphasises the launcher/collection purpose; the "daily" part is carried by a thin calendar tab at the top.
- **Shape**: square base 104×104 at (12,12)–(116,116), rx 8, tray **Blue 3 `#3584e4`**, chin 8 px **Blue 5 `#1a5fb4`**; a 24×8 "today" tab at (52,4) in **Red 2 `#ed333b`** (calendar reference). Inside: 2×2 tiles 40×40 rx 6 at x 20/68, y 20/68 with their own 4 px chins: Green 3/Green 5, Yellow 3/Yellow 5, Purple 2/Purple 4, Orange 2/Orange 4; the top-left tile carries a white 5-point star (Light 1) 24 px wide.
- **Risk**: 2×2 tiles is the generic "app grid" symbol (`view-app-grid-symbolic`), and the star at 32 px becomes a blob; weaker name link than A/B. Keep as fallback or as inspiration for in-app category artwork.
- **Symbolic**: 2×2 rounded squares 6×6 with 2 px gaps, top-left square replaced by a star — hard at 16 px; alternative: four squares, top-left hollow (2 px stroke).
- **Brand colors**: light Blue 1 `#99c1f1`, dark Blue 5 `#1a5fb4`.

### Comparison
| | A Daily Grid | B Sunrise Board | C Game Tray |
|---|---|---|---|
| Name link ("Dailies") | strong (calendar page) | strong (new day) | weak (small tab) |
| Purpose link (guessing games) | strong (feedback tiles) | medium (one row) | medium (tray of games) |
| Uniqueness vs GNOME icons | medium (Calendar is also a tear-off card; tiles differentiate) | high | low (app-grid look) |
| 32 px legibility | high | high | medium |
| Contrast light/dark | high | medium (dark board) | high |
| Symbolic simplicity | high | high | low |
| **Recommendation** | **primary** | alternate | drop |

---

## 11. Recommendations for Dailies (actionable)

1. **App ID**: `io.github.tim_van_oudheusden.Dailies`; icon file names derive from it (§5.1). Decide before drawing, because App Icon Preview names the project after the ID.
2. **Create the icon with App Icon Preview 3.5.1 + Inkscape** from the official template; commit the `.Source.svg` (Bazaar pattern) plus the three exported SVGs under `data/icons/hicolor/{scalable,symbolic}/apps/`.
3. **Adopt Concept A**; iterate once in App Icon Preview against GNOME Calendar, Cartridges, Bazaar to tune visual weight; then ask for feedback on GNOME Discourse (design category) or the GNOME design team's icon-request channel (exact request repo not verified — ask on Discourse). Start from the draft SVGs in Appendix F.
4. **Meson**: copy Bazaar's `data/icons/meson.build` (with the `development` option) so `-Ddevelopment=true` installs the striped `.Devel.svg`; add `meson_options.txt` `option('development', type: 'boolean', value: false)`.
5. **Keep the exported SVGs clean**: no `clipPath`/`mask`/filter/`mix-blend-mode` (KDE Qt renderer, Bazaar PR #895); paths/rects/circles only in the symbolic; run `svgo` or `scour`.
6. **MetaInfo**: `<launchable type="desktop-id">`, `<branding>` Blue 1/Blue 5, 4–5 screenshots with captions, `<releases>`; validate with `appstreamcli validate --pedantic` and `flatpak-builder-lint`.
7. **Screenshots**: GNOME window screenshot, 960×640-ish window, default settings, light first + one dark; store in `data/screenshots/`, reference by tag URL; embed icon + first screenshot in README (Cartridges layout).
8. **Cross-platform (if pursued)**: generate `.ico`/`.icns` from the 128 px SVG at build time (Cartridges checks pre-built `build-aux/windows/icon.ico` and `build-aux/macos/icon.icns` into git); note the HIG chin/perspective looks fine on Windows/macOS but macOS expects a rounded-square mask — out of GNOME scope.
9. **Later**: consider the GTK 4.22 `.gpa` animated symbolic format for *in-app* UI icons (favorite toggle), never for the app icon itself.

---

## 12. Open questions
- Confirm the app ID (`io.github.tim_van_oudheusden.Dailies`) before any artwork or Flathub submission; renaming later costs a `<replaces>` entry (Cartridges did this).
- Owner preference between Concept A and B; whether the green/yellow feedback-tile motif is acceptable given its Wordle association (legal/brand risk is low with GNOME palette hues, but not assessed by a lawyer).
- Whether to request a design-team review (Tobias Bernard drew Bazaar's icon; GNOME Circle membership would make this easier) — the exact icon-request issue tracker was not verified.
- Whether Dailies will ship a separate `.Devel` app ID (GNOME style) or Bazaar's same-ID artwork swap.
- Whether cross-platform builds are in scope (determines `.ico`/`.icns` generation).

---

## Sources (primary unless noted)
- GNOME HIG, App Icons: https://developer.gnome.org/hig/guidelines/app-icons.html (source: https://gitlab.gnome.org/Teams/Design/hig-www/-/blob/main/source/guidelines/app-icons.rst; commit history via https://gitlab.gnome.org/api/v4/projects/15144/repository/commits?path=source/guidelines/app-icons.rst)
- GNOME HIG, UI Icons: https://developer.gnome.org/hig/guidelines/ui-icons.html
- GNOME HIG, Palette: https://developer.gnome.org/hig/reference/palette.html
- HIG app icon template repo: https://gitlab.gnome.org/Teams/Design/HIG-app-icons (`template.svg`, `GNOME HIG.gpl`; commits via GitLab API)
- App Icon Preview: https://flathub.org/apps/org.gnome.design.AppIconPreview ; https://gitlab.gnome.org/World/design/app-icon-preview (clone: `meson.build`, `src/common.rs`, `src/project.rs`, `data/resources/templates/empty_project.svg`, `data/resources/templates/stripes.svg`, `data/icons/meson.build`, metainfo releases)
- Color Palette app: https://flathub.org/apps/org.gnome.design.Palette ; Symbolic Preview: https://flathub.org/apps/org.gnome.design.SymbolicPreview ; Icon Library: https://flathub.org/apps/org.gnome.design.IconLibrary
- Icon Development Kit: https://gitlab.gnome.org/Teams/Design/icon-development-kit
- Tobias Bernard, "Designing an icon for your app" (2019-12-30): https://blogs.gnome.org/tbernard/2019/12/30/designing-an-icon-for-your-app/
- GTK symbolic icon format: https://docs.gtk.org/gtk4/icon-format.html ; "Animated icons for GTK" (2025-09-19): https://discourse.gnome.org/t/animated-icons-for-gtk/31564 ; "SVG in GTK" (2025-10-23): https://blogs.gnome.org/gtk/2025/10/ ; "An update on SVG in GTK" (2026-02-25): https://blogs.gnome.org/gtk/2026/02/25/an-update-on-svg-in-gtk/ ; GTK 4.22 release coverage (secondary): https://www.phoronix.com/news/GTK-4.22-Released
- Flatpak conventions (icons, desktop files, MetaInfo): https://docs.flatpak.org/en/latest/conventions.html#application-icons
- Flathub requirements: https://docs.flathub.org/docs/for-app-authors/requirements (icons §, app ID §)
- Flathub MetaInfo guidelines: https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines/ (icons, brand color, screenshots, releases)
- Flathub quality guidelines: https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines/quality-guidelines (icon, brand colors, screenshots)
- Flathub icon grid: https://docs.flathub.org/img/app-icon-grid.svg ; banner preview: https://docs.flathub.org/banner-preview
- Flathub linter checks: https://docs.flathub.org/docs/for-app-authors/linter
- AppStream spec `<branding>`: https://www.freedesktop.org/software/appstream/docs/chap-Metadata.html#tag-branding
- Cartridges: https://github.com/kra-mo/cartridges (clone: `data/icons/**`, `data/icons/meson.build`, `data/page.kramo.Cartridges.metainfo.xml.in`, `cartridges/main.py`, `data/screenshots/`, `build-aux/{windows,macos}`; commits via GitHub API)
- Bazaar: https://github.com/bazaar-org/bazaar (clone: `data/icons/**`, `data/io.github.kolunmi.Bazaar.metainfo.xml.in`, `screenshots/`); PR #864 https://github.com/bazaar-org/bazaar/pull/864 ; PR #895 https://github.com/bazaar-org/bazaar/pull/895 ; KDE bug https://bugs.kde.org/show_bug.cgi?id=448234 (referenced by PR, not fetched)
- GNOME Circle membership guide: https://gitlab.gnome.org/Teams/Circle/-/blob/main/membership_guide.md
- Flathub Discourse threads on screenshots (secondary): https://discourse.flathub.org/t/quality-guidelines-help-with-screenshots/7414 ; https://discourse.flathub.org/t/how-to-create-beautiful-screenshots-for-flathub/5922

Not verifiable / not found: a 2024–2026 full-color icon style refresh (none found); a formal "no text" HIG rule (none exists); the GNOME design team's icon-request tracker URL; `developer-old.gnome.org` (DNS failure).

---

## Appendix A — HIG "App Icons" page source (reproduced verbatim from `hig-www/source/guidelines/app-icons.rst`, last change 2024-08-10)

```rst
App Icons
=========

In addition to having a :doc:`great name <app-naming>`, every app also needs a great icon. This page provides guidance on how to create one.

Typically, creating an app icon requires pre-existing visual design skills. However, GNOME app icons are deliberately simple in style, in order to make icon creation as accessible as possible.

The `App Icon Preview <https://flathub.org/apps/details/org.gnome.design.AppIconPreview>`_ tool is recommended for app icon creation. It supports each stage of the process, from generating a template, previewing the icon in relevant contexts, and exporting the final assets.

**App icons should be unique to each and every app. Reusing existing icons for app identities is strongly discouraged.**

Metaphor
--------

Each app icon should have a simple, recognizable metaphor. Ideally this should have a clear and obvious relationship with the :doc:`app name <app-naming>`. Common types of metaphors include:

* Physical objects directly related to what the app does (for example, a speaker for a music app).
* Physical objects which are at least somewhat related to the app's domain, or to an older analog version of it (for example, a cassette tape for a podcasting app).
* Symbols related to the domain (for example, the "play" triangle for a video player).
* If the app has a distinctive UI, a simplified, stylized version of it.

Avoid metaphors that are unrelated to the name or function of the app, such as using characters or mascots. Also avoid using logos which rely on a specific visual style.

GNOME App Icon Style
--------------------

The GNOME app icon style is simple and geometric. In many cases you can draw an entire icon with only basic shapes.

Size & Shape
~~~~~~~~~~~~

App icons are drawn within a 128×128px area, but shouldn't fill this space. When judging how large to draw the icon, follow the guides in the `app icon template <https://gitlab.gnome.org/Teams/Design/HIG-app-icons/blob/master/template.svg>`_, and ensure that your icon has a similar visual weight to other app icons.

* Avoid extreme aspect ratios for the icon shape, such as very narrow or very wide shapes.
* The bottom of the icon should be aligned against the standard baseline, which is indicated in the template.

Perspective
~~~~~~~~~~~

While the app icon style is simple, it is not "flat". Depth is introduced by combining the "top" and "front" of the object, so that each icon has an additional profile at the bottom of the object. This "front" profile is shaded darker than the top surface.

In most cases the profile is subtle, not taller than `2 detail units` (`4 nominal pixels`). But as the example aboves show there can be exceptions.

Material & Lighting
~~~~~~~~~~~~~~~~~~~

Icons can make use of skeuomorphic materials (for example: wood, metal, or glass) if required. Otherwise, simple colors and textures are recommended. Use the :doc:`standard color palette </reference/palette>` as a base for colors.

Straight surfaces should have flat colors, with gradients being reserved for curved surfaces.

Shadows should be avoided if possible, but can be used if it is necessary to give contrast to different icon elements. When drawing shadows, the light source should point straight down from above. Do not draw shadows outside the main silhouette of the icon, as these are generated programmatically based on the context.

Detail
~~~~~~

App icons are defined at 128×128px, but are typically viewed at 64×64px, and can be scaled down to 32×32px. Therefore, avoid adding too much detail, as this will be lost at small sizes.

The template includes a 2px grid which should be followed, and will help to avoid adding excess details.

Symbolic App Icons
------------------

Each app should have an additional symbolic version of its app icon, which is used to represent the app icon at smaller sizes, and in some special contexts. A description of the symbolic icon style can be found in the :doc:`UI icons guidelines <ui-icons>`.

App symbolics can be drawn in the same SVG as the full-size app icon, as indicated in the app icon template. App Icon Preview will export both the full-size and symbolic versions of the icon.

Where possible, the same metaphor as the full size app icon should be used for the symbolic.

Nightly Variant
---------------

If you provide a nightly or beta build of your app, it is recommended to create a specific version of the app icon for it so it is possible to tell them apart.

`App Icon Preview <https://flathub.org/apps/details/org.gnome.design.AppIconPreview>`_ is able to generate a nightly variant of the icon automatically. In some cases it may be desirable to adjust the output manually, though in most cases this shouldn't be necessary.
```
(Image directives omitted.)

## Appendix B — `GNOME HIG.gpl` (GIMP/Inkscape palette, from HIG-app-icons)

```
GIMP Palette
Name: GNOME HIG Colors
Columns: 0
#
153 193 241	Blue 1
 98 160 234	Blue 2
 53 132 228	Blue 3
 28 113 216	Blue 4
 26  95 180	Blue 5
143 240 164	Green 1
 87 227 137	Green 2
 51 209 122	Green 3
 46 194 126	Green 4
 38 162 105	Green 5
249 240 107	Yellow 1
248 228  92	Yellow 2
246 211  45	Yellow 3
245 194  17	Yellow 4
229 165  10	Yellow 5
255 190 111	Orange 1
255 163  72	Orange 2
255 120   0	Orange 3
230  97   0	Orange 4
198  70   0	Orange 5
246  97  81	Red 1
237  51  59	Red 2
224  27  36	Red 3
192  28  40	Red 4
165  29  45	Red 5
220 138 221	Purple 1
192  97 203	Purple 2
145  65 172	Purple 3
129  61 156	Purple 4
 97  53 131	Purple 5
205 171 143	Brown 1
181 131  90	Brown 2
152 106  68	Brown 3
134  94  60	Brown 4
 99  69  44	Brown 5
255 255 255	Light 1
246 245 244	Light 2
222 221 218	Light 3
192 191 188	Light 4
154 153 150	Light 5
119 118 123	Dark 1
 94  92 100	Dark 2
 61  56  70	Dark 3
 36  31  49	Dark 4
  0   0   0	Dark 5
```

## Appendix C — Meson icon install files (verbatim)

`app-icon-preview/data/icons/meson.build` (GNOME-style separate Devel app ID; `application_id` = `base_id` or `base_id + 'Devel'`):
```meson
install_data(
  '@0@.svg'.format(application_id),
  install_dir: iconsdir / 'hicolor' / 'scalable' / 'apps'
)

install_data(
  '@0@-symbolic.svg'.format(base_id),
  install_dir: iconsdir / 'hicolor' / 'symbolic' / 'apps',
  rename: '@0@-symbolic.svg'.format(application_id)
)
```
Cartridges and Bazaar versions are in §5.2.

## Appendix D — Flathub `app-icon-grid.svg` (verbatim, 128×128 overlay)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="128.00002" height="127.99999" viewBox="0 0 33.866671 33.866665" version="1.1" id="svg1"
   xmlns="http://www.w3.org/2000/svg" xmlns:svg="http://www.w3.org/2000/svg">
  <g id="layer1" transform="translate(-32.279167,-138.64166)">
    <circle cx="49.212509" cy="155.575" r="15.743801" id="circle2892"
       style="opacity:0.2;fill:none;stroke:currentColor;stroke-width:0.2619375" />
    <rect ry="2.096508" rx="2.096508" y="141.94769" x="35.585205" height="27.254602" width="27.254602" id="rect2896"
       style="opacity:0.2;fill:none;stroke:currentColor;stroke-width:0.2619375" />
  </g>
</svg>
```
(Inkscape namedview attributes stripped; geometry equals a Ø119 circle and a 103×103 rx 7.9 square in 128-px units — i.e. the HIG square/circle base shapes.)

## Appendix E — Cartridges symbolic icon (verbatim, `page.kramo.Cartridges-symbolic.svg`)

```xml
<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path fill-rule="evenodd" clip-rule="evenodd" d="M3 3C1.89543 3 1 3.89543 1 5V11C1 12.1046 1.89543 13 3 13H13C14.1046 13 15 12.1046 15 11V5C15 3.89543 14.1046 3 13 3H3ZM6 5C5.44772 5 5 5.44772 5 6V10C5 10.5523 5.44772 11 6 11H10C10.5523 11 11 10.5523 11 10V6C11 5.44772 10.5523 5 10 5H6ZM12 8C12 7.44772 12.4477 7 13 7C13.5523 7 14 7.44772 14 8C14 8.55228 13.5523 9 13 9C12.4477 9 12 8.55228 12 8ZM3 7C2.44772 7 2 7.44772 2 8C2 8.55228 2.44772 9 3 9C3.55228 9 4 8.55228 4 8C4 7.44772 3.55228 7 3 7Z" fill="black"/>
</svg>
```

## Appendix F — Draft SVGs for Concept A "Daily Grid" (researcher's drafts, follow §10; refine in Inkscape/App Icon Preview before shipping)

`data/icons/hicolor/scalable/apps/io.github.tim_van_oudheusden.Dailies.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <!-- front profile / chin (Light 4) -->
  <rect x="12" y="20" width="104" height="96" rx="8" fill="#c0bfbc"/>
  <!-- page face (Light 2) -->
  <rect x="12" y="12" width="104" height="96" rx="8" fill="#f6f5f4"/>
  <!-- header band (Blue 3), top corners rounded -->
  <path d="M20 12h88a8 8 0 0 1 8 8v16H12V20a8 8 0 0 1 8-8z" fill="#3584e4"/>
  <!-- header front edge (Blue 4) -->
  <rect x="12" y="36" width="104" height="4" fill="#1c71d8"/>
  <!-- binder rings (Dark 2) -->
  <rect x="32" y="4" width="8" height="20" rx="4" fill="#5e5c64"/>
  <rect x="88" y="4" width="8" height="20" rx="4" fill="#5e5c64"/>
  <!-- guess row 1: Green 4, Yellow 4, Green 4 -->
  <rect x="26" y="50" width="20" height="20" rx="3" fill="#2ec27e"/>
  <rect x="54" y="50" width="20" height="20" rx="3" fill="#f5c211"/>
  <rect x="82" y="50" width="20" height="20" rx="3" fill="#2ec27e"/>
  <!-- guess row 2: unsolved (Light 3) -->
  <rect x="26" y="78" width="20" height="20" rx="3" fill="#deddda"/>
  <rect x="54" y="78" width="20" height="20" rx="3" fill="#deddda"/>
  <rect x="82" y="78" width="20" height="20" rx="3" fill="#deddda"/>
</svg>
```

`data/icons/hicolor/symbolic/apps/io.github.tim_van_oudheusden.Dailies-symbolic.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
  <!-- header bar with rounded top -->
  <path d="M3 1h10a2 2 0 0 1 2 2v1H1V3a2 2 0 0 1 2-2z" fill="#2e3436"/>
  <!-- row 1 -->
  <rect x="1" y="6" width="4" height="3" fill="#2e3436"/>
  <rect x="6" y="6" width="4" height="3" fill="#2e3436"/>
  <rect x="11" y="6" width="4" height="3" fill="#2e3436"/>
  <!-- row 2 -->
  <rect x="1" y="11" width="4" height="3" fill="#2e3436"/>
  <rect x="6" y="11" width="4" height="3" fill="#2e3436"/>
  <rect x="11" y="11" width="4" height="3" fill="#2e3436"/>
</svg>
```
Notes: GTK recolors the symbolic regardless of the fill value (Cartridges uses `fill="black"`, Bazaar omits fill). The Devel variant should be generated by App Icon Preview (stripes overlay) rather than hand-drawn. Both drafts use only rects/paths — no masks or filters — for KDE compatibility.

## Appendix G — MetaInfo fragment for Dailies (icon-related parts)

```xml
<component type="desktop-application">
  <id>io.github.tim_van_oudheusden.Dailies</id>
  <name>Dailies</name>
  <summary>Play your daily puzzles in one place</summary>   <!-- ≤35 chars, imperative, no period -->
  <launchable type="desktop-id">io.github.tim_van_oudheusden.Dailies.desktop</launchable>
  <branding>
    <color type="primary" scheme_preference="light">#99c1f1</color>
    <color type="primary" scheme_preference="dark">#1a5fb4</color>
  </branding>
  <screenshots>
    <screenshot type="default">
      <image>https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/v0.1.0/data/screenshots/1.png</image>
      <caption>Your favorite daily games on the home page</caption>
    </screenshot>
    <screenshot>
      <image>https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/v0.1.0/data/screenshots/2.png</image>
      <caption>Popular and trending games this week</caption>
    </screenshot>
    <screenshot>
      <image>https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/v0.1.0/data/screenshots/3.png</image>
      <caption>Playing a game in the built-in browser</caption>
    </screenshot>
    <screenshot>
      <image>https://raw.githubusercontent.com/Tim-van-Oudheusden/Dailies/v0.1.0/data/screenshots/4.png</image>
      <caption>Dark style</caption>
    </screenshot>
  </screenshots>
</component>
```
(The summary wording is a placeholder subject to the Flathub summary rules in the quality guidelines: 10–35 chars, sentence case, no toolkit names, no trailing period.)
