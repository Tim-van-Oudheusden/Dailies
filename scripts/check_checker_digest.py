#!/usr/bin/env python3
"""Compare the pinned flatpak-external-data-checker image digest with the image's current `:latest`.

.github/workflows/external-data-checker.yml runs `docker://ghcr.io/flathub/flatpak-external-data-checker@sha256:…`.
Dependabot does not update docker:// references, so scripts/nightly-compliance.sh runs this script each night to
report when Flathub has published a newer `:latest`. It asks ghcr.io anonymously: a pull token from /token, then a
HEAD of manifests/latest that accepts the multi-arch index types, and reads the Docker-Content-Digest header. The
standard library is enough; the script needs no requirements.

Usage:
    python -I scripts/check_checker_digest.py [--workflow .github/workflows/external-data-checker.yml]

Exits 0 when the pin is the current `:latest`, 1 when it drifted (both digests and the bump procedure in
CONTRIBUTING.md are printed), and 2 when the workflow holds no single pin or ghcr.io could not be read.
"""

import argparse
import http
import http.client
import json
import re
import sys
import urllib.parse
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

REPOSITORY = "flathub/flatpak-external-data-checker"
WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "external-data-checker.yml"
TOKEN_URL = f"https://ghcr.io/token?scope=repository:{REPOSITORY}:pull"
MANIFEST_URL = f"https://ghcr.io/v2/{REPOSITORY}/manifests/latest"
# The index types first: the digest of a multi-arch image is the digest of its index, which is what the pin names.
ACCEPT = (
    "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, "
    "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json"
)
PIN = re.compile(rf"docker://ghcr\.io/{re.escape(REPOSITORY)}@(sha256:[0-9a-f]{{64}})")
TIMEOUT = 30

# (method, url, headers) -> (response headers, body). Raises OSError when the request fails or is not answered 2xx.
Fetch = Callable[[str, str, dict[str, str]], tuple[Mapping[str, str], bytes]]


class DigestError(Exception):
    """The workflow or ghcr.io did not yield a digest; the message says why."""


def https_fetch(method: str, url: str, headers: dict[str, str]) -> tuple[Mapping[str, str], bytes]:
    """Send one HTTPS request; the default Fetch."""
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
    if not http.HTTPStatus.OK <= response.status < http.HTTPStatus.MULTIPLE_CHOICES:
        msg = f"{method} {url}: HTTP {response.status} {response.reason}"
        raise OSError(msg)
    return dict(response.getheaders()), body


def pinned_digest(workflow: str) -> str:
    """The one sha256 digest the workflow pins the checker image to."""
    digests = PIN.findall(workflow)
    if len(digests) != 1:
        msg = f"expected one docker://ghcr.io/{REPOSITORY}@sha256 digest pin, found {len(digests)}"
        raise DigestError(msg)
    return digests[0]


def latest_digest(fetch: Fetch) -> str:
    """The digest ghcr.io currently serves for the checker's `:latest` tag."""
    _, body = fetch("GET", TOKEN_URL, {})
    try:
        token = json.loads(body)["token"]
    except (ValueError, KeyError, TypeError) as error:
        msg = f"no token in the ghcr.io /token answer: {error!r}"
        raise DigestError(msg) from error
    headers, _ = fetch("HEAD", MANIFEST_URL, {"Authorization": f"Bearer {token}", "Accept": ACCEPT})
    digest = next((value for key, value in headers.items() if key.lower() == "docker-content-digest"), "")
    if not digest:
        msg = "ghcr.io answered manifests/latest without a Docker-Content-Digest header"
        raise DigestError(msg)
    return digest


def main(argv: Sequence[str] | None = None, fetch: Fetch = https_fetch) -> int:
    """Print whether the pin is the current `:latest`; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workflow", type=Path, default=WORKFLOW, help="workflow that pins the image")
    args = parser.parse_args(argv)
    try:
        pinned = pinned_digest(args.workflow.read_text(encoding="utf-8"))
    except (OSError, DigestError) as error:
        sys.stderr.write(f"check_checker_digest: could not read the pin from {args.workflow}: {error}\n")
        return 2
    try:
        latest = latest_digest(fetch)
    except (OSError, DigestError) as error:
        sys.stderr.write(f"check_checker_digest: could not read ghcr.io: {error}\n")
        return 2
    if pinned == latest:
        sys.stdout.write(f"{REPOSITORY} pin is up to date: {pinned}\n")
        return 0
    sys.stdout.write(
        f"{REPOSITORY}:latest moved on.\n"
        f"pinned: {pinned}\n"
        f"latest: {latest}\n"
        f'Bump the digest in {args.workflow.name} as CONTRIBUTING.md ("Dependencies") describes.\n'
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
