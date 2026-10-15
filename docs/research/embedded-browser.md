# Dailies — Research report: opening DLE game URLs (embedded browser vs. external browser)

Research key: `embedded-browser`
Date of research: 2026-10-15
Author: research subagent (for the Dailies architecture/design document)

Legend used throughout: **[V]** = verified against a primary source or by running a command on this machine (source given); **[I]** = inference / recommendation by the author; **[U]** = could not be verified.

---

## 0. TL;DR

1. **WebKitGTK 6.0 is in the GNOME Flatpak runtime; no module to build.** `org.gnome.Platform//49`, `//50` and `//51` all ship `libwebkitgtk-6.0.so.4.19.4`, `WebKit-6.0.typelib`, and the `WebKitWebProcess`/`WebKitNetworkProcess`/`WebKitGPUProcess` helpers in `/usr/libexec/webkitgtk-6.0/`. The gnome-49 branch of gnome-build-meta builds **WebKitGTK 2.54.1** (released 2026-10-02). **[V]** (inspected the installed runtimes with `flatpak run --command=sh org.gnome.Platform//49`; `elements/sdk/webkitgtk.inc` on gnome-49.)
2. **Persistent game progress needs two things:** a *non-ephemeral* `WebKit.NetworkSession.new(data_dir, cache_dir)` (gives persistent localStorage/IndexedDB under `data_dir`), **plus** an explicit `cookie_manager.set_persistent_storage(path, SQLITE)` because *"By default, cookie_manager doesn't store the cookies persistently"* **[V]** (WebKitCookieManager.cpp doc comment). Every reference app (Tangram, Wike, Komikku) does exactly this.
3. **Opening the system default browser from a Flatpak = `Gtk.UriLauncher`** (GTK ≥ 4.10; runtime 49 has GTK 4.20.4). In a sandbox GTK routes it to the `org.freedesktop.portal.OpenURI` portal (needs portal version ≥ 3). The portal **skips the app chooser for `http`/`https` when a default browser exists** and opens the host's default browser. **[V]** (gtkurilauncher.c, xdg-desktop-portal `desktop-portal/open-uri.c`.) Bazaar (the UI reference app) uses `gtk_uri_launcher_launch()` everywhere. **[V]**
4. **"Open in a specific, user-chosen browser" is the hard part.** Inside the sandbox an app cannot enumerate host browsers (`gio mime x-scheme-handler/https` inside `org.gnome.Platform//49` → *"No default applications"*; `/run/host/share` contains only `icons`) **[V, measured here]**. The realistic options are: (a) the portal's own chooser via the `ask=true` option (`libportal` `XDP_OPEN_URI_FLAG_ASK`, or a direct D-Bus call; `Gtk.UriLauncher` does not expose it) **[V]**; (b) `flatpak-spawn --host …`, which requires `--talk-name=org.freedesktop.Flatpak`, flagged by the Flathub linter as `finish-args-flatpak-spawn-access` ("Granted on sufficient explanation"; it is literally a sandbox escape — *"a sandbox escape allowing arbitrary code execution"* per flatpak's own D-Bus interface docs) **[V]**. 168 of the 1 542 apps in Flathub's `exceptions.json` hold that exception; one (`io.github.alyraffauf.Switchyard`) has it for exactly "Required to launch browsers the user has installed on their system" — so it is *possible*, but it is a heavy ask for a game launcher. **[V]**
5. **Recommended design:** default to the **built-in WebKitGTK browser** (persistent shared session, back/forward/reload toolbar, "Open in Browser" escape hatch, per-game override); offer **"System default browser"** (portal) and **"Ask which app"** (portal chooser, `ask=true`); ship an *opt-in power-user* key `external-browser-command` that only works if the user themselves grants `org.freedesktop.Flatpak` via `flatpak override` — do **not** request it in the Flathub manifest. Cross-platform: make WebKit a Meson feature option (as Tuba does with `-Din-app-browser`) and degrade to the external browser where WebKitGTK does not exist (Windows). Full GSettings schema in §10.
6. **Legal/privacy:** NYT's Terms of Service (effective 2026-01-20) restrict *"display (including framing and inline linking)"* of Content (§2.2) and limit use to personal, non-commercial purposes **[V]**. A top-level WebView is a browser, not a frame **[I]**, but Dailies must *not* block ads, inject scripts, rewrite pages or spoof a foreign browser identity, and should show the real URL and offer "Open in Browser" at all times. Obsidian's Web viewer enables ad blocking by default — Dailies should not copy that. **[I]**

---

## 1. WebKitGTK 6.0 in the GNOME Flatpak runtime — verification

### 1.1 What is actually in `org.gnome.Platform`

Run on this machine (Flatpak 1.18.4) on 2026-10-15:

```
$ flatpak run --user --command=sh org.gnome.Platform//49 -c '...'
libjavascriptcoregtk-4.1.so.0.11.8      libjavascriptcoregtk-6.0.so.1.8.8
libwebkit2gtk-4.1.so.0.24.4             libwebkitgtk-6.0.so.4.19.4
girepository-1.0: JavaScriptCore-4.1  JavaScriptCore-6.0  Soup-3.0  WebKit2-4.1
                  WebKit2WebExtension-4.1  WebKit-6.0  WebKitWebProcessExtension-6.0
/usr/libexec/webkitgtk-6.0: jsc  MiniBrowser  WebKitGPUProcess  WebKitNetworkProcess  WebKitWebProcess
/etc/os-release: NAME=GNOME VERSION="49 (Flatpak runtime)" ID=org.gnome.Platform
```

Identical library versions were found in `org.gnome.Platform//50` and `//51` (runtime commits dated 2026-10-03 for 49/50 and 2026-10-14 for 51). **[V]**

Other runtime facts measured in `//49` (relevant to the stack choice): `libgtk-4.so.1.2000.4` (GTK 4.20.4), `libsoup-3.0.so.0.7.4`, Python 3.13.15, PyGObject 3.54.5, GJS 1.86.0, typelibs `Gtk-4.0`, `Adw-1`, `WebKit-6.0`, `Soup-3.0`. **No libportal** (`Xdp-1.0` / `XdpGtk4-1.0` typelibs are *absent*) — Epiphany's manifest builds libportal as its own module for that reason. **[V]**

### 1.2 Which WebKitGTK version, and how it is built

`gnome-build-meta` branch `gnome-49`, file `elements/sdk/webkitgtk.inc` **[V]**:

```yaml
sources:
- kind: tar
  url: webkitgtk:webkitgtk-2.54.1.tar.xz
  ref: ea0bbb02dbdbc596874a4e7ad35b66645b3e0a232bd0e4081de5ed92eb0a397d
...
depends:
- sdk/at-spi2-core.bst
- sdk/enchant-2.bst
- sdk/libmanette-0.2.bst
- sdk/libsecret.bst
- freedesktop-sdk.bst:components/bubblewrap.bst
- freedesktop-sdk.bst:components/gstreamer-plugins-bad.bst
- freedesktop-sdk.bst:components/libavif.bst
- freedesktop-sdk.bst:components/libjxl.bst
- freedesktop-sdk.bst:components/xdg-dbus-proxy.bst
...
environment:
  CC: clang
  CXX: clang++
```

and `elements/sdk/webkitgtk-6.0.bst` **[V]**:

```yaml
kind: cmake
(@):
  - elements/sdk/webkitgtk.inc
depends:
  (>):
  - sdk/gtk.bst
  - sdk/libsoup.bst
variables:
  cmake-local: >-
    -DPORT=GTK
    -DENABLE_SPEECH_SYNTHESIS=OFF
    -DUSE_GTK4=ON
    -DUSE_LIBBACKTRACE=OFF
```

webkitgtk.org lists **2.54.1 as the latest stable, dated 2026-10-02** **[V]**. Consequence for Dailies: the `org.gnome.Platform` branch you pick determines the WebKit engine; GNOME runtimes are "supported for a year and EOL-ed upon the release of a new stable version" (docs.flatpak.org, Available runtimes) **[V]**.

### 1.3 Real GNOME apps that embed WebKitGTK 6.0 (verified) and ones that do not

| App | Flathub ID | Language | Builds WebKit itself? | Runtime | What it uses WebKit for | Source checked |
|---|---|---|---|---|---|---|
| Tangram | `re.sonny.Tangram` | GJS | No (runtime) | GNOME 51 | Full "web-app per tab" browser, one persistent `NetworkSession` per tab | `src/WebView.js`, `src/instances.js` **[V]** |
| GNOME Web (Epiphany) | `org.gnome.Epiphany` | C | No (runtime; builds `libportal`, `libpwquality` only) | `master` | Browser | `org.gnome.Epiphany.json` **[V]** |
| Wike | `com.github.hugolabe.Wike` | Python | No | GNOME 50 | Wikipedia reader (default `NetworkSession` + persistent cookies) | `src/view.py` **[V]** |
| Komikku | `info.febvre.Komikku` | Python | No | GNOME 50 | Hidden WebView for Cloudflare challenges / OAuth; own `NetworkSession.new(data,cache)` | `komikku/webview.py` **[V]** |
| Tuba | `dev.geopjr.Tuba` | Vala | No (optional `-Din-app-browser` Meson feature) | GNOME 51 | In-app browser `Adw.Dialog` with back/forward/reload/"Open in Browser" | `meson.build`, `src/Views/Browser.vala`, gschema **[V]** |
| NewsFlash | `io.gitlab.news_flash.NewsFlash` | Rust | No | GNOME 50 | Article view | manifest **[V]** (code not inspected) |
| Decibels | `org.gnome.Decibels` | — | — | — | **does not use WebKit** (0 matches in manifest) | **[V]** |
| Spot | `dev.alextren.Spot` | — | — | — | **does not use WebKit** (0 matches in manifest) | **[V]** |

All WebKit-embedding manifests above share the finish-args pattern `--share=network --share=ipc --socket=wayland --socket=fallback-x11 --device=dri` (+ `--socket=pulseaudio` when media matters). **[V]** Epiphany additionally has `--filesystem=xdg-download` (because it saves downloads itself) and `--device=input`. **[V]**

### 1.4 Flatpak sandbox permissions needed for a WebKitGTK view

- `--share=network` — obviously. **[V]** (all reference manifests)
- `--device=dri` — "Direct Rendering Interface. Necessary for GL." (docs.flatpak.org sandbox-permissions) **[V]**; WebKitGTK ≥ 2.46 renders with Skia on the GPU by default and shares composited buffers as DMA-BUF **[V]** (webkitgtk.org 2.46 notes; Igalia blog 2024-09-27). Without `--device=dri` you get software rendering at best. **[I]**
- `--share=ipc` with `--socket=fallback-x11` (Flathub linter: `finish-args-x11-without-ipc` is "never granted" otherwise). **[V]**
- `--socket=pulseaudio` only if games with sound matter. **[I]**
- **No** `--filesystem` is needed for website data: WebKit stores it under the app's own `$XDG_DATA_HOME`/`$XDG_CACHE_HOME`, which inside Flatpak are `~/.var/app/<id>/data` and `~/.var/app/<id>/cache`. **[V/I]** (default dirs below; Flatpak redirects XDG dirs.)
- **No** extra D-Bus names: WebKit's own multi-process sandbox inside Flatpak is done with `flatpak-spawn --sandbox` through the always-available `org.freedesktop.portal.Flatpak`; `ProcessLauncherGLib.cpp`: *"You cannot use bubblewrap within Flatpak or some containers so lets ensure it never happens"*, and `isFlatpakSpawnUsable()` probes `flatpak-spawn --sandbox …` (needs "flatpak >= 1.5.2 on the host and flatpak-xdg-utils > 1.0.1 in the sandbox"). **[V]**
- `--filesystem=xdg-download` only if you let WebKit save downloads itself (default destination is `G_USER_DIRECTORY_DOWNLOAD`). Recommended instead: cancel downloads and hand the URL to the external browser (Tangram/Tuba pattern), so no filesystem permission at all. **[V]** for the pattern, **[I]** for the recommendation.

---

## 2. WebKitGTK 6.0 API usage from a GTK4/Libadwaita app

All names below are from the `webkitgtk-6.0` reference (webkitgtk.org/reference/webkitgtk/stable/, library 2.54.1) unless noted.

### 2.1 Network session, website data, persistence

- `WebKit.NetworkSession.new(data_directory, cache_directory)` — *"A base directory for data, or NULL"*; *"if NULL is passed, the default directory will be passed to WebKitWebsiteDataManager"*. `WebKit.NetworkSession.new_ephemeral()` for private sessions. `WebKit.NetworkSession.get_default()` returns the default one. All since 2.40. **[V]**
- Default directories (WebKit source `WebsiteDataStoreGLib.cpp`): `<user data dir>/<g_get_prgname()>` and `<user cache dir>/<g_get_prgname()>` (falls back to `"webkitgtk"` if no prgname). **[V]**
- `WebKit.WebsiteDataManager` (obtained via `network_session.get_website_data_manager()`): properties `base-data-directory`, `base-cache-directory`, `is-ephemeral`, `origin-storage-ratio` (2.42; default −1.0 = the 1 GiB default quota), `total-storage-ratio` (2.42); methods `fetch/remove/clear` (2.16), `set_favicons_enabled` (2.40, favicons are disabled by default), `get_favicon_database` (2.40). **[V]**
- Within `base-data-directory` WebKit creates `localstorage/`, `databases/indexeddb/`, `itp/`, `serviceworkers/` (`WebKitWebsiteDataManager.cpp`). **[V]**
- `WebKit.WebsiteDataTypes` flags (all 2.16): `MEMORY_CACHE`, `DISK_CACHE`, `OFFLINE_APPLICATION_CACHE`, `SESSION_STORAGE`, `LOCAL_STORAGE`, `INDEXEDDB_DATABASES`, `COOKIES`, `DEVICE_ID_HASH_SALT`, `HSTS_CACHE`, `ITP`, `SERVICE_WORKER_REGISTRATIONS`, `DOM_CACHE`, `ALL`(4095). Use them for a "Clear website data" preference. **[V]**
- **Cookies:** `network_session.get_cookie_manager()`; `set_persistent_storage(filename, WebKit.CookiePersistentStorage.SQLITE|TEXT)`; `set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS|NEVER|NO_THIRD_PARTY)`. Source doc comment: *"By default, @cookie_manager doesn't store the cookies persistently, so you need to call this method to keep cookies saved across sessions. This method should never be called on a WebKitCookieManager associated with an ephemeral WebKitWebsiteDataManager."* **[V]** — this is the single most important detail for streak persistence.
- **ITP:** `network_session.set_itp_enabled(bool)` (2.40). *"while ITP is enabled the accept policy WEBKIT_COOKIE_POLICY_ACCEPT_NO_THIRD_PARTY is ignored and WEBKIT_COOKIE_POLICY_ACCEPT_ALWAYS is used instead"* (WebKitNetworkSession.cpp). Default value not stated in docs **[U]**; Komikku explicitly calls `set_itp_enabled(False)`. **[V]**
- Credentials: `set_persistent_credential_storage_enabled`; TLS: `set_tls_errors_policy(WebKit.TLSErrorsPolicy.FAIL)` (Tangram does this). **[V]**

### 2.2 WebView construction and the "related-view" rule

`WebKit.WebView` construct-only properties: `network-session` (2.40), `settings`, `user-content-manager`, `web-context`, `related-view` (write-only: *"The related WebKitWebView used when creating the view to share the same web process and network session"*), `is-controlled-by-automation`. The view is scrollable on its own (no `Gtk.ScrolledWindow`). **[V]**

Key methods: `load_uri`, `go_back`, `go_forward`, `reload`, `stop_loading`, `get_estimated_load_progress`, `get_title`, `get_uri`, `get_page_icons()` → `WebKit.ImageList` (2.54; `get_favicon` deprecated 2.54), `evaluate_javascript`, `set_zoom_level`, `set_background_color` (2.8), `terminate_web_process` (2.34), `try_close` (2.12). Bindable properties used by Tuba: `title`, `uri`, `estimated-load-progress`, `is-loading`. **[V]**

### 2.3 Settings: user agent, hardware acceleration, JS/popups

`WebKit.Settings` properties relevant to Dailies **[V]**:

| Property | Note |
|---|---|
| `user-agent` / `set_user_agent_with_application_details(name, version)` | *"appending the application details to the default user agent"*. Default UA (WebCore `UserAgentGLib.cpp`): `Mozilla/5.0 (<platform>) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/60.5 Safari/605.1.15` — *"Many websites discriminate against relatively recent Safari versions, so we need to pick a higher version number than real Safari."* |
| `hardware-acceleration-policy` (2.16) | enum has only `ALWAYS` (0) and `NEVER` (1) in 6.0 (the old ON_DEMAND is gone). Tuba sets `NEVER` for its in-app browser; Tangram/Wike/Komikku leave the default. Default value not stated on the enum page **[U]**; 2.46 release notes say accelerated compositing is now on by default **[V]**. |
| `enable-2d-canvas-acceleration` (2.46) | Default on. Many DLEs are canvas-free DOM games, but some use canvas. |
| `javascript-can-open-windows-automatically` | Popups; Tuba `false`, Tangram `true`. |
| `allow-modal-dialogs` | `window.showModalDialog`. |
| `enable-developer-extras` | Web Inspector; enable only in dev profile. |
| `enable-back-forward-navigation-gestures` (2.24) | Horizontal swipe = back/forward; nice on touchpads. |
| `enable-smooth-scrolling`, `enable-webgl`, `enable-media` (2.26), `enable-mediasource` (2.4), `enable-webrtc` (2.38; set false), `media-playback-requires-user-gesture` | self-explanatory |
| `allow-top-navigation-to-data-urls` (2.28) | keep `false` (phishing). |
| `enable-write-console-messages-to-stdout` (2.2) | debugging. |
| `webkit_settings_apply_from_key_file()` (2.46) | lets you ship settings as a GKeyFile. |
| `webkit_settings_get_all_features()` / `set_feature_enabled()` | Komikku uses this to toggle internal features (e.g. `JavaScriptCanAccessClipboard`). |

### 2.4 Popups / new windows: `create` + `decide-policy`

- `WebKitWebView::create(navigation_action) → WebKitWebView*|NULL`: *"Emitted when the creation of a new WebKitWebView is requested… The new WebKitWebView must be related to web_view, see WebKitWebView:related-view… should not be displayed to the user until the WebKitWebView::ready-to-show signal is emitted"*. Return `NULL` to decline. **[V]**
- `decide-policy(decision, type)` with `WebKit.PolicyDecisionType`:
  - `NAVIGATION_ACTION` (0): *"requested when WebKit is about to navigate to a new page"* → `use()`/`ignore()`.
  - `NEW_WINDOW_ACTION` (1): about to create a new window → useful *"forcing the new window to open in a tab when a keyboard modifier is active"*.
  - `RESPONSE` (2): response received → `use()`, `ignore()`, or `download()` *"rather than rendered in the WebView"*. `WebKit.ResponsePolicyDecision.is_mime_type_supported()` tells you whether WebKit can render it. **[V]**
- `WebKit.NavigationAction` exposes `get_navigation_type()` (`LINK_CLICKED`, `RELOAD`, `BACK_FORWARD`, `OTHER`, …), `get_mouse_button()`, `get_modifiers()`, `get_request().get_uri()`. **[V]** (used by Tangram, Wike)

Patterns found:
- **Tangram** (`src/WebView.js`): `create` → if tab is "temporary" load in same view, else `Gtk.show_uri(window, url)` (external browser). `decide-policy` NAVIGATION_ACTION: middle-click or Ctrl+click → `decision.ignore()` + open externally. **[V]**
- **Tuba** (`src/Views/Browser.vala`): `create` → open URL externally and return `null`; `decide-policy` NEW_WINDOW_ACTION → load in *same* view + `ignore()`; RESPONSE with unsupported, non-`text/*` MIME → open externally + `ignore()`; `download-started` → `download.cancel()` + open externally. **[V]**
- **Wike** (`src/view.py`): `do_decide_policy` LINK_CLICKED to non-wikipedia host → `ignore()` + `Gtk.show_uri`; middle-click → new in-app page. **[V]**

### 2.5 Downloads

`WebKit.NetworkSession::download-started(download)`; `WebKit.Download` signals `decide-destination(suggested_filename)` (call `set_destination()`), `created-destination`, `received-data`, `finished`, `failed`; `set_allow_overwrite` (2.6), `cancel()`, `get_request()`, `get_response()`, `get_estimated_progress()`. *If `decide-destination` is not handled WebKit saves to `G_USER_DIRECTORY_DOWNLOAD` with the server-suggested filename* — inside Flatpak that needs `--filesystem=xdg-download`. **[V]** Tangram shows a `Gtk.FileDialog.save()` and routes `http(s)` downloads to the default browser (`AppInfo.launch_default_for_uri`) — with a comment pointing at WebKit bug 201868 regarding `set_allow_overwrite`. **[V]**

### 2.6 Hardware acceleration & graphics in Flatpak

- WebKitGTK 2.46+ uses **Skia**, GPU rendering by default, DMA-BUF buffer sharing between web process and UI process; `enable-2d-canvas-acceleration` added. **[V]** (webkitgtk.org 2.46 "What's new"; Igalia blog 2024-09-27 — *"webkit://gpu reports the DMA-BUF buffer format and modifier"*; `webkit://gpu/stdout`.)
- `WEBKIT_DISABLE_DMABUF_RENDERER` still exists in WebKit main (`Source/WebKit/UIProcess/gtk/AcceleratedBackingStore.cpp`: `getenv("WEBKIT_DISABLE_DMABUF_RENDERER")`, else requires `EGL_KHR_platform_gbm` or `EGL_MESA_platform_surfaceless`). `WEBKIT_DISABLE_COMPOSITING_MODE=1` forces accelerated compositing off (WebKitGTK ≥ 2.10.9, trac wiki; page marked possibly outdated). Tauri's Linux troubleshooting guide uses both as workarounds. **[V]** Caveat: WebKit bug 306993 (Feb 2026 build) reported crashes when either variable is set. **[V]** → expose them only as a hidden "safe rendering" toggle. **[I]**
- Flatpak side: `--device=dri` is the standard GL permission; the runtime pulls Mesa through `org.freedesktop.Platform.GL.default`. **[V]**

### 2.7 Memory footprint and process model

- WebKitGTK is multi-process: UI process (your app) + `WebKitNetworkProcess` + one or more `WebKitWebProcess` (+ `WebKitGPUProcess` binary present in the runtime). `WebKit.WebContext` in 6.0 exposes **no** `set_process_model`/`web-process-count-limit` any more (not in the 6.0 docs) **[V]**; process allocation is WebKit-internal. **[I]**
- `WebKit.MemoryPressureSettings` can be attached via `WebContext:memory-pressure-settings` (2.34) and `WebKit.NetworkSession.set_memory_pressure_settings()` (2.40) **[V]** (the class page itself returned 404 in this session so individual method names are **[U]**).
- `WebKit.WebContext.set_cache_model(WebKit.CacheModel.DOCUMENT_VIEWER | DOCUMENT_BROWSER | WEB_BROWSER)` — Komikku uses `DOCUMENT_VIEWER` (smallest), Tuba `DOCUMENT_BROWSER`. **[V]**
- **Hard numbers:** no current primary source gives per-view RSS; only old anecdotes (Epiphany 2016: ≈250 MB per loaded-tab web process, ≈55 MB unloaded, network+DB ≈40 MB). **[U]** I did *not* measure on this machine because MiniBrowser needs a visible window on the user's desktop. **Recommendation [I]:** keep at most one live `WebKit.WebView` per open game page, destroy the view when the page is popped (`try_close()`), and set a conservative cache model.

### 2.8 Web Inspector / debugging

`enable-developer-extras=true` + `webview.get_inspector().show()`; env `WEBKIT_INSPECTOR_SERVER=ip:port` / `WEBKIT_INSPECTOR_HTTP_SERVER` for remote inspection; `WEBKIT_SHOW_FPS=1`; `WEBKIT_DEBUG=all`. **[V]** (trac wiki, archived.)

---

## 3. Opening the *system default* browser from the sandbox

### 3.1 API

- `Gtk.UriLauncher.new(uri)`; `launch(parent_window, cancellable, callback)`; `launch_finish()`; since GTK 4.10. `can_launch()` since 4.20 (*"whether the launcher is likely to succeed"*). Docs: it *"may or may not show an app chooser dialog"*. **[V]**
- `gtk_show_uri()` is **deprecated since 4.10** → *"Use gtk_file_launcher_launch() or gtk_uri_launcher_launch() instead."* **[V]** (Tangram and Wike still use `Gtk.show_uri`; Bazaar, Tuba and Wike's "Open in browser" action use `Gtk.UriLauncher`.) **[V]**
- Implementation (`gtk/gtkurilauncher.c`): `if (gdk_display_should_use_portal (display, PORTAL_OPENURI_INTERFACE, 3)) gtk_openuri_portal_open_uri_async (...)` else `gtk_show_uri_full (...)`. **It passes no `ask` option and no activation token.** **[V]**
- Fallbacks seen in the wild: Tuba catches a `Gtk.UriLauncher` error and retries with `Gio.AppInfo.launch_default_for_uri_async()`. **[V]** Cartridges uses `Gio.AppInfo.launch_default_for_uri()` directly. **[V]** (GLib itself uses the portal when sandboxed and no handler is found — **[U]**, page returned 404.)

### 3.2 What the portal does (xdg-desktop-portal `desktop-portal/open-uri.c`, main branch, interface version 5)

- `OpenURI(parent_window s, uri s, options a{sv}) → handle o`; options `handle_token`, `writable`, `ask` (v3), `activation_token` (v4). `SchemeSupported(scheme)` (v5). `file://` must go through `OpenFile(fd)`. **[V]**
- App selection: `resolve_scheme_and_content_type` → `x-scheme-handler/https`; `find_recommended_choices` collects the host's default handler (`g_app_info_get_default_for_type`) + recommended apps; `should_use_default_app`:
  ```c
  const char *skipped_schemes[] = { "http", "https", "ftp", "mailto", "webcal", "calendar", NULL };
  /* We skip the app chooser for Internet URIs, to be open in the browser, */
  ```
  Chooser is skipped if (1) default handler exists and scheme is in that list, (2) only one candidate, or (3) the stored choice reached its threshold (`DEFAULT_THRESHOLD` = 3). `ask=true` **forces** the chooser; so does a per-content-type `always-ask` flag or threshold `G_MAXINT` ("paranoid mode"). The chooser is the backend `org.freedesktop.impl.portal.AppChooser.ChooseApplication(handle, app_id, parent_window, choices, options{last_choice, modal, content_type, uri, filename, activation_token})`. Launch is `g_app_info_launch_uris()` of `<choice_id>.desktop` on the **host**. Choices are persisted in the permission store table `"desktop-used-apps"` (`shared/xdp-types.h`: `#define OPEN_URI_PERMISSION_TABLE "desktop-used-apps"`). **[V]**
- Observed on this host (`flatpak permissions desktop-used-apps`): entries such as `application/pdf  md.obsidian.Obsidian  app.zen_browser.zen,3,3` and `x-scheme-handler/obsidian  app.zen_browser.zen  obsidian,2,3` — i.e. `<chosen app>,<count>,<threshold>`. **[V]**
- Also observed: this host's default `x-scheme-handler/https` is `org.chromium.Chromium.desktop` (a Flatpak browser) — the portal would open it directly without a dialog. **[V]**

### 3.3 Limits

- You cannot tell the portal *which* browser; you can only (a) accept the host default or (b) force the chooser (`ask`). `Gtk.UriLauncher` cannot even do (b). **[V]**
- A quirk: `launch_application_with_uri` returns TRUE regardless of launch success, so a failed host launch is reported as success and the choice is still recorded. **[V]** (as read from source)
- There is **no frontend `org.freedesktop.portal.AppChooser` interface** for apps; only the backend `impl` interface exists. **[V]**
- Requires portal interface version ≥ 3 for GTK to use it (xdg-desktop-portal from ~2019 onward). **[V]**

---

## 4. Opening a *specific user-chosen* browser from inside Flatpak

### 4.1 What the sandbox can see (measured)

Inside `org.gnome.Platform//49` on this machine:

```
XDG_DATA_DIRS=/app/share:/usr/share:/usr/share/runtime/share:/run/host/user-share:/run/host/share
/run/host/share:       icons
/run/host/user-share:  icons
gio mime x-scheme-handler/https  →  "No default applications for “x-scheme-handler/https”"
```

So `Gio.AppInfo.get_all()` / `get_default_for_uri_scheme()` **cannot enumerate or resolve host browsers**; only the runtime's own `.desktop` files are visible (Flatpak exposes host icons and fonts, not applications). **[V]**

### 4.2 Option matrix

| Option | Mechanism | Flathub status | Security | Verdict |
|---|---|---|---|---|
| **A. Portal default** | `Gtk.UriLauncher` → OpenURI | Always allowed (portals need no finish-args; `finish-args-portal-talk-name` is "never granted" because unnecessary) **[V]** | Sandbox-safe | **Default for "external"** |
| **B. Portal chooser** | `OpenURI` with `ask=true` via `libportal` `xdp_portal_open_uri(..., XDP_OPEN_URI_FLAG_ASK)` or a direct `Gio.DBusProxy` call (libportal is *not* in runtime 49, so either bundle libportal as a module like Epiphany, or call D-Bus directly) **[V]** | Always allowed | Sandbox-safe; user picks per click; the portal records choice count but `ask` forces the dialog every time **[V]** | **Offer as "Ask which app"** |
| **C. `flatpak-spawn --host <cmd> <url>`** (e.g. `flatpak run org.mozilla.firefox <url>` or `xdg-open`) | `org.freedesktop.Flatpak.Development.HostCommand` | Needs `--talk-name=org.freedesktop.Flatpak`; linter `finish-args-flatpak-spawn-access`: *"Granted on sufficient explanation being provided. See inclusion policy"*; 168/1542 apps in `exceptions.json` have it; precedent **`io.github.alyraffauf.Switchyard`: "Required to launch browsers the user has installed on their system."**, also `org.pvermeer.WebAppHub` **[V]** | flatpak's D-Bus XML: *"a sandbox escape allowing arbitrary code execution"*, *"must not be allowed for applications where sandboxing is a security boundary"* **[V]**; Flathub also says sandbox-escape exceptions will be refused if LLM usage is detected in the software or the PR **[V]** | **Do not request in the manifest.** Support it *opportunistically* if the user grants it themselves with `flatpak override --user --talk-name=org.freedesktop.Flatpak io.github.tim_van_oudheusden.Dailies` **[I]** |
| **D. Launch another Flatpak without --host** | none exists: Flathub Discourse (Dec 2023): *"flatpak-spawn --host is currently the only way to launch another Flatpak."* **[V]** | — | — | Not available |
| **E. D-Bus activation of the browser** (`org.freedesktop.Application.Open` on e.g. `org.gnome.Epiphany`) | Requires the browser's `.desktop` to be `DBusActivatable=true` and `--talk-name=<browser id>` | Epiphany's `org.gnome.Epiphany.desktop.in.in` has **no** `DBusActivatable` line; Chromium Flatpak `.desktop` has none either **[V]** | fine | Not viable in general **[I]** |
| **F. Read host `.desktop` files** (`--filesystem=xdg-data/applications:ro`, `--filesystem=/var/lib/flatpak/exports/share/applications:ro`) to *list* browsers, then launch via portal | Listing only; still cannot launch a *specific* one through the portal | `finish-args-arbitrary-xdg-data-mode-access` → "Granted on sufficient explanation" **[V]** | read-only | Pointless without C; skip **[I]** |

### 4.3 Reference implementations of C (for the opt-in path only)

`flatpak-spawn` man page: *"Unlike other flatpak commands, flatpak-spawn is available to applications inside the sandbox"*; `--host`: *"This requires access to the org.freedesktop.Flatpak D-Bus interface."*; useful flags `--watch-bus`, `--env=`, `--directory=`. **[V]** `HostCommand(cwd_path ay, argv aay, fds a{uh}, envs a{ss}, flags u) → pid u`, flags `CLEAR_ENV`=1, `WATCH_BUS`=2. **[V]** Detecting availability at runtime: attempt the D-Bus call and treat `org.freedesktop.DBus.Error.AccessDenied`/`ServiceUnknown` as "not granted" and hide the option. **[I]**

---

## 5. What Obsidian actually does

- **Web viewer** core plugin, introduced in **Obsidian 1.8.0 desktop (2024-12-18)**: *"lets you open external links within Obsidian"*, *"disabled by default, and needs to be enabled manually in settings."* **[V]** (obsidian.md changelog)
- Help page (obsidian.md/help/plugins/web-viewer): based on *"Chromium's webview feature"* (the Electron `<webview>` tag), independently audited; tabs can be split/popped out; **Reader view** (Mozilla Readability); **Save to vault**; **Ad blocking enabled by default** with optional filter lists (EasyList); warning: *"third-party plugins have full access to cookies in Web viewer"*, so *"use your primary browser for sensitive tasks and password-protected websites."* Desktop only. **[V]**
- Setting *"Open external links"* in Web viewer settings; when off, clicks go to the default browser and the "open in web viewer" context-menu item disappears. "Open in default browser" is available via right-click; users have requested a modifier-click to bypass the viewer. **[V]** (Obsidian forum threads 110982, 96429)
- Electron context: the `<webview>` tag is *"not recommended"* by Electron (*"impacts the stability of webviews"*); alternatives `iframe`, `WebContentsView` (BrowserView is being replaced); `partition="persist:<name>"` gives a persistent, shareable storage partition, otherwise in-memory. **[V]**
- Lessons for Dailies **[I]**: (1) in-app viewer *optional and discoverable*; (2) always a one-click "Open in default browser"; (3) a single global switch *plus* per-link override; (4) **don't** copy the default ad blocking (ToS risk, see §7); (5) isolate storage deliberately (Electron partitions ≈ WebKit `NetworkSession`s).

---

## 6. Cross-platform considerations

- **WebKitGTK does not run on Windows.** WebKit maintainers (webkit-dev, 2019): the last WebKitGTK with Windows support was 2.4 (2014); *"WebKit2 does not support Windows… you must use the WinCairo port instead"*. **[V]** The GTK4 API (`webkitgtk-6.0`) is Linux/Unix only; a 2025 GNOME Discourse thread proposing CEF-in-GTK4, a Windows port, or `servo-gtk` got **no replies** before auto-closing. **[V]**
- Packaging reality: MSYS2 ships `mingw-w64-libadwaita 1.10.0-2` **[V]** but **no** `webkitgtk`/`webkit2gtk` package (only `mingw-w64-qtwebkit`) **[V]**; gvsbuild supports GTK 3/4 but lists neither WebKitGTK nor libadwaita in its README. **[V]**
- Industry pattern: Tauri uses **WebView2** (Windows), **WKWebView** (macOS/iOS), **WebKitGTK** (Linux) and bundles none of them. **[V]** There is no GTK widget for WebView2. **[I]**
- **Recommendation [I]:** follow Tuba — `meson_options.txt` feature `in-app-browser` with `webkit_dep = dependency('webkitgtk-6.0', required: get_option('in-app-browser'))` and a `--define=WEBKIT`/`HAVE_WEBKIT` conditional (Tuba `meson.build` lines 101–172 **[V]**). On platforms without WebKit the "Built-in browser" option is hidden and `open-mode` falls back to `external`. In Python, do `gi.require_version('WebKit', '6.0')` inside a `try:` and set a `HAVE_WEBKIT` flag.

---

## 7. Privacy, legal and UX considerations of showing third-party games in-app

### 7.1 Legal (not legal advice)

- **NYT Terms of Service (effective 2026-01-20)** (thenewyorktimeshelpcenter.helpjuice.com) — Wordle, Connections, Strands are NYT Games: §2.1 *"intended for your personal, non-commercial use"*; §2.2 restricted uses include *"display (including framing and inline linking)"*; §2.3 *"Copying or storing of any Content for other than personal use is expressly prohibited"*; §3.2 *"The Services may be used only in a noncommercial manner"*; §4.1 forbids robots/scrapers, caching/archiving, disproportionate load. Games are referenced in §1.1 (*"mobile sites and applications (including Cooking, Games or The Athletic)"*). Wordle/Connections are not named. **[V]**
- A `WebKit.WebView` performing a *top-level* navigation to the game URL is functionally a user-agent (like Tangram or GNOME Web), **not** an `<iframe>`; it does not strip, overlay or combine the page with Dailies content. That is materially different from "framing" **[I]**, but Dailies must stay on the safe side: **no ad blocking, no content scripts, no UA spoofing of another browser, no scraping of game results, real URL always visible, "Open in Browser" always offered.** **[I]**
- Dailies is GPL-3.0 and non-commercial; still, popularity scraping (the GitHub Action pipeline) must respect robots.txt and rate limits (§4.1 (4), (6)). **[I]** Note: many DLEs are indie sites with their own terms; the "add a DLE via GitHub issue" template should ask the submitter to confirm the site has no anti-embedding terms. **[I]**

### 7.2 Privacy

- A persistent shared session means NYT/Google analytics cookies persist in `~/.var/app/<id>/data/...` exactly like in a browser. Expose "Clear website data" (`WebsiteDataManager.clear(ALL, 0)`) and "Clear on exit". **[I]**
- Cookie policy: `NO_THIRD_PARTY` reduces cross-site tracking but **breaks some logins** (NYT uses `myaccount.nytimes.com` redirects) — default to `ALWAYS` like Wike/Komikku, offer `NO_THIRD_PARTY` as a toggle. **[I]** ITP: leave WebKit's default; add a toggle. **[I]**
- Per-game isolation (one `NetworkSession` per game) vs. shared: shared is the better default because sibling games share a login (all NYT games, all Britannica games…), and because a WebView's `network-session` is construct-only, so isolation is a per-view decision made when the page opens. **[I]** Tangram proves the per-instance model works (`data_dir = <data>/Tangram/<id>`, `cache_dir = <cache>/Tangram/<id>`). **[V]**
- Downloads: never write files silently; route to the external browser (Tuba/Tangram pattern). **[I]**
- Notifications/permissions: `permission-request` → `deny()` by default (Tangram allows only notifications). **[V]**

### 7.3 UX

- GNOME HIG "Browsing" pattern: back button top-left (*"an important part of recognition"*), header bar updates with the view; standard shortcuts Back `Alt+←`, Forward `Alt+→`, Reload `Ctrl+R`, Enter Location `Ctrl+L`, Home `Alt+Home`. **[V]**
- Tuba's in-app browser is a good libadwaita template: `Adw.Dialog` (1200×1200) → `Adw.ToolbarView` with an `Adw.HeaderBar` whose title widget is `Adw.WindowTitle(title, uri)`, a padlock icon bound to TLS state, a primary `Gtk.MenuButton` whose menu has a `display-hint="horizontal-buttons"` section (Back/Refresh/Stop/Forward with `verb-icon`s) and a section "Open in Browser" / "Copy URL"; accent-coloured progress bar drawn in `snapshot()`; mouse buttons 8/9 bound to back/forward via `Gtk.GestureClick`. **[V]**
- For Dailies I recommend an `Adw.NavigationPage` pushed onto the main `Adw.NavigationView` (full-window game, back arrow returns to the launcher) rather than a dialog, with the same header-bar contents; plus a `Gtk.Shortcut` for `Ctrl+Shift+O` "Open in Browser". **[I]**

---

## 8. Reference-app code worth copying (verbatim excerpts)

### 8.1 Tangram `src/WebView.js` (GJS, GPL) — session + downloads + popups

```js
const network_session = WebKit2.NetworkSession.new(data_dir, cache_dir);
network_session.set_tls_errors_policy(TLSErrorsPolicy.FAIL);
network_session.connect("download-started", (self, download) => {
  download.set_allow_overwrite(false);
  const uri = download.get_request().get_uri();
  if (uri.startsWith("http")) {
    download.cancel();
    AppInfo.launch_default_for_uri(uri, null);
    return;
  }
  ...
});
const website_data_manager = network_session.get_website_data_manager();
website_data_manager.set_favicons_enabled(true);
const cookieManager = network_session.get_cookie_manager();
cookieManager.set_accept_policy(CookieAcceptPolicy.NO_THIRD_PARTY);
cookieManager.set_persistent_storage(
  build_filenamev([data_dir, "cookies.sqlite"]),
  CookiePersistentStorage.SQLITE,
);
const settings = new Settings({
  enable_smooth_scrolling: true,
  media_playback_requires_user_gesture: true,
  enable_back_forward_navigation_gestures: true,
  enable_developer_extras: true,
  javascript_can_open_windows_automatically: true,
  allow_top_navigation_to_data_urls: false,
});
settings.set_user_agent_with_application_details("Tangram", pkg.version);
const webView = new WebView({ web_context, user_content_manager, settings, network_session });
connect(webView, {
  create(navigation_action) {
    const request_url = navigation_action.get_request().get_uri();
    if (webView.mode === MODES.TEMPORARY) { webView.load_uri(request_url); return; }
    Gtk.show_uri(window, request_url, Gdk.CURRENT_TIME);   // external browser
  },
  ["permission-request"](request) {
    if (request instanceof NotificationPermissionRequest) { request.allow(); return; }
    request.deny();
  },
  ["decide-policy"](decision, decision_type) {
    if (decision_type === PolicyDecisionType.NAVIGATION_ACTION) {
      const navigation_action = decision.get_navigation_action();
      const request_url = navigation_action.get_request().get_uri();
      if (didUserRequestOpenInBrowser(navigation_action)) {   // middle click or Ctrl
        decision.ignore();
        Gtk.show_uri(window, request_url, Gdk.CURRENT_TIME);
        return true;
      }
    }
    return false;
  },
});
```

### 8.2 Komikku `komikku/webview.py` (Python, GPL) — session with own dirs

```python
self.web_context = WebKit.WebContext(time_zone_override=tzlocal.get_localzone_name())
self.web_context.set_cache_model(WebKit.CacheModel.DOCUMENT_VIEWER)
self.network_session = WebKit.NetworkSession.new(
    os.path.join(get_webview_data_dir(), 'data'),
    os.path.join(get_webview_data_dir(), 'cache')
)
self.network_session.get_website_data_manager().set_favicons_enabled(True)
self.network_session.set_itp_enabled(False)
self.network_session.get_cookie_manager().set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)
self.network_session.get_cookie_manager().set_persistent_storage(
    os.path.join(get_webview_data_dir(), 'cookies.sqlite'),
    WebKit.CookiePersistentStorage.SQLITE
)
self.webkit_webview = WebKit.WebView(
    web_context=self.web_context, network_session=self.network_session, settings=self.settings
)
```

### 8.3 Tuba `data/dev.geopjr.Tuba.gschema.xml` — the preference key

```xml
<key name="use-in-app-browser-if-available" type="b">
  <default>true</default>
  <summary>Open Links In-App</summary>
  <description>Open links in a nested web browser instead of the host one</description>
</key>
```

and `src/Utils/Host.vala`:

```vala
private async static bool open_in_default_app (string uri) {
    try {
        yield (new Gtk.UriLauncher (uri)).launch (app.active_window, null);
    } catch (Error e) {
        warning (@"Error opening uri \"$uri\": $(e.message)");
        return yield open_in_default_app_using_dbus (uri);   // AppInfo.launch_default_for_uri_async
    }
    return true;
}
```

### 8.4 Tangram `re.sonny.Tangram.json` (full manifest, for finish-args reference)

```json
{
  "id": "re.sonny.Tangram",
  "runtime": "org.gnome.Platform",
  "runtime-version": "51",
  "sdk": "org.gnome.Sdk",
  "command": "re.sonny.Tangram",
  "finish-args": [
    "--device=dri",
    "--share=ipc",
    "--share=network",
    "--socket=fallback-x11",
    "--socket=pulseaudio",
    "--socket=wayland",
    "--system-talk-name=org.freedesktop.GeoClue2",
    "--require-version=1.1.2"
  ],
  "cleanup": ["/include", "/lib/pkgconfig", "/man", "/share/doc", "/share/gtk-doc", "/share/man",
              "/share/pkgconfig", "/share/installed-tests", "*.la", "*.a"],
  "modules": [
    { "name": "Tangram", "buildsystem": "meson", "sources": [ { "type": "dir", "path": "." } ] }
  ]
}
```

---

## 9. Recommendations for Dailies

### 9.1 Resolution order (what happens when the user clicks a game)

```
effective_mode = game.override_mode  if set
               else settings.open-mode

switch effective_mode:
  'in-app'     : if HAVE_WEBKIT → push GamePage(WebView, session = shared|per-game)
                 else            → fall through to 'external'
  'custom'     : if host-command access is granted (probe org.freedesktop.Flatpak once)
                   → flatpak-spawn --host <external-browser-command> <url>
                 else → fall through to 'external' (and show a one-time toast explaining why)
  'ask'        : OpenURI portal with ask=true (D-Bus call) → portal chooser
  'external'   : Gtk.UriLauncher(url).launch(window)  → portal → host default browser
                 on error → Gio.AppInfo.launch_default_for_uri_async(url)
```

This is the owner's "configured browser → built-in → external" order, mapped onto what the sandbox can actually do: a *configured* browser exists only when the user has deliberately opted into the escape hatch; otherwise "built-in" is first and "external/ask" are explicit choices. **[I]**

### 9.2 GSettings schema (proposed; schema id follows the app id — final id to be decided by the repo-scaffolding research)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<schemalist gettext-domain="dailies">
  <enum id="io.github.tim_van_oudheusden.Dailies.OpenMode">
    <value nick="in-app"   value="0"/>   <!-- built-in WebKitGTK view -->
    <value nick="external" value="1"/>   <!-- system default browser via OpenURI portal -->
    <value nick="ask"      value="2"/>   <!-- portal app chooser (OpenURI ask=true) -->
    <value nick="custom"   value="3"/>   <!-- external-browser-command via flatpak-spawn --host (opt-in) -->
  </enum>
  <enum id="io.github.tim_van_oudheusden.Dailies.SessionIsolation">
    <value nick="shared"   value="0"/>
    <value nick="per-game" value="1"/>
  </enum>
  <enum id="io.github.tim_van_oudheusden.Dailies.CookiePolicy">
    <value nick="always"         value="0"/>
    <value nick="no-third-party" value="2"/>
  </enum>

  <schema id="io.github.tim_van_oudheusden.Dailies" path="/io/github/tim_van_oudheusden/Dailies/">
    <key name="open-mode" enum="io.github.tim_van_oudheusden.Dailies.OpenMode">
      <default>'in-app'</default>
      <summary>How game links are opened</summary>
      <description>in-app: built-in browser; external: system default browser; ask: choose an app each time; custom: run external-browser-command on the host (requires org.freedesktop.Flatpak access granted by the user).</description>
    </key>
    <key name="external-browser-command" type="s">
      <default>''</default>
      <summary>Command used for the 'custom' open mode</summary>
      <description>Executed on the host through flatpak-spawn --host with the URL appended, e.g. 'flatpak run org.mozilla.firefox' or 'xdg-open'. Ignored unless the sandbox has been granted --talk-name=org.freedesktop.Flatpak.</description>
    </key>
    <key name="session-isolation" enum="io.github.tim_van_oudheusden.Dailies.SessionIsolation">
      <default>'shared'</default>
      <summary>Website data isolation for the built-in browser</summary>
      <description>shared: one persistent session for all games (logins shared, e.g. all NYT games); per-game: a separate cookie/storage directory per game.</description>
    </key>
    <key name="cookie-policy" enum="io.github.tim_van_oudheusden.Dailies.CookiePolicy">
      <default>'always'</default>
      <summary>Cookie acceptance policy</summary>
    </key>
    <key name="itp-enabled" type="b">
      <default>true</default>
      <summary>Intelligent Tracking Prevention</summary>
    </key>
    <key name="hardware-acceleration" type="b">
      <default>true</default>
      <summary>GPU rendering in the built-in browser</summary>
      <description>Maps to WebKitSettings:hardware-acceleration-policy ALWAYS/NEVER. Turn off on broken drivers.</description>
    </key>
    <key name="user-agent" type="s">
      <default>''</default>
      <summary>Custom user agent</summary>
      <description>Empty uses WebKit's default with 'Dailies/&lt;version&gt;' appended via set_user_agent_with_application_details().</description>
    </key>
    <key name="clear-web-data-on-exit" type="b">
      <default>false</default>
      <summary>Clear website data when the app quits</summary>
    </key>
    <key name="developer-extras" type="b">
      <default>false</default>
      <summary>Enable the Web Inspector</summary>
    </key>
  </schema>

  <!-- relocatable, one per game, path /io/github/tim_van_oudheusden/Dailies/games/<slug>/ -->
  <schema id="io.github.tim_van_oudheusden.Dailies.Game">
    <key name="open-mode-override" type="s">
      <default>''</default>
      <summary>Per-game override of open-mode ('' = use global)</summary>
    </key>
    <key name="isolated-session" type="b">
      <default>false</default>
      <summary>Force a private per-game session for this game</summary>
    </key>
  </schema>
</schemalist>
```

(Pattern for the relocatable per-game schema follows Tangram's `re.sonny.Tangram.Instance` with `path=/re/sonny/Tangram/instances/<id>/`. **[V]**) Favourites/state belong to the data-model research, not here.

### 9.3 Flatpak manifest `finish-args` (Flathub-clean)

```yaml
finish-args:
  - --share=network
  - --share=ipc
  - --socket=wayland
  - --socket=fallback-x11
  - --device=dri
  - --socket=pulseaudio        # only if games with audio should work in-app
# NOT: --talk-name=org.freedesktop.Flatpak  (users may add it with `flatpak override`)
# NOT: --filesystem=xdg-download             (downloads are delegated to the external browser)
```

### 9.4 Python sketch of the in-app page (PyGObject, WebKit 6.0)

```python
import gi
gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")
try:
    gi.require_version("WebKit", "6.0")
    from gi.repository import WebKit
    HAVE_WEBKIT = True
except (ValueError, ImportError):
    HAVE_WEBKIT = False
from gi.repository import Gtk, Adw, Gio, GLib

class WebSessions:
    """One persistent NetworkSession per isolation key ('shared' or game slug)."""
    _cache = {}
    @classmethod
    def get(cls, key: str, settings: Gio.Settings) -> "WebKit.NetworkSession":
        if key in cls._cache:
            return cls._cache[key]
        data = GLib.build_filenamev([GLib.get_user_data_dir(), "web", key])
        cache = GLib.build_filenamev([GLib.get_user_cache_dir(), "web", key])
        for d in (data, cache):
            GLib.mkdir_with_parents(d, 0o700)
        s = WebKit.NetworkSession.new(data, cache)
        s.set_tls_errors_policy(WebKit.TLSErrorsPolicy.FAIL)
        s.set_itp_enabled(settings.get_boolean("itp-enabled"))
        cm = s.get_cookie_manager()
        cm.set_accept_policy(WebKit.CookieAcceptPolicy(settings.get_enum("cookie-policy")))
        cm.set_persistent_storage(GLib.build_filenamev([data, "cookies.sqlite"]),
                                  WebKit.CookiePersistentStorage.SQLITE)   # REQUIRED for streaks
        s.get_website_data_manager().set_favicons_enabled(True)
        s.connect("download-started", cls._on_download)
        cls._cache[key] = s
        return s

    @staticmethod
    def _on_download(session, download):
        download.cancel()                     # never write files silently
        open_external(download.get_request().get_uri())

class GamePage(Adw.NavigationPage):
    def __init__(self, game, settings, window):
        super().__init__(title=game.name)
        key = game.slug if game.isolated or settings.get_enum("session-isolation") == 1 else "shared"
        ws = WebKit.Settings(
            enable_developer_extras=settings.get_boolean("developer-extras"),
            enable_back_forward_navigation_gestures=True,
            enable_smooth_scrolling=True,
            javascript_can_open_windows_automatically=False,
            allow_top_navigation_to_data_urls=False,
            enable_webrtc=False,
            hardware_acceleration_policy=(WebKit.HardwareAccelerationPolicy.ALWAYS
                if settings.get_boolean("hardware-acceleration") else WebKit.HardwareAccelerationPolicy.NEVER),
        )
        ua = settings.get_string("user-agent")
        if ua: ws.set_user_agent(ua)
        else:  ws.set_user_agent_with_application_details("Dailies", VERSION)
        self.view = WebKit.WebView(network_session=WebSessions.get(key, settings), settings=ws)
        self.view.connect("create", lambda v, nav: (open_external(nav.get_request().get_uri()), None)[1])
        self.view.connect("decide-policy", self._on_policy)
        self.view.connect("permission-request", lambda v, req: (req.deny(), True)[1])
        self.view.load_uri(game.url)
        # header bar: Back / Forward / Reload|Stop, Adw.WindowTitle(title, host), menu: Open in Browser, Copy URL
        ...

    def _on_policy(self, view, decision, dtype):
        if dtype == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
            view.load_uri(decision.get_navigation_action().get_request().get_uri()); decision.ignore(); return True
        if dtype == WebKit.PolicyDecisionType.RESPONSE and not decision.is_mime_type_supported():
            open_external(decision.get_request().get_uri()); decision.ignore(); return True
        return False

def open_external(uri, window=None, ask=False):
    if ask:   # portal chooser; Gtk.UriLauncher cannot do this
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call(
            "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.OpenURI", "OpenURI",
            GLib.Variant("(ssa{sv})", ("", uri, {"ask": GLib.Variant("b", True)})),
            GLib.VariantType("(o)"), Gio.DBusCallFlags.NONE, -1, None, None)
        return
    def done(launcher, res):
        try: launcher.launch_finish(res)
        except GLib.Error:
            Gio.AppInfo.launch_default_for_uri_async(uri, None, None, None)
    Gtk.UriLauncher.new(uri).launch(window, None, done)
```

(Parent-window identifier for the D-Bus `ask` path should be filled with the `wayland:`/`x11:` handle; libadwaita/GTK do this internally for `Gtk.UriLauncher`.) **[I]**

### 9.5 Behavioural rules for the in-app browser

1. Default `open-mode = in-app`; first launch shows an inline banner "Games open inside Dailies. You can change this in Preferences." **[I]**
2. Header bar: Back/Forward (disabled states bound to `can_go_back/forward` on `load-changed`), Reload/Stop (bound to `is-loading`), `Adw.WindowTitle` with page title and host, padlock from TLS state, menu: **Open in Browser** (`Ctrl+Shift+O`), **Copy URL**, **Clear data for this game**. Progress indicator bound to `estimated-load-progress`. Mouse buttons 8/9 and `Alt+←/→` for history. **[I]** (Tuba pattern **[V]**)
3. Popups/new windows: load in the same view, except when the target host differs from the game host → external browser. **[I]**
4. Downloads: cancel and open externally. **[V pattern]**
5. Unsupported MIME types: open externally. **[V pattern]**
6. Never inject CSS/JS into game pages (ToS/attribution risk); the only allowed `UserContentManager` use is a dark-background `set_background_color` while loading. **[I]**
7. Destroy the WebView when the page is popped (`try_close()` then unparent) to free the web process. **[I]**
8. Show "Opened in your browser" toast with an "Undo → open here" action when a game is opened externally. **[I]**
9. Settings UI (Adw.PreferencesDialog → "Links" page): `AdwComboRow` for open-mode (hide "Built-in" when `HAVE_WEBKIT` is false; hide "Custom command" unless host access detected), expander row with isolation/cookie/ITP/GPU/UA, button row "Clear website data…" (uses `WebsiteDataManager.clear(ALL)`). **[I]**

---

## 10. Open questions

1. **Memory footprint numbers** for WebKitGTK 2.54 inside Flatpak are unmeasured; a quick benchmark (`/usr/libexec/webkitgtk-6.0/MiniBrowser` in `org.gnome.Platform//49` loading a NYT game, then `smem`/`ps` on `WebKitWebProcess` + `WebKitNetworkProcess`) should be done once the owner is at the keyboard. **[U]**
2. **Default `hardware-acceleration-policy` and `itp-enabled` values** are not stated in the 6.0 docs pages read; confirm by `WebKit.Settings().get_hardware_acceleration_policy()` / `NetworkSession.get_itp_enabled()` at runtime. **[U]**
3. **Whether NYT and other publishers consider an embedded top-level WebView acceptable** under their ToS is a legal judgement; consider adding a "This game is provided by <publisher>; opening it here is equivalent to using a web browser" note in the About/README, and keep "Open in Browser" prominent. **[U]**
4. **App ID** (`io.github.tim_van_oudheusden.Dailies` assumed here; Flathub requires control of the domain/namespace — GitHub-based IDs use `io.github.<user>.<App>`) — align with the repository-scaffolding research. **[I]**
5. **Should `ask` mode be exposed at all?** It is sandbox-clean but the GTK portal dialog only lists host apps that register `x-scheme-handler/https`; for users with one browser it degenerates to "external". **[I]**
6. **libportal bundling** vs direct D-Bus call for `ask=true`: libportal is not in the GNOME 49 runtime (Epiphany builds it); a 30-line D-Bus call is simpler for a Python/GJS app. **[V/I]**
7. **GLib portal fallback in `Gio.AppInfo.launch_default_for_uri_async`** inside the sandbox could not be re-verified (docs page 404 this session); Tuba's fallback suggests it works. **[U]**

---

## 11. Sources

Primary sources fetched/inspected on 2026-10-15 (URL — what it was used for):

**Runtime / build**
- Local inspection: `flatpak run --user --command=sh org.gnome.Platform//{49,50,51}` (lib, typelib, libexec listings, `/etc/os-release`, `XDG_DATA_DIRS`, `gio mime`), `flatpak info --user org.gnome.Platform//49`, `flatpak permissions desktop-used-apps`, `gio mime x-scheme-handler/https` on host.
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-49/elements/sdk/webkitgtk.inc (via GitLab API `…/repository/files/elements%2Fsdk%2Fwebkitgtk.inc/raw?ref=gnome-49`) — WebKitGTK 2.54.1 in GNOME 49.
- https://gitlab.gnome.org/GNOME/gnome-build-meta/-/raw/gnome-49/elements/sdk/webkitgtk-6.0.bst — cmake flags.
- https://webkitgtk.org/ — latest stable 2.54.1 (2026-10-02).
- https://docs.flatpak.org/en/latest/available-runtimes.html — GNOME runtime support period.
- https://docs.flatpak.org/en/latest/sandbox-permissions.html — `--device=dri`, D-Bus/session-bus warnings, filesystem keys.

**WebKitGTK 6.0 API**
- https://webkitgtk.org/reference/webkitgtk/stable/class.NetworkSession.html
- https://webkitgtk.org/reference/webkitgtk/stable/ctor.NetworkSession.new.html
- https://webkitgtk.org/reference/webkitgtk/stable/method.NetworkSession.set_itp_enabled.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.WebsiteDataManager.html
- https://webkitgtk.org/reference/webkitgtk/stable/flags.WebsiteDataTypes.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.CookieManager.html
- https://webkitgtk.org/reference/webkitgtk/stable/enum.CookieAcceptPolicy.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.WebView.html
- https://webkitgtk.org/reference/webkitgtk/stable/signal.WebView.create.html
- https://webkitgtk.org/reference/webkitgtk/stable/property.WebView.related-view.html
- https://webkitgtk.org/reference/webkitgtk/stable/method.WebView.get_page_icons.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.Settings.html
- https://webkitgtk.org/reference/webkitgtk/stable/method.Settings.set_user_agent_with_application_details.html
- https://webkitgtk.org/reference/webkitgtk/stable/enum.HardwareAccelerationPolicy.html
- https://webkitgtk.org/reference/webkitgtk/stable/enum.PolicyDecisionType.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.Download.html
- https://webkitgtk.org/reference/webkitgtk/stable/class.WebContext.html
- https://webkitgtk.org/2024/10/04/webkitgtk-2.46.html — Skia, settings added in 2.46.
- https://blogs.igalia.com/carlosgc/?p=1029 — 2.46 graphics architecture (2024-09-27).
- https://trac.webkit.org/wiki/EnvironmentVariables — env vars (archived, marked possibly outdated).
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/API/glib/WebKitCookieManager.cpp — "doesn't store the cookies persistently" doc comment.
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/API/glib/WebKitWebsiteDataManager.cpp — sub-directory layout.
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/WebsiteData/glib/WebsiteDataStoreGLib.cpp — default base dirs.
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/API/glib/WebKitNetworkSession.cpp — ITP vs cookie policy note.
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/gtk/AcceleratedBackingStore.cpp — `WEBKIT_DISABLE_DMABUF_RENDERER`.
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebKit/UIProcess/Launcher/glib/ProcessLauncherGLib.cpp — `flatpak-spawn --sandbox` inside Flatpak.
- https://raw.githubusercontent.com/WebKit/WebKit/main/Source/WebCore/platform/glib/UserAgentGLib.cpp — default UA.
- https://bugs.webkit.org/show_bug.cgi?id=306993 (via search) — crash with the two env vars (Feb 2026).

**Reference apps**
- https://github.com/sonnyp/Tangram (cloned; `re.sonny.Tangram.json`, `src/WebView.js`, `src/instances.js`, `src/env.js`, `data/re.sonny.Tangram.gschema.xml`, README).
- https://github.com/hugolabe/Wike (cloned; `src/view.py`, `src/window.py`, `src/application.py`).
- https://codeberg.org/valos/Komikku (cloned; `komikku/webview.py`).
- https://github.com/GeopJr/Tuba (cloned; `meson.build`, `src/Views/Browser.vala`, `src/Utils/Host.vala`, `data/dev.geopjr.Tuba.gschema.xml`, `src/Widgets/RichLabel.vala`).
- https://github.com/kra-mo/cartridges (cloned; `cartridges/main.py`).
- https://gitlab.gnome.org/World/bazaar (cloned; `src/bz-window.c`, `src/bz-inspector.c`, …).
- https://gitlab.gnome.org/GNOME/epiphany/-/raw/main/org.gnome.Epiphany.json and `data/org.gnome.Epiphany.desktop.in.in`.
- Flathub manifests via `gh api repos/flathub/<id>/contents/<file>`: `com.github.hugolabe.Wike.json`, `io.gitlab.news_flash.NewsFlash.json`, `dev.geopjr.Tuba.yaml`, `info.febvre.Komikku.json`, `dev.alextren.Spot.json`, `org.gnome.Decibels.json`, `io.github.flattool.Warehouse.json`, `org.gnome.Builder.json`.

**Portals / GTK / GLib**
- https://docs.gtk.org/gtk4/class.UriLauncher.html
- https://docs.gtk.org/gtk4/func.show_uri.html — deprecated since 4.10.
- https://gitlab.gnome.org/GNOME/gtk/-/raw/main/gtk/gtkurilauncher.c — portal decision, no `ask`.
- https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.OpenURI.html
- https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.impl.portal.AppChooser.html
- https://raw.githubusercontent.com/flatpak/xdg-desktop-portal/main/desktop-portal/open-uri.c — skipped schemes, threshold, chooser.
- https://github.com/flatpak/xdg-desktop-portal/blob/main/shared/xdp-types.h (via `gh search code`) — `OPEN_URI_PERMISSION_TABLE "desktop-used-apps"`.
- https://libportal.org/method.Portal.open_uri.html and https://libportal.org/flags.OpenUriFlags.html — `XDP_OPEN_URI_FLAG_ASK`.
- https://developer.gnome.org/hig/patterns/nav/browsing.html and https://developer.gnome.org/hig/reference/keyboard.html — HIG browsing + shortcuts.

**Flatpak host access / Flathub policy**
- https://raw.githubusercontent.com/flatpak/flatpak/main/doc/flatpak-spawn.xml — `--host` requires `org.freedesktop.Flatpak`.
- https://raw.githubusercontent.com/flatpak/flatpak/main/data/org.freedesktop.Flatpak.xml — `Development.HostCommand`, "sandbox escape" wording.
- https://docs.flathub.org/docs/for-app-authors/requirements — minimal permissions / portals mandatory.
- https://docs.flathub.org/docs/for-app-authors/linter — `finish-args-flatpak-spawn-access`, `finish-args-portal-talk-name`, exceptions process, LLM clause.
- https://raw.githubusercontent.com/flathub/flatpak-builder-lint/master/flatpak_builder_lint/staticfiles/exceptions.json — 168/1542 apps with spawn exception; Switchyard precedent.
- https://discourse.flathub.org/t/launching-flatpak-inside-flatpak/5708 — "flatpak-spawn --host is currently the only way to launch another Flatpak" (2023-12).
- https://github.com/tinywrkb/org.qutebrowser.qutebrowser/wiki (via search) — security characterisation of the permission.

**Obsidian / Electron**
- https://obsidian.md/changelog/2024-12-18-desktop-v1.8.0/ — Web viewer introduction.
- https://obsidian.md/help/plugins/web-viewer — features, Chromium webview, ad blocking, cookie warning.
- https://forum.obsidian.md/t/web-viewer-add-option-to-open-in-webviewer-in-context-menu-even-when-browser-is-the-default/110982 and https://forum.obsidian.md/t/some-mouse-shortcut-for-open-link-in-default-browser-bypass-web-viewer/96429 — "Open external links" setting and "open in default browser" UX.
- https://www.electronjs.org/docs/latest/api/webview-tag — not recommended, `partition`.

**Cross-platform**
- https://lists.webkit.org/pipermail/webkit-dev/2019-June/030700.html and …/2017-August/029352.html (via search) — WebKitGTK Windows support ended with 2.4; WebKit2 not on Windows.
- https://discourse.gnome.org/t/webview-for-gtk4-multi-os-lin-win-mac-cef-webkit-or-now-servo-gtk/32690 — 2025 thread, no replies.
- https://packages.msys2.org/base/mingw-w64-libadwaita — libadwaita 1.10.0-2 on Windows.
- https://packages.msys2.org/search?q=webkit — no webkitgtk package.
- https://raw.githubusercontent.com/wingtk/gvsbuild/main/README.md — GTK4 yes, no WebKitGTK/libadwaita listed.
- https://v2.tauri.app/reference/webview-versions/ — WebView2/WKWebView/WebKitGTK per platform.
- https://v2.tauri.app/develop/debug/linux-graphics/ (via search) — env-var workarounds.

**Legal**
- https://thenewyorktimeshelpcenter.helpjuice.com/115014893428-Terms-of-Service — NYT ToS effective 2026-01-20 (§2.1, §2.2, §2.3, §3.2, §4.1).
