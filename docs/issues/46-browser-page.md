---
key: 46
title: feat(browser): built-in WebKitGTK browser page with persistent session
type: Feature
labels: milestone::M1, type::feature, priority::high, app
parent: 3
blocked_by: 41, 45
---
> **Risk tier:** medium (code), high in review (privacy/ToS) · **Size:** L

## Why

The built-in browser is what sets Dailies apart from a bookmark folder (brief: "like Obsidian's web viewer"). WebKitGTK 6.0 is already in `org.gnome.Platform//51` (2.54.1, `WebKit-6.0.typelib`), so no module has to be built.

## Page (`data/ui/browser-page.blp`, `dailies/ui/browser_page.py`)

An `Adw.NavigationPage` (not a dialog) pushed onto the window's `Adw.NavigationView` (#41), containing an `Adw.ToolbarView`:

- **Header `[start]`:** Back and Forward (sensitivity follows `can-go-back` / `can-go-forward`, refreshed on `load-changed`), Reload/Stop (swapped on `is-loading`)
- **`[title]`:** `Adw.WindowTitle { title: bind web_view.title; subtitle: <host> }`. The real URL host is always visible
- **`[end]`:** a `Gtk.MenuButton` with **Open in Browser** (Ctrl+Shift+O), **Copy Link**, *separator*, **Clear Data for This Site**
- **Progress:** a 2 px `Gtk.ProgressBar` with the `osd` style overlaid at the top, bound to `estimated-load-progress` and hidden when loading finishes (Tuba pattern)
- **Keys:** Alt+Left/Right and mouse buttons 8/9 for history; Ctrl+R reloads; Ctrl+L focuses or copies the URL (show the full URL in a popover entry)

## Session (copy exactly; the cookie line is the one everybody forgets)

```python
session = WebKit.NetworkSession.new(data_dir, cache_dir)  # $XDG_DATA_HOME/dailies/web/shared, $XDG_CACHE_HOME/dailies/web/shared
session.get_cookie_manager().set_persistent_storage(
    f"{data_dir}/cookies.sqlite", WebKit.CookiePersistentStorage.SQLITE)        # REQUIRED for streaks
session.get_cookie_manager().set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)  # NYT login redirects need it
session.set_tls_errors_policy(WebKit.TLSErrorsPolicy.FAIL)
session.connect("download-started", lambda s, d: (d.cancel(), open_external(d.get_request().get_uri())))
settings = WebKit.Settings(javascript_can_open_windows_automatically=False,
                           allow_top_navigation_to_data_urls=False, enable_webrtc=False,
                           enable_back_forward_navigation_gestures=True, enable_smooth_scrolling=True)
settings.set_user_agent_with_application_details("Dailies", VERSION)
```

- **One shared session for all games** (sibling NYT games share a login). Per-game isolation is #74
- Create the session once per app run and reuse it

## Behavioural rules

| Event | Action |
|---|---|
| `create` (popup / `window.open`) | Open the URL externally; return `None` |
| `decide-policy` `NEW_WINDOW_ACTION` | Load in the same view |
| `decide-policy` `RESPONSE` with an unsupported MIME type | Open externally; ignore |
| `download-started` | Cancel and open externally (no `--filesystem=xdg-download`) |
| `permission-request` | `deny()` |
| Page popped | `web_view.try_close()` and drop the reference; **only one live WebView at a time** |
| TLS error | Fail (policy above) |

Also set the cache model to `WebKit.CacheModel.DOCUMENT_VIEWER` to keep memory down (proposal §17 risk 4).

## Never (ToS and attribution; see proposal §14)

No `UserContentManager` scripts or styles, no ad blocking, no user-agent spoofing, no iframes. The only allowed customisation is setting the background colour while a page loads. "Open in Browser" is always one click away.

## Clear data

- `clear_site_data(host)`: `WebsiteDataManager.fetch` → filter by host → `remove` (used by the menu item)
- `clear_all()`: `WebsiteDataManager.clear(WebKit.WebsiteDataTypes.ALL, 0)` (used by Preferences, #47)
- When `clear-web-data-on-exit` is true, call `clear_all()` on `shutdown`

## Acceptance criteria

- [ ] Play NYT Wordle in-app, quit, and relaunch: the game state and streak persist
- [ ] Log into NYT once: Connections in the same session is logged in too
- [ ] A link with `target=_blank` loads in the same view; a `window.open` popup goes to the external browser
- [ ] A download link opens in the external browser and nothing is written inside the sandbox
- [ ] Back from the browser page frees the web process (`ps` shows no `WebKitWebProcess` within a few seconds)
- [ ] The header always shows the page's real host
- [ ] Memory is measured in #52

## References

- [`mvp-first.md` §5.2, §14 (Built-in browser), §17 risks 2 and 4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`embedded-browser.md` §1, §2, §7, §8 (Tangram/Komikku excerpts), §9.4, §9.5](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)
- [`libadwaita-ui-patterns.md` §15, Appendix A.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/libadwaita-ui-patterns.md)
