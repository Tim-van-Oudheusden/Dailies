#!/usr/bin/env python3
"""Fetch each game's icon and store it as a 64x64 PNG in data/v1/icons/ (#77, decision #17 option b).

The icons are served from GitHub Pages with the rest of data/v1/ and never go into the Flatpak (data/meson.build
installs only games.json and popularity.json). For each game the candidates are tried in this order:

    manifest          the web-app manifest's icons (purpose "any"), named by <link rel="manifest">
    apple-touch-icon  <link rel="apple-touch-icon"> (and -precomposed)
    icon              <link rel="icon"> (and "shortcut icon")
    favicon.ico       /favicon.ico on the site the game page ended up on
    google            Google's (unofficial) faviconV2 service
    duckduckgo        DuckDuckGo's (unofficial) ip3 service

Within one source, the smallest icon of at least 64 px comes first, then icons of unknown size, then smaller ones. SVG
icons are skipped (Pillow does not render them), and so are images that are not nearly square (a cover image named as
an icon). The first candidate that decodes to an image of at least 64 px wins; when none does, the largest one of at
least 16 px is used, and a game without one keeps its category glyph in the app.

Every request goes through scripts/lib/urlcheck.py: https only, every redirect hop and the connected peer must be a
public address, so a page cannot point the fetcher at an internal one. Icons are capped at MAX_ICON_BYTES and
MAX_PIXELS before they are decoded, and only raster formats are accepted. The output is deterministic, so a re-run
over an unchanged icon leaves the file untouched. Requests are polite: one at a time, at most two a second.

Each fetched game's catalog entry records the result (docs/data-format.md, "Icons"): `icon` is "icons/<id>.png" and
`icon_source` is "site", "google" or "duckduckgo"; a game with no icon gets `icon_source: "none"` and no `icon`. When a
fetch finds nothing but an earlier run stored a PNG, both stay. An entry whose `icon_source` is "manual" holds an icon
a maintainer placed by hand and is never fetched. When an entry changed, `generated_at` becomes the current time and
games.json is written in its committed format.

Ids listed in scripts/data/icon-takedowns.txt are never fetched; their PNG is deleted and their entry gets
`icon_source: "none"`, even a manual one. That is how a site's request to remove its icon is honoured (README, "Game
icons").

Usage:
    python -I scripts/icons/fetch_icon.py --catalog data/v1/games.json --out data/v1/icons [--id ID ...]
        [--missing-only] [--takedowns FILE]

Without --id it fetches every game that is not retired; --missing-only skips games that already have a PNG. Prints
one line per game naming where its icon came from. Exits 0 when the run finished, even if some games got no icon, and
2 on a usage error (an unknown --id, an unreadable catalog or takedown list).
"""

import argparse
import html.parser
import io
import json
import logging
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import quote, urljoin, urlsplit

from PIL import Image

# scripts/lib is not a package and `python -I` leaves the script's directory off sys.path, so add it by path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import linkstatus
import urlcheck

TAKEDOWNS = Path(__file__).resolve().parent.parent / "data" / "icon-takedowns.txt"
SIZE = 64
# A candidate this large ends the search; a smaller one is kept only if no later candidate is bigger.
GOOD_SIZE = SIZE
MIN_SIZE = 16
# Enough of the game page to find the <link> tags in its <head>.
MAX_PAGE_BYTES = 512 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
MAX_ICON_BYTES = 1024 * 1024
# Checked from the image header, before any pixel is decoded (decompression bombs).
MAX_PIXELS = 4096 * 4096
# An icon is (nearly) square; a wider image is a banner or a social-media cover, not an icon.
MAX_ASPECT = 1.25
FORMATS = ("PNG", "ICO", "JPEG", "GIF", "WEBP", "BMP")
# One request every half second at most: two a second overall (as scripts/check_links.py).
MIN_INTERVAL = 0.5
# Catalog ids become file names; the schema allows only these, but never trust that here.
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
GOOGLE = "https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url={origin}&size=64"
DUCKDUCKGO = "https://icons.duckduckgo.com/ip3/{host}.ico"


class Throttle:
    """A session that sends one request at a time, starting at most one every `interval` seconds."""

    def __init__(
        self,
        session: urlcheck.Session,
        interval: float = MIN_INTERVAL,
        clock: Callable[[], float] = monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._session = session
        self._interval = interval
        self._clock = clock
        self._sleep = sleep
        self._next: float | None = None

    def request(self, method: str, url: str, **kwargs: Any) -> urlcheck.Response:
        """Wait for the next free slot, then send the request."""
        if self._next is not None:
            wait = self._next - self._clock()
            if wait > 0:
                self._sleep(wait)
        self._next = self._clock() + self._interval
        return self._session.request(method, url, **kwargs)


@dataclass
class PageLinks:
    """The icon links of a game page, each list best first, as absolute URLs."""

    manifest: str | None = None
    touch_icons: list[str] = field(default_factory=list)
    icons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Icon:
    """A game's icon as a 64x64 PNG, and where it came from.

    Attributes:
        png: The normalised PNG.
        source: Which candidate it is, e.g. "apple-touch-icon" (see the module docstring).
        url: The URL it was downloaded from.
        source_size: The shorter side of the downloaded image, in pixels.
    """

    png: bytes
    source: str
    url: str
    source_size: int


def _largest_size(sizes: str) -> int | None:
    """The largest dimension in a `sizes` attribute such as "48x48 96x96", or None for "any" or nothing."""
    found = [max(int(w), int(h)) for w, h in re.findall(r"(\d+)[xX](\d+)", sizes)]
    return max(found) if found else None


def _rank(size: int | None) -> tuple[int, int]:
    """Sort key: the smallest icon of at least SIZE px first, then unknown sizes, then the largest smaller one."""
    if size is None:
        return (1, 0)
    return (0, size) if size >= SIZE else (2, -size)


def _is_svg(url: str, mime_type: str) -> bool:
    return mime_type.strip().lower() == "image/svg+xml" or urlsplit(url).path.lower().endswith(".svg")


def _best_first(icons: list[tuple[str, int | None]]) -> list[str]:
    # sorted() is stable: icons of the same rank keep the page's order.
    return [url for url, _size in sorted(icons, key=lambda icon: _rank(icon[1]))]


class _LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "link":
            self.links.append({name: value or "" for name, value in attrs})


def page_links(page: str, base_url: str) -> PageLinks:
    """The manifest and icon links of an HTML page, resolved against the URL it was read from."""
    parser = _LinkParser()
    parser.feed(page)
    links = PageLinks()
    touch: list[tuple[str, int | None]] = []
    icons: list[tuple[str, int | None]] = []
    for link in parser.links:
        href = link.get("href", "").strip()
        if not href:
            continue
        try:
            url = urljoin(base_url, href)
        except ValueError:
            continue
        rel = set(link.get("rel", "").lower().split())
        if "manifest" in rel and links.manifest is None:
            links.manifest = url
        if _is_svg(url, link.get("type", "")):
            continue
        size = _largest_size(link.get("sizes", ""))
        if rel & {"apple-touch-icon", "apple-touch-icon-precomposed"}:
            touch.append((url, size))
        elif "icon" in rel:
            icons.append((url, size))
    links.touch_icons = _best_first(touch)
    links.icons = _best_first(icons)
    return links


def manifest_icons(manifest: object, manifest_url: str) -> list[str]:
    """The raster icons of a web-app manifest whose purpose includes "any", best first, as absolute URLs."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("icons"), list):
        return []
    icons: list[tuple[str, int | None]] = []
    for icon in manifest["icons"]:
        if not isinstance(icon, dict) or not isinstance(icon.get("src"), str):
            continue
        purpose = str(icon.get("purpose", "any")).lower().split()
        if "any" not in purpose:
            continue
        try:
            url = urljoin(manifest_url, icon["src"])
        except ValueError:
            continue
        if _is_svg(url, str(icon.get("type", ""))):
            continue
        icons.append((url, _largest_size(str(icon.get("sizes", "")))))
    return _best_first(icons)


def candidates(page_url: str, links: PageLinks, from_manifest: list[str]) -> list[tuple[str, str]]:
    """Every (source, url) to try for a game whose page ended up at page_url, in order, each URL once."""
    parts = urlsplit(page_url)
    origin = f"{parts.scheme}://{parts.netloc}"
    ordered = [
        *(("manifest", url) for url in from_manifest),
        *(("apple-touch-icon", url) for url in links.touch_icons),
        *(("icon", url) for url in links.icons),
        ("favicon.ico", f"{origin}/favicon.ico"),
        ("google", GOOGLE.format(origin=quote(origin, safe=""))),
        ("duckduckgo", DUCKDUCKGO.format(host=parts.hostname or "")),
    ]
    seen: set[str] = set()
    unique = []
    for source, url in ordered:
        if url not in seen:
            seen.add(url)
            unique.append((source, url))
    return unique


def _read(response: urlcheck.Response, limit: int, *, truncate: bool) -> bytes | None:
    """The body of a response: cut at `limit` bytes when truncate, else None when it is longer; None when slow."""
    # The request timeout bounds each socket read, not the whole body: a server can trickle bytes forever.
    deadline = monotonic() + urlcheck.TIMEOUT
    body = bytearray()
    try:
        for chunk in response.iter_content(64 * 1024):
            body.extend(chunk)
            if len(body) > limit:
                return bytes(body[:limit]) if truncate else None
            if monotonic() > deadline:
                return None
    finally:
        response.close()
    return bytes(body)


def _get(
    url: str, session: urlcheck.Session, resolve: urlcheck.Resolver, limit: int, *, truncate: bool = False
) -> tuple[str, bytes] | None:
    """GET a public https URL: the final URL and the body, or None on any failure or a non-2xx answer."""
    try:
        final_url, response = urlcheck.fetch(session, "GET", url, resolve)
    except urlcheck.CheckError:
        return None
    if not HTTPStatus.OK <= response.status_code < HTTPStatus.MULTIPLE_CHOICES:
        response.close()
        return None
    body = _read(response, limit, truncate=truncate)
    return None if body is None else (final_url, body)


def normalise(data: bytes) -> tuple[bytes, int] | None:
    """A raster image as a 64x64 RGBA PNG centred on a transparent square, and its shorter side in pixels.

    Returns:
        None when the data is not a PNG, ICO, JPEG, GIF, WebP or BMP image, has more than MAX_PIXELS pixels, is not
        nearly square (MAX_ASPECT), cannot be decoded, or is fully transparent.
    """
    try:
        with Image.open(io.BytesIO(data), formats=FORMATS) as picture:
            width, height = picture.size
            if width * height > MAX_PIXELS or max(width, height) > MAX_ASPECT * min(width, height):
                return None
            # An ICO holds several sizes; Pillow loads the largest.
            rgba = picture.convert("RGBA")
    except (OSError, ValueError, SyntaxError, EOFError, Image.DecompressionBombError):
        return None
    if rgba.getchannel("A").getbbox() is None:
        return None
    side = max(width, height)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(rgba, ((side - width) // 2, (side - height) // 2))
    if side != SIZE:
        square = square.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    square.save(out, "PNG", optimize=True)
    return out.getvalue(), min(width, height)


def fetch_icon(game: dict[str, Any], session: urlcheck.Session, resolve: urlcheck.Resolver) -> Icon | None:
    """The best icon for a catalog entry, or None when no candidate gives a usable one."""
    page = _get(game["url"], session, resolve, MAX_PAGE_BYTES, truncate=True)
    page_url = page[0] if page else game["url"]
    links = page_links(page[1].decode("utf-8", errors="replace"), page_url) if page else PageLinks()
    from_manifest: list[str] = []
    if links.manifest:
        manifest = _get(links.manifest, session, resolve, MAX_MANIFEST_BYTES)
        if manifest:
            try:
                from_manifest = manifest_icons(json.loads(manifest[1]), manifest[0])
            except ValueError:  # not JSON, or not UTF-8
                from_manifest = []
    best: Icon | None = None
    for source, url in candidates(page_url, links, from_manifest):
        got = _get(url, session, resolve, MAX_ICON_BYTES)
        result = normalise(got[1]) if got else None
        if result is None:
            continue
        icon = Icon(png=result[0], source=source, url=url, source_size=result[1])
        if icon.source_size >= GOOD_SIZE:
            return icon
        if icon.source_size >= MIN_SIZE and (best is None or icon.source_size > best.source_size):
            best = icon
    return best


def load_takedowns(path: Path) -> set[str]:
    """The game ids of a takedown list: one per line, without blank lines and "#" comments."""
    return set(urlcheck.load_blocklist(path))


def _load_catalog(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("games"), list):
        msg = f"{path} does not hold a catalog object with a games list"
        raise TypeError(msg)
    return data


def _with_icon(entry: dict[str, Any], icon: str | None, source: str) -> dict[str, Any]:
    """The entry with `icon` (dropped when None) and `icon_source` right after `domain`, other keys in order."""
    fields = {"icon": icon, "icon_source": source} if icon else {"icon_source": source}
    updated: dict[str, Any] = {}
    for key, value in entry.items():
        if key in {"icon", "icon_source"}:
            continue
        updated[key] = value
        if key == "domain":
            updated.update(fields)
    updated.update({key: value for key, value in fields.items() if key not in updated})
    return updated


def _update(entry: dict[str, Any], out: Path, icon: Icon | None, *, taken_down: bool) -> tuple[dict[str, Any], str]:
    """Write, keep or delete a game's PNG; the entry that records it, and what happened in one line."""
    game_id = entry["id"]
    path = out / f"{game_id}.png"
    if taken_down:
        path.unlink(missing_ok=True)
        return _with_icon(entry, None, "none"), f"{game_id}: taken down, no icon"
    if icon is None:
        # A site that is down this week keeps the icon an earlier run found.
        kept = entry if path.exists() else _with_icon(entry, None, "none")
        return kept, f"{game_id}: no icon, the category glyph stays"
    if not path.exists() or path.read_bytes() != icon.png:
        path.write_bytes(icon.png)
    source = icon.source if icon.source in {"google", "duckduckgo"} else "site"
    updated = _with_icon(entry, f"icons/{game_id}.png", source)
    return updated, f"{game_id}: {icon.source} {icon.url} ({icon.source_size} px)"


def main(
    argv: list[str] | None = None,
    *,
    session: urlcheck.Session | None = None,
    resolve: urlcheck.Resolver = urlcheck.resolve_host,
    now: datetime | None = None,
) -> int:
    """Fetch the icons of the games named on the command line and record them in the catalog.

    Args:
        argv: The command-line arguments; sys.argv by default.
        session: Sends the requests; a throttled, public-only ``requests.Session`` by default. A session passed in is
            used as is, without the throttle.
        resolve: Resolves a host name to its IP addresses.
        now: The time recorded in `generated_at` when an entry changed; the current UTC time by default.

    Returns:
        0 when the run finished, 2 on a usage or internal error.
    """
    parser = argparse.ArgumentParser(description="Fetch game icons as 64x64 PNGs.")
    parser.add_argument("--catalog", type=Path, required=True, help="data/v1/games.json, updated in place")
    parser.add_argument("--out", type=Path, required=True, help="the icon directory, data/v1/icons")
    parser.add_argument("--id", action="append", dest="ids", help="fetch only this game (repeatable)")
    parser.add_argument("--missing-only", action="store_true", help="skip games that already have an icon")
    parser.add_argument("--takedowns", type=Path, default=TAKEDOWNS, help="ids whose icon must not be published")
    args = parser.parse_args(argv)
    try:
        catalog = _load_catalog(args.catalog)
        games: list[dict[str, Any]] = catalog["games"]
        takedowns = load_takedowns(args.takedowns)
        unknown = sorted(set(args.ids or ()) - {game.get("id") for game in games})
        if unknown:
            sys.stderr.write(f"fetch_icon: not in the catalog: {', '.join(unknown)}\n")
            return 2
        args.out.mkdir(parents=True, exist_ok=True)
        changed = False
        with urlcheck.public_session() as default_session:
            throttled = session or Throttle(default_session)
            for index, game in enumerate(games):
                game_id = str(game.get("id"))
                if game.get("status") == "retired" or (args.ids and game_id not in args.ids):
                    continue
                if not SAFE_ID.match(game_id):
                    sys.stderr.write(f"fetch_icon: skipping unsafe id {game_id!r}\n")
                    continue
                taken_down = game_id in takedowns
                if not taken_down and (
                    game.get("icon_source") == "manual"
                    or (args.missing_only and (args.out / f"{game_id}.png").exists())
                ):
                    continue
                icon = None if taken_down else fetch_icon(game, throttled, resolve)
                updated, line = _update(game, args.out, icon, taken_down=taken_down)
                changed = changed or updated != game
                games[index] = updated
                sys.stdout.write(line + "\n")
                sys.stdout.flush()
        if changed:
            catalog["generated_at"] = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
            args.catalog.write_text(linkstatus.dump_catalog(catalog), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"fetch_icon: {error!r}\n")
        return 2
    except Exception:
        logging.getLogger(__name__).exception("fetch_icon: internal error")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
