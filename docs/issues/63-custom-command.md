---
key: 63
title: feat(open): opt-in custom-command open mode with host-access probe
type: Feature
labels: milestone::M2, type::feature, priority::medium, app
parent: 4
blocked_by: 45, 47
---
> **Risk tier:** medium (high in review: sandbox boundary) · **Size:** S · **Brief:** "configured browser" is the first preference

## Why

This is the brief's first preference, a *specific* user-configured browser, implemented **without** requesting `--talk-name=org.freedesktop.Flatpak` in the manifest. That permission is "a sandbox escape allowing arbitrary code execution" (Flatpak docs), and Flathub grants it only "on sufficient explanation". The option stays invisible until the user grants host access themselves:

```sh
flatpak override --user --talk-name=org.freedesktop.Flatpak io.github.tim_van_oudheusden.Dailies
```

## Tasks

- [ ] **Host-access probe** (once per session, cached): call `org.freedesktop.Flatpak.Development` with an invalid argument over the session bus. `AccessDenied` or `ServiceUnknown` means **not granted**; a method-level error means **granted**. This is **[I]**, so verify it on a real system and document the exact behaviour
- [ ] **Outside Flatpak** (`/.flatpak-info` absent): the custom command runs directly through `Gio.Subprocess`, and the option is always available
- [ ] **Execution:**
  - inside Flatpak: `flatpak-spawn --host <argv…> <url>`; outside: `<argv…> <url>`
  - split `argv` with `GLib.shell_parse_argv(external-browser-command)`, then append the URL as **one separate argv element**
  - never use `sh -c` and never do string interpolation
- [ ] **Opener** (#45): `mode == custom and host_access_granted and command != ""` → spawn. Otherwise fall back to in-app (if WebKit is present) or external, and toast "Custom command unavailable — opened in …" once per session
- [ ] **Preferences** (#47):
  - show "Custom command" in the combo only when the probe says granted
  - `Adw.EntryRow` "Command" (`show-apply-button: true`, monospace), visible only in custom mode
  - a dimmed help line explaining the override and linking to the README section
- [ ] Document it in the README and `CONTRIBUTING.md`, clearly labelled as a sandbox escape the user chooses

## Acceptance criteria

- [ ] Without the override, Preferences shows no "Custom command" option
- [ ] With the override and `firefox --new-window`, a tile opens in host Firefox
- [ ] A command of `notify-send` (or a crafted URL containing `;`, `$()` or spaces) runs with the URL as a single argument; nothing is shell-interpreted
- [ ] The manifest still has exactly the five finish-args (`flatpak-builder-lint` passes, and #33/#29 show no finish-args change)

## References

- [`mvp-first.md` §3.3 (`external-browser-command`), §5.1, §14 (Sandbox)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`embedded-browser.md` §4, §9.1](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)
- [`cartridges.md` §8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/cartridges.md)
