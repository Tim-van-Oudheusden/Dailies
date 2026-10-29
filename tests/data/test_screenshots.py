"""Checks for the store screenshots in data/screenshots/ and the metainfo entries that point at them.

The metainfo names each screenshot by a raw GitHub URL on a release tag, and the release workflow mirrors those URLs
(CONTRIBUTING.md, "Releasing"), so a URL on a branch, on a tag that is not a release, or on a file that is not in the
tree only shows up once a tag is pushed. The PNGs are re-rendered by hand (BRANDING.md §6), so their format is pinned
here too. Standard library only.
"""

import re
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCREENSHOTS = ROOT / "data" / "screenshots"
METAINFO = ROOT / "data" / "io.github.tim_van_oudheusden.Dailies.metainfo.xml.in"
README = ROOT / "README.md"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
COLOUR_TYPE_RGBA = 6

SCREENSHOT = re.compile(r"<screenshot(?P<attrs>(?:\s[^>]*)?)>(?P<body>.*?)</screenshot>", re.DOTALL)
IMAGE = re.compile(r"<image>(?P<url>[^<]*)</image>")
CAPTION = re.compile(r"<caption>(?P<text>[^<]*)</caption>")
RELEASE = re.compile(r'<release version="(?P<version>[^"]+)"')
# A tag, never a branch: the URL has to keep showing what that release shipped.
IMAGE_URL = re.compile(
    r"https://raw\.githubusercontent\.com/Tim-van-Oudheusden/Dailies/"
    r"v(?P<version>\d+\.\d+\.\d+)/data/screenshots/(?P<name>[^/]+\.png)"
)
README_IMAGE = re.compile(r'src="data/screenshots/(?P<name>[^"]+)"')


def screenshots() -> list[tuple[str, str, str]]:
    """Return (attributes, image URL, caption) for each metainfo screenshot, in order."""
    entries = []
    for match in SCREENSHOT.finditer(METAINFO.read_text(encoding="utf-8")):
        image = IMAGE.search(match["body"])
        caption = CAPTION.search(match["body"])
        entries.append((match["attrs"], image["url"] if image else "", caption["text"].strip() if caption else ""))
    return entries


def image_urls() -> list[re.Match[str]]:
    urls = [url for _, url, _ in screenshots()]
    matches = [IMAGE_URL.fullmatch(url) for url in urls]
    assert all(matches), urls
    return [match for match in matches if match]


def header(path: Path) -> tuple[int, int, int, int]:
    """Return width, height, bit depth and colour type from a PNG's IHDR chunk."""
    data = path.read_bytes()
    assert data[:8] == PNG_SIGNATURE, path.name
    assert data[12:16] == b"IHDR", path.name
    return struct.unpack(">IIBB", data[16:26])


def top_left_pixel(path: Path) -> bytes:
    """Return the first RGBA pixel of an 8-bit non-interlaced PNG.

    Every filter type predicts the first pixel of the first row from zeros, so its bytes are the raw pixel.
    """
    data = path.read_bytes()
    idat = b""
    offset = 8
    while offset < len(data):
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        kind = data[offset + 4 : offset + 8]
        if kind == b"IHDR":
            assert data[offset + 20] == 0, f"{path.name} is interlaced"
        if kind == b"IDAT":
            idat += data[offset + 8 : offset + 8 + length]
        offset += 12 + length
    row = zlib.decompressobj().decompress(idat, 5)
    return row[1:5]


def test_metainfo_lists_three_to_six_captioned_screenshots_with_the_default_first() -> None:
    entries = screenshots()
    assert 3 <= len(entries) <= 6, len(entries)
    defaults = [index for index, (attrs, _, _) in enumerate(entries) if 'type="default"' in attrs]
    assert defaults == [0], defaults
    assert all(caption for _, _, caption in entries), entries


def test_screenshot_urls_are_on_one_released_tag() -> None:
    released = set(RELEASE.findall(METAINFO.read_text(encoding="utf-8")))
    versions = {match["version"] for match in image_urls()}
    assert len(versions) == 1, versions
    assert versions <= released, (versions, sorted(released))


def test_screenshot_urls_are_not_on_the_newest_release() -> None:
    # The newest release's tag is pushed only after its version-bump and pin pull requests merge, and the Flatpak CI
    # job's repo lint fetches every screenshot URL on those pull requests (appstream-missing-screenshots).
    newest = RELEASE.search(METAINFO.read_text(encoding="utf-8"))
    assert newest, "the metainfo lists no release"
    versions = {match["version"] for match in image_urls()}
    assert newest["version"] not in versions, (versions, newest["version"])


def test_every_screenshot_file_is_listed_once_in_the_metainfo() -> None:
    names = [match["name"] for match in image_urls()]
    assert len(names) == len(set(names)), names
    assert sorted(names) == sorted(path.name for path in SCREENSHOTS.iterdir()), names


def test_readme_shows_only_screenshots_that_exist() -> None:
    names = README_IMAGE.findall(README.read_text(encoding="utf-8"))
    assert names
    assert all((SCREENSHOTS / name).is_file() for name in names), names


def test_screenshots_are_rgba_pngs_of_one_size() -> None:
    headers = {path.name: header(path) for path in SCREENSHOTS.iterdir()}
    assert all(depth == 8 and colour == COLOUR_TYPE_RGBA for _, _, depth, colour in headers.values()), headers
    assert len({(width, height) for width, height, _, _ in headers.values()}) == 1, headers


def test_screenshots_keep_the_transparent_margin_around_the_window_shadow() -> None:
    # A window-only capture with GTK's own shadow has a transparent margin; a flat corner means a cropped desktop.
    corners = {path.name: top_left_pixel(path) for path in SCREENSHOTS.iterdir()}
    assert all(len(pixel) == 4 and pixel[3] == 0 for pixel in corners.values()), corners
