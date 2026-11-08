#!/usr/bin/env python3
"""Check that GitHub Pages serves the checkout's games.json and popularity.json, byte for byte.

Every installed app fetches its data from Pages first (DATA_URLS in dailies/config.py.in), and a Pages 404 does not fall
back to raw.githubusercontent.com. When a Pages run fails, Pages keeps serving the previous deployment, which the app
accepts because it is valid: a merged data fix, such as retiring a hijacked game, then reaches nobody and nothing says
so (docs/runbooks/pages.md, #435). scripts/nightly-compliance.sh runs this each night on main, so that case fails a row
and opens the nightly compliance issue.

A mismatch is not failed while the file's last commit is younger than GRACE: Pages deploys a few minutes after the push
and serves with `max-age=600`. In the workflow's shallow checkout the last commit of every file is HEAD, so a commit in
the hour before the run puts a real mismatch off by one night. A file Pages does not serve fails whatever its age. The
icons are not compared: they follow the catalog, and a stale games.json is the signal. The standard library is enough.

Usage:
    python3 -I scripts/check_pages.py [--repo DIR]

Exits 0 when Pages serves both files as the checkout holds them (or a mismatch is younger than GRACE), 1 when a file
differs or Pages does not serve it, and 2 when the checkout or its commit time could not be read.
"""

import argparse
import datetime as dt
import hashlib
import subprocess
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path

BASE_URL = "https://tim-van-oudheusden.github.io/Dailies/v1/"
DATA = "data/v1/"
FILES = ("games.json", "popularity.json")
GRACE = dt.timedelta(hours=1)
TIMEOUT = 30
RUNBOOK = "docs/runbooks/pages.md"

# url -> body. Raises OSError when the request fails or is not answered 2xx (urllib's HTTPError is one).
Fetch = Callable[[str], bytes]
# (checkout, path in it) -> committer time of the last commit that touched the path.
Committed = Callable[[Path, str], dt.datetime]
Clock = Callable[[], dt.datetime]


def https_get(url: str) -> bytes:
    """GET `url`, following redirects as the app does; the default Fetch."""
    if urllib.parse.urlsplit(url).scheme != "https":
        msg = f"{url} is not https"
        raise OSError(msg)
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:  # noqa: S310 - https only, checked above
        return response.read()


def last_commit(repo: Path, path: str) -> dt.datetime:
    """The committer time of the last commit in `repo` that touched `path`; the default Committed."""
    out = subprocess.run(  # noqa: S603 - fixed arguments, no shell
        ["git", "-C", str(repo), "log", "-1", "--format=%cI", "--", path],  # noqa: S607 - git from PATH, as in CI
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return dt.datetime.fromisoformat(out)


def sha(body: bytes) -> str:
    """The first 16 hex digits of `body`'s SHA-256, as the runbook prints them."""
    return hashlib.sha256(body).hexdigest()[:16]


def age_text(age: dt.timedelta) -> str:
    """`age` in whole days, hours or minutes, whichever is the largest unit it reaches."""
    if age.days >= 1:
        return f"{age.days} day{'s' * (age.days != 1)}"
    hours, minutes = age.seconds // 3600, age.seconds // 60
    if hours >= 1:
        return f"{hours} hour{'s' * (hours != 1)}"
    return f"{minutes} minute{'s' * (minutes != 1)}"


def main(
    argv: Sequence[str] | None = None,
    fetch: Fetch = https_get,
    committed: Committed = last_commit,
    now: Clock = lambda: dt.datetime.now(dt.UTC),
) -> int:
    """Compare each file on Pages with the checkout; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1], help="the checkout")
    args = parser.parse_args(argv)
    failed = False
    for name in FILES:
        path = DATA + name
        try:
            local = (args.repo / path).read_bytes()
        except OSError as error:
            sys.stderr.write(f"check_pages: could not read {path}: {error}\n")
            return 2
        try:
            served = fetch(BASE_URL + name)
        except OSError as error:
            sys.stdout.write(f"{name}: Pages did not serve it: {error}\n")
            failed = True
            continue
        if served == local:
            sys.stdout.write(f"{name}: Pages serves this checkout's copy (sha256 {sha(local)})\n")
            continue
        try:
            age = now() - committed(args.repo, path)
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            sys.stderr.write(f"check_pages: could not read the commit time of {path}: {error}\n")
            return 2
        line = (
            f"{name}: Pages serves sha256 {sha(served)}, this checkout has {sha(local)}"
            f" (last changed {age_text(age)} ago)"
        )
        if age < GRACE:
            sys.stdout.write(f"{line}; waiting for the deploy, this fails once the change is {age_text(GRACE)} old\n")
        else:
            sys.stdout.write(f"{line}\n")
            failed = True
    if failed:
        sys.stdout.write(f"Pages is not serving this checkout's data to the apps; see {RUNBOOK}.\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
