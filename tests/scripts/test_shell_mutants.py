"""Hand mutants of the shell scripts, which neither pytest-cov nor a mutation tool measures (#331).

Each row changes one string in a script and names the test that must fail on the result. A mutant that survives marks a
branch that runs but that no assertion pins (#198, #329). When a hand mutation pass finds one, add the test that kills
it and a row here; see docs/testing.md "Shell mutants".
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GIT = shutil.which("git")
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    GIT is None or BASH is None or shutil.which("jq") is None, reason="needs git, bash and jq"
)


@dataclass(frozen=True)
class Mutant:
    """`old` in `script` replaced by `new`: the test `killed_by` must fail on the result."""

    name: str
    script: str
    old: str
    new: str
    killed_by: str


POPULARITY_REPORT = "scripts/popularity-report.sh"
POPULARITY_REPORT_TESTS = "tests/scripts/test_popularity_report.py"
NIGHTLY_COMPLIANCE = "scripts/nightly-compliance.sh"
NIGHTLY_COMPLIANCE_TESTS = "tests/scripts/test_nightly_compliance.py"
MERGE_QUEUE = "scripts/merge-queue.sh"
MERGE_QUEUE_TESTS = "tests/scripts/test_merge_queue.py"

MUTANTS = [
    Mutant(
        "a timed_out, startup_failure or action_required run does not count as succeeded (#198)",
        POPULARITY_REPORT,
        '.conclusion == "success"',
        '.conclusion != "failure"',
        f"{POPULARITY_REPORT_TESTS}::test_a_finished_run_that_did_not_succeed_counts_against_the_rate",
    ),
    Mutant(
        "a valid_until in another form fails instead of being compared as text (#198)",
        POPULARITY_REPORT,
        "NF == 2 && utc($1) && utc($2)",
        "NF == 2 && utc($1)",
        f"{POPULARITY_REPORT_TESTS}::test_a_timestamp_it_cannot_compare_fails",
    ),
    Mutant(
        "--runs with no value is a usage error (#198)",
        POPULARITY_REPORT,
        '--runs) [ "$#" -ge 2 ] || usage; ',
        "--runs) ",
        f"{POPULARITY_REPORT_TESTS}::test_usage_errors",
    ),
    Mutant(
        "--prs with no value is a usage error (#198)",
        POPULARITY_REPORT,
        '--prs) [ "$#" -ge 2 ] || usage; ',
        "--prs) ",
        f"{POPULARITY_REPORT_TESTS}::test_usage_errors",
    ),
    Mutant(
        "--weeks with no value is a usage error (#191)",
        POPULARITY_REPORT,
        '--weeks) [ "$#" -ge 2 ] || usage; ',
        "--weeks) ",
        f"{POPULARITY_REPORT_TESTS}::test_usage_errors",
    ),
    Mutant(
        "a links check error after the links were checked shows their report (#331)",
        NIGHTLY_COMPLIANCE,
        '    if [ -s "$links_md" ]; then\n      details+=',
        "    if false; then\n      details+=",
        f"{NIGHTLY_COMPLIANCE_TESTS}::test_a_links_check_error_with_a_report_puts_the_report_under_failures",
    ),
    Mutant(
        "a links check error puts its report under Failures, not Warnings (#331)",
        NIGHTLY_COMPLIANCE,
        'details+="$(cat "$links_md")"',
        'warnings+="$(cat "$links_md")"',
        f"{NIGHTLY_COMPLIANCE_TESTS}::test_a_links_check_error_with_a_report_puts_the_report_under_failures",
    ),
    Mutant(
        "the queue asks again while GitHub answers UNKNOWN for the merge state",
        MERGE_QUEUE,
        '[ "$state" != UNKNOWN ] && break',
        "break",
        f"{MERGE_QUEUE_TESTS}::test_next_asks_again_while_github_is_still_computing_the_merge_state",
    ),
    Mutant(
        "the queue stops asking for the merge state after three answers",
        MERGE_QUEUE,
        "for attempt in 1 2 3; do",
        "for attempt in 1 2 3 4; do",
        f"{MERGE_QUEUE_TESTS}::test_next_gives_up_on_a_merge_state_still_unknown_after_three_asks",
    ),
    Mutant(
        "the queue rates a pull request from the merge base, as tier-classifier.yml does",
        MERGE_QUEUE,
        '"HEAD...$1"',
        '"HEAD..$1"',
        f"{MERGE_QUEUE_TESTS}::test_next_rates_only_the_pull_requests_own_changes_when_main_moved_since_it_branched",
    ),
    Mutant(
        "a linked issue the queue could not close is named in a warning",
        MERGE_QUEUE,
        '|| echo "::warning title=Merge queue::could not close',
        '|| true "::warning title=Merge queue::could not close',
        f"{MERGE_QUEUE_TESTS}::test_land_still_starts_main_push_workflows_and_the_next_run_when_closing_an_issue_fails",
    ),
]


def copy_repo(dest: Path) -> Path:
    """Copies the files git sees (tracked, and untracked but not ignored) to `dest`, so the mutant never touches ROOT.

    The tests find their script relative to their own file, so the copied test runs the copied script.
    """
    assert GIT is not None
    listed = subprocess.run(  # noqa: S603 - fixed git command, no user input
        [GIT, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    for name in filter(None, listed.decode().split("\0")):
        source = ROOT / name
        if not source.is_file():  # tracked but deleted in the working tree
            continue
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return dest


def run_pytest(repo: Path, node: str, basetemp: Path) -> subprocess.CompletedProcess[str]:
    """Runs one test node in `repo` with its own temporary directory and none of the outer run's pytest or coverage
    settings."""
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith(("PYTEST_", "COV_CORE_", "COVERAGE_"))
    }
    return subprocess.run(  # noqa: S603 - this interpreter, node ids from the table above
        [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", f"--basetemp={basetemp}", node],
        cwd=repo,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


# Without this control, a harness that cannot run the copied test at all (a node id that names no test, a test that
# needs something the copy lacks) would count every mutant as killed.
@pytest.mark.parametrize("node", sorted({mutant.killed_by for mutant in MUTANTS}))
def test_the_killing_test_passes_on_an_unmutated_copy(tmp_path: Path, node: str) -> None:
    repo = copy_repo(tmp_path / "repo")

    result = run_pytest(repo, node, tmp_path / "basetemp")

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("mutant", MUTANTS, ids=[mutant.name for mutant in MUTANTS])
def test_the_mutant_is_killed(tmp_path: Path, mutant: Mutant) -> None:
    source = (ROOT / mutant.script).read_text(encoding="utf-8")
    # A row the script has moved away from must fail here, not pass by mutating nothing.
    assert source.count(mutant.old) == 1, f"{mutant.old!r} must occur exactly once in {mutant.script}"
    repo = copy_repo(tmp_path / "repo")
    (repo / mutant.script).write_text(source.replace(mutant.old, mutant.new), encoding="utf-8")

    result = run_pytest(repo, mutant.killed_by, tmp_path / "basetemp")

    # Exit 1 is "tests failed"; 2-5 (interrupted, internal error, usage error, nothing collected) are not a kill.
    assert result.returncode == 1, f"the mutant survived {mutant.killed_by}:\n{result.stdout}{result.stderr}"
