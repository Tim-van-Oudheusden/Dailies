"""scripts/merge-queue.sh, run offline: a stub `gh` answers from a JSON file and records every other call, and the
pull requests are real commits in a throwaway origin repository whose `refs/pull/<n>/head` carry each head, as
GitHub's do."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "merge-queue.sh"
WORKFLOWS = ROOT / ".github" / "workflows"
BASH = shutil.which("bash")
GIT = shutil.which("git")

pytestmark = pytest.mark.skipif(
    BASH is None or shutil.which("jq") is None or shutil.which("git") is None, reason="needs bash, jq and git"
)

RUN_URL = "https://github.com/owner/dailies/actions/runs/42"
MAIN_FILES = {"README.md": "Dailies\n"}
# Medium risk (docs/risk-tiers.md): app code.
APP_CHANGE = {"dailies/core/search.py": "x = 1\n"}
# High risk: workflow files.
WORKFLOW_CHANGE = {"dailies/core/search.py": "x = 1\n", ".github/workflows/ci.yml": "name: CI\n"}

# Stands in for the gh CLI. `gh pr list` and `gh pr view <n>` answer from $FAKE_DIR/prs.json, filtered through `--jq`
# like gh does. Every other call is appended to $FAKE_DIR/calls.log, one line per call. A call fails when it starts
# with the text in $FAKE_DIR/fail, or only the first such call does if $FAKE_DIR/fail-once exists. While
# $FAKE_DIR/unknown-<n> holds a count above 0, asking for the merge state of pull request <n> answers UNKNOWN, as GitHub
# does before it has computed it, and takes one off the count.
FAKE_GH = r"""#!/usr/bin/env bash
set -euo pipefail
fails() {
  [ -f "$FAKE_DIR/fail" ] && [[ "$*" == "$(cat "$FAKE_DIR/fail")"* ]] || return 1
  [ ! -f "$FAKE_DIR/fail-once" ] || rm "$FAKE_DIR/fail"
}
if [ "$1" = pr ] && { [ "$2" = list ] || [ "$2" = view ]; }; then
  if fails "$@"; then
    echo "gh: HTTP 502" >&2
    exit 1
  fi
  sub="$2"
  shift 2
  number=""
  filter=.
  while [ $# -gt 0 ]; do
    case "$1" in
      --jq) filter="$2"; shift 2 ;;
      --*) shift 2 ;;
      *) number="$1"; shift ;;
    esac
  done
  countdown="$FAKE_DIR/unknown-$number"
  left="$(cat "$countdown" 2>/dev/null || echo 0)"
  if [ "$sub" = view ] && [ "$filter" = .mergeStateStatus ] && [ "$left" -gt 0 ]; then
    echo $((left - 1)) > "$countdown"
    echo UNKNOWN
  elif [ "$sub" = view ]; then
    jq -r --argjson n "$number" ".[] | select(.number == \$n) | $filter" "$FAKE_DIR/prs.json"
  else
    jq -r "$filter" "$FAKE_DIR/prs.json"
  fi
  exit 0
fi
echo "$*" >> "$FAKE_DIR/calls.log"
if fails "$@"; then
  exit 1
fi
"""

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed git binary, test-controlled arguments
        [GIT, *args], cwd=cwd, env={**os.environ, **GIT_ENV}, capture_output=True, text=True, check=True, timeout=60
    )
    return result.stdout.strip()


def commit_files(repo: Path, files: dict[str, str], message: str) -> str:
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(repo, "add", "--all")
    git(repo, "commit", "--quiet", "-m", message)
    return git(repo, "rev-parse", "HEAD")


class Queue:
    """An origin with main and one `refs/pull/<n>/head` per pull request, a clone of main, and the stub gh."""

    def __init__(self, work: Path, main_files: dict[str, str], pull_requests: list[dict]) -> None:
        self.work = work
        self.origin = work / "origin.git"
        self.seed = work / "seed"
        self.clone = work / "clone"
        git(work, "init", "--quiet", "--bare", "--initial-branch=main", str(self.origin))
        git(work, "init", "--quiet", "--initial-branch=main", str(self.seed))
        commit_files(self.seed, main_files, "main")
        git(self.seed, "push", "--quiet", str(self.origin), "main")
        heads = {}
        for pull_request in pull_requests:
            number = pull_request["number"]
            git(self.seed, "switch", "--quiet", "--create", f"pr-{number}", "main")
            files = pull_request.get("files", {f"dailies/core/pr_{number}.py": "x = 1\n"})
            heads[number] = commit_files(self.seed, files, "pr")
            git(self.seed, "push", "--quiet", str(self.origin), f"HEAD:refs/pull/{number}/head")
        git(work, "clone", "--quiet", str(self.origin), str(self.clone))
        self.heads = heads
        self.write_listing(pull_requests)

    def write_listing(self, pull_requests: list[dict]) -> None:
        listing = [
            {
                "number": pull_request["number"],
                "headRefOid": self.heads[pull_request["number"]],
                "isDraft": pull_request.get("isDraft", False),
                "isCrossRepository": pull_request.get("isCrossRepository", False),
                "labels": [{"name": name} for name in pull_request.get("labels", [])],
                "mergeStateStatus": pull_request.get("mergeStateStatus", "CLEAN"),
                "closingIssuesReferences": [
                    {"number": issue, "url": f"https://github.com/owner/dailies/issues/{issue}"}
                    for issue in pull_request.get("closingIssues", [])
                ],
            }
            for pull_request in pull_requests
        ]
        (self.work / "prs.json").write_text(json.dumps(listing), encoding="utf-8")

    @property
    def main(self) -> str:
        return git(self.clone, "rev-parse", "HEAD")

    def fail_calls_starting_with(self, prefix: str) -> None:
        (self.work / "fail").write_text(prefix, encoding="utf-8")

    def fail_first_call_starting_with(self, prefix: str) -> None:
        self.fail_calls_starting_with(prefix)
        (self.work / "fail-once").write_text("", encoding="utf-8")

    def answer_unknown_merge_state(self, number: int, times: int) -> None:
        """GitHub answers UNKNOWN for the merge state of <number> the next <times> asks."""
        (self.work / f"unknown-{number}").write_text(f"{times}\n", encoding="utf-8")

    def move_main(self) -> None:
        commit_files(self.seed, {"docs/other.md": "other\n"}, "other")
        git(self.seed, "push", "--quiet", str(self.origin), "HEAD:main")

    def sleeps(self) -> list[str]:
        """The seconds the last run asked `sleep` for, in order."""
        return (self.work / "sleeps.log").read_text(encoding="utf-8").splitlines()

    def run(self, *args: str) -> "Result":
        gh = self.work / "gh"
        gh.write_text(FAKE_GH, encoding="utf-8")
        gh.chmod(0o755)
        # The script waits between attempts; the tests only record how long.
        sleep = self.work / "sleep"
        sleep.write_text('#!/bin/sh\necho "$1" >> "$FAKE_DIR/sleeps.log"\n', encoding="utf-8")
        sleep.chmod(0o755)
        output = self.work / "github-output"
        output.write_text("", encoding="utf-8")
        (self.work / "calls.log").unlink(missing_ok=True)
        (self.work / "sleeps.log").write_text("", encoding="utf-8")
        result = subprocess.run(  # noqa: S603 - fixed script, test-controlled environment
            [BASH, str(SCRIPT), *args],
            cwd=self.clone,
            env={
                **os.environ,
                **GIT_ENV,
                "PATH": f"{self.work}{os.pathsep}{os.environ['PATH']}",
                "FAKE_DIR": str(self.work),
                "GITHUB_OUTPUT": str(output),
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        outputs = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines() if line)
        calls_path = self.work / "calls.log"
        calls = calls_path.read_text(encoding="utf-8").splitlines() if calls_path.exists() else []
        return Result(result.returncode, result.stdout, result.stderr, outputs, calls)


class Result:
    def __init__(self, status: int, stdout: str, stderr: str, outputs: dict[str, str], calls: list[str]) -> None:
        self.status = status
        self.stdout = stdout
        self.stderr = stderr
        self.outputs = outputs
        self.calls = calls


def queue_of(tmp_path: Path, pull_requests: list[dict], main_files: dict[str, str] | None = None) -> Queue:
    return Queue(tmp_path, main_files or MAIN_FILES, pull_requests)


def keep_out_labels() -> list[str]:
    """KEEP_OUT_LABELS in the script: every label that keeps a pull request out of the queue."""
    match = re.search(r"^KEEP_OUT_LABELS=\(([^)]*)\)", SCRIPT.read_text(encoding="utf-8"), re.MULTILINE)
    assert match, "scripts/merge-queue.sh has no KEEP_OUT_LABELS array"
    return match.group(1).split()


def main_push_workflows() -> list[str]:
    """The workflows GitHub starts on a push to main; a bare `push:` filters no branch, so it covers main too."""
    names = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        triggers = YAML(typ="safe", pure=True).load(path.read_text(encoding="utf-8"))["on"]
        if isinstance(triggers, dict) and "push" in triggers:
            branches = (triggers["push"] or {}).get("branches")
            if branches is None and "tags" in (triggers["push"] or {}):
                continue
            if branches is None or "main" in branches:
                names.append(path.name)
    return names


def merge_command(number: int, head: str) -> str:
    return f"pr merge {number} --merge --match-head-commit {head}"


# --- next ---------------------------------------------------------------------------------------------------------


def test_next_picks_the_oldest_same_repo_ready_pull_request_whose_required_checks_pass(tmp_path: Path) -> None:
    queue = queue_of(
        tmp_path,
        [
            {"number": 9},
            {"number": 3, "isDraft": True},
            {"number": 4, "isCrossRepository": True},
            {"number": 5, "labels": ["hold"]},
            {"number": 6, "mergeStateStatus": "BLOCKED"},
            {"number": 7, "labels": ["stage/100-merge-queue"]},
        ],
    )

    result = queue.run("next")

    assert result.status == 0, result.stderr
    assert result.outputs == {"number": "7", "head": queue.heads[7], "main": queue.main}


@pytest.mark.parametrize("label", keep_out_labels())
def test_next_leaves_a_pull_request_with_a_keep_out_label_and_picks_the_next_one(tmp_path: Path, label: str) -> None:
    queue = queue_of(tmp_path, [{"number": 2, "labels": [label]}, {"number": 8}])

    result = queue.run("next")

    assert result.status == 0, result.stderr
    assert result.outputs["number"] == "8"


def test_the_keep_out_labels_cover_the_ones_the_maintainer_uses_to_stop_a_merge() -> None:
    # `hold` first: reject adds it. `sentinel-alert` is Hive's flag on a sensitive change, `blocked` marks a pull
    # request waiting on something outside the repository, `automated` marks the pull requests workflows open, whose
    # merge policy is their own (#79): the popularity one merges itself, catalog and link-status ones a maintainer
    # merges.
    assert keep_out_labels() == ["hold", "blocked", "sentinel-alert", "automated"]


def test_next_leaves_a_high_risk_pull_request_for_the_maintainer_and_picks_the_next_one(tmp_path: Path) -> None:
    queue = queue_of(tmp_path, [{"number": 2, "files": WORKFLOW_CHANGE}, {"number": 8, "files": APP_CHANGE}])

    result = queue.run("next")

    assert result.status == 0, result.stderr
    assert result.outputs["number"] == "8"
    assert result.outputs["head"] == queue.heads[8]
    assert "#2 is high risk" in result.stdout


def test_next_rates_a_file_moved_out_of_a_high_risk_path_by_its_old_path(tmp_path: Path) -> None:
    # Moving a workflow out of .github/ still edits CI; git's rename detection would list only the new, medium path.
    queue = queue_of(tmp_path, [], {"scripts/release.sh": "#!/bin/sh\necho release\n"})
    git(queue.seed, "switch", "--quiet", "--create", "pr-5", "main")
    git(queue.seed, "mv", "scripts/release.sh", "release.sh")
    git(queue.seed, "commit", "--quiet", "-m", "move")
    queue.heads[5] = git(queue.seed, "rev-parse", "HEAD")
    git(queue.seed, "push", "--quiet", str(queue.origin), "HEAD:refs/pull/5/head")
    queue.write_listing([{"number": 5}])

    result = queue.run("next")

    assert result.status == 0, result.stderr
    assert result.outputs == {}


def test_next_rates_only_the_pull_requests_own_changes_when_main_moved_since_it_branched(tmp_path: Path) -> None:
    # A workflow change merged to main after the pull request branched is not part of the pull request:
    # tier-classifier.yml rates BASE...HEAD, from the merge base, and so does the queue.
    queue = queue_of(tmp_path, [{"number": 5, "files": APP_CHANGE}])
    git(queue.seed, "switch", "--quiet", "main")
    commit_files(queue.seed, {".github/workflows/ci.yml": "name: CI\n"}, "workflow")
    git(queue.seed, "push", "--quiet", str(queue.origin), "main")
    git(queue.clone, "pull", "--quiet")

    result = queue.run("next")

    assert result.status == 0, result.stderr
    assert result.outputs == {"number": "5", "head": queue.heads[5], "main": queue.main}


def test_next_asks_again_while_github_is_still_computing_the_merge_state(tmp_path: Path) -> None:
    # GitHub answers UNKNOWN until it has computed the merge state; taking the first answer would skip a ready pull
    # request until something starts the queue again.
    queue = queue_of(tmp_path, [{"number": 7}])
    queue.answer_unknown_merge_state(7, times=2)

    result = queue.run("next")

    assert result.status == 0, result.stderr
    assert result.outputs["number"] == "7"
    assert queue.sleeps() == ["5", "5"]


def test_next_gives_up_on_a_merge_state_still_unknown_after_three_asks(tmp_path: Path) -> None:
    queue = queue_of(tmp_path, [{"number": 7}])
    queue.answer_unknown_merge_state(7, times=3)

    result = queue.run("next")

    assert result.status == 0, result.stderr
    assert result.outputs == {}
    assert queue.sleeps() == ["5", "5"]


def test_next_picks_nothing_when_no_pull_request_is_ready(tmp_path: Path) -> None:
    result = queue_of(tmp_path, [{"number": 4, "mergeStateStatus": "BLOCKED"}]).run("next")

    assert result.status == 0, result.stderr
    assert result.outputs == {}
    assert result.calls == []


def test_next_picks_nothing_when_no_pull_request_is_open(tmp_path: Path) -> None:
    result = queue_of(tmp_path, []).run("next")

    assert result.status == 0, result.stderr
    assert result.outputs == {}


def test_next_skips_a_pull_request_pushed_to_since_it_was_listed(tmp_path: Path) -> None:
    queue = queue_of(tmp_path, [{"number": 4}, {"number": 5}])
    commit_files(queue.seed, {"dailies/core/more.py": "y = 2\n"}, "push")
    git(queue.seed, "push", "--quiet", "--force", str(queue.origin), "HEAD:refs/pull/4/head")

    result = queue.run("next")

    assert result.status == 0, result.stderr
    assert result.outputs["number"] == "5"


def test_next_fails_instead_of_reporting_an_empty_queue_when_listing_fails(tmp_path: Path) -> None:
    # An empty listing is an empty queue; a failed one must not pass for it.
    queue = queue_of(tmp_path, [{"number": 7}])
    queue.fail_calls_starting_with("pr list")

    result = queue.run("next")

    assert result.status != 0
    assert result.outputs == {}


# --- land ---------------------------------------------------------------------------------------------------------


def test_land_merges_the_verified_head_then_starts_each_main_push_workflow_and_the_next_run(tmp_path: Path) -> None:
    # A merge made with GITHUB_TOKEN starts no push workflow, so land starts every workflow that runs on a push to
    # main, or that gate never runs for queue merges.
    queue = queue_of(tmp_path, [{"number": 7}])

    result = queue.run("land", "7", queue.heads[7], queue.main)

    assert result.status == 0, result.stderr
    assert result.calls[0] == merge_command(7, queue.heads[7])
    assert result.calls[-1] == "workflow run merge-queue.yml --ref main"
    assert sorted(result.calls[1:-1]) == [f"workflow run {name} --ref main" for name in main_push_workflows()]


@pytest.mark.parametrize("name", main_push_workflows())
def test_every_main_push_workflow_can_be_started_by_hand(name: str) -> None:
    # `gh workflow run` fails on a workflow without a workflow_dispatch trigger.
    triggers = YAML(typ="safe", pure=True).load((WORKFLOWS / name).read_text(encoding="utf-8"))["on"]
    assert "workflow_dispatch" in triggers


def test_land_fails_and_closes_nothing_starts_nothing_when_the_merge_is_refused(tmp_path: Path) -> None:
    # A refused merge (the head moved, a token without write access) must not close the linked issues or start main's
    # push workflows and the next run as if it had landed.
    queue = queue_of(tmp_path, [{"number": 7, "closingIssues": [12]}])
    queue.fail_calls_starting_with("pr merge")

    result = queue.run("land", "7", queue.heads[7], queue.main)

    assert result.status != 0
    assert result.calls == [merge_command(7, queue.heads[7])]


def test_land_closes_every_issue_the_merged_pull_request_links_after_merging_it(tmp_path: Path) -> None:
    # GitHub does not close an issue linked with `Fixes #N` when GITHUB_TOKEN merges the pull request.
    queue = queue_of(tmp_path, [{"number": 7, "closingIssues": [12, 13]}])

    result = queue.run("land", "7", queue.heads[7], queue.main)
    closes = [call for call in result.calls if call.startswith("issue close ")]

    assert result.status == 0, result.stderr
    assert result.calls.index(closes[0]) > result.calls.index(merge_command(7, queue.heads[7]))
    assert len(closes) == 2
    assert closes[0].startswith("issue close https://github.com/owner/dailies/issues/12 --reason completed --comment ")
    assert closes[1].startswith("issue close https://github.com/owner/dailies/issues/13 --reason completed --comment ")
    assert "#7" in closes[0]


def test_land_still_starts_main_push_workflows_and_the_next_run_when_closing_an_issue_fails(tmp_path: Path) -> None:
    queue = queue_of(tmp_path, [{"number": 7, "closingIssues": [12, 13]}])
    queue.fail_calls_starting_with("issue close https://github.com/owner/dailies/issues/12")

    result = queue.run("land", "7", queue.heads[7], queue.main)
    runs = sorted(call for call in result.calls if call.startswith("workflow run "))

    assert result.status == 0, result.stderr
    assert len([call for call in result.calls if call.startswith("issue close ")]) == 2
    assert (
        "::warning title=Merge queue::could not close https://github.com/owner/dailies/issues/12 after merging #7"
        in result.stdout
    )
    assert runs == sorted(f"workflow run {name} --ref main" for name in [*main_push_workflows(), "merge-queue.yml"])


def test_land_warns_and_carries_on_when_reading_the_linked_issues_fails(tmp_path: Path) -> None:
    queue = queue_of(tmp_path, [{"number": 7, "closingIssues": [12]}])
    queue.fail_calls_starting_with("pr view 7 --json closingIssuesReferences")

    result = queue.run("land", "7", queue.heads[7], queue.main)
    runs = sorted(call for call in result.calls if call.startswith("workflow run "))

    assert result.status == 0, result.stderr
    assert "::warning title=Merge queue::" in result.stdout
    assert "#7" in result.stdout
    assert runs == sorted(f"workflow run {name} --ref main" for name in [*main_push_workflows(), "merge-queue.yml"])


def test_land_tries_again_when_a_workflow_does_not_start_the_first_time(tmp_path: Path) -> None:
    # The merge has landed by now, and with GITHUB_TOKEN these runs are the only way main's gates run on it (#392).
    queue = queue_of(tmp_path, [{"number": 7}])
    queue.fail_first_call_starting_with("workflow run ci.yml")

    result = queue.run("land", "7", queue.heads[7], queue.main)

    assert result.status == 0, result.stderr
    assert "::error" not in result.stdout
    assert result.calls.count("workflow run ci.yml --ref main") == 2
    assert queue.sleeps() == ["10"]
    assert result.calls[-1] == "workflow run merge-queue.yml --ref main"


@pytest.mark.parametrize("name", main_push_workflows())
def test_land_starts_the_rest_names_the_workflow_that_would_not_start_and_fails(tmp_path: Path, name: str) -> None:
    queue = queue_of(tmp_path, [{"number": 7}])
    queue.fail_calls_starting_with(f"workflow run {name}")

    result = queue.run("land", "7", queue.heads[7], queue.main)
    others = [other for other in main_push_workflows() if other != name]
    runs = [call for call in result.calls if call.startswith("workflow run ") and name not in call]

    assert result.status == 1
    assert (
        f"::error title=Merge queue::could not start {name}; start it by hand: gh workflow run {name} --ref main"
        in result.stdout
    )
    assert result.calls.count(f"workflow run {name} --ref main") == 3
    assert queue.sleeps() == ["10", "10"]
    assert sorted(runs) == sorted(f"workflow run {other} --ref main" for other in [*others, "merge-queue.yml"])
    assert result.calls[-1] == "workflow run merge-queue.yml --ref main"


def test_land_fails_when_the_next_queue_run_will_not_start_after_a_merge(tmp_path: Path) -> None:
    queue = queue_of(tmp_path, [{"number": 7}])
    queue.fail_calls_starting_with("workflow run merge-queue.yml")

    result = queue.run("land", "7", queue.heads[7], queue.main)

    assert result.status == 1
    assert "::error title=Merge queue::could not start merge-queue.yml" in result.stdout
    assert result.calls.count("workflow run merge-queue.yml --ref main") == 3


def test_land_does_not_merge_when_main_moved_after_verification_and_queues_a_rerun(tmp_path: Path) -> None:
    queue = queue_of(tmp_path, [{"number": 7, "closingIssues": [12]}])
    verified_main = queue.main
    queue.move_main()

    result = queue.run("land", "7", queue.heads[7], verified_main)

    assert result.status == 0, result.stderr
    assert result.calls == ["workflow run merge-queue.yml --ref main"]


@pytest.mark.parametrize(
    "change",
    [
        {"labels": ["hold"]},
        {"labels": ["blocked"]},
        {"labels": ["sentinel-alert"]},
        {"labels": ["automated"]},
        {"isDraft": True},
        {"mergeStateStatus": "BLOCKED"},
    ],
    ids=["put on hold", "blocked", "flagged by the sentinel", "labelled automated", "made a draft", "failing checks"],
)
def test_land_does_not_merge_a_pull_request_that_stopped_being_ready_during_verification(
    tmp_path: Path, change: dict
) -> None:
    queue = queue_of(tmp_path, [{"number": 7, "closingIssues": [12], **change}])

    result = queue.run("land", "7", queue.heads[7], queue.main)

    assert result.status == 0, result.stderr
    assert result.calls == ["workflow run merge-queue.yml --ref main"]


# --- reject -------------------------------------------------------------------------------------------------------


def test_reject_holds_the_pull_request_links_the_failed_run_and_moves_on(tmp_path: Path) -> None:
    result = queue_of(tmp_path, [{"number": 7}]).run("reject", "7", RUN_URL)

    assert result.status == 0, result.stderr
    assert len(result.calls) == 3
    assert result.calls[0] == "pr edit 7 --add-label hold"
    assert result.calls[1].startswith("pr comment 7 --body ")
    assert RUN_URL in result.calls[1]
    assert result.calls[2] == "workflow run merge-queue.yml --ref main"


# --- usage --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("args", [[], ["bogus"], ["next", "extra"], ["land", "7"], ["reject", "7"]])
def test_a_wrong_command_line_exits_2_with_usage(tmp_path: Path, args: list[str]) -> None:
    result = queue_of(tmp_path, []).run(*args)

    assert result.status == 2
    assert "usage:" in result.stderr
