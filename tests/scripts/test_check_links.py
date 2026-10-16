import importlib.util
import itertools
import json
import socket
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

# The checker's dependencies come from scripts/requirements.txt; without them there is nothing to test.
requests = pytest.importorskip("requests")
pytest.importorskip("tldextract")

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_links.py"
SUNDAY = date(2026, 10, 18)
PUBLIC_IP = "93.184.215.14"
LANDING = "https://www.lucky-spin-777.net/promo"
API = "https://api.github.com/repos/o/r"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_links", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cl = load_script()


class FakeResponse:
    def __init__(self, status: int = 200, headers: dict[str, str] | None = None, body: str = "") -> None:
        self.status_code = status
        self.headers = {key.lower(): value for key, value in (headers or {}).items()}
        self.encoding = "utf-8"
        self._body = body.encode()

    def iter_content(self, chunk_size: int) -> object:
        for start in range(0, len(self._body), chunk_size):
            yield self._body[start : start + chunk_size]

    def close(self) -> None:
        pass


class FakeSession:
    """Answers requests from a table of (method, url) -> response or exception; unknown URLs get a 404."""

    def __init__(self, routes: dict[tuple[str, str], FakeResponse | Exception] | None = None) -> None:
        self.routes = routes or {}
        self.calls: list[tuple[str, str]] = []
        self.user_agents: set[str] = set()

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        assert kwargs["allow_redirects"] is False
        self.calls.append((method, url))
        self.user_agents.add(kwargs["headers"]["User-Agent"])
        answer = self.routes.get((method, url), FakeResponse(404))
        if isinstance(answer, Exception):
            raise answer
        return answer


def live(url: str, title: str = "Worldle - guess the country") -> dict[tuple[str, str], FakeResponse | Exception]:
    page = f"<html><head><title>{title}</title></head><body></body></html>"
    return {("HEAD", url): FakeResponse(200), ("GET", url): FakeResponse(200, body=page)}


def hijacked(url: str) -> dict[tuple[str, str], FakeResponse | Exception]:
    return {
        ("HEAD", url): FakeResponse(301, {"Location": LANDING}),
        ("HEAD", LANDING): FakeResponse(200),
        ("GET", url): FakeResponse(302, {"Location": LANDING}),
        ("GET", LANDING): FakeResponse(200, body="<title>Welcome</title>"),
    }


def walled(url: str) -> dict[tuple[str, str], FakeResponse | Exception]:
    return {("HEAD", url): FakeResponse(403), ("GET", url): FakeResponse(403)}


def resolve_public(_host: str) -> list[str]:
    return [PUBLIC_IP]


def game(game_id: str, url: str, domain: str, *, status: str = "active", tags: list[str] | None = None) -> dict:
    entry: dict[str, object] = {"id": game_id, "name": game_id.title(), "url": url, "domain": domain}
    entry["status"] = status
    if tags is not None:
        entry["tags"] = tags
    return entry


WORLDLE = game("worldle", "https://worldle.teuteuf.fr/", "teuteuf.fr")
MOVIEDLE = game("moviedle", "https://moviedle.app/", "moviedle.app")
ARTLE = game("artle", "https://www.nga.gov/artle.html", "nga.gov", tags=["art", "bot-walled"])


def check(entry: dict, routes: dict, resolve: object = resolve_public) -> object:
    return cl.check_entry(entry, FakeSession(routes), resolve, ["casino", "slots"])


# Hijacked or dead dle domains (docs/research/dle-catalog.md §1.4) that now redirect to another site.
GRAVEYARD = ["moviedle.app", "absurdle.online", "posterdle.com", "cladder.io", "cloudle.app", "foodle.io"]


@pytest.mark.parametrize("domain", GRAVEYARD)
def test_graveyard_domain_is_reported_as_a_cross_domain_redirect(domain: str) -> None:
    url = f"https://{domain}/"

    result = check(game(domain.partition(".")[0], url, domain), hijacked(url))

    assert result.outcome == "redirected-cross-domain"
    assert result.failed
    assert "lucky-spin-777.net" in result.reason
    assert result.suggested_status == "broken"


def test_redirect_to_plain_http_on_another_site_is_a_cross_domain_redirect() -> None:
    routes = {("HEAD", MOVIEDLE["url"]): FakeResponse(302, {"Location": "http://lucky-spin-777.net/"})}

    result = check(MOVIEDLE, routes)

    assert result.outcome == "redirected-cross-domain"
    assert result.reason.startswith("redirects to another site (lucky-spin-777.net): the URL must start with https://")


def test_moved_game_whose_new_site_blocks_scripts_is_a_cross_domain_redirect() -> None:
    # A bot-walled game that moved: the 403 comes from the new site, so the entry's url and domain are stale.
    footy = game("immaculate-footy", "https://www.immaculatefooty.com/", "immaculatefooty.com", tags=["bot-walled"])
    new = "https://www.sports-reference.com/immaculate-footy/"
    routes = {
        ("HEAD", footy["url"]): FakeResponse(301, {"Location": new}),
        ("HEAD", new): FakeResponse(403),
        ("GET", footy["url"]): FakeResponse(301, {"Location": new}),
        ("GET", new): FakeResponse(403),
    }

    result = check(footy, routes)

    assert result.outcome == "redirected-cross-domain"
    assert result.reason == f"redirects to another site (sports-reference.com): {new} answered HTTP 403"


def test_live_game_passes() -> None:
    result = check(WORLDLE, live(WORLDLE["url"]))

    assert result.outcome == "ok"
    assert not result.failed
    assert not result.warning
    assert result.suggested_status is None


def test_gambling_title_is_blocked() -> None:
    result = check(WORLDLE, live(WORLDLE["url"], title="Best Online Casino 2026"))

    assert result.outcome == "blocked-title"
    assert result.failed
    assert "casino" in result.reason


@pytest.mark.parametrize("status", [404, 410, 500])
def test_http_error_is_reported_with_its_code(status: int) -> None:
    result = check(WORLDLE, {("HEAD", WORLDLE["url"]): FakeResponse(status)})

    assert result.outcome == f"http-{status}"
    assert result.failed


def test_timeout_is_reported() -> None:
    result = check(WORLDLE, {("HEAD", WORLDLE["url"]): requests.Timeout()})

    assert result.outcome == "timeout"
    assert result.failed


def test_host_that_does_not_resolve_is_unreachable() -> None:
    def fail(host: str) -> list[str]:
        raise socket.gaierror(host)

    result = check(MOVIEDLE, live(MOVIEDLE["url"]), resolve=fail)

    assert result.outcome == "unreachable"
    assert result.failed
    assert "does not resolve" in result.reason


@pytest.mark.parametrize(
    "headers",
    [{"Server": "cloudflare"}, {"cf-mitigated": "challenge"}, {"Server": "nginx", "CF-Mitigated": "challenge"}],
)
def test_cloudflare_challenge_is_a_bot_walled_warning(headers: dict[str, str]) -> None:
    challenge = FakeResponse(403, headers, body="<title>Just a moment...</title>")
    routes = {("HEAD", WORLDLE["url"]): challenge, ("GET", WORLDLE["url"]): challenge}

    result = check(WORLDLE, routes)

    assert result.outcome == "bot-walled"
    assert result.warning
    assert not result.failed
    assert result.suggested_status is None


def test_403_on_a_game_the_catalog_marks_bot_walled_is_a_warning() -> None:
    result = check(ARTLE, {("HEAD", ARTLE["url"]): FakeResponse(403), ("GET", ARTLE["url"]): FakeResponse(403)})

    assert result.outcome == "bot-walled"
    assert result.warning


def test_timeout_on_a_game_the_catalog_marks_bot_walled_is_a_warning() -> None:
    # Some walls never answer a script at all (washingtonpost.com stalls until the read timeout).
    result = check(ARTLE, {("HEAD", ARTLE["url"]): requests.Timeout()})

    assert result.outcome == "bot-walled"
    assert result.warning
    assert not result.failed
    assert result.suggested_status is None


def test_403_without_a_challenge_on_an_ordinary_game_fails() -> None:
    result = check(WORLDLE, {("HEAD", WORLDLE["url"]): FakeResponse(403), ("GET", WORLDLE["url"]): FakeResponse(403)})

    assert result.outcome == "http-403"
    assert result.failed


def test_title_page_that_fails_after_head_passes_is_reported() -> None:
    result = check(WORLDLE, {("HEAD", WORLDLE["url"]): FakeResponse(200), ("GET", WORLDLE["url"]): FakeResponse(503)})

    assert result.outcome == "http-503"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def test_throttle_keeps_requests_at_least_half_a_second_apart() -> None:
    clock = FakeClock()
    sent: list[float] = []

    class Recorder:
        def request(self, _method: str, _url: str, **_kwargs: object) -> FakeResponse:
            sent.append(clock.now)
            clock.now += 0.1  # the request itself takes a while
            return FakeResponse(200)

    throttle = cl.Throttle(Recorder(), interval=0.5, clock=clock, sleep=clock.sleep)
    for _ in range(4):
        throttle.request("HEAD", "https://worldle.teuteuf.fr/")
    clock.now += 2  # an idle gap needs no sleep
    throttle.request("HEAD", "https://worldle.teuteuf.fr/")

    assert [round(b - a, 6) for a, b in itertools.pairwise(sent)] == [0.5, 0.5, 0.5, 2.1]
    assert [round(seconds, 6) for seconds in clock.slept] == [0.4, 0.4, 0.4]


def test_catalog_is_checked_one_host_at_a_time_and_skips_inactive_entries() -> None:
    catalog = {
        "games": [
            game("worldle", "https://worldle.teuteuf.fr/", "teuteuf.fr"),
            game("wordle", "https://www.nytimes.com/games/wordle/", "nytimes.com"),
            game("flagle", "https://www.flagle.io/", "flagle.io", status="broken"),
            game("globle", "https://globle-game.com/", "globle-game.com", status="retired"),
            game("connections", "https://www.nytimes.com/games/connections", "nytimes.com"),
            game("countryle", "https://countryle.com/", "countryle.com"),
        ]
    }
    routes: dict = {}
    for entry in catalog["games"]:
        routes.update(live(entry["url"]))
    session = FakeSession(routes)

    results = cl.check_catalog(catalog, session, resolve_public, [])

    assert sorted(result.entry["id"] for result in results) == ["connections", "countryle", "wordle", "worldle"]
    hosts = [url.split("/")[2] for _method, url in session.calls]
    assert hosts == sorted(hosts, key=hosts.index)  # every host's requests are contiguous
    assert "www.flagle.io" not in hosts
    assert session.user_agents == {cl.urlcheck.USER_AGENT}
    assert "DailiesSubmissionCheck" in cl.urlcheck.USER_AGENT


def test_hosts_are_not_revisited() -> None:
    catalog = {
        "games": [
            game("a", "https://a.example/", "a.example"),
            game("b", "https://b.example/", "b.example"),
            game("c", "https://a.example/two", "a.example"),
        ]
    }
    routes: dict = {}
    for entry in catalog["games"]:
        routes.update(live(entry["url"]))
    session = FakeSession(routes)

    cl.check_catalog(catalog, session, resolve_public, [])

    hosts = [url.split("/")[2] for _method, url in session.calls]
    changes = [host for index, host in enumerate(hosts) if index == 0 or hosts[index - 1] != host]
    assert changes == ["a.example", "b.example"]


def test_report_lists_failures_and_warnings_with_reasons_and_suggestions() -> None:
    results = [
        cl.check_entry(WORLDLE, FakeSession(live(WORLDLE["url"])), resolve_public, []),
        cl.check_entry(MOVIEDLE, FakeSession(hijacked(MOVIEDLE["url"])), resolve_public, []),
        cl.check_entry(ARTLE, FakeSession(walled(ARTLE["url"])), resolve_public, []),
    ]

    report = cl.render_report(results, SUNDAY)

    assert report.startswith(cl.REPORT_MARKER)
    assert "1 broken link" in report
    assert "week 2026-W42" in report
    assert "| `moviedle` | `https://moviedle.app/` | ❌ redirected-cross-domain |" in report
    assert "redirects to another site (lucky-spin-777.net)" in report
    assert "`active` → `broken`" in report
    assert "| `artle` | `https://www.nga.gov/artle.html` | ⚠️ bot-walled |" in report
    assert "worldle" not in report


def test_report_renders_page_titles_inert() -> None:
    title = "Casino | @maintainer [win](https://evil.example)"
    result = cl.check_entry(WORLDLE, FakeSession(live(WORLDLE["url"], title=title)), resolve_public, ["casino"])

    report = cl.render_report([result], SUNDAY)

    assert "`" + 'title "Casino \\| @maintainer [win](https://evil.example)" contains "casino"' + "`" in report


def test_report_without_problems_says_so() -> None:
    result = cl.check_entry(WORLDLE, FakeSession(live(WORLDLE["url"])), resolve_public, [])

    assert "All 1 active entries passed." in cl.render_report([result], SUNDAY)


def test_issue_title_counts_failures_and_names_the_iso_week() -> None:
    assert cl.issue_title(1, SUNDAY) == "data: 1 broken links (week 2026-W42)"


class FakeGitHub:
    """A tiny GitHub issues API: list, create and update issues of repository o/r."""

    def __init__(self, issues: list[dict] | None = None) -> None:
        self.issues = issues or []
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> object:
        self.calls.append((method, url))
        assert kwargs["headers"]["Authorization"] == "Bearer t0ken"
        if method == "GET" and url == f"{API}/issues":
            assert kwargs["params"]["state"] == "open"
            assert kwargs["params"]["labels"] == "data"
            return FakeApiResponse(200, [issue for issue in self.issues if issue["state"] == "open"])
        if method == "POST" and url == f"{API}/issues":
            issue = {"number": 100 + len(self.issues), "state": "open", **kwargs["json"]}
            self.issues.append(issue)
            return FakeApiResponse(201, issue)
        number = int(url.rsplit("/", 1)[1])
        issue = next(issue for issue in self.issues if issue["number"] == number)
        assert method == "PATCH"
        issue.update(kwargs["json"])
        return FakeApiResponse(200, issue)


class FakeApiResponse:
    def __init__(self, status: int, data: object) -> None:
        self.status_code = status
        self._data = data

    def json(self) -> object:
        return self._data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def test_issue_is_opened_once_and_then_updated() -> None:
    github = FakeGitHub([{"number": 7, "state": "open", "title": "Add Flagle", "body": "a submission"}])

    first = cl.upsert_issue(github, "o/r", "t0ken", "data: 1 broken links (week 2026-W42)", cl.REPORT_MARKER + "\none")
    second = cl.upsert_issue(github, "o/r", "t0ken", "data: 2 broken links (week 2026-W43)", cl.REPORT_MARKER + "\ntwo")

    assert first == "opened #101"
    assert second == "updated #101"
    assert [call[0] for call in github.calls] == ["GET", "POST", "GET", "PATCH"]
    opened = github.issues[1]
    assert opened["title"] == "data: 2 broken links (week 2026-W43)"
    assert opened["labels"] == ["data"]
    assert opened["body"].endswith("two")
    assert len(github.issues) == 2


def test_issue_is_found_by_title_when_its_marker_was_edited_away() -> None:
    github = FakeGitHub([{"number": 9, "state": "open", "title": "data: 3 broken links (week 2026-W41)", "body": ""}])

    assert cl.upsert_issue(github, "o/r", "t0ken", "data: 1 broken links (week 2026-W42)", "x") == "updated #9"


def test_pull_requests_and_closed_issues_are_not_updated() -> None:
    github = FakeGitHub(
        [
            {"number": 3, "state": "closed", "title": "data: 1 broken links (week 2026-W40)", "body": ""},
            {"number": 4, "state": "open", "title": "data: 1 broken links (fix)", "body": "", "pull_request": {}},
        ]
    )

    assert cl.upsert_issue(github, "o/r", "t0ken", "data: 1 broken links (week 2026-W42)", "x") == "opened #102"


def write_catalog(tmp_path: Path, games: list[dict]) -> Path:
    path = tmp_path / "games.json"
    path.write_text(json.dumps({"schema_version": 1, "games": games}), encoding="utf-8")
    return path


def run_cli(tmp_path: Path, games: list[dict], routes: dict, *extra: str, api: object = None) -> tuple[int, str]:
    out = tmp_path / "links.md"
    argv = ["--catalog", str(write_catalog(tmp_path, games)), "--out", str(out), *extra]
    code = cl.main(argv, session=FakeSession(routes), resolve=resolve_public, api=api, today=SUNDAY)
    return code, out.read_text(encoding="utf-8") if out.exists() else ""


@pytest.fixture
def token(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "GITHUB_REPOSITORY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GH_TOKEN", "t0ken")
    return monkeypatch


def test_cli_exits_0_when_every_link_is_live(tmp_path: Path) -> None:
    code, report = run_cli(tmp_path, [WORLDLE], live(WORLDLE["url"]))

    assert code == 0
    assert "All 1 active entries passed." in report


def test_cli_exits_0_with_only_bot_walled_warnings(tmp_path: Path) -> None:
    code, report = run_cli(tmp_path, [ARTLE], walled(ARTLE["url"]))

    assert code == 0
    assert "bot-walled" in report


@pytest.mark.usefixtures("token")
def test_cli_exits_1_on_a_graveyard_entry_and_opens_the_issue(tmp_path: Path) -> None:
    github = FakeGitHub()
    routes = {**live(WORLDLE["url"]), **hijacked(MOVIEDLE["url"])}

    code, report = run_cli(tmp_path, [WORLDLE, MOVIEDLE], routes, "--open-issue", "--repo", "o/r", api=github)

    assert code == 1
    assert "moviedle" in report
    assert len(github.issues) == 1
    assert github.issues[0]["title"] == "data: 1 broken links (week 2026-W42)"
    assert github.issues[0]["labels"] == ["data"]
    assert github.issues[0]["body"] == report


@pytest.mark.usefixtures("token")
def test_second_cli_run_updates_the_issue_instead_of_opening_another(tmp_path: Path) -> None:
    github = FakeGitHub()
    args = ("--open-issue", "--repo", "o/r")

    run_cli(tmp_path, [MOVIEDLE], hijacked(MOVIEDLE["url"]), *args, api=github)
    code, _ = run_cli(tmp_path, [MOVIEDLE], hijacked(MOVIEDLE["url"]), *args, api=github)

    assert code == 1
    assert len(github.issues) == 1
    assert [call[0] for call in github.calls] == ["GET", "POST", "GET", "PATCH"]


@pytest.mark.usefixtures("token")
def test_cli_does_not_touch_issues_when_every_link_passes(tmp_path: Path) -> None:
    github = FakeGitHub()

    code, _ = run_cli(tmp_path, [WORLDLE], live(WORLDLE["url"]), "--open-issue", "--repo", "o/r", api=github)

    assert code == 0
    assert github.calls == []


def test_cli_takes_the_repository_from_the_environment(tmp_path: Path, token: pytest.MonkeyPatch) -> None:
    token.setenv("GITHUB_REPOSITORY", "o/r")
    github = FakeGitHub()

    code, _ = run_cli(tmp_path, [MOVIEDLE], hijacked(MOVIEDLE["url"]), "--open-issue", api=github)

    assert code == 1
    assert [call[0] for call in github.calls] == ["GET", "POST"]


def test_cli_needs_a_token_and_a_repository_to_open_the_issue(tmp_path: Path, token: pytest.MonkeyPatch) -> None:
    github = FakeGitHub()

    code, report = run_cli(tmp_path, [MOVIEDLE], hijacked(MOVIEDLE["url"]), "--open-issue", api=github)

    assert code == 2
    assert "moviedle" in report
    token.delenv("GH_TOKEN")
    assert run_cli(tmp_path, [MOVIEDLE], hijacked(MOVIEDLE["url"]), "--open-issue", "--repo", "o/r", api=github)[0] == 2
    assert github.calls == []


@pytest.mark.usefixtures("token")
def test_cli_refuses_a_malformed_repository(tmp_path: Path) -> None:
    github = FakeGitHub()

    code, _ = run_cli(tmp_path, [MOVIEDLE], hijacked(MOVIEDLE["url"]), "--open-issue", "--repo", "o/r/../x", api=github)

    assert code == 2
    assert github.calls == []


@pytest.mark.usefixtures("token")
def test_cli_exits_2_when_the_issue_cannot_be_written(tmp_path: Path) -> None:
    class Down:
        def request(self, *_args: object, **_kwargs: object) -> FakeApiResponse:
            return FakeApiResponse(503, {})

    code, _ = run_cli(tmp_path, [MOVIEDLE], hijacked(MOVIEDLE["url"]), "--open-issue", "--repo", "o/r", api=Down())

    assert code == 2


def test_cli_exits_2_on_an_unreadable_catalog(tmp_path: Path) -> None:
    bad = tmp_path / "games.json"
    bad.write_text("[]", encoding="utf-8")

    assert cl.main(["--catalog", str(bad), "--out", str(tmp_path / "links.md")]) == 2
    assert cl.main(["--catalog", str(tmp_path / "missing.json"), "--out", str(tmp_path / "links.md")]) == 2
    bad.write_text('{"games": "none"}', encoding="utf-8")
    assert cl.main(["--catalog", str(bad), "--out", str(tmp_path / "links.md")], session=FakeSession()) == 2


def casino_landing(url: str) -> dict[tuple[str, str], FakeResponse | Exception]:
    return {**hijacked(url), ("GET", LANDING): FakeResponse(200, body="<title>Lucky Spin Casino - Slots</title>")}


def test_redirect_to_a_gambling_page_on_another_site_is_hijacked() -> None:
    result = check(MOVIEDLE, casino_landing(MOVIEDLE["url"]))

    assert result.outcome == "hijacked"
    assert result.failed
    assert result.reason == (
        'redirects to another site (lucky-spin-777.net); its page title "Lucky Spin Casino - Slots" contains "casino"'
    )
    assert result.suggested_status == "retired"


def test_redirect_to_another_site_whose_title_cannot_be_read_is_a_cross_domain_redirect() -> None:
    routes = {**hijacked(MOVIEDLE["url"]), ("GET", LANDING): FakeResponse(500)}

    assert check(MOVIEDLE, routes).outcome == "redirected-cross-domain"


def test_report_suggests_retiring_a_hijacked_game() -> None:
    result = check(MOVIEDLE, casino_landing(MOVIEDLE["url"]))

    assert "| ❌ hijacked |" in cl.render_report([result], SUNDAY)
    assert "`active` → `retired`" in cl.render_report([result], SUNDAY)


def test_catalog_checks_broken_entries_when_asked() -> None:
    catalog = {"games": [WORLDLE, game("flagle", "https://www.flagle.io/", "flagle.io", status="broken")]}
    routes = {**live(WORLDLE["url"]), **live("https://www.flagle.io/")}

    results = cl.check_catalog(catalog, FakeSession(routes), resolve_public, [], statuses=("active", "broken"))

    assert sorted(result.entry["id"] for result in results) == ["flagle", "worldle"]


FLAGLE = game("flagle", "https://www.flagle.io/", "flagle.io", status="broken")


def run_tracked(
    tmp_path: Path, games: list[dict], routes: dict, day: date, *extra: str, api: object = None
) -> tuple[int, str]:
    """One weekly run that keeps its streaks in tmp_path/state.json and writes changes to tmp_path/status/."""
    state = tmp_path / "state.json"
    previous = tmp_path / "previous.json"
    if state.exists():
        state.replace(previous)
    status = tmp_path / "status"
    for name in ("changes.json", "pr-body.md"):
        (status / name).unlink(missing_ok=True)
    out = tmp_path / "links.md"
    argv = [
        "--catalog",
        str(write_catalog(tmp_path, games)),
        "--out",
        str(out),
        "--previous-state",
        str(previous),
        "--state-out",
        str(state),
        "--status-out",
        str(status),
        *extra,
    ]
    code = cl.main(argv, session=FakeSession(routes), resolve=resolve_public, api=api, today=day)
    return code, out.read_text(encoding="utf-8")


LAST_SUNDAY = date(2026, 10, 11)
NOT_FOUND = {("HEAD", WORLDLE["url"]): FakeResponse(404)}


@pytest.mark.usefixtures("token")
def test_a_single_failure_only_opens_the_issue(tmp_path: Path) -> None:
    github = FakeGitHub()

    code, report = run_tracked(tmp_path, [WORLDLE], NOT_FOUND, SUNDAY, "--open-issue", "--repo", "o/r", api=github)

    assert code == 1
    assert "| `worldle` |" in report
    assert len(github.issues) == 1
    assert not (tmp_path / "status" / "changes.json").exists()
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["games"] == {"worldle": {"check": "http-404", "since": "2026-W42", "last": "2026-W42"}}


@pytest.mark.usefixtures("token")
def test_a_game_failing_twice_gets_a_broken_status_change(tmp_path: Path) -> None:
    github = FakeGitHub()
    args = ("--open-issue", "--repo", "o/r")

    run_tracked(tmp_path, [WORLDLE], NOT_FOUND, LAST_SUNDAY, *args, api=github)
    code, _ = run_tracked(tmp_path, [WORLDLE], NOT_FOUND, SUNDAY, *args, api=github)

    assert code == 1
    assert len(github.issues) == 1  # the issue is still opened, then updated
    changes = json.loads((tmp_path / "status" / "changes.json").read_text(encoding="utf-8"))
    assert changes == {
        "week": "2026-W42",
        "changes": [
            {
                "id": "worldle",
                "status": "broken",
                "event": "broken",
                "note": "link check: http-404 in 2026-W41 and 2026-W42 (https://worldle.teuteuf.fr/ answered HTTP 404)",
            }
        ],
    }
    body = (tmp_path / "status" / "pr-body.md").read_text(encoding="utf-8")
    assert "| `worldle` | `active` → `broken` |" in body


def test_a_broken_game_passing_twice_is_restored_without_a_report_row(tmp_path: Path) -> None:
    routes = {**live(WORLDLE["url"]), **live(FLAGLE["url"])}

    run_tracked(tmp_path, [WORLDLE, FLAGLE], routes, LAST_SUNDAY)
    code, report = run_tracked(tmp_path, [WORLDLE, FLAGLE], routes, SUNDAY)

    assert code == 0
    assert "All 1 active entries passed." in report
    changes = json.loads((tmp_path / "status" / "changes.json").read_text(encoding="utf-8"))
    assert [(change["id"], change["status"], change["event"]) for change in changes["changes"]] == [
        ("flagle", "active", "restored")
    ]


def test_a_failing_broken_game_does_not_fail_the_run(tmp_path: Path) -> None:
    code, report = run_tracked(tmp_path, [WORLDLE, FLAGLE], live(WORLDLE["url"]), SUNDAY)

    assert code == 0
    assert "flagle" not in report


def test_a_hijacked_game_is_retired_on_the_first_run(tmp_path: Path) -> None:
    code, _ = run_tracked(tmp_path, [MOVIEDLE], casino_landing(MOVIEDLE["url"]), SUNDAY)

    assert code == 1
    changes = json.loads((tmp_path / "status" / "changes.json").read_text(encoding="utf-8"))
    assert [(change["id"], change["status"]) for change in changes["changes"]] == [("moviedle", "retired")]
    assert "`active` → `retired`" in (tmp_path / "status" / "pr-body.md").read_text(encoding="utf-8")


def test_an_unreadable_previous_state_starts_over(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "state.json").write_text("garbage", encoding="utf-8")

    code, _ = run_tracked(tmp_path, [WORLDLE], NOT_FOUND, SUNDAY)

    assert code == 1
    assert "starting the streaks over" in capsys.readouterr().err
    assert not (tmp_path / "status" / "changes.json").exists()
    assert json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))["games"]["worldle"]["since"] == "2026-W42"
