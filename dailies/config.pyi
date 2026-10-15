# Type stub for config.py, which Meson generates from config.py.in at build time.
from typing import Final, Literal

APP_ID: Final[str]
VERSION: Final[str]
PREFIX: Final[str]
PROFILE: Final[Literal["release", "development"]]
PKGDATADIR: Final[str]
LOCALEDIR: Final[str]
HAVE_WEBKIT: Final[bool]
DATA_URLS: Final[list[str]]
