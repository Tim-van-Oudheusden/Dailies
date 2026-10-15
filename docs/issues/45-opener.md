---
key: 45
title: feat(open): link opener — built-in vs default browser resolution
type: Feature
labels: milestone::M1, type::feature, priority::high, app
parent: 3
blocked_by: 9, 38, 41
---
> **Risk tier:** medium · **Size:** S · **Brief:** "Clicking a link should open a browser in the application. Preference order: configured browser → built-in browser → external browser. Must be configurable."

## Why this shape

Inside a Flatpak, a *specific* host browser cannot be reached without `--talk-name=org.freedesktop.Flatpak`. Flatpak's own docs call that "a sandbox escape allowing arbitrary code execution", and Flathub grants it only "on sufficient explanation". The research measured `gio mime x-scheme-handler/https` inside the runtime: it returns "No default applications". So the MVP maps the brief onto what the sandbox allows **without** that permission. The "configured browser" tier arrives in M2 as an opt-in that only works once the user grants the permission themselves (#63).

## `dailies/ui/opener.py`

```text
mode = settings.open-mode
if mode == custom and host_access_granted and command != "":      # implemented in #63
    run custom command
elif mode in (in-app, custom) and HAVE_WEBKIT:
    push BrowserPage(url)                                          # #46
else:
    Gtk.UriLauncher(uri=url).launch(window, None, cb)             # OpenURI portal → host default browser
    on error: Gio.AppInfo.launch_default_for_uri_async(url, None, None, cb)
```

- [ ] `HAVE_WEBKIT`: import WebKit lazily (`gi.require_version("WebKit", "6.0")` inside `try/except (ValueError, ImportError)`) the **first time** it is needed, not at startup (keeps cold start low, #52). The Meson `webkitgtk-6.0` lookup is `required: false`
- [ ] `open_external(url)` is public: the browser page's "Open in Browser" (#46), the empty-state "Suggest a game" link (#42) and download hand-offs all use it
- [ ] Default mode comes from #9 (proposed `in-app`). If that holds, show a **first-run `Adw.Banner`** on the library page: "Games open inside Dailies. You can change this in Preferences." with the button "Preferences". Record its dismissal in `State` (add the key `first-run-banner-dismissed` (`b`) to the schema from #38)
- [ ] The portal's "ask which app" mode (`OpenURI ask=true` through a direct D-Bus call) is **not** in the MVP; for single-browser users it behaves like external

## Acceptance criteria

- [ ] `open-mode = in-app` with WebKit present: the game opens in the built-in page
- [ ] `open-mode = external`: the host default browser opens through the portal (check `flatpak run` on GNOME and on one other desktop)
- [ ] Simulated `HAVE_WEBKIT = False`: in-app mode falls back to external, with no crash and no error toast
- [ ] Startup does not import WebKit (`python3 -X importtime` shows no `gi.repository.WebKit` before the first open)

## References

- [`mvp-first.md` §5, §5.1, §15](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`embedded-browser.md` §3, §4, §9.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)
- [`stack-crossplatform.md` §3.2](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/stack-crossplatform.md)
