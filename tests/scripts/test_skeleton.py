from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_scripts_tests_run_from_the_repository_root() -> None:
    # Placeholder until the first script lands; script tests locate files relative to the repository root.
    assert (ROOT / "pyproject.toml").is_file()
