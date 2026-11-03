"""The Devel Flatpak manifest builds and sandboxes the app the way the release manifest does.

Each manifest keeps its own copy of the build: `runtime`, `sdk`, `command`, `finish-args` (the sandbox permissions),
`cleanup` and the modules. CI's `flatpak` job lints, builds and tests the Devel manifest only; the release manifest is
linted and built only when a tag is pushed. A key changed or added in one manifest alone fails nothing: a permission
added only to the release manifest skips flatpak-builder-lint on review, and a permission, dependency module or
`command` changed only in the Devel manifest lets CI pass an app the shipped manifest does not build.

Only the keys that differ on purpose are left out of the comparison: the top-level `id`, `tags` and
`desktop-file-name-suffix`, and the `dailies` module's `run-tests`, `config-opts` and `sources`. A new intentional
difference goes into `DIFFER_ON_PURPOSE` or `APP_MODULE_DIFFERS_ON_PURPOSE` in the pull request that introduces it.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "build-aux" / "flatpak"
RELEASE_MANIFEST = MANIFESTS / "io.github.tim_van_oudheusden.Dailies.json"
DEVEL_MANIFEST = MANIFESTS / "io.github.tim_van_oudheusden.Dailies.Devel.json"

APP_MODULE = "dailies"
DIFFER_ON_PURPOSE = frozenset({"id", "tags", "desktop-file-name-suffix"})
APP_MODULE_DIFFERS_ON_PURPOSE = frozenset({"run-tests", "config-opts", "sources"})


def _without(data: dict, keys: frozenset[str]) -> dict:
    return {key: value for key, value in data.items() if key not in keys}


def _shared(manifest: Path) -> dict:
    """The manifest without the keys that differ on purpose."""
    data = _without(json.loads(manifest.read_text(encoding="utf-8")), DIFFER_ON_PURPOSE)
    data["modules"] = [
        _without(module, APP_MODULE_DIFFERS_ON_PURPOSE)
        if isinstance(module, dict) and module.get("name") == APP_MODULE
        else module
        for module in data["modules"]
    ]
    return data


def test_devel_manifest_differs_from_the_release_manifest_only_where_documented() -> None:
    assert _shared(DEVEL_MANIFEST) == _shared(RELEASE_MANIFEST)
