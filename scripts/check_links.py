#!/usr/bin/env python3
"""Check every active catalog entry's link with the submission validator's rules.

Games die, move and get hijacked. Each week (scripts/nightly-compliance.sh, Sundays) this script fetches every
`status: active` entry of data/v1/games.json and applies the checks in scripts/lib/urlcheck.py: a public https URL, a
2xx answer, a final registrable domain equal to the entry's `domain`, and no gambling keyword in the page title.

Each entry gets one outcome:
    ok                       the game passed every check
    redirected-cross-domain  the link (or a redirect hop) leads to another site
    blocked-title            the page title holds a gambling keyword
    hijacked                 the link leads to another site whose page title holds a gambling keyword
    http-<code>              the site answered a non-2xx status, e.g. http-404
    timeout                  a request or the page body took longer than 10 s
    unreachable              the host does not resolve, refuses the connection, or is not a public https site
    bot-walled               a bot challenge (Cloudflare, or a 403 or timeout on an entry tagged bot-walled): a warning

Requests are polite: one at a time, so one host at a time (entries are grouped by host), at most two a second
overall, with the validator's descriptive User-Agent.

Usage:
    python -I scripts/check_links.py --catalog data/v1/games.json --out links.md [--open-issue] [--repo OWNER/REPO]
        [--previous-state FILE] [--state-out FILE] [--status-out DIR]

Writes a Markdown report (it starts with REPORT_MARKER) listing each failing or bot-walled game with its reason and a
suggested status change. With --open-issue and at least one failure, it opens one issue "data: N broken links
(week W)" labelled `data`, or updates the open one, through the GitHub API; the token comes from GH_TOKEN or
GITHUB_TOKEN and the repository from --repo or GITHUB_REPOSITORY. Exits 0 when no entry failed (bot-walled warnings
allowed), 1 when one did, and 2 on a usage or internal error, or when the issue could not be written.

With --state-out or --status-out it also checks the `broken` entries (they are left out of the report and the exit
code) and tracks streaks with scripts/lib/linkstatus.py: it reads the last run's streaks from --previous-state (a
missing or unreadable file starts them over), writes this run's to --state-out and, when a game's status should
change, writes DIR/changes.json (for scripts/apply_link_status.py) and DIR/pr-body.md. An active game failing the same
check two weeks in a row becomes `broken`, a broken game passing two weeks in a row becomes `active` again, and a
`hijacked` game is `retired` at once.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from time import monotonic
from typing import Any, Protocol
from urllib.parse import urlsplit

import requests

# scripts/lib is not a package and `python -I` leaves the script's directory off sys.path, so add it by path.
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import linkstatus
import urlcheck

REPORT_MARKER = "<!-- dailies-link-check -->"
# One request every half second at most: two a second overall.
MIN_INTERVAL = 0.5
LABEL = "data"
GITHUB_API = "https://api.github.com"
# How an earlier run titled its issue, so it is found even if its body was edited.
ISSUE_TITLE = re.compile(r"^data: \d+ broken links \(week ")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
# Outcomes that can be a passing hiccup: suggest waiting a week before flipping the status.
TRANSIENT = frozenset({"timeout", "unreachable"})


class ApiResponse(Protocol):
    """The part of ``requests.Response`` the GitHub API calls read."""

    def json(self) -> object:
        """The decoded JSON body."""

    def raise_for_status(self) -> None:
        """Raise ``requests.HTTPError`` for a 4xx or 5xx answer."""


class Api(Protocol):
    """The part of ``requests.Session`` the GitHub API calls use."""

    def request(self, method: str, url: str, **kwargs: Any) -> ApiResponse:
        """Send one request."""


class Throttle:
    """A session that sends one request at a time, starting at most one every `interval` seconds."""

    def __init__(
        self,
        session: urlcheck.Session,
        interval: float = MIN_INTERVAL,
        clock: Callable[[], float] = monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._session = session
        self._interval = interval
        self._clock = clock
        self._sleep = sleep
        self._next: float | None = None

    def request(self, method: str, url: str, **kwargs: Any) -> urlcheck.Response:
        """Wait for the next free slot, then send the request."""
        if self._next is not None:
            wait = self._next - self._clock()
            if wait > 0:
                self._sleep(wait)
        self._next = self._clock() + self._interval
        return self._session.request(method, url, **kwargs)


@dataclass(frozen=True)
class LinkResult:
    """The outcome of checking one catalog entry; `outcome` is one of the names in the module docstring."""

    entry: dict[str, Any]
    outcome: str
    reason: str = ""

    @property
    def warning(self) -> bool:
        """Whether the result is worth a look but is not a failure."""
        return self.outcome == "bot-walled"

    @property
    def failed(self) -> bool:
        """Whether the entry's link is broken."""
        return self.outcome not in {"ok", "bot-walled"}

    @property
    def suggested_status(self) -> str | None:
        """The status a maintainer should consider for the entry, or None to keep it active."""
        if self.outcome == linkstatus.HIJACKED:
            return "retired"
        return "broken" if self.failed else None


def _classify(error: urlcheck.CheckError, entry: dict[str, Any]) -> LinkResult:
    reason = str(error)
    if error.url is not None and (domain := urlcheck.registrable_domain(error.url)) != entry["domain"]:
        return LinkResult(
            entry, "redirected-cross-domain", f"redirects to another site ({domain or error.url}): {reason}"
        )
    tagged = "bot-walled" in entry.get("tags", [])
    if error.bot_wall or (tagged and (error.timed_out or error.status in urlcheck.BOT_WALL_STATUSES)):
        return LinkResult(entry, "bot-walled", reason)
    if error.timed_out:
        return LinkResult(entry, "timeout", reason)
    if error.status is not None:
        return LinkResult(entry, f"http-{error.status}", reason)
    return LinkResult(entry, "unreachable", reason)


def _gambling_title(url: str | None, session: urlcheck.Session, resolve: urlcheck.Resolver, keywords: list[str]) -> str:
    """Why the page at `url` is a gambling page, or "" when it is not or cannot be read."""
    if url is None:
        return ""
    try:
        _final_url, title = urlcheck.read_title(url, session, resolve)
    except urlcheck.CheckError:
        return ""
    keyword = urlcheck.blocked_keyword(title, keywords)
    return "" if keyword is None else f'its page title "{title}" contains "{keyword}"'


def check_entry(
    entry: dict[str, Any], session: urlcheck.Session, resolve: urlcheck.Resolver, blocklist: Iterable[str]
) -> LinkResult:
    """Check one catalog entry's link."""
    keywords = list(blocklist)
    site = urlcheck.check_site(entry["url"], entry["domain"], session, resolve, keywords)
    error = site.unreachable or site.title_error
    if error is not None:
        return _classify(error, entry)
    if site.other_site is not None:
        # A hijacked domain: retire the game at once instead of waiting for a second week.
        if gambling := _gambling_title(site.other_url, session, resolve, keywords):
            return LinkResult(entry, linkstatus.HIJACKED, f"{site.other_site}; {gambling}")
        return LinkResult(entry, "redirected-cross-domain", site.other_site)
    if site.keyword is not None:
        return LinkResult(entry, "blocked-title", f'title "{site.title}" contains "{site.keyword}"')
    return LinkResult(entry, "ok")


def _host(entry: dict[str, Any]) -> str:
    try:
        return urlsplit(entry["url"]).hostname or ""
    except ValueError:
        return ""


def check_catalog(
    catalog: dict[str, Any],
    session: urlcheck.Session,
    resolve: urlcheck.Resolver,
    blocklist: Iterable[str],
    statuses: Iterable[str] = ("active",),
) -> list[LinkResult]:
    """Check every entry with one of `statuses`, one host at a time.

    Returns:
        One result per checked entry, grouped by host.
    """
    games = catalog["games"]
    if not isinstance(games, list) or not all(isinstance(game, dict) for game in games):
        msg = "the catalog's games is not a list of objects"
        raise TypeError(msg)
    wanted = frozenset(statuses)
    checked = sorted((game for game in games if game.get("status") in wanted), key=lambda g: (_host(g), g["id"]))
    keywords = tuple(blocklist)
    results = []
    for entry in checked:
        result = check_entry(entry, session, resolve, keywords)
        sys.stderr.write(f"check_links: {entry['id']}: {result.outcome}\n")
        results.append(result)
    return results


def issue_title(failures: int, day: date) -> str:
    """The title of the broken-links issue for a run on `day`."""
    return f"data: {failures} broken links (week {linkstatus.iso_week(day)})"


def _suggestion(result: LinkResult) -> str:
    if result.suggested_status is None:
        return "keep `active`"
    suggestion = f"`active` → `{result.suggested_status}`"
    transient = result.outcome in TRANSIENT or result.outcome.startswith("http-5")
    return f"{suggestion} if it still fails next week" if transient else suggestion


def render_report(results: list[LinkResult], day: date) -> str:
    """The Markdown report: REPORT_MARKER, a summary line and a table of the failures, then the warnings."""
    failures = [result for result in results if result.failed]
    warnings = [result for result in results if result.warning]
    lines = [
        REPORT_MARKER,
        f"### Link check: {len(failures)} broken links, {len(warnings)} bot-walled (week {linkstatus.iso_week(day)})",
        "",
        (
            f"Checked {len(results)} active entries of `data/v1/games.json` on {day.isoformat()} with the submission"
            " validator's rules (`scripts/lib/urlcheck.py`)."
        ),
        "",
    ]
    if not failures and not warnings:
        lines += [f"All {len(results)} active entries passed.", ""]
        return "\n".join(lines)
    lines += ["| Game | URL | Result | Reason | Suggested status |", "| --- | --- | --- | --- | --- |"]
    for result in failures + warnings:
        mark = "❌" if result.failed else "⚠️"
        lines.append(
            f"| {urlcheck.table_cell(result.entry['id'])} | {urlcheck.table_cell(result.entry['url'])} "
            f"| {mark} {result.outcome} | {urlcheck.table_cell(result.reason)} | {_suggestion(result)} |"
        )
    lines += [
        "",
        (
            "An active game that fails the same check next week gets a `data/link-status` pull request that sets its"
            " `status` to `broken`, and a `hijacked` game one that sets `retired` at once. A game that moved needs its"
            " `url` and `domain` updated by hand with a `url-changed` event instead. Never delete an entry. ⚠️"
            " bot-walled sites answer scripts with a bot challenge; they are likely live, so they are warnings, not"
            " failures."
        ),
        "",
    ]
    return "\n".join(lines)


STATUS_MARKER = "<!-- dailies-link-status -->"


def render_pr_body(changes: list[linkstatus.Change], results: list[LinkResult], week: str) -> str:
    """The Markdown body of the status pull request: one row per change, with the history note it adds."""
    before = {result.entry["id"]: result.entry["status"] for result in results}
    lines = [
        STATUS_MARKER,
        f"### Link status changes (week {week})",
        "",
        (
            "The weekly link check (`scripts/check_links.py`, in the nightly compliance workflow) proposes these status"
            " changes for `data/v1/games.json`: `broken` after the same failed check two weeks in a row, `active` again"
            " after two passing weeks, `retired` at once when the link leads to a gambling page on another site."
        ),
        "",
        "| Game | Status | History note |",
        "| --- | --- | --- |",
    ]
    lines += [
        f"| {urlcheck.table_cell(change.id)} | `{before.get(change.id, '?')}` → `{change.status}` "
        f"| {urlcheck.table_cell(change.note)} |"
        for change in changes
    ]
    lines += [
        "",
        (
            "Open each game before merging. If a game only moved, close this pull request and update its `url` and"
            " `domain` with a `url-changed` event instead. Entries are never deleted; a maintainer merges."
        ),
        "",
    ]
    return "\n".join(lines)


def _is_link_issue(issue: dict[str, Any]) -> bool:
    if "pull_request" in issue:
        return False
    return REPORT_MARKER in (issue.get("body") or "") or bool(ISSUE_TITLE.match(issue.get("title") or ""))


def upsert_issue(api: Api, repo: str, token: str, title: str, body: str) -> str:
    """Open the broken-links issue, or update the open one, through the GitHub REST API.

    Args:
        api: A ``requests.Session`` (or a stand-in) for api.github.com.
        repo: The repository, OWNER/REPO.
        token: A token that may write issues.
        title: The issue title.
        body: The issue body, the report.

    Returns:
        "opened #N" or "updated #N".

    Raises:
        requests.RequestException: The API refused a request.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": urlcheck.USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    issues_url = f"{GITHUB_API}/repos/{repo}/issues"
    params = {"state": "open", "labels": LABEL, "per_page": 100}
    listing = api.request("GET", issues_url, headers=headers, params=params, timeout=urlcheck.TIMEOUT)
    listing.raise_for_status()
    existing = next((issue for issue in listing.json() if _is_link_issue(issue)), None)
    if existing is None:
        payload = {"title": title, "body": body, "labels": [LABEL]}
        response = api.request("POST", issues_url, headers=headers, json=payload, timeout=urlcheck.TIMEOUT)
        response.raise_for_status()
        return f"opened #{response.json()['number']}"
    number = int(existing["number"])
    payload = {"title": title, "body": body}
    response = api.request("PATCH", f"{issues_url}/{number}", headers=headers, json=payload, timeout=urlcheck.TIMEOUT)
    response.raise_for_status()
    return f"updated #{number}"


def _load_catalog(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = f"{path} does not hold a JSON object"
        raise TypeError(msg)
    return data


def _open_issue(api: Api | None, repo: str | None, title: str, body: str) -> bool:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token or not repo or not REPOSITORY.match(repo):
        sys.stderr.write("check_links: --open-issue needs GH_TOKEN or GITHUB_TOKEN and --repo or GITHUB_REPOSITORY\n")
        return False
    try:
        with requests.Session() as default_api:
            outcome = upsert_issue(api or default_api, repo, token, title, body)
    except (requests.RequestException, KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"check_links: could not write the {title!r} issue ({error})\n")
        return False
    sys.stderr.write(f"check_links: {outcome}: {title}\n")
    return True


def _track(
    results: list[LinkResult], day: date, previous: Path | None, state_out: Path | None, status_out: Path | None
) -> None:
    """Update the streaks and, when a status should change, write the changes and the pull-request body."""
    week = linkstatus.iso_week(day)
    state: dict[str, Any] = {}
    if previous is not None:
        try:
            state = linkstatus.load_state(previous)
        except ValueError as error:
            sys.stderr.write(f"check_links: {error}; starting the streaks over\n")
    observations = [
        linkstatus.Observation(result.entry["id"], result.entry["status"], result.outcome, result.reason)
        for result in results
    ]
    state, changes = linkstatus.track(observations, state, week)
    if state_out is not None:
        linkstatus.write_state(state_out, state)
    if status_out is not None and changes:
        linkstatus.write_changes(status_out / "changes.json", week, changes)
        (status_out / "pr-body.md").write_text(render_pr_body(changes, results, week), encoding="utf-8")
    for change in changes:
        sys.stderr.write(f"check_links: {change.id}: propose status {change.status}\n")


def main(
    argv: list[str] | None = None,
    *,
    session: urlcheck.Session | None = None,
    resolve: urlcheck.Resolver = urlcheck.resolve_host,
    api: Api | None = None,
    today: date | None = None,
) -> int:
    """Check the catalog named on the command line, write the report and, if asked, open or update the issue.

    Args:
        argv: The command-line arguments; sys.argv by default.
        session: Sends the requests to the games; a throttled, public-only ``requests.Session`` by default. A session
            passed in is used as is, without the throttle.
        resolve: Resolves a host name to its IP addresses.
        api: Sends the requests to the GitHub API; a new ``requests.Session`` by default.
        today: The day of the run; today in UTC by default.

    Returns:
        0 when no entry failed, 1 when one did, 2 on a usage or internal error or when the issue could not be written.
    """
    parser = argparse.ArgumentParser(description="Check every active catalog entry's link.")
    parser.add_argument("--catalog", type=Path, required=True, help="data/v1/games.json")
    parser.add_argument("--out", type=Path, required=True, help="where to write the Markdown report")
    parser.add_argument("--open-issue", action="store_true", help="open or update the broken-links issue on failure")
    parser.add_argument("--repo", help="OWNER/REPO for --open-issue; GITHUB_REPOSITORY by default")
    parser.add_argument("--previous-state", type=Path, help="the streaks the last run wrote (--state-out)")
    parser.add_argument("--state-out", type=Path, help="where to write this run's streaks")
    parser.add_argument("--status-out", type=Path, help="directory for changes.json and pr-body.md")
    args = parser.parse_args(argv)
    day = today or datetime.now(UTC).date()
    try:
        catalog = _load_catalog(args.catalog)
        with urlcheck.public_session() as default_session:
            statuses = ("active", "broken") if args.state_out or args.status_out else ("active",)
            checked = check_catalog(
                catalog, session or Throttle(default_session), resolve, urlcheck.load_blocklist(), statuses
            )
        # Broken entries are only checked to see whether they recovered: the report is about active ones.
        results = [result for result in checked if result.entry["status"] == "active"]
        report = render_report(results, day)
        args.out.write_text(report, encoding="utf-8")
        if args.state_out or args.status_out:
            _track(checked, day, args.previous_state, args.state_out, args.status_out)
    except (OSError, KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"check_links: {error!r}\n")
        return 2
    except Exception:
        # A bug or a malformed catalog: exit 2, so it is not mistaken for a broken link.
        logging.getLogger(__name__).exception("check_links: internal error")
        return 2
    failures = sum(result.failed for result in results)
    if failures and args.open_issue:
        repo = args.repo or os.environ.get("GITHUB_REPOSITORY")
        if not _open_issue(api, repo, issue_title(failures, day), report):
            return 2
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
