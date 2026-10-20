"""The release app id is hand-copied outside meson.build, so a rename has nothing to catch a missed copy.

meson.build's `app_id` (profile-dependent: plain for a release build, `.Devel`-suffixed for development) is
templated via `conf.set('APP_ID', app_id)` into every generated `.in` file at build time. scripts/dev.sh,
scripts/release_check.py, scripts/flatpark_payload.py and data/icons/meson.build cannot read that: they are
deliberately standalone, dependency-free tools that run before or without a Meson build, so each hand-copies the
release (non-Devel) app id as its own literal instead. A missed copy fails at release or build time (a wrong
manifest path, or `flatpak build-init` targeting the wrong application id), not on review.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_MESON_APP_ID = re.compile(r"^\s*app_id = '(?P<value>[^']+)'$", re.MULTILINE)
_DEV_SH_APP_ID = re.compile(r"^readonly APP_ID=(?P<value>\S+)$", re.MULTILINE)
_PY_APP_ID = re.compile(r'^APP_ID = "(?P<value>[^"]+)"$', re.MULTILINE)
_ICONS_BASE_ID = re.compile(r"^base_id = '(?P<value>[^']+)'$", re.MULTILINE)


def meson_release_app_id() -> str:
    """The release (non-`.Devel`) `app_id` from the top-level meson.build's profile branch."""
    text = (ROOT / "meson.build").read_text(encoding="utf-8")
    ids = _MESON_APP_ID.findall(text)
    release = [value for value in ids if not value.endswith(".Devel")]
    assert len(release) == 1, f"expected exactly one release app_id in meson.build, found {ids}"
    return release[0]


def test_dev_sh_names_the_meson_release_app_id() -> None:
    text = (ROOT / "scripts" / "dev.sh").read_text(encoding="utf-8")
    match = _DEV_SH_APP_ID.search(text)
    assert match is not None, "scripts/dev.sh no longer declares readonly APP_ID=..."
    assert match.group("value") == meson_release_app_id()


def test_release_check_names_the_meson_release_app_id() -> None:
    text = (ROOT / "scripts" / "release_check.py").read_text(encoding="utf-8")
    match = _PY_APP_ID.search(text)
    assert match is not None, "scripts/release_check.py no longer declares APP_ID = ..."
    assert match.group("value") == meson_release_app_id()


def test_flatpark_payload_names_the_meson_release_app_id() -> None:
    text = (ROOT / "scripts" / "flatpark_payload.py").read_text(encoding="utf-8")
    match = _PY_APP_ID.search(text)
    assert match is not None, "scripts/flatpark_payload.py no longer declares APP_ID = ..."
    assert match.group("value") == meson_release_app_id()


def test_icons_base_id_names_the_meson_release_app_id() -> None:
    text = (ROOT / "data" / "icons" / "meson.build").read_text(encoding="utf-8")
    match = _ICONS_BASE_ID.search(text)
    assert match is not None, "data/icons/meson.build no longer declares base_id = ..."
    assert match.group("value") == meson_release_app_id()


def test_release_manifest_exists_under_the_meson_release_app_id() -> None:
    manifest = ROOT / "build-aux" / "flatpak" / f"{meson_release_app_id()}.json"
    assert manifest.is_file(), f"{manifest} does not exist: did the release app id change?"
