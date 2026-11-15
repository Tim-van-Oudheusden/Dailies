import datetime as dt
import hashlib
import importlib.util
import io
import os
import shutil
import subprocess
import urllib.error
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_pages.py"
BASE = "https://tim-van-oudheusden.github.io/Dailies/v1/"
NOW = dt.datetime(2026, 11, 8, 3, 23, tzinfo=dt.UTC)
GAMES = b'{"schema_version": 1, "games": []}\n'
POPULARITY = b'{"schema_version": 1, "shelves": []}\n'
OLD = b'{"schema_version": 1, "games": ["old"]}\n'


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_pages", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cp = load_script()


def checkout(tmp_path: Path, games: bytes = GAMES, popularity: bytes = POPULARITY) -> Path:
    data = tmp_path / "data" / "v1"
    data.mkdir(parents=True)
    (data / "games.json").write_bytes(games)
    (data / "popularity.json").write_bytes(popularity)
    return tmp_path


class FakePages:
    """Serves `files` by URL; any other URL answers like a Pages 404.

    `failures` maps a URL to the errors its first requests raise, in order, before it is served.
    """

    def __init__(self, files: dict[str, bytes], failures: dict[str, list[OSError]] | None = None) -> None:
        self.files = files
        self.failures = failures or {}
        self.requests: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.requests.append(url)
        if self.failures.get(url):
            raise self.failures[url].pop(0)
        if url not in self.files:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore[arg-type]
        return self.files[url]


def serving(games: bytes = GAMES, popularity: bytes = POPULARITY) -> FakePages:
    return FakePages({BASE + "games.json": games, BASE + "popularity.json": popularity})


def committed_ago(age: dt.timedelta):  # noqa: ANN201 - a test double
    def committed(_repo: Path, _path: str) -> dt.datetime:
        return NOW - age

    return committed


def run(
    repo: Path, fetch: FakePages, age: dt.timedelta = dt.timedelta(days=2), sleeps: list[float] | None = None
) -> int:
    pauses = [] if sleeps is None else sleeps
    return cp.main(
        ["--repo", str(repo)], fetch=fetch, committed=committed_ago(age), now=lambda: NOW, sleep=pauses.append
    )


def reset() -> OSError:
    """What urlopen raised on the night of #462: the connection dropped before Pages answered."""
    return urllib.error.URLError(ConnectionResetError(104, "Connection reset by peer"))


def http_error(code: int) -> OSError:
    return urllib.error.HTTPError(BASE + "games.json", code, "Error", {}, None)  # type: ignore[arg-type]


def test_matching_files_pass_and_both_are_fetched_from_pages(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pages = serving()
    assert run(checkout(tmp_path), pages) == 0
    assert pages.requests == [BASE + "games.json", BASE + "popularity.json"]
    out = capsys.readouterr().out
    assert f"games.json: Pages serves this checkout's copy (sha256 {hashlib.sha256(GAMES).hexdigest()[:16]})" in out
    assert "popularity.json: Pages serves this checkout's copy" in out


def test_the_base_url_is_the_first_data_url_the_app_fetches() -> None:
    config = (ROOT / "dailies" / "config.py.in").read_text(encoding="utf-8")
    # The quoted entries of DATA_URLS, in order; a comment above the list names the fallback too.
    assert config.index(f'    "{cp.BASE_URL}",') < config.index('    "https://raw.githubusercontent.com/')


def test_an_old_deployment_fails_with_both_checksums_and_the_runbook(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(checkout(tmp_path), serving(games=OLD)) == 1
    out = capsys.readouterr().out
    assert (
        f"games.json: Pages serves sha256 {hashlib.sha256(OLD).hexdigest()[:16]},"
        f" this checkout has {hashlib.sha256(GAMES).hexdigest()[:16]} (last changed 2 days ago)"
    ) in out
    # The other file is still checked and reported.
    assert "popularity.json: Pages serves this checkout's copy" in out
    assert "docs/runbooks/pages.md" in out


def test_a_mismatch_younger_than_the_grace_passes_and_says_when_it_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(checkout(tmp_path), serving(popularity=OLD), age=dt.timedelta(minutes=59)) == 0
    out = capsys.readouterr().out
    assert "popularity.json: Pages serves sha256" in out
    assert "(last changed 59 minutes ago); waiting for the deploy, this fails once the change is 1 hour old" in out
    assert "docs/runbooks/pages.md" not in out


def test_a_mismatch_fails_once_the_change_is_exactly_the_grace_old(tmp_path: Path) -> None:
    assert run(checkout(tmp_path), serving(popularity=OLD), age=cp.GRACE) == 1


def test_a_file_pages_does_not_serve_fails_at_once_whatever_its_age(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pages = FakePages({BASE + "popularity.json": POPULARITY})
    assert run(checkout(tmp_path), pages, age=dt.timedelta(minutes=1)) == 1
    out = capsys.readouterr().out
    assert "games.json: Pages did not serve it: HTTP Error 404: Not Found" in out
    assert "docs/runbooks/pages.md" in out


# A dropped connection, a timeout, a 429 and a 5xx are what the app itself treats as transient (it tries the next
# data URL), so one of them on a single request says nothing about what Pages serves (#462).
@pytest.mark.parametrize(
    "error",
    [
        reset(),
        urllib.error.URLError(TimeoutError("timed out")),
        TimeoutError("timed out"),
        http_error(500),
        http_error(429),
    ],
    ids=["reset", "urlopen-timeout", "read-timeout", "500", "429"],
)
def test_a_transient_failure_is_retried_and_passes_when_pages_then_serves_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], error: OSError
) -> None:
    pages = FakePages(
        {BASE + "games.json": GAMES, BASE + "popularity.json": POPULARITY}, {BASE + "games.json": [error]}
    )
    sleeps: list[float] = []
    assert run(checkout(tmp_path), pages, sleeps=sleeps) == 0
    assert pages.requests == [BASE + "games.json", BASE + "games.json", BASE + "popularity.json"]
    assert sleeps == [cp.RETRY_DELAY]
    assert "games.json: Pages serves this checkout's copy" in capsys.readouterr().out


def test_a_connection_that_keeps_failing_fails_after_the_last_attempt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pages = FakePages(
        {BASE + "games.json": GAMES, BASE + "popularity.json": POPULARITY},
        {BASE + "games.json": [reset() for _ in range(cp.ATTEMPTS)]},
    )
    sleeps: list[float] = []
    assert run(checkout(tmp_path), pages, sleeps=sleeps) == 1
    assert pages.requests.count(BASE + "games.json") == cp.ATTEMPTS
    assert sleeps == [cp.RETRY_DELAY] * (cp.ATTEMPTS - 1)
    out = capsys.readouterr().out
    assert (
        f"games.json: Pages did not serve it: <urlopen error [Errno 104] Connection reset by peer>"
        f" ({cp.ATTEMPTS} attempts, {cp.RETRY_DELAY} s apart)"
    ) in out
    assert "docs/runbooks/pages.md" in out


def test_a_404_is_not_retried(tmp_path: Path) -> None:
    # A 404 does not fall back in the app (docs/runbooks/pages.md), so it is an answer, not a transient failure.
    pages = FakePages({BASE + "popularity.json": POPULARITY})
    sleeps: list[float] = []
    assert run(checkout(tmp_path), pages, sleeps=sleeps) == 1
    assert pages.requests.count(BASE + "games.json") == 1
    assert sleeps == []


def test_the_retries_fit_the_nightly_job() -> None:
    # Two files, each waiting out every delay and every attempt's timeout, stay well inside the job's 15 minutes.
    assert len(cp.FILES) * (cp.ATTEMPTS * cp.TIMEOUT + (cp.ATTEMPTS - 1) * cp.RETRY_DELAY) <= 5 * 60


def test_an_unreadable_checkout_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(tmp_path, serving()) == 2
    assert "check_pages: could not read" in capsys.readouterr().err


# What last_commit raises when git fails, when git is not on PATH, and when it prints no date (a path no commit has).
@pytest.mark.parametrize(
    "error",
    [subprocess.CalledProcessError(128, ["git"]), FileNotFoundError("git"), ValueError("Invalid isoformat string: ''")],
    ids=["git-failed", "no-git", "no-date"],
)
def test_a_commit_time_that_cannot_be_read_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], error: Exception
) -> None:
    def broken(_repo: Path, _path: str) -> dt.datetime:
        raise error

    rc = cp.main(["--repo", str(checkout(tmp_path))], fetch=serving(games=OLD), committed=broken, now=lambda: NOW)
    assert rc == 2
    assert "check_pages: could not read the commit time of data/v1/games.json" in capsys.readouterr().err


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_last_commit_reads_the_committer_time_of_the_file(tmp_path: Path) -> None:
    repo = checkout(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.org",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.org",
        "GIT_AUTHOR_DATE": "2026-11-01T10:00:00Z",
        "GIT_COMMITTER_DATE": "2026-11-02T12:33:52Z",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    for command in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "data"]):
        subprocess.run(["git", "-C", str(repo), *command], env=env, check=True)  # noqa: S603, S607 - test repo

    assert cp.last_commit(repo, "data/v1/games.json") == dt.datetime(2026, 11, 2, 12, 33, 52, tzinfo=dt.UTC)

    # A later commit that touches only the other file moves that file's time, not this one's. A full clone has both
    # commits; the workflow's shallow clone has one, so this is what a local run reports.
    (repo / "data" / "v1" / "popularity.json").write_bytes(OLD)
    later = {**env, "GIT_AUTHOR_DATE": "2026-11-05T08:00:00Z", "GIT_COMMITTER_DATE": "2026-11-05T08:00:00Z"}
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "popularity"], env=later, check=True)  # noqa: S603, S607

    assert cp.last_commit(repo, "data/v1/games.json") == dt.datetime(2026, 11, 2, 12, 33, 52, tzinfo=dt.UTC)
    assert cp.last_commit(repo, "data/v1/popularity.json") == dt.datetime(2026, 11, 5, 8, 0, tzinfo=dt.UTC)


@pytest.mark.parametrize(
    ("age", "text"),
    [
        (dt.timedelta(days=1, hours=5), "1 day"),
        (dt.timedelta(days=3), "3 days"),
        (dt.timedelta(hours=1, minutes=59), "1 hour"),
        (dt.timedelta(hours=23), "23 hours"),
        (dt.timedelta(minutes=1, seconds=30), "1 minute"),
    ],
)
def test_age_text_names_the_largest_whole_unit(age: dt.timedelta, text: str) -> None:
    assert cp.age_text(age) == text


def test_the_defaults_compare_this_repository_against_the_clock_in_utc() -> None:
    # nightly-compliance.sh runs the script with no arguments, so --repo and the clock come from the defaults.
    files = {BASE + name: (ROOT / "data" / "v1" / name).read_bytes() for name in cp.FILES}
    assert cp.main([], fetch=FakePages(files)) == 0

    # The committer time git prints carries an offset, so the default clock must too, or the subtraction raises.
    def yesterday(_repo: Path, _path: str) -> dt.datetime:
        return dt.datetime.now(dt.UTC) - dt.timedelta(days=1, minutes=5)

    stale = {**files, BASE + "games.json": OLD}
    assert cp.main([], fetch=FakePages(stale), committed=yesterday) == 1


def test_https_get_refuses_a_url_that_is_not_https() -> None:
    with pytest.raises(OSError, match="not https"):
        cp.https_get("http://tim-van-oudheusden.github.io/Dailies/v1/games.json")


def test_https_get_returns_the_body_and_sets_a_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, float]] = []

    def urlopen(url: str, timeout: float) -> io.BytesIO:
        calls.append((url, timeout))
        return io.BytesIO(GAMES)

    monkeypatch.setattr(cp.urllib.request, "urlopen", urlopen)
    assert cp.https_get(BASE + "games.json") == GAMES
    assert calls == [(BASE + "games.json", cp.TIMEOUT)]
