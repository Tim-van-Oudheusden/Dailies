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


def pr(number: int, branch: str | None, login: str | None, *, merged: bool, body: str | None = None) -> dict:
    """One entry of `gh pr list --json number,mergedAt,headRefName,author`, with `body` too when one is given."""
    entry = {
        "number": number,
        "mergedAt": MERGED if merged else None,
        "headRefName": branch,
        "author": None if login is None else {"login": login},
    }
    return entry if body is None else {**entry, "body": body}


def metrics(stdin: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed script, test-controlled arguments
        [BASH, str(SCRIPT), *args], input=stdin, capture_output=True, text=True, check=False, timeout=60
    )


def test_splits_agent_and_other_pull_requests() -> None:
    prs = [
        pr(1, "claude/12-search", "tim", merged=True),
        pr(2, "claude/13-popularity", "tim", merged=False),
        # The Hive bot counts as an agent whatever its branch, as gh (app/) and the REST API ([bot]) name it, under
        # its current name and the one it had before the GitHub App was renamed.
        pr(3, "feat/14-tiles", "app/hive-forge-app", merged=True),
        pr(4, "fix/15-crash", "hive-forge-app[bot]", merged=True),
        pr(8, "quality/test-gap", "app/hive-worker-bee", merged=True),
        pr(9, "scanner/fix-pin", "hive-worker-bee[bot]", merged=False),
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
        "| Agent | 6 | 4 | 2 | 66.7% |\n"
        "| Other | 3 | 1 | 2 | 33.3% |\n"
        "| **All** | 9 | 5 | 4 | 55.6% |\n"
        "\n"
        "Agent: head branch `claude/*`, author `hive-worker-bee` (GitHub App, formerly `hive-forge-app`), "
        "or a Hive signature in the PR body.\n"
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


def test_a_branch_named_like_claude_without_the_slash_is_not_an_agent() -> None:
    result = metrics(
        json.dumps([pr(1, "claudette/1-x", "someone", merged=True)]), "--since", "2026-09-17", "--days", "7"
    )

    assert "| Agent | 0 | 0 | 0 | n/a |" in result.stdout
    assert "| Other | 1 | 1 | 0 | 100% |" in result.stdout


@pytest.mark.parametrize(
    "signature",
    [
        pytest.param("— hive: agent=quality backend=claude model=claude-opus-5-5 effort=high", id="hive"),
        pytest.param("— omp (Claude Code), model=claude-opus-5-5", id="omp"),
    ],
)
def test_a_signed_body_is_an_agent_on_any_branch_and_under_any_author(signature: str) -> None:
    # A contributor run opens its PR under the maintainer's account on a <type>/<N> branch; only the signature tells.
    prs = [pr(1, "test/1-x", "tim", merged=True, body=f"Fixes #1\n\n{signature}")]

    result = metrics(json.dumps(prs), "--since", "2026-09-17", "--days", "7")

    assert "| Agent | 1 | 1 | 0 | 100% |" in result.stdout
    assert "| Other | 0 | 0 | 0 | n/a |" in result.stdout


def test_a_body_without_a_signature_leaves_the_split_to_the_branch_and_author() -> None:
    prs = [pr(1, "feat/1-x", "tim", merged=True, body="Fixes #1"), pr(2, "feat/2-y", "tim", merged=True, body=None)]

    result = metrics(json.dumps(prs), "--since", "2026-09-17", "--days", "7")

    assert "| Agent | 0 | 0 | 0 | n/a |" in result.stdout
    assert "| Other | 2 | 2 | 0 | 100% |" in result.stdout


def test_a_dependabot_pull_request_is_not_agent_work() -> None:
    result = metrics(
        json.dumps([pr(1, "dependabot/pip/x", "dependabot[bot]", merged=True)]), "--since", "2026-09-17", "--days", "7"
    )

    assert "| Agent | 0 | 0 | 0 | n/a |" in result.stdout
    assert "| Other | 1 | 1 | 0 | 100% |" in result.stdout


def test_the_rate_is_rounded_to_the_nearest_tenth() -> None:
    prs = [pr(1, "claude/1-x", "tim", merged=True), pr(2, "claude/2-y", "tim", merged=True)]
    prs.append(pr(3, "claude/3-z", "tim", merged=False))

    result = metrics(json.dumps(prs), "--since", "2026-09-17", "--days", "7")

    # 2 of 3 is 66.666...%: rounded, not truncated to 66.6%.
    assert "| Agent | 3 | 2 | 1 | 66.7% |" in result.stdout


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
