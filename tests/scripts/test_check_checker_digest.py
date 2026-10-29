import datetime as dt
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
MANIFESTS = "https://ghcr.io/v2/flathub/flatpak-external-data-checker/manifests/"
MANIFEST_URL = MANIFESTS + "latest"
BLOBS = "https://ghcr.io/v2/flathub/flatpak-external-data-checker/blobs/"
NOW = dt.datetime(2026, 11, 10, 12, 0, tzinfo=dt.UTC)
PINNED_BUILT = "2026-06-14T05:24:16.208759428Z"

WORKFLOW = f"""
jobs:
  check:
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: docker://ghcr.io/flathub/flatpak-external-data-checker@{PINNED}
        with:
          args: --update
"""

# The pin with the date comment that --bump rewrites, as in .github/workflows/external-data-checker.yml.
DATED_WORKFLOW = f"""
jobs:
  check:
    steps:
      # Pinned by digest: ghcr.io/flathub/flatpak-external-data-checker:latest as of 2026-10-16.
      - uses: docker://ghcr.io/flathub/flatpak-external-data-checker@{PINNED}
        with:
          args: --edit-only
"""


def built(age: dt.timedelta) -> str:
    """An image config `created` time exactly `age` before NOW, in the nanosecond form ghcr.io images carry."""
    return (NOW - age).strftime("%Y-%m-%dT%H:%M:%S.000000000Z")


def clock() -> dt.datetime:
    return NOW


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_checker_digest", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ccd = load_script()


class FakeRegistry:
    """Answers (method, url) like ghcr.io does; records each request's headers.

    `built` maps an image (index) digest to its config's `created` time. Each index lists an attestation manifest and
    the linux/amd64 manifest `<digest>-amd64`, whose config blob is `<digest>-config`.
    """

    def __init__(
        self, latest: str = PINNED, fail: Exception | None = None, built: dict[str, str] | None = None
    ) -> None:
        self.latest = latest
        self.fail = fail
        self.built = {PINNED: PINNED_BUILT, NEWER: "2026-06-20T08:00:00Z"} if built is None else built
        self.requests: list[tuple[str, str, dict[str, str]]] = []

    def __call__(self, method: str, url: str, headers: dict[str, str]) -> tuple[dict[str, str], bytes]:
        self.requests.append((method, url, headers))
        if self.fail is not None:
            raise self.fail
        if url == AUTH_URL:
            return {}, json.dumps({"token": "anon"}).encode()
        if headers.get("Authorization") == "Bearer anon":
            if url == MANIFEST_URL:
                return {"docker-content-digest": self.latest}, b""
            reference = url.removeprefix(MANIFESTS).removeprefix(BLOBS)
            if url.startswith(MANIFESTS) and reference in self.built:
                return {}, json.dumps(self.index(reference)).encode()
            if url.startswith(MANIFESTS) and reference.endswith("-amd64"):
                config = {"digest": reference.removesuffix("-amd64") + "-config"}
                return {}, json.dumps({"config": config}).encode()
            if url.startswith(BLOBS) and reference.removesuffix("-config") in self.built:
                return {}, json.dumps({"created": self.built[reference.removesuffix("-config")]}).encode()
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, io.BytesIO())  # type: ignore[arg-type]

    @staticmethod
    def index(digest: str) -> dict[str, object]:
        return {
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [
                {"digest": f"{digest}-attestation", "platform": {"architecture": "unknown", "os": "unknown"}},
                {"digest": f"{digest}-amd64", "platform": {"architecture": "amd64", "os": "linux"}},
            ],
        }


def drifted(latest_age: dt.timedelta) -> FakeRegistry:
    """A registry whose `:latest` is NEWER, built `latest_age` before NOW; the pin is PINNED."""
    return FakeRegistry(latest=NEWER, built={PINNED: PINNED_BUILT, NEWER: built(latest_age)})


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


@pytest.mark.parametrize("age", [dt.timedelta(0), dt.timedelta(days=9, hours=23)], ids=["just-built", "9d23h"])
def test_drift_passes_while_latest_is_younger_than_ten_days(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], age: dt.timedelta
) -> None:
    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))], fetch=drifted(age), now=clock)

    out = capsys.readouterr().out
    assert rc == 0
    assert "moved on" in out
    assert f"latest: {NEWER}" in out


@pytest.mark.parametrize("age", [dt.timedelta(days=10), dt.timedelta(days=40)], ids=["10d", "40d"])
def test_drift_fails_once_latest_is_ten_days_old_with_both_digests_and_the_pin_pull_request(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], age: dt.timedelta
) -> None:
    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))], fetch=drifted(age), now=clock)

    out = capsys.readouterr().out
    assert rc == 1
    assert f"pinned: {PINNED}" in out
    assert f"latest: {NEWER}" in out
    assert "ci/checker-pin" in out


@pytest.mark.parametrize(
    "registry",
    [
        FakeRegistry(latest=NEWER, built={}),
        FakeRegistry(latest=NEWER, built={NEWER: "yesterday"}),
        FakeRegistry(latest=NEWER, built={NEWER: "2026-11-01T00:00:00"}),
    ],
    ids=["no-image", "not-a-date", "no-timezone"],
)
def test_an_unreadable_build_time_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], registry: FakeRegistry
) -> None:
    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))], fetch=registry, now=clock)

    assert rc == 2
    assert "could not read ghcr.io" in capsys.readouterr().err


def test_an_index_without_a_linux_amd64_image_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(FakeRegistry, "index", staticmethod(lambda digest: {"manifests": [{"digest": digest}]}))

    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))], fetch=drifted(dt.timedelta(days=12)), now=clock)

    assert rc == 2
    assert "linux/amd64" in capsys.readouterr().err


# --bump: the checker-pin job of nightly-compliance.yml.


def test_bump_waits_while_latest_is_younger_than_three_days(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    workflow = write_workflow(tmp_path, DATED_WORKFLOW)
    body = tmp_path / "pr-body.md"

    rc = ccd.main(
        ["--workflow", str(workflow), "--bump", "--pr-body", str(body)],
        fetch=drifted(dt.timedelta(days=2, hours=23)),
        now=clock,
    )

    assert rc == 0
    assert workflow.read_text(encoding="utf-8") == DATED_WORKFLOW
    assert not body.exists()
    assert "3 days" in capsys.readouterr().out


def test_bump_moves_the_pin_and_its_date_once_latest_is_three_days_old(tmp_path: Path) -> None:
    workflow = write_workflow(tmp_path, DATED_WORKFLOW)
    body = tmp_path / "pr-body.md"

    rc = ccd.main(
        ["--workflow", str(workflow), "--bump", "--pr-body", str(body)],
        fetch=drifted(dt.timedelta(days=3)),
        now=clock,
    )

    assert rc == 0
    assert workflow.read_text(encoding="utf-8") == DATED_WORKFLOW.replace(PINNED, NEWER).replace(
        ":latest as of 2026-10-16", ":latest as of 2026-11-10"
    )
    text = body.read_text(encoding="utf-8")
    assert f"`{PINNED}`" in text
    assert f"`{NEWER}`" in text
    assert "2026-06-14 05:24 UTC" in text
    assert "2026-11-07 12:00 UTC" in text
    # Every upstream commit between the two builds, the second build's day included.
    assert (
        "https://github.com/flathub-infra/flatpak-external-data-checker/commits/master?since=2026-06-14&until=2026-11-08"
        in text
    )


def test_bump_leaves_a_current_pin_alone(tmp_path: Path) -> None:
    workflow = write_workflow(tmp_path, DATED_WORKFLOW)
    body = tmp_path / "pr-body.md"

    rc = ccd.main(["--workflow", str(workflow), "--bump", "--pr-body", str(body)], fetch=FakeRegistry(), now=clock)

    assert rc == 0
    assert workflow.read_text(encoding="utf-8") == DATED_WORKFLOW
    assert not body.exists()


def test_bump_without_the_date_comment_is_an_error_and_changes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = write_workflow(tmp_path)

    rc = ccd.main(["--workflow", str(workflow), "--bump"], fetch=drifted(dt.timedelta(days=5)), now=clock)

    assert rc == 2
    assert workflow.read_text(encoding="utf-8") == WORKFLOW
    assert "as of" in capsys.readouterr().err


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


# 499, 520 and 530 are codes http.HTTPStatus does not name (Cloudflare uses 520-530).
@pytest.mark.parametrize("status", [301, 401, 404, 429, 499, 503, 520, 530])
def test_https_fetch_raises_oserror_on_an_answer_that_is_not_2xx(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    connections = FakeConnections(FakeResponse(status, "Nope", [], b""))
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", connections)

    with pytest.raises(OSError, match=rf"^HEAD {re.escape(MANIFEST_URL)}: HTTP {status} Nope$"):
        ccd.https_fetch("HEAD", MANIFEST_URL, {})
    assert connections.opened[0]["closed"] is True


def test_https_fetch_accepts_a_2xx_status_http_does_not_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", FakeConnections(FakeResponse(299, "", [], b"ok")))

    assert ccd.https_fetch("GET", AUTH_URL, {})[1] == b"ok"


def test_https_fetch_raises_oserror_when_the_connection_breaks(monkeypatch: pytest.MonkeyPatch) -> None:
    connections = FakeConnections(fail=http.client.RemoteDisconnected("Remote end closed connection"))
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", connections)

    with pytest.raises(OSError, match="RemoteDisconnected"):
        ccd.https_fetch("GET", AUTH_URL, {})
    assert connections.opened[0]["closed"] is True


class SequencedConnections(FakeConnections):
    """Answers the requests in order, one response each."""

    def __init__(self, *responses: FakeResponse) -> None:
        super().__init__()
        self.responses = list(responses)

    def getresponse(self) -> FakeResponse:
        return self.responses.pop(0)


BLOB_URL = BLOBS + "sha256:" + "c" * 64
SIGNED_BLOB = "https://pkg-containers.githubusercontent.com/ghcrblobs/blobs/sha256:cc?sig=x&se=1"


def test_https_fetch_follows_a_blob_redirect_without_the_registry_token(monkeypatch: pytest.MonkeyPatch) -> None:
    connections = SequencedConnections(
        FakeResponse(307, "Temporary Redirect", [("Location", SIGNED_BLOB)], b""),
        FakeResponse(200, "OK", [], b'{"created": "2026-10-29T15:56:36Z"}'),
    )
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", connections)

    _, body = ccd.https_fetch("GET", BLOB_URL, {"Authorization": "Bearer anon"})

    assert body == b'{"created": "2026-10-29T15:56:36Z"}'
    assert [(c["netloc"], c["target"], c["headers"], c["closed"]) for c in connections.opened] == [
        ("ghcr.io", BLOB_URL.removeprefix("https://ghcr.io"), {"Authorization": "Bearer anon"}, True),
        ("pkg-containers.githubusercontent.com", "/ghcrblobs/blobs/sha256:cc?sig=x&se=1", {}, True),
    ]


@pytest.mark.parametrize(
    "location",
    ["http://pkg-containers.githubusercontent.com/blob", "ftp://example.org/blob"],
    ids=["plain-http", "ftp"],
)
def test_https_fetch_refuses_a_redirect_away_from_https(monkeypatch: pytest.MonkeyPatch, location: str) -> None:
    connections = SequencedConnections(FakeResponse(307, "Temporary Redirect", [("Location", location)], b""))
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", connections)

    with pytest.raises(OSError, match=rf": redirect to {re.escape(location)} is not https$"):
        ccd.https_fetch("GET", BLOB_URL, {"Authorization": "Bearer anon"})
    assert len(connections.opened) == 1


def test_https_fetch_stops_after_too_many_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = FakeResponse(302, "Found", [("Location", BLOB_URL)], b"")
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", SequencedConnections(*[loop] * 10))

    with pytest.raises(OSError, match="redirects"):
        ccd.https_fetch("GET", BLOB_URL, {})


@pytest.mark.parametrize(
    "connections",
    [
        FakeConnections(FakeResponse(401, "Unauthorized", [], b"")),
        FakeConnections(FakeResponse(520, "", [], b"")),
        FakeConnections(fail=http.client.IncompleteRead(b"")),
    ],
    ids=["http-401", "http-520", "incomplete-read"],
)
def test_the_default_fetch_reports_a_failed_request_as_unreadable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], connections: FakeConnections
) -> None:
    monkeypatch.setattr(ccd.http.client, "HTTPSConnection", connections)

    rc = ccd.main(["--workflow", str(write_workflow(tmp_path))])

    assert rc == 2
    assert f"could not read ghcr.io: GET {AUTH_URL}" in capsys.readouterr().err
