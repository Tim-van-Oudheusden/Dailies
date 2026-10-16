import http.client
import importlib.util
import io
import json
import re
import urllib.error
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_checker_digest.py"
PINNED = "sha256:" + "a" * 64
NEWER = "sha256:" + "b" * 64
AUTH_URL = "https://ghcr.io/token?scope=repository:flathub/flatpak-external-data-checker:pull"
MANIFEST_URL = "https://ghcr.io/v2/flathub/flatpak-external-data-checker/manifests/latest"

WORKFLOW = f"""
jobs:
  check:
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: docker://ghcr.io/flathub/flatpak-external-data-checker@{PINNED}
        with:
          args: --update
"""


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_checker_digest", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ccd = load_script()


class FakeRegistry:
    """Answers (method, url) like ghcr.io does; records each request's headers."""

    def __init__(self, latest: str = PINNED, fail: Exception | None = None) -> None:
        self.latest = latest
        self.fail = fail
        self.requests: list[tuple[str, str, dict[str, str]]] = []

    def __call__(self, method: str, url: str, headers: dict[str, str]) -> tuple[dict[str, str], bytes]:
        self.requests.append((method, url, headers))
        if self.fail is not None:
            raise self.fail
        if url == AUTH_URL:
            return {}, json.dumps({"token": "anon"}).encode()
        if url == MANIFEST_URL and headers.get("Authorization") == "Bearer anon":
            return {"docker-content-digest": self.latest}, b""
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, io.BytesIO())  # type: ignore[arg-type]


def write_workflow(tmp_path: Path, text: str = WORKFLOW) -> Path:
    path = tmp_path / "external-data-checker.yml"
    path.write_text(text, encoding="utf-8")
    return path


def test_reads_the_pinned_digest_from_the_workflow() -> None:
    assert ccd.pinned_digest(WORKFLOW) == PINNED


@pytest.mark.parametrize(
    "text",
    [
        "steps:\n  - uses: docker://ghcr.io/flathub/flatpak-external-data-checker:latest\n",
        WORKFLOW + WORKFLOW.replace(PINNED, NEWER),
    ],
    ids=["unpinned", "two-pins"],
)
def test_a_workflow_without_exactly_one_pin_is_an_error(text: str) -> None:
    with pytest.raises(ccd.DigestError, match="digest"):
        ccd.pinned_digest(text)


def test_reads_the_latest_digest_with_an_anonymous_token_and_index_accept_headers() -> None:
    registry = FakeRegistry(latest=NEWER)

    assert ccd.latest_digest(registry) == NEWER
    method, url, headers = registry.requests[-1]
    assert (method, url) == ("HEAD", MANIFEST_URL)
    accept = headers["Accept"]
    assert "application/vnd.oci.image.index.v1+json" in accept
    assert "application/vnd.docker.distribution.manifest.list.v2+json" in accept


def test_a_matching_digest_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))], fetch=FakeRegistry())

    assert rc == 0
    assert f"up to date: {PINNED}" in capsys.readouterr().out


def test_drift_fails_with_both_digests_and_the_bump_procedure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))], fetch=FakeRegistry(latest=NEWER))

    out = capsys.readouterr().out
    assert rc == 1
    assert f"pinned: {PINNED}" in out
    assert f"latest: {NEWER}" in out
    assert "CONTRIBUTING.md" in out


def test_an_unreachable_registry_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry = FakeRegistry(fail=urllib.error.URLError("Name or service not known"))

    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))], fetch=registry)

    assert rc == 2
    assert "could not read ghcr.io" in capsys.readouterr().err


def test_a_response_without_a_digest_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))], fetch=FakeRegistry(latest=""))

    assert rc == 2
    assert "Docker-Content-Digest" in capsys.readouterr().err


def test_a_workflow_without_a_pin_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = ccd.main(["--workflow", str(write_workflow(tmp_path, "jobs: {}\n"))], fetch=FakeRegistry())

    assert rc == 2
    assert "digest" in capsys.readouterr().err


@pytest.mark.parametrize(
    "body",
    [b"<html>rate limited</html>", b'{"access_token": "anon"}', b'["anon"]'],
    ids=["not-json", "no-token", "not-an-object"],
)
def test_a_token_answer_without_a_token_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], body: bytes
) -> None:
    def fetch(_method: str, _url: str, _headers: dict[str, str]) -> tuple[dict[str, str], bytes]:
        return {}, body

    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))], fetch=fetch)

    assert rc == 2
    assert "no token in the ghcr.io /token answer" in capsys.readouterr().err


# https_fetch, the default Fetch, against a stand-in for http.client.HTTPSConnection.


class FakeResponse:
    def __init__(self, status: int, reason: str, headers: list[tuple[str, str]], body: bytes) -> None:
        self.status = status
        self.reason = reason
        self.headers = headers
        self.body = body

    def read(self) -> bytes:
        return self.body

    def getheaders(self) -> list[tuple[str, str]]:
        return self.headers


class FakeConnections:
    """Replaces HTTPSConnection: answers every request with `response`, or raises `fail`; records each connection."""

    def __init__(self, response: FakeResponse | None = None, fail: Exception | None = None) -> None:
        self.response = response
        self.fail = fail
        self.opened: list[dict[str, object]] = []

    def __call__(self, netloc: str, timeout: float) -> "FakeConnections":
        self.opened.append({"netloc": netloc, "timeout": timeout, "closed": False})
        return self

    def request(self, method: str, target: str, headers: dict[str, str]) -> None:
        self.opened[-1].update(method=method, target=target, headers=headers)
        if self.fail is not None:
            raise self.fail

    def getresponse(self) -> FakeResponse:
        assert self.response is not None
        return self.response

    def close(self) -> None:
        self.opened[-1]["closed"] = True


def test_https_fetch_sends_the_request_and_returns_the_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    connections = FakeConnections(FakeResponse(200, "OK", [("Docker-Content-Digest", NEWER)], b'{"token": "anon"}'))
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", connections)

    headers, body = ccd.https_fetch("GET", AUTH_URL, {"Accept": "application/json"})

    assert (dict(headers), body) == ({"Docker-Content-Digest": NEWER}, b'{"token": "anon"}')
    assert connections.opened == [
        {
            "netloc": "ghcr.io",
            "timeout": ccd.TIMEOUT,
            "method": "GET",
            "target": "/token?scope=repository:flathub/flatpak-external-data-checker:pull",
            "headers": {"Accept": "application/json"},
            "closed": True,
        }
    ]


def test_https_fetch_requests_a_url_without_a_query_by_its_path(monkeypatch: pytest.MonkeyPatch) -> None:
    connections = FakeConnections(FakeResponse(200, "OK", [], b""))
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", connections)

    ccd.https_fetch("HEAD", MANIFEST_URL, {})

    assert connections.opened[0]["target"] == "/v2/flathub/flatpak-external-data-checker/manifests/latest"


@pytest.mark.parametrize("status", [301, 401, 404, 429, 503])
def test_https_fetch_raises_oserror_on_an_answer_that_is_not_2xx(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    connections = FakeConnections(FakeResponse(status, "Nope", [], b""))
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", connections)

    with pytest.raises(OSError, match=rf"^HEAD {re.escape(MANIFEST_URL)}: HTTP {status} Nope$"):
        ccd.https_fetch("HEAD", MANIFEST_URL, {})
    assert connections.opened[0]["closed"] is True


def test_https_fetch_raises_oserror_when_the_connection_breaks(monkeypatch: pytest.MonkeyPatch) -> None:
    connections = FakeConnections(fail=http.client.RemoteDisconnected("Remote end closed connection"))
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", connections)

    with pytest.raises(OSError, match="RemoteDisconnected"):
        ccd.https_fetch("GET", AUTH_URL, {})
    assert connections.opened[0]["closed"] is True


@pytest.mark.parametrize(
    "connections",
    [
        FakeConnections(FakeResponse(401, "Unauthorized", [], b"")),
        FakeConnections(fail=http.client.IncompleteRead(b"")),
    ],
    ids=["http-401", "incomplete-read"],
)
def test_the_default_fetch_reports_a_failed_request_as_unreadable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], connections: FakeConnections
) -> None:
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", connections)

    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))])

    assert rc == 2
    assert f"could not read ghcr.io: GET {AUTH_URL}" in capsys.readouterr().err
