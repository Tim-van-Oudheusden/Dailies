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


def test_mutmut_mutates_the_core_and_runs_the_core_and_data_tests() -> None:
    mutmut = load_pyproject()["tool"]["mutmut"]
    assert mutmut["source_paths"] == ["dailies/core"]
    assert mutmut["pytest_add_cli_args_test_selection"] == ["tests/core", "tests/data"]


def test_mutmut_copies_what_the_selected_tests_read_from_outside_tests() -> None:
    # mutmut runs the tests inside mutants/, and `tests/` is the only tree it copies on its own. A file named here
    # rather than a directory would need its parent in mutants/ already, which only the repository root is sure of.
    also_copy = load_pyproject()["tool"]["mutmut"]["also_copy"]
    assert also_copy == ["README.md", "data", "scripts/data"]
    for path in also_copy:
        assert (ROOT / path).exists(), path
    assert (ROOT / "README.md").is_file()
    assert (ROOT / "data").is_dir()
    assert (ROOT / "scripts" / "data").is_dir()


def test_mutmut_deselects_a_test_that_exists() -> None:
    # A renamed test would no longer be deselected, and pytest accepts a --deselect that matches nothing.
    flag, node = load_pyproject()["tool"]["mutmut"]["pytest_add_cli_args"]
    path, _, name = node.partition("::")
    assert flag == "--deselect"
    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8")


def test_mutmut_does_not_fork_workers_from_the_process_that_ran_the_suite() -> None:
    # That process's lru_cache entries would answer for the code behind them, and its mutants would survive.
    assert load_pyproject()["tool"]["mutmut"]["process_isolation"] == "forkserver"


def test_there_is_no_separate_ruff_config() -> None:
    # Ruff reads pyproject.toml; a ruff.toml would silently take precedence over it.
    assert not (ROOT / "ruff.toml").exists()
    assert not (ROOT / ".ruff.toml").exists()
