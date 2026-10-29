#!/usr/bin/env python3
"""Open, update or close the one nightly compliance issue from a scripts/nightly-compliance.sh report.

.github/workflows/auto-issues.yml runs this after each Nightly compliance run on main, with that run's
`nightly-compliance` artifact. A failing check opens one issue "ci: nightly compliance: N failing checks", labelled `ci`
and `automated`, or updates the open one; the first run where every check passes again comments on it and closes it.
A run that left no report (it failed before the upload) opens or updates the issue as "ci: nightly compliance: no
report". The open issue is found by MARKER in its body or by its title, so it is still found after its body was edited.

Catalog links are left out: on a failure the link check opens its own `data` issue (scripts/check_links.py).

Usage:
    python -I scripts/compliance_issue.py --report nightly-compliance.md --run-url URL [--repo OWNER/REPO]

The token comes from GH_TOKEN or GITHUB_TOKEN (it needs issues: write) and the repository from --repo or
GITHUB_REPOSITORY. The standard library is enough; the script needs no requirements. Exits 0 once the issue matches
the report (failing checks included: the compliance run itself already failed), 2 on a usage error or when GitHub
refused a request.
"""

import argparse
import http
import http.client
import json
import os
import re
import sys
import urllib.parse
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

MARKER = "<!-- dailies-nightly-compliance -->"
LABELS = ["ci", "automated"]
TITLE_PREFIX = "ci: nightly compliance: "
# How an earlier run titled its issue, so it is found even if its body was edited.
ISSUE_TITLE = re.compile(rf"^{re.escape(TITLE_PREFIX)}(\d+ failing checks?|no report)$")
REPORT_HEADING = "# Nightly compliance\n"
FAILING_ROW = re.compile(r"^\| (?P<check>.+) \| ❌ fail \|$", re.MULTILINE)
# The link check reports its failures in its own `data` issue.
OWN_ISSUE_CHECKS = ("Catalog links",)
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
# GitHub refuses an issue body longer than 65536 characters.
MAX_BODY = 65536
API_HOST = "api.github.com"
TIMEOUT = 30

# (method, path, JSON payload or None) -> the decoded JSON answer. Raises OSError when the request fails or is refused.
Api = Callable[[str, str, dict[str, Any] | None], Any]


def github_api(token: str) -> Api:
    """The default Api: HTTPS requests to api.github.com with `token`."""
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "dailies-compliance-issue",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    def request(method: str, path: str, payload: dict[str, Any] | None) -> object:
        connection = http.client.HTTPSConnection(API_HOST, timeout=TIMEOUT)
        body = None if payload is None else json.dumps(payload)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            data = response.read()
        except http.client.HTTPException as error:
            msg = f"{method} {path}: {error!r}"
            raise OSError(msg) from error
        finally:
            connection.close()
        if not http.HTTPStatus.OK <= response.status < http.HTTPStatus.MULTIPLE_CHOICES:
            msg = f"{method} {path}: HTTP {response.status} {data.decode(errors='replace')[:300]}"
            raise OSError(msg)
        return json.loads(data) if data else None

    return request


def failing_checks(report: str) -> list[str] | None:
    """The failing checks of a nightly compliance report, minus those with their own issue; None if it is no report."""
    if not report.startswith(REPORT_HEADING):
        return None
    checks = [match["check"] for match in FAILING_ROW.finditer(report)]
    return [check for check in checks if not check.startswith(OWN_ISSUE_CHECKS)]


def issue_title(failing: list[str] | None) -> str:
    """The issue title for a run with these failing checks (None: no report)."""
    if failing is None:
        return f"{TITLE_PREFIX}no report"
    return f"{TITLE_PREFIX}{len(failing)} failing check{'s' if len(failing) != 1 else ''}"


def issue_body(failing: list[str] | None, report: str, run_url: str) -> str:
    """The issue body: the failing checks and the run, then the report, cut to fit GitHub's limit."""
    footer = (
        "Each Nightly compliance run on `main` updates this issue, and the first run where every check passes closes"
        " it (`.github/workflows/auto-issues.yml`). Broken catalog links have their own `data` issue."
    )
    if failing is None:
        return (
            f"{MARKER}\n[This Nightly compliance run]({run_url}) left no `nightly-compliance` report: it failed before"
            f" the upload. Its log says why.\n\n{footer}\n"
        )
    checks = "".join(f"- {check}\n" for check in failing)
    head = f"{MARKER}\n[Nightly compliance]({run_url}) has failing checks:\n\n{checks}\n{footer}\n\n"
    open_report, close_report = "<details>\n<summary>Report</summary>\n\n", "\n</details>\n"
    cut_note = "\n\n… (cut to fit an issue; the run's `nightly-compliance` artifact has the full report)"
    room = MAX_BODY - len(head) - len(open_report) - len(close_report)
    if len(report) > room:
        report = report[: room - len(cut_note)] + cut_note
    return head + open_report + report + close_report


def _is_compliance_issue(issue: dict[str, Any]) -> bool:
    if "pull_request" in issue:
        return False
    return MARKER in (issue.get("body") or "") or bool(ISSUE_TITLE.match(issue.get("title") or ""))


def sync(api: Api, repo: str, report: str | None, run_url: str) -> str:
    """Make the open compliance issue match the report; return what was done ("opened #N", ..., "nothing to do")."""
    failing = failing_checks(report or "")
    issues = f"/repos/{repo}/issues"
    query = urllib.parse.urlencode({"state": "open", "labels": LABELS[0], "per_page": 100})
    existing = next((issue for issue in api("GET", f"{issues}?{query}", None) if _is_compliance_issue(issue)), None)
    if failing == []:
        if existing is None:
            return "nothing to do"
        number = int(existing["number"])
        comment = f"Every nightly compliance check passes again in [this run]({run_url}). Closing."
        api("POST", f"{issues}/{number}/comments", {"body": comment})
        api("PATCH", f"{issues}/{number}", {"state": "closed", "state_reason": "completed"})
        return f"closed #{number}"
    title, body = issue_title(failing), issue_body(failing, report or "", run_url)
    if existing is None:
        created = api("POST", issues, {"title": title, "body": body, "labels": LABELS})
        return f"opened #{created['number']}"
    number = int(existing["number"])
    api("PATCH", f"{issues}/{number}", {"title": title, "body": body})
    return f"updated #{number}"


def _read_report(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def main(argv: Sequence[str] | None = None, *, api: Api | None = None) -> int:
    """Sync the compliance issue with the report named on the command line; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", type=Path, required=True, help="the run's nightly-compliance.md (may be missing)")
    parser.add_argument("--run-url", required=True, help="the Nightly compliance run, linked from the issue")
    parser.add_argument("--repo", help="OWNER/REPO; GITHUB_REPOSITORY by default")
    args = parser.parse_args(argv)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo or not REPOSITORY.match(repo):
        sys.stderr.write("compliance_issue: needs GH_TOKEN or GITHUB_TOKEN and --repo or GITHUB_REPOSITORY\n")
        return 2
    try:
        outcome = sync(api or github_api(token), repo, _read_report(args.report), args.run_url)
    except (OSError, KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"compliance_issue: could not write the nightly compliance issue ({error})\n")
        return 2
    sys.stderr.write(f"compliance_issue: {outcome}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
