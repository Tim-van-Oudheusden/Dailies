import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITHUB_ACTIONS_APP_ID = 15368
REPOSITORY_ADMIN_ROLE_ID = 5


def load_ruleset() -> dict:
    return json.loads((ROOT / ".github/rulesets/main.json").read_text(encoding="utf-8"))


def rules_by_type() -> dict[str, dict]:
    return {rule["type"]: rule for rule in load_ruleset()["rules"]}


def workflow_job_names() -> set[str]:
    # A job's display name is the `name:` four spaces deep, directly under its job id in `jobs:`.
    job_name = re.compile(r"^    name: (.+)$", re.MULTILINE)
    return {
        match.strip().strip("'\"")
        for workflow in (ROOT / ".github/workflows").glob("*.yml")
        for match in job_name.findall(workflow.read_text(encoding="utf-8"))
    }


def test_ruleset_protects_the_default_branch() -> None:
    ruleset = load_ruleset()
    assert ruleset["target"] == "branch"
    assert ruleset["enforcement"] == "active"
    assert ruleset["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]


def test_ruleset_has_no_read_only_api_fields() -> None:
    # The file is POSTed and PUT as-is; fields the API returns but does not accept make that fail.
    assert set(load_ruleset()) <= {"name", "target", "enforcement", "conditions", "bypass_actors", "rules"}


def test_main_cannot_be_deleted_or_force_pushed() -> None:
    assert {"deletion", "non_fast_forward"} <= rules_by_type().keys()


def test_changes_land_through_merge_commit_pull_requests_without_approvals() -> None:
    parameters = rules_by_type()["pull_request"]["parameters"]
    assert parameters["required_approving_review_count"] == 0
    assert parameters["allowed_merge_methods"] == ["merge"]


def test_required_checks_are_exactly_the_five_gates() -> None:
    checks = rules_by_type()["required_status_checks"]["parameters"]["required_status_checks"]
    assert sorted(check["context"] for check in checks) == sorted(
        ["PR review rubric", "Build, lint, test", "Unit-test coverage floors", "Static checks", "Flatpak (x86_64)"]
    )
    assert {check["integration_id"] for check in checks} == {GITHUB_ACTIONS_APP_ID}


def test_every_required_check_is_a_workflow_job_name() -> None:
    # A required context that no job reports blocks every pull request forever.
    checks = rules_by_type()["required_status_checks"]["parameters"]["required_status_checks"]
    assert {check["context"] for check in checks} <= workflow_job_names()


def test_repository_admins_can_bypass_on_pull_requests_only() -> None:
    assert load_ruleset()["bypass_actors"] == [
        {"actor_id": REPOSITORY_ADMIN_ROLE_ID, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}
    ]
