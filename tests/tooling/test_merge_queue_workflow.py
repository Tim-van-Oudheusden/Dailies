"""`.github/workflows/merge-queue.yml`, which merges ready pull requests one at a time (`scripts/merge-queue.sh`).

The generic workflow invariants (token scopes, pins, timeouts) are in test_workflows.py; these are the ones that only
make sense for the queue.
"""

import json
import re
from pathlib import Path

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
RULESET = ROOT / ".github" / "rulesets" / "main.json"
SCRIPT = ROOT / "scripts" / "merge-queue.sh"


def load(name: str) -> dict:
    # YAML 1.2: the `on:` key stays the string "on".
    return YAML(typ="safe", pure=True).load((WORKFLOWS / name).read_text(encoding="utf-8"))


QUEUE = load("merge-queue.yml")


def required_checks() -> set[str]:
    rules = json.loads(RULESET.read_text(encoding="utf-8"))["rules"]
    parameters = next(rule for rule in rules if rule["type"] == "required_status_checks")["parameters"]
    return {check["context"] for check in parameters["required_status_checks"]}


def workflows_holding_a_required_check() -> set[str]:
    required = required_checks()
    holding = set()
    for path in WORKFLOWS.glob("*.yml"):
        workflow = load(path.name)
        if any(job.get("name") in required for job in (workflow.get("jobs") or {}).values()):
            holding.add(workflow["name"])
    return holding


def keep_out_labels() -> list[str]:
    match = re.search(r"^KEEP_OUT_LABELS=\(([^)]*)\)", SCRIPT.read_text(encoding="utf-8"), re.MULTILINE)
    assert match, "scripts/merge-queue.sh has no KEEP_OUT_LABELS array"
    return match.group(1).split()


def label_lists(expression: str) -> list[list[str]]:
    """Every `fromJSON('[...]')` list in a workflow expression."""
    return [json.loads(raw) for raw in re.findall(r"fromJSON\('(\[[^']*\])'\)", expression)]


def workflows_checking_pull_requests() -> set[str]:
    names = set()
    for path in WORKFLOWS.glob("*.yml"):
        workflow = load(path.name)
        if {"pull_request", "pull_request_target"} & set(workflow["on"]):
            names.add(workflow["name"])
    return names - {QUEUE["name"]}


def test_runs_when_any_workflow_checking_a_pull_request_finishes() -> None:
    # workflow_run matches workflows by name. The queue picks only a CLEAN pull request, one with no check red or
    # pending, required or not, so it has to run again when the last check finishes. A workflow it does not watch
    # (Windows (experimental) usually finishes after CI) leaves the pull request waiting for the next unrelated run.
    workflow_run = QUEUE["on"]["workflow_run"]

    assert workflow_run["types"] == ["completed"]
    assert set(workflow_run["workflows"]) == workflows_checking_pull_requests()
    assert workflows_holding_a_required_check() <= set(workflow_run["workflows"])


def test_can_be_started_by_hand_and_when_a_draft_is_marked_ready_or_a_label_comes_off() -> None:
    assert set(QUEUE["on"]) == {"workflow_run", "pull_request", "workflow_dispatch"}
    assert QUEUE["on"]["pull_request"]["types"] == ["ready_for_review", "unlabeled"]


def test_the_label_lists_in_the_workflow_are_the_scripts_keep_out_labels() -> None:
    # GitHub expressions cannot read a shell variable, so the workflow restates KEEP_OUT_LABELS in its concurrency
    # group and in the pick job's `if`. A partial edit would stall the queue, or let a run that picks nothing replace a
    # pending one that would merge.
    expected = keep_out_labels()
    group = str(QUEUE["concurrency"]["group"])
    pick_if = str(QUEUE["jobs"]["pick"]["if"])

    assert label_lists(group) == [expected]
    assert label_lists(pick_if) == [expected]


def test_only_events_that_can_make_a_pull_request_ready_share_the_queues_concurrency_group() -> None:
    concurrency = QUEUE["concurrency"]
    group = str(concurrency["group"])

    assert "'merge-queue'" in group
    assert "github.run_id" in group
    assert concurrency["cancel-in-progress"] is False


def test_a_label_only_starts_the_queue_when_a_person_removed_it() -> None:
    # test_workflows.py's bot-label check, spelled out: a bot's label event never starts or replaces a run.
    assert "github.event.sender.type == 'User'" in str(QUEUE["concurrency"]["group"])
    assert "github.event.sender.type == 'User'" in str(QUEUE["jobs"]["pick"]["if"])


SUCCESSFUL_RUN = "(github.event_name == 'workflow_run' && github.event.workflow_run.conclusion == 'success')"
SAME_REPO = "github.event.pull_request.head.repo.full_name == github.repository"


def test_only_a_successful_workflow_run_starts_the_queue() -> None:
    # A failed check cannot make a pull request ready; its run must neither pick nor replace a pending run.
    assert SUCCESSFUL_RUN in " ".join(str(QUEUE["concurrency"]["group"]).split())
    assert SUCCESSFUL_RUN in " ".join(str(QUEUE["jobs"]["pick"]["if"]).split())


def test_a_fork_pull_request_event_neither_starts_the_queue_nor_joins_its_concurrency_group() -> None:
    # A fork's event gets a read-only token, so its land would fail; in the queue's group it could replace a pending
    # run that would merge.
    for expression in (str(QUEUE["concurrency"]["group"]), str(QUEUE["jobs"]["pick"]["if"])):
        flat = " ".join(expression.split())
        assert f"(github.event_name == 'pull_request' && {SAME_REPO} && (" in flat


def test_verify_runs_the_gate_commands_of_ci_build_job_from_a_checkout_that_keeps_no_token() -> None:
    # Verification runs the pull request's code merged onto main: the same Build, lint, test gate CI runs, with no
    # token left behind.
    verify = QUEUE["jobs"]["verify"]
    ci_build = load("ci.yml")["jobs"]["build"]
    queue_commands = [str(step["run"]).strip() for step in verify["steps"] if "run" in step]
    ci_commands = [str(step["run"]).strip() for step in ci_build["steps"] if "run" in step]
    checkouts = [step for step in verify["steps"] if str(step.get("uses", "")).startswith("actions/checkout@")]

    assert [command for command in ci_commands if command in queue_commands] == ci_commands
    assert len(checkouts) == 1
    assert checkouts[0]["with"]["persist-credentials"] is False
    assert verify.get("permissions") is None


def test_the_jobs_with_write_access_run_mains_scripts_not_the_pull_requests_code() -> None:
    # pick, land and reject check out main; only verify holds the pull request's code, and it has a read-only token.
    for job_id in ("pick", "land", "reject"):
        checkouts = [
            step for step in QUEUE["jobs"][job_id]["steps"] if str(step.get("uses", "")).startswith("actions/checkout@")
        ]
        assert [step["with"]["ref"] for step in checkouts] == ["main"], job_id
    assert QUEUE["jobs"]["land"]["needs"] == ["pick", "verify"]
    assert QUEUE["jobs"]["reject"]["if"] == "always() && needs.verify.result == 'failure'"


def test_a_failed_labeler_step_cannot_keep_a_pull_request_out_of_the_queue() -> None:
    # The queue takes only merge state CLEAN, which any red check blocks. A failed API call on a convenience label
    # would hold a ready pull request until someone re-runs the check (#405).
    steps = load("labeler.yml")["jobs"]["label"]["steps"]
    assert [step.get("continue-on-error") for step in steps] == [True]
