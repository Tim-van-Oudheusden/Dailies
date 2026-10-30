import http.client
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "compliance_issue.py"
REPO = "o/r"
RUN_URL = "https://github.com/o/r/actions/runs/42"
ISSUES = f"/repos/{REPO}/issues"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("compliance_issue", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ci = load_script()


def report(*rows: tuple[str, bool], failures: str = "") -> str:
    """A report as scripts/nightly-compliance.sh prints it: a `| check | result |` row per check, then the end line."""
    lines = ["# Nightly compliance", "", "Commit: `0123abc`", "", "| Check | Result |", "| ----- | ------ |"]
    lines += [f"| {check} | {'✅ pass' if passed else '❌ fail'} |" for check, passed in rows]
    if failures:
        lines += ["", "## Failures", "", failures]
    lines += ["", "<!-- nightly-compliance: end -->"]
    return "\n".join(lines) + "\n"


PASSING = report(
    ("Dependabot alerts (high+)", True),
    ("Script dependencies (pip-audit)", True),
    ("ACMM codebase level (L5+)", True),
)
FAILING = report(
    ("Dependabot alerts (high+)", False),
    ("Script dependencies (pip-audit)", True),
    ("ACMM codebase level (L5+)", False),
    failures="- GHSA-aaaa-bbbb-cccc (high) requests: Bad thing",
)


class FakeGitHub:
    """Answers the issue endpoints like api.github.com, from a list of issues; records every request."""

    def __init__(self, issues: list[dict[str, Any]] | None = None, fail: Exception | None = None) -> None:
        self.issues = issues or []
        self.fail = fail
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []

    def __call__(self, method: str, path: str, payload: dict[str, Any] | None) -> object:
        self.requests.append((method, path, payload))
        if self.fail is not None:
            raise self.fail
        if method == "GET" and path.startswith(f"{ISSUES}?"):
            assert "state=open" in path
            assert "labels=ci" in path
            return [issue for issue in self.issues if issue.get("state", "open") == "open"]
        if method == "POST" and path == ISSUES:
            assert payload is not None
            issue = {"number": 100 + len(self.issues), **payload}
            self.issues.append(issue)
            return issue
        number = int(path.split("/")[-2 if path.endswith("/comments") else -1])
        issue = next(issue for issue in self.issues if issue["number"] == number)
        if method == "POST" and path.endswith("/comments"):
            return {"id": 1}
        if method == "PATCH":
            assert payload is not None
            issue.update(payload)
            return issue
        msg = f"unexpected request {method} {path}"
        raise AssertionError(msg)

    def writes(self) -> list[tuple[str, str, dict[str, Any] | None]]:
        return [request for request in self.requests if request[0] != "GET"]


def compliance_issue(number: int = 7, **fields: Any) -> dict[str, Any]:
    return {
        "number": number,
        "title": "ci: nightly compliance: 1 failing check",
        "body": f"{ci.MARKER}\nold",
        "labels": [{"name": "ci"}],
        **fields,
    }


def run(tmp_path: Path, text: str | None, api: FakeGitHub, monkeypatch: pytest.MonkeyPatch, *extra: str) -> int:
    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    path = tmp_path / "nightly-compliance.md"
    if text is not None:
        path.write_text(text, encoding="utf-8")
    return ci.main(["--report", str(path), "--run-url", RUN_URL, *extra], api=api)


def test_a_failing_run_opens_one_labelled_issue_naming_the_failing_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    api = FakeGitHub()

    assert run(tmp_path, FAILING, api, monkeypatch) == 0

    [(method, path, payload)] = api.writes()
    assert (method, path) == ("POST", ISSUES)
    assert payload is not None
    assert payload["title"] == "ci: nightly compliance: 2 failing checks"
    assert payload["labels"] == ["ci", "automated"]
    body = payload["body"]
    assert body.startswith(ci.MARKER)
    assert "- Dependabot alerts (high+)\n- ACMM codebase level (L5+)\n" in body
    assert "Script dependencies (pip-audit)\n" not in body.split("<details>")[0]
    assert RUN_URL in body
    # The full report follows, Failures section included.
    assert "- GHSA-aaaa-bbbb-cccc (high) requests: Bad thing" in body
    assert "opened #100" in capsys.readouterr().err


def test_one_failing_check_is_singular(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeGitHub()
    run(tmp_path, report(("ACMM codebase level (L5+)", False)), api, monkeypatch)
    assert api.issues[0]["title"] == "ci: nightly compliance: 1 failing check"


def test_a_failing_run_updates_the_open_issue_instead_of_opening_another(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    api = FakeGitHub([compliance_issue()])

    assert run(tmp_path, FAILING, api, monkeypatch) == 0

    [(method, path, payload)] = api.writes()
    assert (method, path) == ("PATCH", f"{ISSUES}/7")
    assert payload is not None
    assert payload["title"] == "ci: nightly compliance: 2 failing checks"
    assert "- Dependabot alerts (high+)" in payload["body"]
    assert "updated #7" in capsys.readouterr().err


def test_the_open_issue_is_found_by_its_title_after_its_body_was_edited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    api = FakeGitHub([compliance_issue(body="Looking into it.")])
    run(tmp_path, FAILING, api, monkeypatch)
    assert [(method, path) for method, path, _ in api.writes()] == [("PATCH", f"{ISSUES}/7")]


def test_other_ci_issues_and_pull_requests_are_left_alone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    other = {"number": 3, "title": "ci: flaky icons test", "body": "", "labels": [{"name": "ci"}]}
    pull_request = compliance_issue(number=5, pull_request={"url": "https://api.github.com/repos/o/r/pulls/5"})
    api = FakeGitHub([other, pull_request])

    run(tmp_path, FAILING, api, monkeypatch)

    assert [(method, path) for method, path, _ in api.writes()] == [("POST", ISSUES)]


def test_a_passing_run_comments_and_closes_the_open_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    api = FakeGitHub([compliance_issue()])

    assert run(tmp_path, PASSING, api, monkeypatch) == 0

    comment, close = api.writes()
    assert comment[:2] == ("POST", f"{ISSUES}/7/comments")
    assert comment[2] is not None
    assert RUN_URL in comment[2]["body"]
    assert close == ("PATCH", f"{ISSUES}/7", {"state": "closed", "state_reason": "completed"})
    assert "closed #7" in capsys.readouterr().err


def test_a_passing_run_without_an_open_issue_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeGitHub([compliance_issue(state="closed")])
    assert run(tmp_path, PASSING, api, monkeypatch) == 0
    assert api.writes() == []


def test_broken_links_alone_open_no_issue_because_the_link_check_opens_its_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    api = FakeGitHub([compliance_issue()])
    links_only = report(("Dependabot alerts (high+)", True), ("Catalog links (weekly)", False))

    run(tmp_path, links_only, api, monkeypatch)

    assert api.issues[0]["state"] == "closed"
    assert not any(method == "POST" and path == ISSUES for method, path, _ in api.writes())


@pytest.mark.parametrize(
    "text", [None, "", "Error: the job ran out of disk\n"], ids=["missing", "empty", "not-a-report"]
)
def test_a_run_without_a_report_opens_the_issue_saying_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str | None
) -> None:
    api = FakeGitHub()

    assert run(tmp_path, text, api, monkeypatch) == 0

    [(_, _, payload)] = api.writes()
    assert payload is not None
    assert payload["title"] == "ci: nightly compliance: no report"
    assert RUN_URL in payload["body"]
    assert "nightly-compliance" in payload["body"]


@pytest.mark.parametrize("rows", [1, 0], ids=["some-rows", "no-rows"])
def test_a_report_cut_short_updates_the_open_issue_instead_of_closing_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rows: int
) -> None:
    # A run that timed out or exited early still uploads what it printed; the rows it never reached are not passes.
    api = FakeGitHub([compliance_issue()])
    cut_short = PASSING.split("\n| Script dependencies")[0] + "\n" if rows else PASSING.split("| Dependabot")[0]

    assert run(tmp_path, cut_short, api, monkeypatch) == 0

    [(method, path, payload)] = api.writes()
    assert (method, path) == ("PATCH", f"{ISSUES}/7")
    assert payload is not None
    assert payload["title"] == "ci: nightly compliance: no report"


def test_a_long_report_is_cut_to_fit_an_issue_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeGitHub()
    huge = report(("Script dependencies (pip-audit)", False), failures="x" * 200_000)

    run(tmp_path, huge, api, monkeypatch)

    body = api.issues[0]["body"]
    assert len(body) <= ci.MAX_BODY
    assert "- Script dependencies (pip-audit)" in body
    assert "cut" in body
    assert body.rstrip().endswith("</details>")


def test_an_api_error_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    api = FakeGitHub(fail=OSError("HTTP 403: Resource not accessible by integration"))
    assert run(tmp_path, FAILING, api, monkeypatch) == 2
    assert "Resource not accessible by integration" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("token", "repo"), [(None, REPO), ("token", None), ("token", "not a repo")], ids=["no-token", "no-repo", "bad-repo"]
)
def test_a_missing_token_or_repository_exits_2_without_a_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token: str | None, repo: str | None
) -> None:
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "GITHUB_REPOSITORY"):
        monkeypatch.delenv(name, raising=False)
    if token:
        monkeypatch.setenv("GITHUB_TOKEN", token)
    if repo:
        monkeypatch.setenv("GITHUB_REPOSITORY", repo)
    path = tmp_path / "nightly-compliance.md"
    path.write_text(FAILING, encoding="utf-8")
    api = FakeGitHub()

    assert ci.main(["--report", str(path), "--run-url", RUN_URL], api=api) == 2
    assert api.requests == []


def test_the_repo_flag_overrides_the_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "someone/else")
    api = FakeGitHub()
    run(tmp_path, FAILING, api, monkeypatch, "--repo", REPO)
    assert api.writes()[0][1] == ISSUES


def test_missing_arguments_are_a_usage_error() -> None:
    with pytest.raises(SystemExit) as exit_info:
        ci.main(["--run-url", RUN_URL], api=FakeGitHub())
    assert exit_info.value.code == 2


# github_api, the default Api, against a stand-in for http.client.HTTPSConnection.


class FakeConnection:
    """Replaces HTTPSConnection: answers with (status, body) or raises `fail`; records the host and each request."""

    def __init__(self, status: int = 200, body: bytes = b"", fail: Exception | None = None) -> None:
        self.status, self.body, self.fail = status, body, fail
        self.hosts: list[str] = []
        self.requests: list[tuple[str, str, str | None, dict[str, str]]] = []
        self.closed = 0

    def __call__(self, host: str, timeout: float) -> "FakeConnection":
        assert timeout > 0
        self.hosts.append(host)
        return self

    def request(self, method: str, path: str, body: str | None, headers: dict[str, str]) -> None:
        self.requests.append((method, path, body, headers))
        if self.fail is not None:
            raise self.fail

    def getresponse(self) -> "FakeConnection":
        return self

    def read(self) -> bytes:
        return self.body

    def close(self) -> None:
        self.closed += 1


def test_github_api_sends_json_with_the_token_and_decodes_the_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection(201, b'{"number": 9}')
    monkeypatch.setattr(ci.http.client, "HTTPSConnection", connection)

    answer = ci.github_api("secret")("POST", ISSUES, {"title": "t"})

    assert answer == {"number": 9}
    assert connection.hosts == ["api.github.com"]
    [(method, path, body, headers)] = connection.requests
    assert (method, path) == ("POST", ISSUES)
    assert body is not None
    assert json.loads(body) == {"title": "t"}
    assert headers["Authorization"] == "Bearer secret"
    assert headers["Accept"] == "application/vnd.github+json"
    assert connection.closed == 1


def test_github_api_sends_no_body_for_a_get_and_reads_an_empty_answer_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection(204, b"")
    monkeypatch.setattr(ci.http.client, "HTTPSConnection", connection)

    assert ci.github_api("secret")("GET", ISSUES, None) is None
    assert connection.requests[0][2] is None


def test_github_api_raises_oserror_with_the_status_on_a_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection(403, b'{"message": "Resource not accessible by integration"}')
    monkeypatch.setattr(ci.http.client, "HTTPSConnection", connection)

    with pytest.raises(OSError, match=r"HTTP 403 .*Resource not accessible by integration"):
        ci.github_api("secret")("PATCH", f"{ISSUES}/7", {"state": "closed"})


def test_github_api_raises_oserror_when_the_connection_drops(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection(fail=http.client.RemoteDisconnected("Remote end closed connection"))
    monkeypatch.setattr(ci.http.client, "HTTPSConnection", connection)

    with pytest.raises(OSError, match="RemoteDisconnected"):
        ci.github_api("secret")("GET", ISSUES, None)
    assert connection.closed == 1
