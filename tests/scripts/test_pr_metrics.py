import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pr-metrics.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("jq") is None, reason="needs bash and jq")

MERGED = "2026-10-01T12:00:00Z"


def pr(number: int, branch: str | None, login: str | None, *, merged: bool) -> dict:
    """One entry of `gh pr list --json number,mergedAt,headRefName,author`."""
    return {
        "number": number,
        "mergedAt": MERGED if merged else None,
        "headRefName": branch,
        "author": None if login is None else {"login": login},
    }


def metrics(stdin: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed script, test-controlled arguments
        [BASH, str(SCRIPT), *args], input=stdin, capture_output=True, text=True, check=False, timeout=60
    )


def test_splits_agent_and_other_pull_requests() -> None:
    prs = [
        pr(1, "claude/12-search", "tim", merged=True),
        pr(2, "claude/13-popularity", "tim", merged=False),
        # The hive-forge bot counts as an agent whatever its branch, as gh (app/) and the REST API ([bot]) name it.
        pr(3, "feat/14-tiles", "app/hive-forge-app", merged=True),
        pr(4, "fix/15-crash", "hive-forge-app[bot]", merged=True),
        pr(5, "feat/16-icons", "tim", merged=True),
        pr(6, "feat/claude/17-not-an-agent-branch", "someone", merged=False),
        pr(7, None, None, merged=False),
    ]

    result = metrics(json.dumps(prs), "--since", "2026-09-17", "--days", "28")

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "## PR acceptance metric\n"
        "\n"
        "PRs closed since 2026-09-17 (last 28 days).\n"
        "\n"
        "| Source | Closed | Merged | Rejected | Acceptance |\n"
        "| --- | ---: | ---: | ---: | ---: |\n"
        "| Agent | 4 | 3 | 1 | 75% |\n"
        "| Other | 3 | 1 | 2 | 33.3% |\n"
        "| **All** | 7 | 4 | 3 | 57.1% |\n"
        "\n"
        "Agent: head branch `claude/*` or author `hive-forge-app` (GitHub App).\n"
    )


def test_no_closed_pull_requests_is_not_a_rate() -> None:
    result = metrics("[]", "--since", "2026-09-17", "--days", "28")

    assert result.returncode == 0, result.stderr
    assert "| Agent | 0 | 0 | 0 | n/a |" in result.stdout
    assert "| **All** | 0 | 0 | 0 | n/a |" in result.stdout


def test_all_merged_is_a_full_rate() -> None:
    result = metrics(json.dumps([pr(1, "claude/1-x", "tim", merged=True)]), "--since", "2026-09-17", "--days", "7")

    assert "PRs closed since 2026-09-17 (last 7 days)." in result.stdout
    assert "| Agent | 1 | 1 | 0 | 100% |" in result.stdout
    assert "| Other | 0 | 0 | 0 | n/a |" in result.stdout


def test_input_that_is_not_a_list_fails() -> None:
    result = metrics('{"number": 1}', "--since", "2026-09-17", "--days", "28")

    assert result.returncode != 0
    assert "expected a JSON array of pull requests" in result.stderr


@pytest.mark.parametrize(
    "args",
    [
        pytest.param([], id="no arguments"),
        pytest.param(["--since", "2026-09-17"], id="no days"),
        pytest.param(["--days", "28"], id="no since"),
        pytest.param(["--since", "2026-09-17", "--days", "28", "--repo", "x"], id="unknown option"),
        # `shift 2` with one argument left shifts nothing, so an unguarded parser loops on the same flag forever.
        pytest.param(["--days", "28", "--since"], id="since without a value"),
        pytest.param(["--since", "2026-09-17", "--days"], id="days without a value"),
    ],
)
def test_usage_errors(args: list[str]) -> None:
    result = metrics("[]", *args)

    assert result.returncode == 2
    assert "--since YYYY-MM-DD --days N" in result.stderr
