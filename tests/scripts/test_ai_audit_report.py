import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ai-audit-report.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("jq") is None, reason="needs bash and jq")

HIVE_SIGNATURE = "— hive: agent=quality backend=claude model=claude-opus-5-5 effort=high"


def pr(number: int, **fields: str | None) -> dict:
    """One entry of `gh pr list --json number,title,author,headRefName,mergedAt,mergedBy,body`.

    Keyword overrides: branch, merged_at, author, merged_by, body, title.
    """
    merged_at = fields.get("merged_at", "2026-10-10T12:00:00Z")
    merged_by = fields.get("merged_by", "Tim-van-Oudheusden")
    return {
        "number": number,
        "title": fields.get("title") or f"PR {number}",
        "author": {"login": fields.get("author", "Tim-van-Oudheusden")},
        "headRefName": fields.get("branch", "fix/1-change"),
        "mergedAt": merged_at,
        "mergedBy": None if merged_by is None else {"login": merged_by},
        "body": fields.get("body", "Fixes #1"),
    }


def report(prs: list[dict] | str, *args: str) -> subprocess.CompletedProcess[str]:
    stdin = prs if isinstance(prs, str) else json.dumps(prs)
    return subprocess.run(  # noqa: S603 - fixed script, test-controlled arguments
        [BASH, str(SCRIPT), *(args or ("--since", "2026-10-01"))],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def rows(result: subprocess.CompletedProcess[str], heading: str) -> list[str]:
    """The table rows (header and divider dropped) under the `## <heading>` section."""
    lines = result.stdout.splitlines()
    section = lines[lines.index(f"## {heading}") + 1 :]
    table = []
    for line in section:
        if line.startswith("## "):
            break
        if line.startswith("|"):
            table.append(line)
    return table[2:]


def test_attributes_each_merged_pr_oldest_merge_first() -> None:
    prs = [
        pr(
            4,
            branch="quality/test-gap",
            merged_at="2026-10-04T09:30:00Z",
            author="app/hive-forge-app",
            body=f"Adds a test.\n\n{HIVE_SIGNATURE}\n",
        ),
        pr(2, branch="claude/issue-1-fix", merged_at="2026-10-02T08:00:00Z", merged_by="app/github-actions"),
        pr(
            3,
            branch="dependabot/github_actions/github-actions-abc",
            merged_at="2026-10-03T07:15:00Z",
            author="app/dependabot",
            body="Bumps the github-actions group.",
        ),
        # A local agent run signs without agent=; a body edited in the web UI has CRLF line ends that must not
        # stick to the last field.
        pr(
            5,
            merged_at="2026-10-05T10:00:00Z",
            body="Closes #1\r\n\r\n— hive: backend=omp model=anthropic/claude-opus-5-5\r\n",
        ),
        pr(6, branch="data/popularity", merged_at="2026-10-06T11:00:00Z", author="app/github-actions"),
    ]

    result = report(prs)

    assert result.returncode == 0, result.stderr
    assert rows(result, "Ledger") == [
        (
            "| #2 | 2026-10-02 08:00 | Claude Code (CI) | — | — | Tim-van-Oudheusden | app/github-actions"
            " | `claude/issue-1-fix` | PR 2 |"
        ),
        (
            "| #3 | 2026-10-03 07:15 | Dependabot | — | — | app/dependabot | Tim-van-Oudheusden"
            " | `dependabot/github_actions/github-actions-abc` | PR 3 |"
        ),
        (
            "| #4 | 2026-10-04 09:30 | Hive | quality | claude-opus-5-5 | app/hive-forge-app | Tim-van-Oudheusden"
            " | `quality/test-gap` | PR 4 |"
        ),
        (
            "| #5 | 2026-10-05 10:00 | Hive | — | anthropic/claude-opus-5-5 | Tim-van-Oudheusden | Tim-van-Oudheusden"
            " | `fix/1-change` | PR 5 |"
        ),
        (
            "| #6 | 2026-10-06 11:00 | Other | — | — | app/github-actions | Tim-van-Oudheusden"
            " | `data/popularity` | PR 6 |"
        ),
    ]


def test_hive_signature_outranks_the_head_branch() -> None:
    result = report([pr(7, branch="claude/issue-7", body="— hive: agent=scanner model=claude-sonnet-5")])

    (row,) = rows(result, "Ledger")
    assert row.startswith("| #7 | 2026-10-10 12:00 | Hive | scanner | claude-sonnet-5 |"), row


def test_hive_forge_app_is_hive_even_without_a_signature() -> None:
    # gh reports a GitHub App author as app/<slug>; the REST API as <slug>[bot].
    result = report(
        [
            pr(8, branch="claude/issue-8", author="app/hive-forge-app", body="No signature."),
            pr(9, author="hive-forge-app[bot]", body=""),
        ]
    )

    sources = [row.split(" | ")[2:5] for row in rows(result, "Ledger")]
    assert sources == [["Hive", "—", "—"], ["Hive", "—", "—"]]


def test_counts_per_source_and_merger_leaving_out_merges_before_the_window() -> None:
    result = report(
        [
            pr(1, merged_at="2026-09-30T23:59:59Z", body="— hive: agent=scanner"),
            pr(2, merged_at="2026-10-01T00:00:00Z", body="— hive: agent=scanner"),
            pr(3, body="— hive: agent=quality", merged_by="app/github-actions"),
            pr(4, branch="dependabot/pip/x", merged_by=None),
            pr(5, merged_by="app/github-actions"),
            pr(6, merged_by="app/github-actions"),
            # Closed without merging: not part of the audit trail.
            pr(7, merged_at=None),
        ]
    )

    assert rows(result, "By source") == [
        "| Hive | 2 |",
        "| Claude Code (CI) | 0 |",
        "| Dependabot | 1 |",
        "| Other | 2 |",
        "| **All** | 5 |",
    ]
    assert rows(result, "Merged by") == [
        "| app/github-actions | 3 |",
        "| Tim-van-Oudheusden | 1 |",
        "| Unknown (no merger recorded) | 1 |",
    ]
    assert [row.split(" | ")[0] for row in rows(result, "Ledger")] == ["| #2", "| #3", "| #4", "| #5", "| #6"]


def test_states_the_reporting_window() -> None:
    assert "Pull requests merged into `main` since 2026-10-01 (UTC)." in report([]).stdout


def test_escapes_pipes_so_a_title_cannot_add_table_columns() -> None:
    result = report([pr(10, title="fix(a|b): keep | out")])

    (row,) = rows(result, "Ledger")
    assert row.endswith("| fix(a\\|b): keep \\| out |"), row


def test_input_that_is_not_a_list_fails_without_output() -> None:
    result = report('{"number": 1}')

    assert result.returncode != 0
    assert result.stdout == ""
    assert "expected a JSON array of pull requests" in result.stderr


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--since"], id="since without a value"),
        pytest.param(["--since", "1 Oct"], id="malformed date"),
        pytest.param(["--days", "7"], id="unknown option"),
        pytest.param(["--since", "2026-10-01", "--days", "7"], id="extra option"),
    ],
)
def test_usage_errors(args: list[str]) -> None:
    result = report([], *args)

    assert result.returncode == 2
    assert "usage:" in result.stderr
