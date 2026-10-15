# Dailies — project brief

Source: project owner, 2026-10-15. This is the requirements statement every design decision must trace back to.

**Name:** Dailies

**What it is:** A launcher for DLE games (e.g. Wordle, Scrandle, Connections). Tagline in README: "Play your daily guessing games in one place". Licence: GPL-3.0.

## Data

- DLEs are added through GitHub issues (open source project). Each entry has: name, URL, category, difficulty.
- Popularity is sourced online and saved in GitHub; the application retrieves it. A GitHub Action plus agentic work composes a popularity report on a set cadence (start with weekly).

## Access

Clicking a link should open a browser in the application. Preference order: configured browser → built-in browser (like Obsidian's web viewer) → external browser. Must be configurable.

## Technology

Flatpak as first-class citizen, GTK4/Libadwaita native. If possible also cross-platform (research needed for the best option).

## UI

Must look like GTK4/Libadwaita. Reference apps: [Cartridges](https://github.com/kra-mo/cartridges) ([Codeberg](https://codeberg.org/kramo/cartridges)) and [Bazaar](https://github.com/bazaar-org/bazaar) ([GNOME GitLab](https://gitlab.gnome.org/World/bazaar)).

## Logo

Must follow Libadwaita/GNOME HIG icon guidelines and represent the name and purpose.

## Features

- Categorised DLEs. Weekly changing categories: Popular, Trending.
- Favorite button.
- No account creation required.
- Top-level category is always Favorites.

## Repository

- Must meet ACMM requirements for Hive ([hivecommons/hive](https://github.com/hivecommons/hive), [hivecommons.dev](https://hivecommons.dev), [docs.hivecommons.dev](https://docs.hivecommons.dev)). Copy scaffolding from the owner's already-compliant repositories [MinimalUI](https://github.com/Tim-van-Oudheusden/MinimalUI) and [website](https://github.com/Tim-van-Oudheusden/website).
- Flatpak build process and GitHub Actions.
- README with the useful features of the owner's other repositories and/or Flatpak repositories.
- Releases set up so Flatpaks can be downloaded (or install instructions given) until a remote is configured later (e.g. Flathub application).
