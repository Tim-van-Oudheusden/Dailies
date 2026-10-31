"""Every copy of the GNOME runtime branch names the one the Flatpak manifests ship on.

The manifests' `runtime-version` sets the runtime the app runs on. Three other places repeat the branch as a literal:
scripts/flatpark_payload.py builds the FlatPark payload in org.gnome.Sdk//RUNTIME_BRANCH, ci.yml's `flatpak build-init`
smoke-tests that payload on the Platform branch it names, and scripts/nightly-compliance.sh checks its default
RUNTIME_REF for end-of-life. The workflow and the shell script cannot import Python, and the payload script keeps its
own constant, so a runtime bump that misses one fails nothing: the payload is built and tested on the old runtime, and
the nightly row reports "supported" for a runtime the app no longer ships on.

The gnome-NN build-image tags and Dockerfile.sandbox also name the branch; CONTRIBUTING's "Dependencies" section says to
bump them when the runtime branch changes.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "build-aux" / "flatpak"
RELEASE_MANIFEST = MANIFESTS / "io.github.tim_van_oudheusden.Dailies.json"
DEVEL_MANIFEST = MANIFESTS / "io.github.tim_van_oudheusden.Dailies.Devel.json"

_PY_RUNTIME_BRANCH = re.compile(r'^RUNTIME_BRANCH = "(?P<value>[^"]+)"$', re.MULTILINE)
_BUILD_INIT_BRANCH = re.compile(r"flatpak build-init \S+ \S+ org\.gnome\.Sdk org\.gnome\.Platform (?P<value>\S+)")
_RUNTIME_REF_DEFAULT = re.compile(
    r'^runtime_ref="\$\{RUNTIME_REF:-org\.gnome\.Platform//(?P<value>[^}]+)\}"$', re.MULTILINE
)


def _runtime_version(manifest: Path) -> str:
    return json.loads(manifest.read_text(encoding="utf-8"))["runtime-version"]


def manifest_branch() -> str:
    """The release manifest's `runtime-version`, the runtime the app ships on."""
    return _runtime_version(RELEASE_MANIFEST)


def test_both_manifests_name_the_same_runtime_branch() -> None:
    assert _runtime_version(DEVEL_MANIFEST) == manifest_branch()


def test_flatpark_payload_builds_on_the_manifest_runtime_branch() -> None:
    text = (ROOT / "scripts" / "flatpark_payload.py").read_text(encoding="utf-8")
    match = _PY_RUNTIME_BRANCH.search(text)
    assert match is not None, 'scripts/flatpark_payload.py no longer declares RUNTIME_BRANCH = "..."'
    assert match.group("value") == manifest_branch()


def test_ci_starts_the_flatpark_payload_on_the_manifest_runtime_branch() -> None:
    branches = _BUILD_INIT_BRANCH.findall((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    assert branches, "ci.yml no longer runs flatpak build-init ... org.gnome.Sdk org.gnome.Platform <branch>"
    assert set(branches) == {manifest_branch()}


def test_nightly_compliance_checks_the_manifest_runtime_branch_by_default() -> None:
    text = (ROOT / "scripts" / "nightly-compliance.sh").read_text(encoding="utf-8")
    match = _RUNTIME_REF_DEFAULT.search(text)
    assert match is not None, "scripts/nightly-compliance.sh no longer defaults RUNTIME_REF to org.gnome.Platform//..."
    assert match.group("value") == manifest_branch()
