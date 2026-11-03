import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "strategy-report.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("jq") is None, reason="needs bash and jq")


def issue(
    number: int,
    *,
    title: str | None = None,
    labels: tuple[str, ...] = (),
    created: str = "2026-09-01T12:00:00Z",
    closed: str | None = None,
) -> dict:
    """One entry of `gh issue list --json number,title,state,labels,createdAt,closedAt`."""
    return {
        "number": number,
        "title": title or f"Issue {number}",
        "state": "OPEN" if closed is None else "CLOSED",
        "labels": [{"name": name} for name in labels],
        "createdAt": created,
        "closedAt": closed,
    }


def report(tmp_path: Path, issues: object, merged_at: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    issues_file = tmp_path / "issues.json"
    issues_file.write_text(json.dumps(issues))
    prs_file = tmp_path / "prs.json"
    prs_file.write_text(json.dumps([{"mergedAt": at} for at in merged_at or []]))
    return run("--since", "2026-10-01", "--issues", str(issues_file), "--prs", str(prs_file))


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed script, test-controlled arguments
        [BASH, str(SCRIPT), *args], capture_output=True, text=True, check=False, timeout=60
    )


def rows(result: subprocess.CompletedProcess[str], heading: str) -> list[str]:
    """The table rows, header and divider dropped, under the `## <heading>` section."""
    section = result.stdout.partition(f"\n## {heading}\n")[2].partition("\n## ")[0]
    return [line for line in section.splitlines() if line.startswith("|")][2:]


def test_counts_flow_from_the_start_of_the_window_on(tmp_path: Path) -> None:
    issues = [
        issue(1, created="2026-09-30T23:59:59Z"),
        issue(2, created="2026-10-01T00:00:00Z"),
        issue(3, created="2026-10-12T08:00:00Z", closed="2026-10-13T08:00:00Z"),
        issue(4, closed="2026-09-30T10:00:00Z"),
        issue(5, closed="2026-10-02T10:00:00Z"),
        issue(6, created="2026-10-20T08:00:00Z"),
    ]
    merged = ["2026-09-29T10:00:00Z", "2026-10-01T00:00:00Z", "2026-10-15T10:00:00Z"]

    result = report(tmp_path, issues, merged)

    assert result.returncode == 0, result.stderr
    assert rows(result, "Flow") == [
        "| Issues opened | 3 |",
        "| Issues closed | 2 |",
        "| Net backlog change | +1 |",
        "| PRs merged | 2 |",
        "| Open issues now | 3 |",
    ]


def test_signs_a_shrinking_backlog_negative_and_an_unchanged_one_zero(tmp_path: Path) -> None:
    shrinking = report(tmp_path, [issue(1, closed="2026-10-02T10:00:00Z")])
    unchanged = report(tmp_path, [issue(1)])

    assert "| Net backlog change | -1 |" in rows(shrinking, "Flow")
    assert "| Net backlog change | 0 |" in rows(unchanged, "Flow")


def test_counts_open_issues_per_stage_in_pipeline_order_with_unstaged_last(tmp_path: Path) -> None:
    issues = [
        issue(1, labels=("bug", "stage/045-needs-decision")),
        issue(2, labels=("stage/010-actionable",)),
        issue(3, labels=("stage/045-needs-decision",)),
        issue(4, labels=("enhancement",)),
        issue(5, labels=("stage/100-merge-queue",), closed="2026-10-02T10:00:00Z"),
    ]

    result = report(tmp_path, issues)

    assert rows(result, "Backlog by stage") == [
        "| stage/010-actionable | 1 |",
        "| stage/045-needs-decision | 2 |",
        "| No stage | 1 |",
    ]


def test_counts_open_issues_per_milestone_with_unplanned_last(tmp_path: Path) -> None:
    issues = [
        issue(1, labels=("milestone::M3", "ci")),
        issue(2, labels=("milestone::M1",)),
        issue(3, labels=("milestone::M3",)),
        issue(4, labels=("ci",)),
        issue(5, labels=("milestone::M1",), closed="2026-10-02T10:00:00Z"),
    ]

    result = report(tmp_path, issues)

    assert rows(result, "Backlog by milestone") == [
        "| milestone::M1 | 1 |",
        "| milestone::M3 | 2 |",
        "| No milestone | 1 |",
    ]


def test_tallies_acmm_gap_issues_per_level_and_names_the_open_ones(tmp_path: Path) -> None:
    acmm = ("acmm",)
    issues = [
        # The dashboard prefixes its titles with `[dashboard]`; the evaluation's own come bare.
        issue(13, title="[dashboard] [ACMM L6] Add Auto issue generation", labels=acmm),
        issue(12, title="[ACMM L4] Add Nightly compliance", labels=acmm, closed="2026-09-03T21:00:00Z"),
        issue(11, title="[ACMM L6] Add Merge queue", labels=acmm, closed="2026-10-29T19:00:00Z"),
        issue(10, title="[ACMM L6] Add Strategic dashboard | pipes", labels=acmm),
        issue(9, title="[ACMM L10] Add Something later", labels=acmm),
        issue(14, title="[ACMM L6] Not filed by the evaluation"),
        issue(15, title="Unrelated acmm issue", labels=acmm),
    ]

    result = report(tmp_path, issues)

    assert result.returncode == 0, result.stderr
    assert rows(result, "ACMM progress") == [
        "| L4 | 1 | 0 | — |",
        "| L6 | 1 | 2 | #10 Strategic dashboard \\| pipes, #13 Auto issue generation |",
        "| L10 | 0 | 1 | #9 Something later |",
    ]


def test_counts_an_acmm_gap_whose_title_leaves_out_add(tmp_path: Path) -> None:
    result = report(tmp_path, [issue(1, title="[ACMM L2] Coverage floors", labels=("acmm",))])

    assert rows(result, "ACMM progress") == ["| L2 | 0 | 1 | #1 Coverage floors |"]


def test_states_the_reporting_window(tmp_path: Path) -> None:
    assert "Since 2026-10-01." in report(tmp_path, []).stdout


def test_fails_naming_the_input_it_cannot_read(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    prs = tmp_path / "prs.json"
    prs.write_text("[]")

    result = run("--since", "2026-10-01", "--issues", str(missing), "--prs", str(prs))

    assert result.returncode == 1
    assert str(missing) in result.stderr
    assert result.stdout == ""


def test_fails_on_input_that_is_not_a_list(tmp_path: Path) -> None:
    result = report(tmp_path, {"not": "a list"})

    assert result.returncode != 0
    assert result.stdout == ""
    assert "expected a JSON array of issues" in result.stderr


@pytest.mark.parametrize(
    "args",
    [
        ["--since", "2026-10-01", "--issues", "a.json"],
        ["--since", "2026-10-01", "--prs", "b.json"],
        ["--issues", "a.json", "--prs", "b.json"],
        ["--issues", "a.json", "--prs"],
        ["--since", "2026-10-01", "--issues"],
        ["--since"],
        ["--bogus"],
        # Usage is checked before the inputs are read, so an unknown flag is not skipped over.
        ["--since", "2026-10-01", "--issues", "a.json", "--prs", "b.json", "--bogus"],
    ],
)
def test_rejects_missing_or_valueless_flags_with_a_usage_line(args: list[str]) -> None:
    result = run(*args)

    assert result.returncode == 2
    assert "usage:" in result.stderr
