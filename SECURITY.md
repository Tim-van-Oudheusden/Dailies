# Security Policy

Dailies is a launcher for daily guessing games: it fetches a game catalog from GitHub, keeps favourites on your
computer, and opens third-party game websites in a built-in WebKitGTK browser or in your own browser. A flaw in it can
open the wrong site, expose website data or favourites, or let a web page or a catalog entry reach past the Flatpak
sandbox, so reports are welcome.

## Supported versions

Fixes go into the next release; older releases are not patched.

| Version | Supported |
| --- | --- |
| Latest [release](https://github.com/Tim-van-Oudheusden/Dailies/releases/latest) | Yes |
| `main` | Yes |
| Older releases, CI Devel bundles | No; update to the latest release |

## Reporting a vulnerability

**Do not open a public issue, pull request, or discussion for a vulnerability.**

Report it privately through GitHub: the repository's **Security** tab → **Report a vulnerability**
([direct link](https://github.com/Tim-van-Oudheusden/Dailies/security/advisories/new)). Only the maintainer
(@Tim-van-Oudheusden) sees the report.

Include what you can of:

- the Dailies version (Main Menu → About Dailies), how you installed it (release bundle, built from source), and your
  distribution and `flatpak --version`
- what an attacker can do, and what they need first (a crafted catalog entry, a malicious web page, a local account, …)
- steps or a proof of concept that reproduce it
- for a leaked secret: where you found it

A game in the catalog whose website now redirects somewhere unexpected or serves malicious content is not a secret:
open a normal issue so the entry is marked broken quickly.

## What to expect

This is a one-person project, so these are aims, not guarantees:

- an acknowledgement within 7 days
- a first assessment (accepted or not, and the severity) within 14 days
- a fix in a release as soon as practical, coordinated with you, then a published GitHub security advisory that credits
  you unless you prefer otherwise

Please keep the details private until the fix is released or 90 days have passed, whichever comes first.

## Scope

In scope:

- the app (`dailies/`, `data/`): the built-in browser's settings and how links are opened, the catalog and popularity
  fetcher and cache, stored settings and favourites, and the released `.flatpak` bundles
- the Flatpak manifests in `build-aux/flatpak/`, including the sandbox permissions they request
- the catalog data in `data/v1/` and the pipeline that changes it: the game submission workflows, the submission
  validator and link checker, and the popularity workflow
- the build and release pipeline in this repository (`.github/workflows/`, `meson.build`, `scripts/`), including
  leaked secrets

Out of scope:

- flaws in the game websites themselves; report those to their publishers
- flaws in WebKitGTK, GTK, the GNOME runtime or Flatpak; report those upstream
- what a host command can do after you grant Dailies `--talk-name=org.freedesktop.Flatpak` yourself (see
  [Custom browser command](CONTRIBUTING.md#custom-browser-command)); that access is a sandbox escape by design. A way
  for a web page or a catalog entry to reach that command is in scope
- advisories in tools that only CI and `scripts/` use (`scripts/requirements.txt`) and that never ship in the Flatpak.
  Dependabot and the nightly compliance check track these; [`docs/testing.md`](docs/testing.md#accepting-an-advisory)
  describes how they are handled

## Related

- [`docs/security/SECURITY-AI.md`](docs/security/SECURITY-AI.md): how AI coding agents may work in this repository
  safely
