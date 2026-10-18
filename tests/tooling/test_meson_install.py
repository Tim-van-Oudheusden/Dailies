"""dailies/meson.build installs every module of the package, so a new module cannot be left out of the Flatpak.

The installed app runs from PKGDATADIR, not from the checkout: a module missing from an `install_data` list passes
`pytest` and crashes the app on launch with `ModuleNotFoundError` (#154). Only the `Flatpak (x86_64)` job would catch
that, about three minutes in; this catches it in `Build, lint, test` and locally.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "dailies"

_INSTALL_DATA = re.compile(r"\binstall_data\((?P<args>.*?)\)", re.DOTALL)
_INSTALL_DIR = re.compile(r"install_dir:\s*moduledir(?:\s*/\s*'(?P<subdir>[^']+)')?\s*,")
_CONFIGURED_OUTPUT = re.compile(r"\bconfigure_file\(.*?output:\s*'(?P<output>[^']+)'.*?\)", re.DOTALL)
_QUOTED = re.compile(r"'([^']+)'")


def install_lists(meson: str) -> list[tuple[str, list[str]]]:
    """Each `install_data` call into the package as (subdirectory of moduledir, files relative to dailies/)."""
    lists = []
    for call in _INSTALL_DATA.finditer(meson):
        args = call.group("args")
        install_dir = _INSTALL_DIR.search(args)
        assert install_dir, f"install_data without an install_dir under moduledir: {args.strip()!r}"
        files = _QUOTED.findall(args[: install_dir.start()])
        lists.append((install_dir.group("subdir") or "", files))
    return lists


def installed_modules(meson: str) -> set[str]:
    return {file for _, files in install_lists(meson) for file in files}


def generated_modules(meson: str) -> set[str]:
    """Modules Meson writes from a template, such as config.py from config.py.in: there is no .py in the checkout."""
    outputs = (match.group("output") for match in _CONFIGURED_OUTPUT.finditer(meson))
    return {output for output in outputs if output.endswith(".py")}


def package_modules(package: Path) -> set[str]:
    return {path.relative_to(package).as_posix() for path in package.rglob("*.py")}


def missing_from_install(package: Path) -> set[str]:
    meson = (package / "meson.build").read_text(encoding="utf-8")
    return package_modules(package) - installed_modules(meson) - generated_modules(meson)


def test_every_module_of_the_package_is_installed() -> None:
    assert missing_from_install(PACKAGE) == set()


def test_every_installed_module_exists() -> None:
    # A listed file that is gone fails `meson setup`, which only the Flatpak job runs.
    assert installed_modules((PACKAGE / "meson.build").read_text(encoding="utf-8")) - package_modules(PACKAGE) == set()


def test_each_module_is_installed_into_its_own_directory() -> None:
    # `core/x.py` installed into `moduledir / 'data'` would import as dailies.data.x, not dailies.core.x.
    for subdir, files in install_lists((PACKAGE / "meson.build").read_text(encoding="utf-8")):
        assert {Path(file).parent.as_posix().removeprefix(".") for file in files} == {subdir}, files


def test_config_py_is_generated_not_listed() -> None:
    assert generated_modules((PACKAGE / "meson.build").read_text(encoding="utf-8")) == {"config.py"}


def test_a_module_left_out_of_meson_build_is_reported(tmp_path: Path) -> None:
    (tmp_path / "core").mkdir()
    for module in ("__init__.py", "core/__init__.py", "core/icons.py"):
        (tmp_path / module).write_text("", encoding="utf-8")
    (tmp_path / "meson.build").write_text(
        "configure_file(\n  input: 'config.py.in',\n  output: 'config.py',\n  install_dir: moduledir,\n)\n"
        "install_data(\n  '__init__.py',\n  install_dir: moduledir,\n)\n"
        "install_data(\n  'core/__init__.py',\n  install_dir: moduledir / 'core',\n)\n",
        encoding="utf-8",
    )
    assert missing_from_install(tmp_path) == {"core/icons.py"}
