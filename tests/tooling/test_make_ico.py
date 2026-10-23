"""build-aux/windows/make_ico.py packs the app icon's PNG renderings into the .ico the Windows installer and its
Start-menu shortcut show."""

import importlib.util
import struct
import zlib
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "build-aux" / "windows" / "make_ico.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("make_ico", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


make_ico = load_script()


def png(size: int) -> bytes:
    """A fully transparent size x size RGBA PNG."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    rows = b"".join(b"\0" + bytes(4 * size) for _ in range(size))
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def read_ico(data: bytes) -> list[tuple[int, int, int, bytes]]:
    """(width, height, bits per pixel, image bytes) per directory entry, as Windows reads them."""
    reserved, kind, count = struct.unpack_from("<HHH", data, 0)
    assert (reserved, kind) == (0, 1)
    images = []
    for index in range(count):
        width, height, colours, _, planes, bpp, length, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * index)
        assert (colours, planes) == (0, 1)
        images.append((width or 256, height or 256, bpp, data[offset : offset + length]))
    return images


def test_every_png_is_stored_unchanged_under_its_own_size() -> None:
    images = [png(16), png(48), png(256)]

    assert read_ico(make_ico.pack(images)) == [
        (16, 16, 32, images[0]),
        (48, 48, 32, images[1]),
        (256, 256, 32, images[2]),
    ]


@pytest.mark.parametrize(
    ("image", "reason"),
    [
        (b"", "not a PNG"),
        (b"<svg/>", "not a PNG"),
        (png(512), "512x512"),
    ],
    ids=["empty", "svg", "too-large"],
)
def test_an_image_windows_cannot_show_is_refused(image: bytes, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        make_ico.pack([png(16), image])
