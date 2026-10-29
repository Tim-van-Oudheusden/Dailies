#!/usr/bin/env python3
"""Compare the pinned flatpak-external-data-checker image digest with the image's current `:latest`.

.github/workflows/external-data-checker.yml runs `docker://ghcr.io/flathub/flatpak-external-data-checker@sha256:…`.
Dependabot does not update docker:// references, and Flathub publishes `:latest` in bursts (several images a day, then
nothing for months), so this script tracks the pin from the image's build time: its config's `created` field. It asks
ghcr.io anonymously: a pull token from /token, a HEAD of manifests/latest that accepts the multi-arch index types for
the Docker-Content-Digest header, then index -> linux/amd64 manifest -> config blob for the build time. The standard
library is enough; the script needs no requirements.

Usage:
    python -I scripts/check_checker_digest.py [--workflow FILE] [--bump [--pr-body FILE]]

Without --bump (scripts/nightly-compliance.sh, each night): exits 0 when the pin is the current `:latest` or `:latest`
is younger than GRACE, 1 when a newer `:latest` is GRACE old and still not pinned, and 2 when the workflow holds no
single pin or ghcr.io could not be read.

With --bump (the checker-pin job of nightly-compliance.yml): once `:latest` is SETTLE old, moves the pin and its
`:latest as of <date>` comment to it and writes the pull request body to --pr-body. Exits 0 whether or not it moved the
pin, 2 on the errors above or when the workflow has no single date comment.
"""

import argparse
import datetime as dt
import http
import http.client
import json
import re
import sys
import urllib.parse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

REPOSITORY = "flathub/flatpak-external-data-checker"
UPSTREAM = "https://github.com/flathub-infra/flatpak-external-data-checker"
WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "external-data-checker.yml"
TOKEN_URL = f"https://ghcr.io/token?scope=repository:{REPOSITORY}:pull"
MANIFESTS_URL = f"https://ghcr.io/v2/{REPOSITORY}/manifests/"
MANIFEST_URL = MANIFESTS_URL + "latest"
BLOBS_URL = f"https://ghcr.io/v2/{REPOSITORY}/blobs/"
# The index types first: the digest of a multi-arch image is the digest of its index, which is what the pin names.
ACCEPT = (
    "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, "
    "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json"
)
PIN = re.compile(rf"docker://ghcr\.io/{re.escape(REPOSITORY)}@(sha256:[0-9a-f]{{64}})")
AS_OF = re.compile(rf"(ghcr\.io/{re.escape(REPOSITORY)}:latest as of )\d{{4}}-\d{{2}}-\d{{2}}")
# The runners are x86_64; the build time of that image stands for the whole index.
PLATFORM = {"os": "linux", "architecture": "amd64"}
# --bump waits this long after the newest `:latest` was built, so a burst of upstream pushes gives one pull request.
SETTLE = dt.timedelta(days=3)
# The nightly row fails once a `:latest` this old is still not pinned: the pin pull request has waited a week.
GRACE = dt.timedelta(days=10)
TIMEOUT = 30
# ghcr.io answers a blob GET with a redirect to a signed storage URL on another host.
REDIRECTS = frozenset({301, 302, 303, 307, 308})
MAX_REDIRECTS = 3

# (method, url, headers) -> (response headers, body). Raises OSError when the request fails or is not answered 2xx.
Fetch = Callable[[str, str, dict[str, str]], tuple[Mapping[str, str], bytes]]
Clock = Callable[[], dt.datetime]


class DigestError(Exception):
    """The workflow or ghcr.io did not yield a digest or a build time; the message says why."""


def https_fetch(method: str, url: str, headers: dict[str, str]) -> tuple[Mapping[str, str], bytes]:
    """Send one HTTPS request, following redirects; the default Fetch.

    A redirect to another host drops the Authorization header: the ghcr.io token is not for the storage host.
    """
    for _ in range(MAX_REDIRECTS + 1):
        parts = urllib.parse.urlsplit(url)
        connection = http.client.HTTPSConnection(parts.netloc, timeout=TIMEOUT)
        try:
            connection.request(method, f"{parts.path}?{parts.query}" if parts.query else parts.path, headers=headers)
            response = connection.getresponse()
            body = response.read()
        except http.client.HTTPException as error:
            msg = f"{method} {url}: {error!r}"
            raise OSError(msg) from error
        finally:
            connection.close()
        response_headers = dict(response.getheaders())
        location = next((value for key, value in response_headers.items() if key.lower() == "location"), "")
        if response.status in REDIRECTS and location:
            target = urllib.parse.urljoin(url, location)
            if urllib.parse.urlsplit(target).scheme != "https":
                msg = f"{method} {url}: redirect to {target} is not https"
                raise OSError(msg)
            if urllib.parse.urlsplit(target).netloc != parts.netloc:
                headers = {key: value for key, value in headers.items() if key.lower() != "authorization"}
            url = target
            continue
        if not http.HTTPStatus.OK <= response.status < http.HTTPStatus.MULTIPLE_CHOICES:
            msg = f"{method} {url}: HTTP {response.status} {response.reason}"
            raise OSError(msg)
        return response_headers, body
    msg = f"{method} {url}: more than {MAX_REDIRECTS} redirects"
    raise OSError(msg)


def pinned_digest(workflow: str) -> str:
    """The one sha256 digest the workflow pins the checker image to."""
    digests = PIN.findall(workflow)
    if len(digests) != 1:
        msg = f"expected one docker://ghcr.io/{REPOSITORY}@sha256 digest pin, found {len(digests)}"
        raise DigestError(msg)
    return digests[0]


def registry_auth(fetch: Fetch) -> dict[str, str]:
    """The Authorization header of an anonymous ghcr.io pull token."""
    _, body = fetch("GET", TOKEN_URL, {})
    try:
        token = json.loads(body)["token"]
    except (ValueError, KeyError, TypeError) as error:
        msg = f"no token in the ghcr.io /token answer: {error!r}"
        raise DigestError(msg) from error
    return {"Authorization": f"Bearer {token}"}


def latest_digest(fetch: Fetch) -> str:
    """The digest ghcr.io currently serves for the checker's `:latest` tag."""
    headers, _ = fetch("HEAD", MANIFEST_URL, {**registry_auth(fetch), "Accept": ACCEPT})
    digest = next((value for key, value in headers.items() if key.lower() == "docker-content-digest"), "")
    if not digest:
        msg = "ghcr.io answered manifests/latest without a Docker-Content-Digest header"
        raise DigestError(msg)
    return digest


def built_at(fetch: Fetch, digest: str) -> dt.datetime:
    """When the image `digest` (an index or a single manifest) was built: its linux/amd64 config's `created` time.

    The publisher sets `created`. It times the settle window and the upstream commit range; it is no security control.
    """
    auth = registry_auth(fetch)
    try:
        manifest = json.loads(fetch("GET", MANIFESTS_URL + digest, {**auth, "Accept": ACCEPT})[1])
        if "manifests" in manifest:
            image = next((m["digest"] for m in manifest["manifests"] if m.get("platform") == PLATFORM), None)
            if image is None:
                msg = f"the {digest} index lists no linux/amd64 image"
                raise DigestError(msg)
            manifest = json.loads(fetch("GET", MANIFESTS_URL + image, {**auth, "Accept": ACCEPT})[1])
        config = json.loads(fetch("GET", BLOBS_URL + manifest["config"]["digest"], auth)[1])
        created = dt.datetime.fromisoformat(config["created"])
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        msg = f"no build time for {digest}: {error!r}"
        raise DigestError(msg) from error
    if created.tzinfo is None:
        msg = f"the build time of {digest} has no time zone: {config['created']}"
        raise DigestError(msg)
    return created


def utc(moment: dt.datetime) -> str:
    """`moment` to the minute in UTC, for people."""
    return f"{moment.astimezone(dt.UTC):%Y-%m-%d %H:%M} UTC"


def age_text(age: dt.timedelta) -> str:
    """`age` in whole days, or in hours under a day."""
    return f"{age.days} days" if age.days >= 1 else f"{age.seconds // 3600} hours"


@dataclass(frozen=True)
class Drift:
    """The pin and the newer `:latest` it lags behind."""

    pinned: str
    latest: str
    latest_built: dt.datetime


def pr_body(drift: Drift, pinned_built: dt.datetime, now: dt.datetime) -> str:
    """The checker-pin pull request's body: both images and the upstream commits between their builds."""
    since = pinned_built.astimezone(dt.UTC).date()
    until = drift.latest_built.astimezone(dt.UTC).date() + dt.timedelta(days=1)
    return (
        f"`ghcr.io/{REPOSITORY}:latest` was built {age_text(now - drift.latest_built)} ago and has not changed since,"
        " so this pull request moves the pin in `.github/workflows/external-data-checker.yml` to it.\n"
        "\n"
        "| | Digest | Built |\n"
        "| --- | --- | --- |\n"
        f"| Pinned | `{drift.pinned}` | {utc(pinned_built)} |\n"
        f"| Latest | `{drift.latest}` | {utc(drift.latest_built)} |\n"
        "\n"
        f"Upstream commits between the two builds: {UPSTREAM}/commits/master?since={since}&until={until}\n"
        "\n"
        "Skim them before you merge: the checker job runs this image with `contents: write` and `pull-requests: write`"
        ' (CONTRIBUTING.md, "Dependencies"). Build times are the images\' `created` field, which the publisher sets.\n'
        "\n"
        "Opened by the `checker-pin` job of `.github/workflows/nightly-compliance.yml` (#269).\n"
    )


def bump(args: argparse.Namespace, text: str, drift: Drift, fetch: Fetch, now: dt.datetime) -> int:
    """Move the pin and its date comment to `:latest` once it has settled; write the pull request body."""
    age = now - drift.latest_built
    if age < SETTLE:
        sys.stdout.write(
            f"{REPOSITORY}:latest moved on to {drift.latest}, built {age_text(age)} ago;"
            f" the pin moves once it is {SETTLE.days} days old.\n"
        )
        return 0
    dates = len(AS_OF.findall(text))
    if dates != 1:
        sys.stderr.write(
            f"check_checker_digest: could not move the pin in {args.workflow}: expected one"
            f" `{REPOSITORY}:latest as of <date>` comment, found {dates}\n"
        )
        return 2
    pinned_built = built_at(fetch, drift.pinned)
    moved = AS_OF.sub(rf"\g<1>{now.astimezone(dt.UTC).date()}", text.replace(drift.pinned, drift.latest))
    args.workflow.write_text(moved, encoding="utf-8")
    if args.pr_body is not None:
        args.pr_body.write_text(pr_body(drift, pinned_built, now), encoding="utf-8")
    sys.stdout.write(f"{REPOSITORY}: moved the pin to {drift.latest} (built {utc(drift.latest_built)}).\n")
    return 0


def report(args: argparse.Namespace, drift: Drift, now: dt.datetime) -> int:
    """The nightly row: pass while `:latest` is younger than GRACE, fail after."""
    age = now - drift.latest_built
    sys.stdout.write(
        f"{REPOSITORY}:latest moved on.\n"
        f"pinned: {drift.pinned}\n"
        f"latest: {drift.latest} (built {utc(drift.latest_built)}, {age_text(age)} ago)\n"
    )
    if age < GRACE:
        sys.stdout.write(
            f"The ci/checker-pin pull request opens once it is {SETTLE.days} days old;"
            f" this check fails once it is {GRACE.days} days old.\n"
        )
        return 0
    sys.stdout.write(
        "Merge the ci/checker-pin pull request (the checker-pin job of nightly-compliance.yml opens it), or bump"
        f' the digest in {args.workflow.name} as CONTRIBUTING.md ("Dependencies") describes.\n'
    )
    return 1


def main(
    argv: Sequence[str] | None = None, fetch: Fetch = https_fetch, now: Clock = lambda: dt.datetime.now(dt.UTC)
) -> int:
    """Report the pin, or with --bump move it; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workflow", type=Path, default=WORKFLOW, help="workflow that pins the image")
    parser.add_argument("--bump", action="store_true", help=f"move the pin once :latest is {SETTLE.days} days old")
    parser.add_argument("--pr-body", type=Path, help="with --bump: where to write the pull request body")
    args = parser.parse_args(argv)
    try:
        text = args.workflow.read_text(encoding="utf-8")
        pinned = pinned_digest(text)
    except (OSError, DigestError) as error:
        sys.stderr.write(f"check_checker_digest: could not read the pin from {args.workflow}: {error}\n")
        return 2
    try:
        latest = latest_digest(fetch)
        if pinned == latest:
            sys.stdout.write(f"{REPOSITORY} pin is up to date: {pinned}\n")
            return 0
        drift = Drift(pinned, latest, built_at(fetch, latest))
        return bump(args, text, drift, fetch, now()) if args.bump else report(args, drift, now())
    except (OSError, DigestError) as error:
        sys.stderr.write(f"check_checker_digest: could not read ghcr.io: {error}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
