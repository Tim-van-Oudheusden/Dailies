import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)


def test_ruff_targets_python_312_at_120_columns() -> None:
    ruff = load_pyproject()["tool"]["ruff"]
    assert ruff["target-version"] == "py312"
    assert ruff["line-length"] == 120


def test_e2e_tests_are_excluded_by_default() -> None:
    options = load_pyproject()["tool"]["pytest"]["ini_options"]
    assert "e2e" in " ".join(options["markers"])
    assert "not e2e" in options["addopts"]


def test_gi_tests_are_left_to_meson() -> None:
    assert "--ignore=tests/gi" in load_pyproject()["tool"]["pytest"]["ini_options"]["addopts"]


def test_coverage_measures_core_and_scripts_only() -> None:
    assert load_pyproject()["tool"]["coverage"]["run"]["source"] == ["dailies/core", "scripts"]


def test_coverage_reports_modules_that_no_test_imports() -> None:
    # coverage.py lists a module that was never imported, at 0 %, only at a source root or inside a package, and the
    # folders under scripts/ have no __init__.py. Without this option a new module there with no tests at all would be
    # missing from coverage.xml and leave the `scripts` floor untouched.
    assert load_pyproject()["tool"]["coverage"]["report"]["include_namespace_packages"] is True


def test_there_is_no_separate_ruff_config() -> None:
    # Ruff reads pyproject.toml; a ruff.toml would silently take precedence over it.
    assert not (ROOT / "ruff.toml").exists()
    assert not (ROOT / ".ruff.toml").exists()
