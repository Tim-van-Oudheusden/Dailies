"""Pack PNG renderings of the app icon into a Windows .ico, for the installer and its Start-menu shortcut.

bundle.sh renders the scalable app icon at each size with rsvg-convert and passes the PNGs here, so no binary icon is
committed. Windows has read PNG-compressed .ico images since Vista; each is stored unchanged under its own size.
"""

import argparse
import struct
from pathlib import Path

_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# The largest side an .ico directory entry can record; it is stored as 0.
_MAX_SIDE = 256


def pack(images: list[bytes]) -> bytes:
    """The .ico holding `images` (PNGs of at most 256x256 px) in the given order."""
    directory = struct.pack("<HHH", 0, 1, len(images))
    offset = len(directory) + 16 * len(images)
    data = b""
    for index, image in enumerate(images):
        # The IHDR chunk always comes first, right after the signature.
        if not image.startswith(_SIGNATURE) or image[12:16] != b"IHDR":
            msg = f"image {index} is not a PNG"
            raise ValueError(msg)
        width, height = struct.unpack_from(">II", image, 16)
        if not 0 < width <= _MAX_SIDE or not 0 < height <= _MAX_SIDE:
            msg = f"image {index} is {width}x{height}; an .ico image is at most {_MAX_SIDE}x{_MAX_SIDE}"
            raise ValueError(msg)
        directory += struct.pack("<BBBBHHII", width % _MAX_SIDE, height % _MAX_SIDE, 0, 0, 1, 32, len(image), offset)
        offset += len(image)
        data += image
    return directory + data


def main(argv: list[str] | None = None) -> int:
    """Write the .ico packed from the PNG files on the command line."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path, help="the .ico to write")
    parser.add_argument("pngs", type=Path, nargs="+", help="the PNG renderings, smallest first")
    args = parser.parse_args(argv)
    args.output.write_bytes(pack([png.read_bytes() for png in args.pngs]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
