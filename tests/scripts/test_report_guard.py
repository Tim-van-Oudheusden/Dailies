import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "popularity" / "report_guard.py"
WEEK = "2026-W43"
REPORT = f"docs/popularity/{WEEK}.md"
GIT = shutil.which("git")


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("report_guard", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report_guard = load_script()


def git(repo: Path, *args: str) -> None:
    assert GIT is not None, "the guard tests need git"
    subprocess.run([GIT, "-C", str(repo), *args], check=True, capture_output=True)  # noqa: S603 - test-controlled


def popularity_text(week: str = WEEK, score: float = 0.9) -> str:
    document = {"week": week, "popular": [{"id": "wordle", "rank": 1, "score": score}], "schema_version": 1}
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A checkout of main with last week's shelves, the catalog and the reports index, plus the compute artifact."""
    checkout = tmp_path / "checkout"
    (checkout / "data" / "v1").mkdir(parents=True)
    (checkout / "docs" / "popularity").mkdir(parents=True)
    (checkout / "data" / "v1" / "popularity.json").write_text(popularity_text("2026-W42", 0.8), encoding="utf-8")
    (checkout / "data" / "v1" / "games.json").write_text('{"games": []}\n', encoding="utf-8")
    (checkout / "docs" / "popularity" / "README.md").write_text("# Reports\n", encoding="utf-8")
    git(checkout, "init", "-q")
    git(checkout, "add", ".")
    git(checkout, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "main")
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / "popularity.json").write_text(popularity_text(), encoding="utf-8")
    (checkout / "data" / "v1" / "popularity.json").write_text(popularity_text(), encoding="utf-8")
    (tmp_path / "git-config").write_bytes((checkout / ".git" / "config").read_bytes())
    return checkout


def run(repo: Path) -> int:
    reference = repo.parent / "reference" / "popularity.json"
    git_config = repo.parent / "git-config"
    return report_guard.main(
        ["--repo", str(repo), "--week", WEEK, "--reference", str(reference), "--git-config", str(git_config)]
    )


def errors(capsys: pytest.CaptureFixture[str]) -> list[str]:
    return [line for line in capsys.readouterr().out.splitlines() if line.startswith("::error::")]


def test_new_shelves_without_a_report_pass_unchanged(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(repo) == 0

    assert errors(capsys) == []
    assert (repo / "data" / "v1" / "popularity.json").read_text(encoding="utf-8") == popularity_text()


def test_the_weeks_report_passes_and_is_linked(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / REPORT).write_text("# Week 2026-W43\n", encoding="utf-8")

    assert run(repo) == 0

    assert errors(capsys) == []
    linked = json.loads((repo / "data" / "v1" / "popularity.json").read_text(encoding="utf-8"))
    assert linked["report"] == f"../popularity/{WEEK}.md"
    assert {key: value for key, value in linked.items() if key != "report"} == json.loads(popularity_text())


def test_the_link_keeps_the_stable_json_format(repo: Path) -> None:
    (repo / REPORT).write_text("# Week 2026-W43\n", encoding="utf-8")

    run(repo)

    text = (repo / "data" / "v1" / "popularity.json").read_text(encoding="utf-8")
    document = json.loads(text)
    assert text == json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def test_a_tampered_catalog_fails_the_job(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """What a prompt tampered to "edit games.json" leaves behind is caught, and nothing gets linked."""
    (repo / REPORT).write_text("# Week 2026-W43\n", encoding="utf-8")
    (repo / "data" / "v1" / "games.json").write_text('{"games": [{"id": "evil"}]}\n', encoding="utf-8")

    assert run(repo) == 1

    assert errors(capsys) == ["::error::Unexpected change outside the weekly report: data/v1/games.json"]
    assert "report" not in json.loads((repo / "data" / "v1" / "popularity.json").read_text(encoding="utf-8"))


def test_changed_numbers_fail_the_job(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "data" / "v1" / "popularity.json").write_text(popularity_text(score=1.0), encoding="utf-8")

    assert run(repo) == 1

    assert errors(capsys) == [
        "::error::data/v1/popularity.json is not byte-identical to the compute artifact; the numbers were changed"
    ]


@pytest.mark.parametrize(
    "path",
    [
        "docs/popularity/README.md",
        "docs/popularity/2026-W42.md",
        "docs/popularity/notes/2026-W43.md",
        "docs/other.md",
        "summary.json",
        "scripts/popularity/report_guard.py",
    ],
)
def test_any_other_written_file_fails_the_job(path: str, repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text("changed\n", encoding="utf-8")

    assert run(repo) == 1

    assert errors(capsys) == [f"::error::Unexpected change outside the weekly report: {path}"]


def test_a_deleted_file_fails_the_job(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "data" / "v1" / "games.json").unlink()

    assert run(repo) == 1

    assert errors(capsys) == ["::error::Unexpected change outside the weekly report: data/v1/games.json"]


@pytest.mark.parametrize("with_report", [False, True], ids=["no report", "with report"])
def test_deleted_shelves_fail_the_job(with_report: bool, repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """popularity.json is an allowed path, but deleting it must not pass: the publish PR would delete the shelves."""
    (repo / "data" / "v1" / "popularity.json").unlink()
    if with_report:
        (repo / REPORT).write_text("# Week 2026-W43\n", encoding="utf-8")

    assert run(repo) == 1

    [error] = errors(capsys)
    assert error.startswith("::error::report guard failed:")
    assert "popularity.json" in error
    assert not (repo / "data" / "v1" / "popularity.json").exists()


def test_a_staged_rename_reports_both_paths(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    git(repo, "mv", "data/v1/games.json", REPORT)

    assert run(repo) == 1

    assert errors(capsys) == ["::error::Unexpected change outside the weekly report: data/v1/games.json"]


def test_a_symlinked_report_fails_the_job(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / REPORT).symlink_to(repo / "data" / "v1" / "games.json")

    assert run(repo) == 1

    assert errors(capsys) == [f"::error::{REPORT} is not a regular file"]


def test_a_changed_git_config_fails_before_git_runs(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A config written by the model could make `git status` run a command (core.fsmonitor)."""
    marker = repo.parent / "ran"
    with (repo / ".git" / "config").open("a", encoding="utf-8") as config:
        config.write(f"[core]\n\tfsmonitor = touch {marker}\n")

    assert run(repo) == 1

    assert errors(capsys) == ["::error::.git/config changed while the report was written"]
    assert not marker.exists()


def test_a_malformed_week_is_a_usage_error(repo: Path) -> None:
    reference = repo.parent / "reference" / "popularity.json"

    assert report_guard.main(["--repo", str(repo), "--week", "../../x", "--reference", str(reference)]) == 2
