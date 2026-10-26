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
SIGNATURE = b"\x89PNG\r\n\x1a\n"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("make_ico", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


make_ico = load_script()


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(width: int, height: int | None = None) -> bytes:
    """A fully transparent width x height RGBA PNG; square when `height` is left out."""
    height = width if height is None else height
    rows = b"".join(b"\0" + bytes(4 * width) for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


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


def test_a_non_square_png_keeps_its_own_width_and_height() -> None:
    images = [png(16, 32), png(256, 48)]

    assert read_ico(make_ico.pack(images)) == [(16, 32, 32, images[0]), (256, 48, 32, images[1])]


def test_main_writes_the_ico_of_the_pngs_in_command_line_order(tmp_path: Path) -> None:
    # bundle.sh passes the renderings smallest first, the order Windows lists them in.
    paths = []
    for size in (16, 48, 256):
        path = tmp_path / f"{size}.png"
        path.write_bytes(png(size))
        paths.append(path)
    output = tmp_path / "Dailies.ico"

    assert make_ico.main([str(output), *map(str, paths)]) == 0
    assert output.read_bytes() == make_ico.pack([path.read_bytes() for path in paths])


def test_main_refuses_to_write_an_ico_without_images(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "Dailies.ico"

    with pytest.raises(SystemExit) as exit_info:
        make_ico.main([str(output)])

    assert exit_info.value.code == 2
    assert "pngs" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize(
    ("image", "reason"),
    [
        (b"", "not a PNG"),
        (b"<svg/>", "not a PNG"),
        (png(512), "512x512"),
        # One side over the limit is enough: a directory entry stores 256 as 0, so 512 would wrap round to 256 too.
        (png(512, 16), "512x16"),
        (png(16, 512), "16x512"),
        # A 0 side reads back as 256 from the directory entry.
        (png(0, 16), "0x16"),
        (png(16, 0), "16x0"),
        # The size is read from fixed offsets, so both the signature and the IHDR chunk in first place are required.
        (b"\x89PNG\r\n\x1a\0" + png(16)[8:], "not a PNG"),
        (SIGNATURE + chunk(b"tEXt", b"x" * 13) + png(16)[8:], "not a PNG"),
    ],
    ids=[
        "empty",
        "svg",
        "too-large",
        "too-wide",
        "too-tall",
        "no-width",
        "no-height",
        "bad-signature",
        "ihdr-not-first",
    ],
)
def test_an_image_windows_cannot_show_is_refused(image: bytes, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        make_ico.pack([png(16), image])
