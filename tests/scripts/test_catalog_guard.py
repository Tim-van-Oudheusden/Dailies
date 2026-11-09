import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "catalog_guard.py"
CATALOG = "data/v1/games.json"
ICON = "data/v1/icons/flagle.png"
GIT = shutil.which("git")


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("catalog_guard", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


catalog_guard = load_script()


def git(repo: Path, *args: str) -> None:
    assert GIT is not None, "the guard tests need git"
    subprocess.run([GIT, "-C", str(repo), *args], check=True, capture_output=True)  # noqa: S603 - test-controlled


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A checkout of main with the catalog and one icon, then the add job's change: a new game and its icon."""
    checkout = tmp_path / "checkout"
    (checkout / "data" / "v1" / "icons").mkdir(parents=True)
    (checkout / CATALOG).write_text('{"games": []}\n', encoding="utf-8")
    (checkout / "data" / "v1" / "icons" / "wordle.png").write_bytes(b"\x89PNG wordle")
    (checkout / "README.md").write_text("# Dailies\n", encoding="utf-8")
    git(checkout, "init", "-q")
    git(checkout, "add", ".")
    git(checkout, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "main")
    (checkout / CATALOG).write_text('{"games": [{"id": "flagle"}]}\n', encoding="utf-8")
    (checkout / ICON).write_bytes(b"\x89PNG flagle")
    return checkout


def errors(capsys: pytest.CaptureFixture[str]) -> list[str]:
    return [line for line in capsys.readouterr().out.splitlines() if line.startswith("::error::")]


def test_a_new_game_and_its_icon_pass(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert catalog_guard.main(["--repo", str(repo)]) == 0

    assert errors(capsys) == []


def test_an_unchanged_checkout_passes(repo: Path) -> None:
    git(repo, "checkout", "--", CATALOG)
    (repo / ICON).unlink()

    assert catalog_guard.main(["--repo", str(repo)]) == 0


@pytest.mark.parametrize(
    "path", ["README.md", "data/v1/popularity.json", "data/v1/games.json.bak", "scripts/add_game.py", "icons/x.png"]
)
def test_any_other_written_file_fails(path: str, repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text("changed\n", encoding="utf-8")

    assert catalog_guard.main(["--repo", str(repo)]) == 1

    assert errors(capsys) == [f"::error::Unexpected change: {path}"]


def test_a_staged_rename_out_of_the_icons_reports_the_new_path(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    git(repo, "mv", "data/v1/icons/wordle.png", "wordle.png")

    assert catalog_guard.main(["--repo", str(repo)]) == 1

    assert errors(capsys) == ["::error::Unexpected change: wordle.png"]


@pytest.mark.parametrize("target", ["../../../.git/config", "/etc/hostname", "missing.png"])
def test_a_symlinked_icon_fails(target: str, repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """pages.yml copies data/v1 with `cp -rL`, so a link would publish what it points to."""
    (repo / ICON).unlink()
    (repo / ICON).symlink_to(target)

    assert catalog_guard.main(["--repo", str(repo)]) == 1

    assert errors(capsys) == [f"::error::{ICON} is not a regular file"]


def test_a_symlinked_catalog_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / CATALOG).unlink()
    (repo / CATALOG).symlink_to("icons/wordle.png")

    assert catalog_guard.main(["--repo", str(repo)]) == 1

    assert errors(capsys) == [f"::error::{CATALOG} is not a regular file"]


def test_a_deleted_catalog_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / CATALOG).unlink()

    assert catalog_guard.main(["--repo", str(repo)]) == 1

    assert errors(capsys) == [f"::error::{CATALOG} is not a regular file"]


def test_an_icon_replaced_by_a_directory_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """git lists the files inside as new icons, and the old icon path as deleted, but it is not a deleted icon."""
    icon = repo / "data" / "v1" / "icons" / "wordle.png"
    icon.unlink()
    icon.mkdir()
    (icon / "inner.png").write_bytes(b"\x89PNG inner")

    assert catalog_guard.main(["--repo", str(repo)]) == 1

    assert errors(capsys) == ["::error::data/v1/icons/wordle.png is not a regular file"]


def test_a_deleted_icon_passes(repo: Path) -> None:
    (repo / "data" / "v1" / "icons" / "wordle.png").unlink()

    assert catalog_guard.main(["--repo", str(repo)]) == 0


def test_a_checkout_without_git_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert catalog_guard.main(["--repo", str(tmp_path)]) == 1

    [error] = errors(capsys)
    assert error.startswith("::error::catalog guard failed:")


def test_runs_as_the_workflow_runs_it(repo: Path, tmp_path: Path) -> None:
    """`python3 -I "$RUNNER_TEMP/trusted/catalog_guard.py"` from the checkout, with report_guard.py copied next to it
    under popularity/: report_guard is found without the script's directory on sys.path."""
    trusted = tmp_path / "trusted"
    (trusted / "popularity").mkdir(parents=True)
    shutil.copy(SCRIPT, trusted)
    shutil.copy(ROOT / "scripts" / "popularity" / "report_guard.py", trusted / "popularity")
    result = subprocess.run(  # noqa: S603 - test-controlled
        [sys.executable, "-I", str(trusted / "catalog_guard.py")], cwd=repo, check=False, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stdout + result.stderr
