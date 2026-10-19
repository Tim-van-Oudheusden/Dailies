# Dailies: making the category badge legible, plus a preference to hide it (research key: `category-badge`)

Research date: 2026-10-19. Stack: GTK 4.24.0, libadwaita 1.10.0, GNOME 51 runtime.

Scope: a game with its own icon shows that icon in the tile's 64×64 `.tile-glyph` square and moves the category glyph into `category_badge` (`data/ui/game-tile.blp`). That badge is a 12 px symbolic icon on a 20×20 circle, styled by `.tile-badge` in `data/ui/style.css`. In the Flatpak the user finds it "very unclear". This report answers whether the badge's **shape**, **opacity**, **colour** and **size** can change, what the libadwaita/GNOME-HIG way to do that is, and how to build a Preferences switch that hides the badge.

Conventions:
- Every factual claim links to its primary source. Source-code links are pinned to the tag or commit that was read: libadwaita `1.10.0` (commit `c9ab1186`, 2026-09-14), GTK `4.24.0` (commit `1f47f368`, 2026-09-11), hig-www `97028eac` (2026-06-20), GLib `main` at `ae8632ba` (2026-10-15), GNOME Software `b71574d2`, Nautilus `8fd4b292`, Bazaar `3d347d5d`, Cartridges `d56323e6`.
- **[I]** marks an inference or recommendation by the researcher that no source states.
- Contrast numbers were computed with the WCAG 2.2 formulas ([relative luminance](https://www.w3.org/TR/WCAG22/#dfn-relative-luminance), [contrast ratio](https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio)), using libadwaita's own colour values. Translucent colours were composited the way GTK mixes them (premultiplied, see §2.3). Nothing was measured from screen pixels, so anti-aliasing is ignored and real 12 px glyphs read worse than these numbers suggest.

---

## 1. Executive summary

1. **The badge really is see-through, but only in the dark style.** `.tile-badge` mixes 18 % of the category colour with `--card-bg-color`. In the light style that variable is opaque `#ffffff`, but in the dark style it is `rgb(255 255 255 / 8%)` ([_colors.scss L61-62, L123-124](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss#L61-124)). GTK's `color-mix()` interpolates with premultiplied alpha ([gtkcsscolor.c L780-830](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkcsscolor.c#L780-830)), so in dark mode the disc ends up about **25 % opaque**, and its 2 px "ring" is 8 % white. The game icon shows through, and glyph contrast drops to **1.9-2.9:1**, below the WCAG 3:1 bar. In the light style glyph contrast is 3.6-5.7:1. There the problem is size: a 12 px glyph is off the 16 px symbolic grid ([HIG UI Icons](https://developer.gnome.org/hig/guidelines/ui-icons.html)). [I: the Flatpak complaint fits the dark style, or a desktop that follows it.]
2. **House precedent is a solid disc with a white glyph.** libadwaita's own small badges use an opaque accent fill with a white or accent-fg label: the AdwIndicatorBin badge ([_view-switcher.scss L104-123](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_view-switcher.scss#L104-123)) and the AdwTabButton attention dot ([_tab-view.scss L201-212](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_tab-view.scss#L201-212)). AdwAvatar switches to white text below 25 px because its pale tinted text stops being legible ([adw-avatar.c L759-762](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/adw-avatar.c#L756-762), [_avatar.scss L35](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_avatar.scss#L35)). AdwIndicatorBin also separates the badge from the content beneath it by masking that content out 2 px around the badge ([adw-indicator-bin.c L177-200](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/adw-indicator-bin.c#L177-200)).
3. **Recommendation (Option A):** a 16 px glyph on a 24 px opaque `--category-color` disc with a white glyph, plus a 2 px ring that is opaque in both styles. The ring is built from CSS background layers (`image(--card-bg-color)` over `--window-bg-color`), so it matches the card exactly without hard-coding colours. White on every Dailies category colour scores **3.01-5.91:1** in light and dark alike: libadwaita's accent palette is the same in both styles ([_colors.scss L155-164](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss#L155-164)). High contrast switches to a neutral disc (`--card-fg-color` glyph, about 12.5:1). The CSS is in §7.
4. **Quieter alternative (Option B):** keep the tinted look, but make it opaque with the same background layers and colour the glyph with libadwaita's "standalone" formula `oklab(from … var(--standalone-color-oklab))`. Glyph contrast rises to **4.6-6.8:1**, but the pale disc stands out less from the icon behind it.
5. **Preference:** the GSettings boolean `show-category-badge` (default `true`) is bound to an `AdwSwitchRow` with `Gio.Settings.bind(…, DEFAULT)`. Each tile binds the same key to a GObject property with `Gio.SettingsBindFlags.GET`. GET-only skips GIO's automatic sensitivity binding ([gsettings.c L3050-3060](https://gitlab.gnome.org/GNOME/glib/-/blob/ae8632bab1b5f09f2bb996c9637b1added5b038f/gio/gsettings.c#L3050-3060)), and the binding keeps the `GSettings` object alive ([L2970](https://gitlab.gnome.org/GNOME/glib/-/blob/ae8632bab1b5f09f2bb996c9637b1added5b038f/gio/gsettings.c#L2970)). The switch hides only the corner badge. A game without an icon keeps its glyph in the big square.

---

## 2. What GTK 4.24 can do (platform facts)

### 2.1 Supported CSS properties

From the [GTK 4 CSS properties reference](https://docs.gtk.org/gtk4/css-properties.html) ([source](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/docs/reference/gtk/css-properties.md)):

| Property | Supported | Notes |
|---|---|---|
| `border-radius` (and per-corner) | yes | CSS Backgrounds 3 |
| `opacity` | yes | CSS Color 3 |
| `filter` | yes | Filter Effects 1 |
| `background-color`, `background-image` (multiple layers), `background-clip` | yes | `background-image` cannot take unquoted urls |
| `box-shadow` | yes | |
| `outline`, `outline-offset` | yes | `outline-style: auto` is not supported |
| `min-width`, `min-height`, `padding`, `border-width` | yes | |
| `transform` | yes | CSS Transforms 1 |
| `-gtk-icon-size` | yes | "size used for builtin icons in buttons and expanders" |
| `-gtk-icon-shadow`, `-gtk-icon-filter`, `-gtk-icon-palette` | yes | applied to builtin and application-loaded icons |
| `-gtk-icon-weight` | yes | applied to "stroked symbolic icons" |
| `color-mix()`, `oklab()`, relative colours | yes | "hwb(), oklab(), oklch(), color(), color-mix() and relative colors are supported" |
| custom properties `--x` / `var()` | yes | "Starting with 4.16" |
| `@media (prefers-color-scheme / prefers-contrast / prefers-reduced-motion)` | yes | "Since GTK 4.20" |

The GTK NEWS file dates these features. `color-mix()`, relative colours and `oklab()` arrived in **4.15.2** (development cycle for 4.16) ([NEWS L3934-3947](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/NEWS#L3934-3947)). CSS variables arrived in **4.15.1** ([NEWS L3986-3997](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/NEWS#L3986-3997)). `-gtk-icon-weight` and the stateful symbolic format arrived in **4.21.0** ([NEWS L1695-1702](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/NEWS#L1695-1702)). All of them are available on GNOME 51.

libadwaita itself uses `image(<color>)` as a one-colour background layer, for example `background-image: image(color-mix(…))` on hovered activatable cards ([_misc.scss L229-238](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_misc.scss#L229-238)), so Dailies can rely on that syntax.

### 2.2 `opacity` on a widget fades the whole widget, icon included

`gtk_widget_create_render_node()` reads the widget's CSS `opacity` and wraps the widget's entire render (background, border and content) in one `gtk_snapshot_push_opacity()` node ([gtkwidget.c L12151-12174](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkwidget.c#L12151-12174)). Setting `opacity < 1` on the badge would therefore fade the glyph along with the disc. To make only the disc translucent, use a colour with alpha. The same mechanism applies to Dailies' own "done" rule `.game-tile.done > box > :not(.done-badge) { opacity: 0.55 }` in `style.css`: the glyph square, game icon and badge are faded together as one group, which is the intended dimming.

### 2.3 How `color-mix()` treats a translucent input

GTK premultiplies each colour by its alpha before interpolating, then un-premultiplies the result ([gtkcsscolor.c L780-830](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkcsscolor.c#L780-830)), following [CSS Color 5 `color-mix()`](https://www.w3.org/TR/css-color-5/#color-mix). The result's alpha is the weighted sum of the input alphas. For the current badge in the dark style that is `0.18 × 1 + 0.82 × 0.08 = 0.2456`.

### 2.4 How `GtkImage` draws a symbolic icon

- **Colour:** the foreground colour of a symbolic icon is the widget's CSS `color` (`color_out[GTK_SYMBOLIC_COLOR_FOREGROUND] = style->used->color`). `-gtk-icon-palette` can override the error, warning, success and accent colours ([gtkcssstyle.c L876-899](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkcssstyle.c#L876-899)). `-gtk-icon-filter`, `-gtk-icon-shadow` and `-gtk-icon-weight` are applied in `gtk_css_style_snapshot_icon_paintable()` ([gtkrendericon.c L95-160](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkrendericon.c#L95-160)).
- **Size versus box:** the icon is drawn at `MIN(allocated size, pixel-size)` and centred in the widget's content box ([gtkiconhelper.c L186-235](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkiconhelper.c#L186-235)). An explicit `pixel-size` wins over `-gtk-icon-size` ([gtkiconhelper.c L403-411](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkiconhelper.c#L403-411)). With `pixel-size: 12` and `min-width/min-height: 20px` the glyph is therefore 12 px, centred, with 4 px of disc around it. To change the glyph size you change `pixel-size` in Blueprint. Box padding or minimum size does not change it.
- **Stroke weight:** Dailies' category icons are stroked symbolics (`stroke-width="2"`, `class="transparent-fill foreground-stroke"`, e.g. `data/icons/categories/dailies-category-words-symbolic.svg`). GTK still reads these legacy class names ([icon-format.md L118](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/docs/reference/gtk/icon-format.md#L118); [docs](https://docs.gtk.org/gtk4/icon-format.html)). Weight 400 keeps the authored width. 1000 maps to `stroke-maxwidth`, 1 to `stroke-minwidth` ([gtksvgelement.c L1172-1235](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/svg/gtksvgelement.c#L1172-1235)), and the defaults are 25 % and 150 % of the authored width ([gtksvgproperty.c L1342-1343](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/svg/gtksvgproperty.c#L1342-1343)). Drawn at 12 px, a 2 px stroke becomes 1.5 px. [I: it is not confirmed that GTK applies weight to class-only legacy icons; the code path is gated on `allow_gpa` and on the min/max values being set. See Open questions.]

### 2.5 Per-layer `background-clip`

GTK draws each background layer with its own `background-clip` box. The `background-color` takes the clip of the last layer ([gtkrenderbackground.c L55-70, L84-133](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkrenderbackground.c#L55-133)). Padding and content boxes keep correctly shrunken rounded corners ([gtkcssboxesimplprivate.h L123-216](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkcssboxesimplprivate.h#L123-216)). This lets one widget paint an opaque card-coloured ring (border box) under a category disc (padding box) without `box-shadow`. §7 relies on this.

---

## 3. libadwaita facts: colours, opacity and house badges

### 3.1 Palette and card colours (1.10)

- **Accent palette:** `--accent-blue #3584e4`, `--accent-teal #2190a4`, `--accent-green #3a944a`, `--accent-yellow #c88800`, `--accent-orange #ed5b00`, `--accent-red #e62d42`, `--accent-pink #d56199`, `--accent-purple #9141ac`, `--accent-slate #6f8396` are defined once in `:root` and **not redefined for the dark style** ([_colors.scss L155-164](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss#L155-164)). The CSS-variables documentation calls them accent **background** colours and pairs every one with foreground `#ffffff`. Text-coloured use goes through separate "standalone" colours (light `min(l, 0.5)`, dark `max(l, 0.85)` in Oklab). For example blue is `#0461be` in light and `#81d0ff` in dark, yellow `#905300` and `#ffc057` ([css-variables: Accent Colors](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/css-variables.html#accent-colors); [source](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/doc/css-variables.md)). So the palette colours are tuned as backgrounds under white, not as text on a light or dark surface.
- **Standalone formula:** `--standalone-color-oklab` is `min(l, 0.5) a b` in light and `max(l, 0.85) a b` in dark. libadwaita derives a standalone colour as `oklab(from <bg> var(--standalone-color-oklab))` ([_colors.scss L145-153, L168-170](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss#L145-170)), and the docs show the same recipe for widget-specific colours ([css-variables](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/css-variables.html#accent-colors)). A Python re-implementation reproduced the documented values (`#0461be`/`#81d0ff`, `#905300`/`#ffc057`, `#007184`/`#7bdff4`).
- **Food uses `--brown-3 #986a44`** from the full GNOME palette ([css-variables: Palette Colors](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/css-variables.html#palette-colors)). It has no documented standalone pair, so it was computed with the same formula.
- **Card and window colours:** light `--card-bg-color #ffffff`, `--card-fg-color rgb(0 0 6 / 80%)`, `--window-bg-color #fafafb`; dark `--card-bg-color rgb(255 255 255 / 8%)`, `--card-fg-color white`, `--window-bg-color #222226` ([_colors.scss L31-33, L61-63, L94-96, L122-125](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss#L31-125)). In the dark style the card therefore shows as about `#343437` only because it sits on the window background. **The variable itself is translucent.**
- **Opacity variables:** `--dim-opacity` is 55 % normally and 90 % in high contrast. `--disabled-opacity` is 50 % normally and 40 % in high contrast ([_colors.scss L316-328](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss#L316-328)). `.dimmed` uses `--dim-opacity` ([style-classes: Dimmed](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/style-classes.html#dimmed)).
- **High contrast:** under `prefers-contrast: more` libadwaita changes border, dim and disabled opacities ([_colors.scss L323-328](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss#L323-328)) and adds outlines on widgets such as `.card` ([_misc.scss L201-214](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_misc.scss#L201-214)). The accent palette stays the same.
- **Accent use:** "Try to avoid using it on large surfaces, or on too many items on the same view" ([css-variables: Accent Colors](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/css-variables.html#accent-colors)). That sentence is about the user's accent colour. [I: the same restraint argues for a small disc rather than a large coloured area.]

### 3.2 `.osd`, `.circular`, `.dimmed`

- `.osd` "Usually … makes the widget background dark and partially transparent, and makes its accent color white" ([style-classes: OSD](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/style-classes.html#osd)). Implementation: `--accent-bg-color: RGB(255 255 255 / 75%)`, dark standalone colours ([_common.scss L44-50](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_common.scss#L44-50)). An OSD button is 32×32 with `RGB(0 0 0 / 65%)` background and `RGB(255 255 255 / 90%)` foreground ([_buttons.scss L113-121](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_buttons.scss#L113-121), [_colors.scss L291-292](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss#L291-292)). It is meant for controls that overlap content, such as the tile's favourite star. Being translucent, it is not suited to a colour-coded badge.
- `.circular` "makes the button round" and is documented for buttons ([style-classes: Circular](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/style-classes.html#circular)), so a non-button `GtkImage` uses `border-radius` instead.
- The activatable card (`button.card`) gets `background-image: image(<4 % currentColor>)` on hover ([_buttons.scss L328-342](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_buttons.scss#L328-342)). [I: a CSS-drawn ring in the card colour therefore differs from the hovered card by 4 %, which is barely visible.]

### 3.3 libadwaita's own small badges (house precedent)

| Widget | Size | Fill | Foreground | Separation from content |
|---|---|---|---|---|
| AdwIndicatorBin dot (view switcher) | 6 px, radius 100 px, 2 px margin | `color-mix(currentColor 40 %)`; needs-attention `var(--accent-color)` | n/a | 2 px **mask** cut out of the child: `gtk_snapshot_push_mask(… GSK_MASK_MODE_INVERTED_ALPHA)` ([_view-switcher.scss L83-102](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_view-switcher.scss#L83-102), [adw-indicator-bin.c L177-200](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/adw-indicator-bin.c#L177-200)) |
| AdwIndicatorBin `.badge` (counter) | min-height 13 px | needs-attention: **`var(--accent-bg-color)`, opaque** | `var(--accent-fg-color)` (otherwise `white`), 0.6 rem bold | same mask ([_view-switcher.scss L104-123](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_view-switcher.scss#L104-123)) |
| AdwTabButton needs-attention | 12 px, radius 8 px | `var(--accent-color)`, opaque | n/a | moved outside the icon with `transform: translate(8px, -8px)`, mirrored for RTL, plus a soft shadow ([_tab-view.scss L201-212](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_tab-view.scss#L201-212)) |
| AdwAvatar | any size, round | palette gradient | pale tint, but **`.contrasted` → `white` below 25 px** | n/a ([_avatar.scss L1-35](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_avatar.scss#L1-35), [adw-avatar.c L756-762](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/adw-avatar.c#L756-762)); avatar icon = `size / 2` ([adw-avatar.c L756](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/adw-avatar.c#L756)) |

Every small coloured indicator in libadwaita is **opaque**. When it carries a glyph or text, that sits in white or `--accent-fg-color` on a saturated fill. AdwAvatar uses the "pale tint on colour" look only at 25 px and up, which is the look Dailies' badge uses at 20 px.

### 3.4 Precedent in GNOME and GNOME-Circle-style apps

- **GNOME Software** `GsSummaryTile`: the "installed" mark is a **16 px** `app-installed-symbolic` with `.success` and **no background**, in the tile's top-end corner, **not on the icon** ([gs-summary-tile.ui L36-52](https://gitlab.gnome.org/GNOME/gnome-software/-/blob/b71574d2cbc1eb45df62b08065c72658daadb4cb/src/gs-summary-tile.ui#L36-52)). A 22 px `info-symbolic` overlays the 64 px app icon's bottom-start corner, also without a background ([L99-117](https://gitlab.gnome.org/GNOME/gnome-software/-/blob/b71574d2cbc1eb45df62b08065c72658daadb4cb/src/gs-summary-tile.ui#L99-117)).
- **Nautilus** grid view: emblems are plain default-size (16 px) symbolic `GtkImage`s in a `.dimmed` vertical box ([nautilus-grid-cell.blp L11-20](https://gitlab.gnome.org/GNOME/nautilus/-/blob/8fd4b29261e641d1e6bdb83cc841837d12aefff6/src/resources/ui/nautilus-grid-cell.blp#L11-20)). They are allocated "into the 'end' margin" beside the icon, never over it ([nautilus-grid-cell.c L179-197, L400-410](https://gitlab.gnome.org/GNOME/nautilus/-/blob/8fd4b29261e641d1e6bdb83cc841837d12aefff6/src/nautilus-grid-cell.c#L179-410)).
- **Bazaar** app tile: a 14 px `verified-checkmark-symbolic` sits beside the title, not on the icon ([bz-app-tile.blp L47-58](https://github.com/bazaar-org/bazaar/blob/3d347d5d0fb828a0ff6ff0c1dcd356b26ddfdd33/src/bz-app-tile.blp#L47-58)). The "Installed" pill pairs a **12 px** icon with a text label on a 15 % success tint ([bz-app-tile.blp L73-88](https://github.com/bazaar-org/bazaar/blob/3d347d5d0fb828a0ff6ff0c1dcd356b26ddfdd33/src/bz-app-tile.blp#L73-88), [style.css L359-397](https://github.com/bazaar-org/bazaar/blob/3d347d5d0fb828a0ff6ff0c1dcd356b26ddfdd33/src/style.css#L359-397)). The 12 px icon is legible there because the word next to it carries the meaning.
- **Cartridges** game cover: overlays on the cover are only `.circular.osd` buttons (play, menu) ([game.blp L13-51](https://github.com/kra-mo/cartridges/blob/d56323e6dd0ba9b500ee4f2b11d95f2e6240b05f/data/gtk/game.blp#L13-51)). It has no informational badge.

[I] Pattern: GNOME apps either keep status glyphs **off** the icon at 16 px (Software, Nautilus, Bazaar) or, when a glyph sits on top of content, put it on an **opaque** fill (libadwaita). None puts a 12 px glyph on a translucent fill over artwork.

---

## 4. GNOME HIG and WCAG

- **Symbolic sizes:** "Symbolics are drawn as 16×16px SVGs and can be used at 32×32px, 64×64px and 128×128px. Avoid other sizes to prevent fuzzy rendering." Main features use 2 px strokes and avoid 1 px ([HIG: UI Icons](https://developer.gnome.org/hig/guidelines/ui-icons.html); [source L9, L47-50](https://gitlab.gnome.org/Teams/Design/hig-www/-/blob/97028eac37922e787cad5796215f7e986451883a/source/guidelines/ui-icons.rst#L9-50)). A 12 px badge glyph is outside that list, and its 2 px strokes render at 1.5 px off the pixel grid.
- **Custom styling:** "use existing style classes and color variables as much as possible, since these automatically adjust for the light, dark and high-contrast styles. Be careful not to use classes and variables outside of their intended uses". Do not use "color as the only means to distinguish items of information" ([HIG: UI Styling](https://developer.gnome.org/hig/guidelines/ui-styling.html); [source L39-48](https://gitlab.gnome.org/Teams/Design/hig-www/-/blob/97028eac37922e787cad5796215f7e986451883a/source/guidelines/ui-styling.rst#L39-48)). Test in high contrast mode: "All parts of the UI should be correctly rendered in the high-contrast style" ([HIG: Accessibility](https://developer.gnome.org/hig/guidelines/accessibility.html)). [I: by the "intended uses" rule, mixing a translucent `--card-bg-color` into an opaque-looking fill is the cause of the bug, and `--accent-*` palette colours belong behind white.]
- **Switches:** use a switch for "a clear binary nature". "Label switches with nouns using header capitalization. For example, *Automatic Location* or *Notifications*". Give the label an access key ([HIG: Switches](https://developer.gnome.org/hig/patterns/controls/switches.html); [source L18-24](https://gitlab.gnome.org/Teams/Design/hig-www/-/blob/97028eac37922e787cad5796215f7e986451883a/source/patterns/controls/switches.rst#L18-24)). Header capitalisation covers "switch labels" ([HIG: Writing Style](https://developer.gnome.org/hig/guidelines/writing-style.html#header-capitalization)). Switch rows have "a title, subtitle, and a switch" ([HIG: Boxed Lists](https://developer.gnome.org/hig/patterns/containers/boxed-lists.html)).
- **Preferences in general:** the current HIG has no explicit "don't add preferences" rule; this research found none in hig-www. The nearest guidance is "Make it Simple … Don't overwhelm people with too many elements" ([HIG: Design Principles](https://developer.gnome.org/hig/principles.html)). The classic GNOME statement is Havoc Pennington's: "preferences have a cost … each one has a price, and you have to carefully consider its value" ([Free software UI](https://ometer.com/free-software-ui.html)).
- **WCAG 2.2 SC 1.4.11 Non-text Contrast (AA):** "Parts of graphics required to understand the content" need "a contrast ratio of at least 3:1 against adjacent color(s)" ([WCAG 2.2](https://www.w3.org/TR/WCAG22/#non-text-contrast)). [I: the category is also given as text on the card (`category_label`, plus the accessible description), so strictly the badge is supplementary. 3:1 is still the bar used here.]

---

## 5. Contrast measurements (glyph versus the colour directly behind it)

Assumptions: light card `#ffffff`; dark card `rgb(255 255 255 / 8%)` over `#222226`, which gives `#343437`; colours as in §3.1; compositing as in §2.3. "Over tint" means the badge sits on the big square's 18 % tint. "Over a white icon pixel" is the worst case: game icons are arbitrary artwork and show through the 25 %-opaque disc.

| Category (`--category-color`) | Current, light | Current, dark (over tint) | Current, dark (over a white icon pixel) | A solid disc + white (light = dark) | B opaque tint + standalone fg, light | B, dark | HC neutral disc, light / dark |
|---|---|---|---|---|---|---|---|
| words (`#3584e4`) | 4.16 | **2.68** | **2.13** | 3.77 | 4.94 | 6.02 | 12.57 / 12.46 |
| geography (`#3a944a`) | 4.20 | **2.68** | **2.13** | 3.81 | 4.58 | 6.75 | 12.57 / 12.46 |
| music (`#9141ac`) | 5.68 | **2.31** | **2.74** | 5.91 | 5.06 | 6.41 | 12.57 / 12.46 |
| movies-tv (`#e62d42`) | 4.59 | **2.50** | **2.46** | 4.36 | 4.90 | 4.83 | 12.57 / 12.46 |
| video-games (`#d56199`) | 3.95 | **2.74** | **2.05** | 3.50 | 5.35 | 5.40 | 12.57 / 12.46 |
| numbers-logic (`#2190a4`) | 4.15 | **2.68** | **2.12** | 3.76 | 4.61 | 6.64 | 12.57 / 12.46 |
| trivia (`#ed5b00`) | 3.89 | **2.74** | **2.08** | 3.44 | 5.23 | 4.96 | 12.57 / 12.46 |
| visual (`#c88800`) | 3.55 | **2.88** | **1.87** | 3.01 | 5.10 | 5.96 | 12.57 / 12.46 |
| food (`#986a44`) | 4.85 | **2.52** | **2.37** | 4.69 | 4.90 | 6.55 | 12.57 / 12.46 |
| sports (`#6f8396`) | 4.28 | **2.66** | **2.14** | 3.92 | 4.88 | 6.41 | 12.57 / 12.46 |

Bold = below 3:1. Further numbers from the same model:
- **Current, dark:** the disc's alpha is 0.25. Over a black icon pixel contrast is 4.5-6.3, so legibility depends on the artwork beneath. That matches "semi-transparent, hard to read".
- **A:** the disc's edge against the ring is 3.0-5.9 in light (ring white). In dark (ring `#343437`) it is 2.1-4.1: purple 2.11, brown 2.66, red 2.86, the rest at least 3.18. The glyph, not the disc edge, is the information, so this is acceptable [I].
- **"Done" tiles:** these cards are faded to 55 % on purpose (§2.2). With Option A, blue drops to 1.98 in light and 2.57 in dark, yellow to 1.78 and 2.23. This follows from the dimming design, not from the badge.

---

## 6. Answers to the five questions

### 6.1 Shape

- **Circle (current) or rounded square:** both are a plain `border-radius` (§2.1). A circle matches every libadwaita indicator (§3.3) and contrasts with the square tile corner. [I: a rounded square, e.g. `border-radius: 6px`, would echo the 16 px-radius tile, but at 24 px it reads as a tiny copy of the tile and competes with the icon's own silhouette. Keep the circle.]
- **Pill:** only useful with text. Bazaar's "Installed" pill is the precedent (§3.4). A text pill does not fit over a 64 px icon. [I]
- **No background (glyph only):** supported. `-gtk-icon-shadow` and `-gtk-icon-filter` can add a halo ([CSS properties](https://docs.gtk.org/gtk4/css-properties.html); [gtkrendericon.c](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkrendericon.c#L95-160)). Over arbitrary artwork, though, contrast cannot be guaranteed. GNOME apps that use bare glyphs (Software's installed mark, Nautilus emblems) place them **beside** the icon (§3.4). [I: if Dailies wants no disc, the GNOME-consistent move is a bare 16 px glyph off the icon, e.g. before the category caption, not a haloed glyph on the icon.]
- **Ring versus mask:** libadwaita separates a badge from content by masking a 2 px gap out of the content (§3.3). In app CSS the equivalent is a 2 px ring in the card colour. It has to be **opaque**, and `--card-bg-color` is not opaque in the dark style, so build it with background layers (§2.5, §7).

### 6.2 Opacity

- The current CSS sets no `opacity`. The disc is opaque in light (`#ffffff` card) and **25 % opaque in dark**, and the 2 px ring is 8 % white (§2.3, §3.1). The user's "semi-transparent circle" is accurate for the dark style.
- Raising the mix (e.g. 30 %) without fixing the translucent card colour keeps the disc translucent in dark (alpha `0.30 + 0.70 × 0.08 = 0.36`). Even with an opaque base it moves the disc colour towards the glyph colour: with the 75 % fg, light contrast falls to 3.96-4.64. **Do not tune the percentage; make the base opaque.** [I, computed]
- A solid `--category-color` disc with white glyph (Option A) gives 3.01-5.91 in both styles, independent of the icon beneath, and is libadwaita's own pairing ([css-variables](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/css-variables.html#accent-colors)).
- Do not use the `opacity` property on the badge, because it also fades the glyph (§2.2).

### 6.3 Colour

| Option | Fill | Glyph | Light | Dark | HC | Notes |
|---|---|---|---|---|---|---|
| **A (recommended)** | `var(--category-color)` opaque | `white` | 3.01-5.91 | same | neutral disc, see §7 | libadwaita badge/avatar precedent. Yellow is the weakest at 3.01. Use literal `white`, as libadwaita's indicator badge does ([_view-switcher.scss L115](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_view-switcher.scss#L115)): `--accent-fg-color` belongs to the user's accent, not to the category colour. |
| B | 18 % category tint over an opaque card colour | `oklab(from var(--category-color) var(--standalone-color-oklab))` | 4.58-5.35 | 4.83-6.75 | neutral disc | Closest to today's look and the big `.tile-glyph`. Weaker figure/ground against bright icons. |
| C | opaque card colour (no tint) | standalone colour | 5.64-6.59 | 5.44-8.27 | neutral disc | Most legible glyph, but the disc becomes a white or grey dot. Category colour only on the glyph. |
| D | as B | `var(--card-fg-color)` | n/a | n/a | n/a | Drops category colour from the badge. This is what the current HC rule already does. |
| `.osd`-style | `RGB(0 0 0 / 65%)` | `RGB(255 255 255 / 90%)` | varies | varies | n/a | Translucent by design (§3.2). For controls, not colour-coded information. Not recommended. |

Dark and light: the palette backgrounds are identical in both styles (§3.1), so Option A behaves the same in each. libadwaita itself only darkens some status backgrounds in dark, e.g. destructive and error `@red_3`→`@red_4`, success `@green_4`→`@green_5` ([_colors.scss L82-86](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss#L82-86)). [I: Dailies does not need that, since white on the palette already passes 3:1.] Option B's glyph is lighter in dark and darker in light through the standalone formula, exactly as libadwaita's own `--accent-color`.

High contrast: libadwaita does not change the palette under `prefers-contrast: more` (§3.1). The existing Dailies rule already switches the glyph to `--card-fg-color` with an inset `currentColor` outline. Keeping that but making the disc neutral and opaque gives about 12.5:1.

### 6.4 Size

- HIG: symbolics are 16 px and should not be drawn at other sizes (§4). **Use `pixel-size: 16`.** [I: 12 px is the main light-style legibility problem.]
- Disc: 16 px glyph plus 4 px padding gives 24 px. AdwAvatar uses glyph = 50 % of the disc (§3.3). [I: 16/24 = 67 % is the smallest disc that keeps a visible coloured edge round a 16 px glyph.] With the 2 px ring, the badge measures 28 px overall.
- Footprint: the 40 px game icon is centred in the 64 px square (12 px margin, from `game-tile.blp`). A 28 px badge at the corner covers up to 16 px of each edge of the icon. libadwaita's AdwTabButton offsets its dot past the icon's corner with `transform: translate(…)` and a `:dir(rtl)` mirror (§3.3). [I: an optional `translate(4px, 4px)` (mirrored as `translate(-4px, 4px)` in RTL) cuts the overlap to 12 px. GtkOverlay does not clip children, so the badge may draw a few pixels outside the square. The tile has 6 px of overlay margin plus 6 px of spacing below the square for it. Check visually.]
- If 28 px is too big: keep a 12 px glyph on a 20 px disc but raise `-gtk-icon-weight` (e.g. 700 ≈ 125 % stroke, §2.4) so strokes stay near 2 px. That only works if GTK applies weight to these legacy-class icons, which is unverified. [I]

### 6.5 Preferences switch

- **Schema:** boolean `show-category-badge`, default `true`, in the app schema. The Dailies schema already uses this shape for `show-other-languages` (`data/io.github.tim_van_oudheusden.Dailies.gschema.xml.in`).
- **Preferences row:** an `Adw.SwitchRow` (it has an `active` property; [AdwSwitchRow](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.SwitchRow.html)) bound with `settings.bind("show-category-badge", row, "active", Gio.SettingsBindFlags.DEFAULT)`, matching the existing rows in `dailies/ui/preferences.py`. The default flags also bind the row's `sensitive` property to the key's writability, so a locked-down key greys out the switch ([Gio.Settings.bind](https://docs.gtk.org/gio/method.Settings.bind.html); [gsettings.c L3050-3060](https://gitlab.gnome.org/GNOME/glib/-/blob/ae8632bab1b5f09f2bb996c9637b1added5b038f/gio/gsettings.c#L3050-3060)).
- **Live reaction in the grid:** tiles come from a `BuilderListItemFactory` template (`data/ui/window.blp`), so the window cannot pass a constructor argument. Two GIO mechanisms exist:
  1. **Bind a tile property** (recommended): give `GameTile` a boolean GObject property (e.g. `show-category-badge`) whose setter re-runs `_show_icon()`, and in `__init__` call `Gio.Settings.new(APP_ID).bind("show-category-badge", self, "show-category-badge", Gio.SettingsBindFlags.GET)`.
     - GET-only means no sensitivity binding is made: it requires `G_SETTINGS_BIND_SET` ([L3050](https://gitlab.gnome.org/GNOME/glib/-/blob/ae8632bab1b5f09f2bb996c9637b1added5b038f/gio/gsettings.c#L3050)). Default flags would otherwise make the whole tile insensitive when an admin locks the key.
     - The binding holds a reference to the `GSettings` ([L2970](https://gitlab.gnome.org/GNOME/glib/-/blob/ae8632bab1b5f09f2bb996c9637b1added5b038f/gio/gsettings.c#L2970)), so the temporary object survives.
     - It connects `changed::<key>` and applies the current value at once ([L3076-3090](https://gitlab.gnome.org/GNOME/glib/-/blob/ae8632bab1b5f09f2bb996c9637b1added5b038f/gio/gsettings.c#L3076-3090)).
     - The binding's lifetime is tied to the object ([docs](https://docs.gtk.org/gio/method.Settings.bind.html)).
     - [I: GridView recycles a bounded set of tiles, so the number of `GSettings` instances stays small.]
  2. **`changed::show-category-badge` handler:** works, but GIO only emits `changed` for a key "if you have read @key at least once while a signal handler was already connected" ([gsettings.c L815-828](https://gitlab.gnome.org/GNOME/glib/-/blob/ae8632bab1b5f09f2bb996c9637b1added5b038f/gio/gsettings.c#L815-828)). The handler must also be disconnected by hand. Dailies uses this style for window-level keys (`dailies/window.py`). [I: for a per-widget visual flag, a property binding is simpler and self-cleaning.]
  - A CSS-class toggle on the grid (e.g. `.hide-category-badges .tile-badge { opacity: 0 }`) would still allocate the badge and use `opacity` as a stand-in for `visible`. Not recommended. [I]
- **Product rule:** `category_badge.visible = has_icon and show_badge`. The glyph in the big square (`glyph.icon_name = None if icon else category glyph`) ignores the switch. That is the fallback for games without an icon. [I: under the repo's TDD rule, put the decision in `dailies/core` as a pure function (e.g. `badge_visible(has_icon: bool, setting: bool) -> bool`) so pytest covers the fallback, and keep `tile.py` thin.]
- **Wording:**
  - HIG-strict: a noun in header capitals with an access key, e.g. **"_Category Badges"**, subtitle **"Show each game's category on its icon"** (§4).
  - Dailies' existing rows use sentence-case phrases ("Show games in other languages", "Mark games as done automatically" in `data/ui/preferences.blp`). [I: follow the app's convention for consistency, e.g. title "Category badge on game icons", subtitle "Games without an icon always show their category". The subtitle states the fallback, so users don't expect the switch to remove the glyph from icon-less games. The HIG/app capitalisation mismatch is app-wide; see Open questions.]
- **Whether to add it at all:** each preference has a cost (§4). [I: fix legibility first (§7). The switch is still a binary, low-risk appearance option, and an "Appearance" group is the natural place.]

---

## 7. Recommendations for Dailies

### 7.1 Recommended: Option A, a solid category disc

Blueprint (`data/ui/game-tile.blp`), `category_badge`: change `pixel-size: 12` to **`pixel-size: 16`**.

CSS (`data/ui/style.css`), replacing the current `.tile-badge` rules:

```css
/* A game with an icon keeps its category glyph in this badge on the square's corner: a white glyph on a solid disc of
 * the category's colour, like libadwaita's own badges, ringed by the card's colour so it stands off the icon. The ring
 * is painted as background layers (card over window), because --card-bg-color is translucent in the dark style. */
.tile-badge {
  min-width: 16px;                 /* the 16 px glyph (pixel-size in game-tile.blp) */
  min-height: 16px;
  padding: 4px;                    /* 24 px disc */
  border: 2px solid transparent;   /* 2 px ring: 28 px overall */
  border-radius: 999px;
  color: white;
  background-color: var(--window-bg-color);
  background-image: image(var(--category-color)), image(var(--card-bg-color));
  background-clip: padding-box, border-box;
}

@media (prefers-contrast: more) {
  .tile-badge {
    color: var(--card-fg-color);
    background-image: none, image(var(--card-bg-color));
    box-shadow: inset 0 0 0 1px currentColor;
  }
}
```

Optional, to cover less of the icon (AdwTabButton precedent, §6.4):

```css
.tile-badge:dir(ltr) { transform: translate(4px, 4px); }
.tile-badge:dir(rtl) { transform: translate(-4px, 4px); }
```

Expected contrast: 3.01-5.91:1 for the glyph in light and dark; about 12.5:1 in high contrast (§5).

### 7.2 Alternative: Option B, opaque tint plus standalone colour (closest to today)

```css
.tile-badge {
  min-width: 16px;
  min-height: 16px;
  padding: 4px;
  border: 2px solid transparent;
  border-radius: 999px;
  color: oklab(from var(--category-color) var(--standalone-color-oklab));
  background-color: var(--window-bg-color);
  background-image:
    image(color-mix(in srgb, var(--category-color) 18%, transparent)),
    image(var(--card-bg-color)),
    image(var(--card-bg-color));
  background-clip: padding-box, padding-box, border-box;
}
```

(Same high-contrast block as in §7.1, with three `background-image` layers: `none, none, image(var(--card-bg-color))`.) Glyph contrast is 4.58-5.35 in light and 4.83-6.75 in dark. [I: consider moving `.tile-glyph`'s foreground to the same standalone formula for consistency. The current 75 % mix scores lower: 3.55-5.68 in light.]

### 7.3 Alternative: Option C, move the glyph off the icon

Show a bare 16 px category glyph before `category_label` in the caption row, as Nautilus, GNOME Software and Bazaar do (§3.4), and drop the corner badge. This needs no disc and no ring, and the glyph inherits the caption's `.dimmed` contrast. The trade-off: the category no longer sits on the icon, where people scan.

### 7.4 Preference

As in §6.5: GSettings boolean `show-category-badge` (default `true`); `Adw.SwitchRow` in an "Appearance" group bound with `DEFAULT`; tile property bound with `GET`. The switch hides only the corner badge, and the big-square glyph fallback always stays.

### 7.5 Verification checklist

Check in GTK Inspector, toggling dark style and high contrast:
1. The badge is opaque over a bright and a dark game icon in both styles.
2. Ring colour matches the card, including on hover (4 % difference expected).
3. The 16 px glyph is crisp.
4. RTL placement, if the transform is used.
5. "Done" tiles are dimmed as before.
6. Flipping the switch updates visible tiles at once, and icon-less games keep their big glyph.

### 7.6 What shipped (#195)

Option A, with two simplifications, checked by rendering tiles with real game icons on the GNOME 51 SDK (Broadway; light, dark, and high contrast through `GtkCssProvider:prefers-contrast`):
- The ring is two stacked outset shadows, `box-shadow: 0 0 0 2px var(--card-bg-color), 0 0 0 2px var(--window-bg-color)`. The first is painted on top, so the translucent dark card colour lands on the opaque window colour and the ring matches the card. The disc keeps a 24 px allocation (`min-width`/`min-height: 24px` around the 16 px glyph); the ring draws outside it, so no `border` or extra background layers are needed.
- No `transform` offset. The badge stays inside the 64 px square.
- High contrast: `--card-fg-color` glyph on `--window-bg-color` under `image(var(--card-bg-color))`, an inset `currentColor` ring, and the same outer ring.

---

## 8. Open questions

- Does GTK 4.24 apply `-gtk-icon-weight` to legacy class-based stroked symbolics (no `gpa:` attributes)? `svg_element_get_stroke` only applies weight when `allow_gpa` is true and min/max widths are set ([gtksvgelement.c L1210-1235](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/svg/gtksvgelement.c#L1172-1235)). This decides whether the "keep 12 px, raise weight" fallback in §6.4 works. Check in GTK Inspector.
- Is a 28 px badge acceptable on a 64 px square with a 40 px icon, or should the game icon shrink (e.g. to 36 px), or the badge be offset with `transform` (§6.4)? This is a visual call for the owner.
- Yellow (`#c88800`) with white scores exactly 3.01:1. Is that enough, or should "visual" use a darker palette yellow, e.g. `--yellow-5`, for its disc only? libadwaita's own warning colour uses `@yellow_5` with a dark foreground ([_colors.scss L19-20](https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss#L19-20)).
- Switch-label capitalisation: the HIG asks for header-capitalised nouns (§4), but Dailies' Preferences rows use sentence case throughout. Resolve this app-wide, not per row.
- The contrast figures model the dark card as `#343437`, which assumes the grid sits on `--window-bg-color` (`#grid { background: none; }` in `style.css`). If the library is later placed on a `.view` background (`--view-bg-color #1d1d20`), recompute.

---

## Sources

- https://docs.gtk.org/gtk4/css-properties.html
- https://docs.gtk.org/gtk4/css-overview.html
- https://docs.gtk.org/gtk4/icon-format.html
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/docs/reference/gtk/css-properties.md
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/docs/reference/gtk/icon-format.md
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/NEWS
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkwidget.c#L12151-12174
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkcsscolor.c#L780-830
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkcssstyle.c#L876-899
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkrendericon.c#L95-160
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkiconhelper.c#L186-235
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkrenderbackground.c#L55-133
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/gtkcssboxesimplprivate.h#L123-216
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/svg/gtksvgelement.c#L1172-1235
- https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.0/gtk/svg/gtksvgproperty.c#L1342-1343
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/css-variables.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/style-classes.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.SwitchRow.html
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/doc/css-variables.md
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_colors.scss
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/_common.scss#L44-50
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_view-switcher.scss#L83-124
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_tab-view.scss#L201-212
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_avatar.scss
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_misc.scss#L201-238
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_buttons.scss#L113-121
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/stylesheet/widgets/_buttons.scss#L328-342
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/adw-indicator-bin.c#L143-200
- https://gitlab.gnome.org/GNOME/libadwaita/-/blob/1.10.0/src/adw-avatar.c#L756-762
- https://developer.gnome.org/hig/guidelines/ui-icons.html
- https://developer.gnome.org/hig/guidelines/ui-styling.html
- https://developer.gnome.org/hig/guidelines/accessibility.html
- https://developer.gnome.org/hig/guidelines/writing-style.html#header-capitalization
- https://developer.gnome.org/hig/patterns/controls/switches.html
- https://developer.gnome.org/hig/patterns/containers/boxed-lists.html
- https://developer.gnome.org/hig/principles.html
- https://gitlab.gnome.org/Teams/Design/hig-www/-/tree/97028eac37922e787cad5796215f7e986451883a/source
- https://docs.gtk.org/gio/method.Settings.bind.html
- https://gitlab.gnome.org/GNOME/glib/-/blob/ae8632bab1b5f09f2bb996c9637b1added5b038f/gio/gsettings.c
- https://www.w3.org/TR/WCAG22/#non-text-contrast
- https://www.w3.org/TR/WCAG22/#dfn-relative-luminance
- https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio
- https://www.w3.org/TR/css-color-5/#color-mix
- https://gitlab.gnome.org/GNOME/gnome-software/-/blob/b71574d2cbc1eb45df62b08065c72658daadb4cb/src/gs-summary-tile.ui
- https://gitlab.gnome.org/GNOME/nautilus/-/blob/8fd4b29261e641d1e6bdb83cc841837d12aefff6/src/resources/ui/nautilus-grid-cell.blp
- https://gitlab.gnome.org/GNOME/nautilus/-/blob/8fd4b29261e641d1e6bdb83cc841837d12aefff6/src/nautilus-grid-cell.c
- https://github.com/bazaar-org/bazaar/blob/3d347d5d0fb828a0ff6ff0c1dcd356b26ddfdd33/src/bz-app-tile.blp
- https://github.com/bazaar-org/bazaar/blob/3d347d5d0fb828a0ff6ff0c1dcd356b26ddfdd33/src/style.css
- https://github.com/kra-mo/cartridges/blob/d56323e6dd0ba9b500ee4f2b11d95f2e6240b05f/data/gtk/game.blp
- https://ometer.com/free-software-ui.html
