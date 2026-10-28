"""The app id is hand-copied outside meson.build, so a rename has nothing to catch a missed copy.

meson.build's `app_id` (profile-dependent: plain for a release build, `.Devel`-suffixed for development) is
templated via `conf.set('APP_ID', app_id)` into every generated `.in` file at build time. scripts/dev.sh,
scripts/release_check.py, scripts/flatpark_payload.py and data/icons/meson.build cannot read that: they are
deliberately standalone, dependency-free tools that run before or without a Meson build, so each hand-copies the
release (non-Devel) app id as its own literal instead. The Flatpak manifests and the workflows copy it too: release.yml
and external-data-checker.yml never run on a pull request, so a stale copy there fails only at release or on the next
scheduled run. A missed copy fails at release or build time (a wrong manifest path, or `flatpak build-init` targeting
the wrong application id), not on review.

Existence alone is not enough for release.yml's `MANIFEST` and external-data-checker.yml's manifest-path literals:
both manifest files always exist, so a copy-paste swap onto the `.Devel` manifest passes a check that only asks
whether the named path is a real file. These two are release-only workflows, so their manifest literal must equal
the release app id specifically, the same way ci.yml's `DEVEL_ID` and `build-init` ids are checked against theirs.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
MANIFESTS = ROOT / "build-aux" / "flatpak"
WINDOWS = ROOT / "build-aux" / "windows"

_MESON_APP_ID = re.compile(r"^\s*app_id = '(?P<value>[^']+)'$", re.MULTILINE)
_DEV_SH_APP_ID = re.compile(r"^readonly APP_ID=(?P<value>\S+)$", re.MULTILINE)
_PY_APP_ID = re.compile(r'^APP_ID = "(?P<value>[^"]+)"$', re.MULTILINE)
_ICONS_BASE_ID = re.compile(r"^base_id = '(?P<value>[^']+)'$", re.MULTILINE)
_WORKFLOW_MANIFEST = re.compile(r"build-aux/flatpak/[\w.-]+\.json")
_DEVEL_ID = re.compile(r"^\s+DEVEL_ID:\s*(?P<value>\S+)\s*$", re.MULTILINE)
_BUILD_INIT = re.compile(r"flatpak build-init \S+ (?P<value>\S+)")
_MANIFEST_ENV = re.compile(r"^\s+MANIFEST:\s*(?P<value>\S+)\s*$", re.MULTILINE)
_BUNDLE_ICON = re.compile(r"data/icons/hicolor/scalable/apps/(?P<value>[\w.]+)\.svg")
_SMOKE_REGISTRY = re.compile(r"HKCU:\\Software\\GSettings\\(?P<value>[\w\\]+)\\State")


def _meson_app_ids() -> list[str]:
    return _MESON_APP_ID.findall((ROOT / "meson.build").read_text(encoding="utf-8"))


def meson_release_app_id() -> str:
    """The release (non-`.Devel`) `app_id` from the top-level meson.build's profile branch."""
    ids = _meson_app_ids()
    release = [value for value in ids if not value.endswith(".Devel")]
    assert len(release) == 1, f"expected exactly one release app_id in meson.build, found {ids}"
    return release[0]


def meson_devel_app_id() -> str:
    """The development (`.Devel`) `app_id` from the top-level meson.build's profile branch."""
    ids = _meson_app_ids()
    devel = [value for value in ids if value.endswith(".Devel")]
    assert len(devel) == 1, f"expected exactly one .Devel app_id in meson.build, found {ids}"
    return devel[0]


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
    manifest = MANIFESTS / f"{meson_release_app_id()}.json"
    assert manifest.is_file(), f"{manifest} does not exist: did the release app id change?"


def test_each_manifest_id_names_the_meson_app_id_its_filename_does() -> None:
    # Renaming a manifest file leaves its "id" behind, and flatpak-builder builds whatever "id" says.
    for app_id in (meson_release_app_id(), meson_devel_app_id()):
        manifest = MANIFESTS / f"{app_id}.json"
        assert manifest.is_file(), f"{manifest} does not exist: did the app id change?"
        assert json.loads(manifest.read_text(encoding="utf-8"))["id"] == app_id, manifest.name


def test_every_manifest_a_workflow_names_exists() -> None:
    named = {
        (workflow.name, path)
        for workflow in sorted(WORKFLOWS.glob("*.yml"))
        for path in _WORKFLOW_MANIFEST.findall(workflow.read_text(encoding="utf-8"))
    }
    assert named, "no workflow names a build-aux/flatpak manifest any more"
    missing = sorted((name, path) for name, path in named if not (ROOT / path).is_file())
    assert not missing, f"workflows name manifests that do not exist: {missing}"


def test_ci_devel_id_names_the_meson_devel_app_id() -> None:
    text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    match = _DEVEL_ID.search(text)
    assert match is not None, "ci.yml no longer declares DEVEL_ID: ..."
    assert match.group("value") == meson_devel_app_id()


def test_workflow_build_init_names_the_meson_release_app_id() -> None:
    # The FlatPark payload runs on a build dir initialised under the release id, as FlatPark installs it.
    ids = _BUILD_INIT.findall((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))
    assert ids, "ci.yml no longer runs flatpak build-init"
    assert set(ids) == {meson_release_app_id()}


def test_release_workflows_name_the_meson_release_manifest() -> None:
    # Unlike test_every_manifest_a_workflow_names_exists, this ties each literal to the release id specifically:
    # both manifest files always exist, so a copy-paste swap onto the .Devel manifest here would otherwise pass.
    release_manifest = f"build-aux/flatpak/{meson_release_app_id()}.json"

    text = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")
    match = _MANIFEST_ENV.search(text)
    assert match is not None, "release.yml no longer declares MANIFEST: ..."
    assert match.group("value") == release_manifest

    text = (WORKFLOWS / "external-data-checker.yml").read_text(encoding="utf-8")
    paths = _WORKFLOW_MANIFEST.findall(text)
    assert paths, "external-data-checker.yml no longer names a build-aux/flatpak manifest"
    assert set(paths) == {release_manifest}


def test_bundle_icon_source_names_the_meson_release_app_id() -> None:
    # bundle.sh rasterizes the scalable app icon by this literal path; a stale copy fails rsvg-convert inside the
    # Windows (experimental) job, which is continue-on-error and not a required check, so nothing else would catch it.
    text = (WINDOWS / "bundle.sh").read_text(encoding="utf-8")
    match = _BUNDLE_ICON.search(text)
    assert match is not None, "bundle.sh no longer renders the scalable app icon from data/icons/hicolor/..."
    assert match.group("value") == meson_release_app_id()


def test_smoke_registry_path_names_the_meson_release_app_id() -> None:
    # smoke.ps1 hand-encodes the app id as a GLib GSettings registry-backend path to seed window State; a stale copy
    # sets the wrong key, so the smoke test would still pass while checking nothing.
    text = (WINDOWS / "smoke.ps1").read_text(encoding="utf-8")
    match = _SMOKE_REGISTRY.search(text)
    assert match is not None, "smoke.ps1 no longer sets the GSettings registry State key"
    assert match.group("value").replace("\\", ".") == meson_release_app_id()
