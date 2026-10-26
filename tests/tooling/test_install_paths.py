"""dailies/config.py.in and dailies/dailies.in find PKGDATADIR and LOCALEDIR where the app is installed.

Meson substitutes absolute paths, except in the Windows build, which is unzipped anywhere: there it substitutes paths
relative to the install prefix, and the generated files resolve them from where they sit (meson.build). Only the
Windows job, which never blocks a merge, starts a moved bundle; these tests render both templates into a prefix the way
`meson install` lays it out and check what they resolve to.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "dailies"
# What meson.build substitutes in the Windows build with the default datadir and localedir.
WINDOWS = {"PKGDATADIR": "share/dailies", "LOCALEDIR": "share/locale"}
# Everywhere else, the absolute paths, as in the Flatpak.
ABSOLUTE = {"PKGDATADIR": "/app/share/dailies", "LOCALEDIR": "/app/share/locale"}
_PLACEHOLDER = re.compile(r"@([A-Z_]+)@")


def render(template: Path, values: dict[str, str]) -> str:
    """`template` with each `@NAME@` replaced, as Meson's configure_file does; a placeholder left over fails."""
    defaults = {"APP_ID": "io.github.example", "VERSION": "0", "PREFIX_PATH": "/", "PROFILE": "release"}
    defaults |= {"HAVE_WEBKIT": "False", "PYTHON": sys.executable}
    values = defaults | values
    missing = set(_PLACEHOLDER.findall(template.read_text(encoding="utf-8"))) - values.keys()
    assert not missing, f"{template.name} has placeholders this test does not fill: {missing}"
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], template.read_text(encoding="utf-8"))


def install_config(prefix: Path, values: dict[str, str]) -> Path:
    """config.py where `meson install` puts it: moduledir, <prefix>/share/dailies/dailies/."""
    config = prefix / "share" / "dailies" / "dailies" / "config.py"
    config.parent.mkdir(parents=True)
    config.write_text(render(PACKAGE / "config.py.in", values), encoding="utf-8")
    return config


def load(config: Path) -> tuple[str, str]:
    spec = importlib.util.spec_from_file_location("config", config)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PKGDATADIR, module.LOCALEDIR


def test_windows_config_resolves_the_relative_paths_against_its_own_prefix(tmp_path: Path) -> None:
    prefix = tmp_path / "Unzipped here" / "Dailies"
    config = install_config(prefix, WINDOWS)

    assert load(config) == (str(prefix / "share" / "dailies"), str(prefix / "share" / "locale"))


def test_windows_config_follows_the_bundle_when_it_is_moved(tmp_path: Path) -> None:
    install_config(tmp_path / "built" / "Dailies", WINDOWS)
    moved = tmp_path / "moved" / "Dailies"
    shutil.copytree(tmp_path / "built" / "Dailies", moved)

    assert load(moved / "share" / "dailies" / "dailies" / "config.py") == (
        str(moved / "share" / "dailies"),
        str(moved / "share" / "locale"),
    )


def test_absolute_config_paths_are_kept_as_meson_wrote_them(tmp_path: Path) -> None:
    config = install_config(tmp_path / "elsewhere", ABSOLUTE)

    assert load(config) == (ABSOLUTE["PKGDATADIR"], ABSOLUTE["LOCALEDIR"])


def stand_in_package(package_dir: Path) -> None:
    """A `dailies` package whose `application.main` prints the file it was imported from."""
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "application.py").write_text("def main():\n    print(__file__)\n    return 0\n", encoding="utf-8")


def run_launcher(prefix: Path, pkgdatadir: str, package_dir: Path, cwd: Path) -> str:
    """Install the launcher in <prefix>/bin and a stand-in `dailies` package in `package_dir`, start the launcher, and
    return the file its `main` was imported from.

    Another `dailies` package is on PYTHONPATH, ahead of site-packages: the launcher must still import its own.
    """
    launcher = prefix / "bin" / "dailies"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(render(PACKAGE / "dailies.in", {"PKGDATADIR": pkgdatadir}), encoding="utf-8")
    stand_in_package(package_dir)
    stand_in_package(cwd / "installed" / "dailies")
    env = os.environ | {"PYTHONPATH": str(cwd / "installed")}
    result = subprocess.run(  # noqa: S603 - the interpreter running these tests, on a script this test wrote
        [sys.executable, str(launcher)], cwd=cwd, env=env, capture_output=True, text=True, check=True, timeout=30
    )
    return result.stdout.strip()


def test_windows_launcher_imports_the_package_from_its_own_prefix(tmp_path: Path) -> None:
    prefix = tmp_path / "Unzipped here" / "Dailies"
    package_dir = prefix / "share" / "dailies" / "dailies"
    (tmp_path / "cwd").mkdir()

    imported = run_launcher(prefix, WINDOWS["PKGDATADIR"], package_dir, cwd=tmp_path / "cwd")

    assert Path(imported).resolve() == (package_dir / "application.py").resolve()


def test_absolute_launcher_path_is_kept_as_meson_wrote_it(tmp_path: Path) -> None:
    package_dir = tmp_path / "pkgdatadir" / "dailies"
    (tmp_path / "cwd").mkdir()

    imported = run_launcher(tmp_path / "prefix", str(tmp_path / "pkgdatadir"), package_dir, cwd=tmp_path / "cwd")

    assert Path(imported).resolve() == (package_dir / "application.py").resolve()
