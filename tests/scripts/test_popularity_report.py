import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "popularity-report.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("jq") is None, reason="needs bash and jq")


def run(conclusion: str) -> dict:
    """One entry of `gh run list --workflow popularity.yml --json conclusion`."""
    return {"conclusion": conclusion}


def pr(commits: int) -> dict:
    """One entry of `gh pr list --state merged --head data/popularity --json commits`."""
    return {"commits": [{"oid": f"{n:040x}"} for n in range(commits)]}


def week(generated_at: str, valid_until: str) -> str:
    return f"{generated_at}\t{valid_until}\n"


def report(tmp_path: Path, runs: object, prs: object, weeks: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "runs.json").write_text(json.dumps(runs))
    (tmp_path / "prs.json").write_text(json.dumps(prs))
    (tmp_path / "weeks.tsv").write_text(weeks)
    args = ["--runs", "runs.json", "--prs", "prs.json", "--weeks", "weeks.tsv"]
    return subprocess.run(  # noqa: S603 - fixed script, test-controlled arguments
        [BASH, str(SCRIPT), *args], cwd=tmp_path, capture_output=True, text=True, check=False, timeout=60
    )


def test_reports_runs_stale_weeks_and_edited_pull_requests(tmp_path: Path) -> None:
    runs = [run("success"), run("failure"), run("success"), run("cancelled"), run("skipped"), run("")]
    prs = [pr(1), pr(1), pr(3)]
    weeks = (
        week("2026-10-05T04:30:00Z", "2026-10-15T04:30:00Z")
        # Generated before the previous file expired: on time.
        + week("2026-10-12T04:30:00Z", "2026-10-22T04:30:00Z")
        # A failed week: the next file came after 2026-10-22T04:30:00Z, so the shelves showed "as of".
        + week("2026-10-26T04:30:00Z", "2026-11-05T04:30:00Z")
    )

    result = report(tmp_path, runs, prs, weeks)

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "## Popularity report\n"
        "\n"
        "| Measure | Count | Rate |\n"
        "| --- | ---: | ---: |\n"
        "| Runs succeeded, of finished runs | 2 of 3 | 66.7% |\n"
        "| Stale weeks, of week-to-week handovers | 1 of 2 | 50% |\n"
        "| Data PRs merged unchanged, of merged | 2 of 3 | 66.7% |\n"
        "\n"
        "Cancelled and skipped runs are not counted. A stale week's shelves had expired before the next run replaced"
        " them. A\n"
        "merged data PR with more than its one workflow commit was edited by the maintainer.\n"
    )


def test_a_file_generated_exactly_at_expiry_is_not_stale(tmp_path: Path) -> None:
    weeks = week("2026-10-05T04:30:00Z", "2026-10-15T04:30:00Z") + week("2026-10-15T04:30:00Z", "2026-10-25T04:30:00Z")

    result = report(tmp_path, [], [], weeks)

    assert result.returncode == 0, result.stderr
    assert "| Stale weeks, of week-to-week handovers | 0 of 1 | 0% |" in result.stdout


def test_no_history_is_not_a_rate(tmp_path: Path) -> None:
    result = report(tmp_path, [], [], "")

    assert result.returncode == 0, result.stderr
    assert "| Runs succeeded, of finished runs | 0 of 0 | n/a |" in result.stdout
    assert "| Stale weeks, of week-to-week handovers | 0 of 0 | n/a |" in result.stdout
    assert "| Data PRs merged unchanged, of merged | 0 of 0 | n/a |" in result.stdout


def test_a_single_file_has_no_handover(tmp_path: Path) -> None:
    result = report(tmp_path, [run("success")], [pr(1)], week("2026-10-15T12:00:00Z", "2026-10-25T12:00:00Z"))

    assert result.returncode == 0, result.stderr
    assert "| Runs succeeded, of finished runs | 1 of 1 | 100% |" in result.stdout
    assert "| Stale weeks, of week-to-week handovers | 0 of 0 | n/a |" in result.stdout


@pytest.mark.parametrize(
    "line",
    [
        # String comparison orders only the one UTC form compute.py writes, so any other form must fail, not miscount.
        pytest.param("2026-10-15T12:00:00+00:00\t2026-10-25T12:00:00Z\n", id="offset"),
        pytest.param("2026-10-15T12:00:00.5Z\t2026-10-25T12:00:00Z\n", id="fractional seconds"),
        pytest.param("2026-10-15T12:00:00Z\n", id="no valid_until"),
        pytest.param("null\tnull\n", id="missing fields"),
    ],
)
def test_a_timestamp_it_cannot_compare_fails(tmp_path: Path, line: str) -> None:
    result = report(tmp_path, [], [], week("2026-10-05T04:30:00Z", "2026-10-15T04:30:00Z") + line)

    assert result.returncode == 1
    assert "--weeks line 2: expected generated_at<TAB>valid_until as YYYY-MM-DDTHH:MM:SSZ" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("runs", "prs", "message"),
    [
        pytest.param({"conclusion": "success"}, [], "--runs: expected a JSON array of workflow runs", id="runs"),
        pytest.param([], {"commits": []}, "--prs: expected a JSON array of pull requests", id="prs"),
    ],
)
def test_input_that_is_not_a_list_fails(tmp_path: Path, runs: object, prs: object, message: str) -> None:
    result = report(tmp_path, runs, prs, "")

    assert result.returncode != 0
    assert message in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    "args",
    [
        pytest.param([], id="no arguments"),
        pytest.param(["--runs", "runs.json", "--prs", "prs.json"], id="no weeks"),
        pytest.param(["--runs", "runs.json", "--weeks", "weeks.tsv"], id="no prs"),
        pytest.param(["--prs", "prs.json", "--weeks", "weeks.tsv"], id="no runs"),
        pytest.param(["--runs", "runs.json", "--prs", "prs.json", "--weeks", "weeks.tsv", "--repo", "x"], id="unknown"),
        # `shift 2` with one argument left shifts nothing, so an unguarded parser loops on the same flag forever.
        pytest.param(["--runs", "runs.json", "--prs", "prs.json", "--weeks"], id="weeks without a value"),
    ],
)
def test_usage_errors(tmp_path: Path, args: list[str]) -> None:
    result = subprocess.run(  # noqa: S603 - fixed script, test-controlled arguments
        [BASH, str(SCRIPT), *args], cwd=tmp_path, capture_output=True, text=True, check=False, timeout=60
    )

    assert result.returncode == 2
    assert "--runs FILE --prs FILE --weeks FILE" in result.stderr
