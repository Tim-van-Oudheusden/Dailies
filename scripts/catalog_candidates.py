#!/usr/bin/env python3
"""List the games The Dles has that the catalog does not: candidates for the "Add a game" form.

The Dles (https://github.com/aukspot/dles, GPL-3.0), whose catalog helped check the seed list, keeps one YAML record
per game in data/dles/ with its name, url, category, status and a dated history. This script downloads that
repository at one commit, reads the records and prints the active ones whose registrable domain no catalog entry has
(whatever the entry's status), newest first, as a Markdown table: the date The Dles added it (or last readded it), its
name, The Dles' category and its URL.

It only reads: nothing is added to the catalog. A maintainer picks games from the list by the submission rules and
files each one through the form (docs/runbooks/catalog-link.md, "Growing the catalog"). Descriptions are not printed:
The Dles' text is GPL-3.0 and the catalog is CC0, so a submission's description is written fresh.

The download follows the rules of scripts/lib/urlcheck.py: https only, every redirect hop and the connected peer on
a public address, 10 s per request, at most 5 redirects. The tarball is read in memory up to MAX_ARCHIVE bytes and
never extracted; records are parsed as safe YAML, and their text is printed as inert code spans.

Usage:
    python -I scripts/catalog_candidates.py --commit SHA [--since YYYY-MM-DD] [--catalog data/v1/games.json]

SHA is the full 40-character hash of an aukspot/dles commit. Exits 0 after printing the table, 2 on a usage error,
a failed download or a malformed record.
"""

import argparse
import io
import json
import re
import sys
import tarfile
from dataclasses import dataclass
from datetime import date
from http import HTTPStatus
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml import YAML, YAMLError

# scripts/lib is not a package and `python -I` leaves the script's directory off sys.path, so add it by path.
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from urlcheck import CheckError, Resolver, Session, fetch, public_session, registrable_domain, resolve_host, table_cell

UPSTREAM = "aukspot/dles"
CATALOG = Path(__file__).resolve().parent.parent / "data" / "v1" / "games.json"
# The whole repository is about 1.4 MB compressed (888 records, October 2026).
MAX_ARCHIVE = 32 * 1024 * 1024
RECORDS = ("data", "dles")
ADDED_EVENTS = frozenset({"added", "readded"})


class UpstreamError(Exception):
    """The download or a record is not what this script expects; the message says which."""


@dataclass(frozen=True)
class Candidate:
    """An active game of The Dles.

    Attributes:
        name: Its name there.
        url: Its URL there.
        category: The Dles' category, which is not one of the catalog's; "" when the record has none.
        added: The day it was last added (or readded) there.
    """

    name: str
    url: str
    category: str
    added: date


def commit_hash(text: str) -> str:
    """A full commit hash, so a run always reads the same records."""
    if not re.fullmatch(r"[0-9a-f]{40}", text):
        msg = "must be the full 40-character hash of a commit"
        raise argparse.ArgumentTypeError(msg)
    return text


def tarball_url(commit: str) -> str:
    """GitHub's gzipped tarball of the upstream repository at a commit."""
    return f"https://codeload.github.com/{UPSTREAM}/tar.gz/{commit}"


def download(url: str, session: Session, resolve: Resolver) -> bytes:
    """GET a URL under the urlcheck rules and return its body.

    Raises:
        CheckError: The URL or a redirect is unsafe, or the request fails.
        UpstreamError: The answer is not 2xx or is larger than MAX_ARCHIVE.
    """
    final_url, response = fetch(session, "GET", url, resolve)
    try:
        if not HTTPStatus.OK <= response.status_code < HTTPStatus.MULTIPLE_CHOICES:
            msg = f"{final_url} answered HTTP {response.status_code}"
            raise UpstreamError(msg)
        body = bytearray()
        for chunk in response.iter_content(64 * 1024):
            body.extend(chunk)
            if len(body) > MAX_ARCHIVE:
                msg = f"{final_url} is larger than {MAX_ARCHIVE} bytes"
                raise UpstreamError(msg)
        return bytes(body)
    finally:
        response.close()


def read_records(archive: bytes) -> dict[str, Any]:
    """The parsed data/dles/*.yaml records of a GitHub tarball, by file name.

    Raises:
        UpstreamError: The archive is not a gzipped tarball, or a record is not valid YAML.
    """
    yaml = YAML(typ="safe", pure=True)
    records: dict[str, Any] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            for member in tar:
                path = PurePosixPath(member.name)
                data = tar.extractfile(member) if member.isfile() else None
                if data is None or path.parent.parts[1:] != RECORDS or path.suffix != ".yaml":
                    continue
                try:
                    records[path.name] = yaml.load(data.read().decode("utf-8"))
                except (YAMLError, UnicodeDecodeError) as error:
                    msg = f"{path.name} is not a valid YAML record ({error})"
                    raise UpstreamError(msg) from error
    except (tarfile.TarError, EOFError, OSError) as error:
        msg = f"the download is not a gzipped tarball ({error})"
        raise UpstreamError(msg) from error
    return records


def _added(history: object) -> date | None:
    """The date of the last "added" or "readded" event of a record's history, or None without one."""
    if not isinstance(history, list):
        return None
    days = [
        date.fromisoformat(str(event.get("date")))
        for event in history
        if isinstance(event, dict) and event.get("event") in ADDED_EVENTS
    ]
    return max(days, default=None)


def active_games(records: dict[str, Any]) -> list[Candidate]:
    """The records whose status is "active".

    Raises:
        UpstreamError: An active record has no name, no URL or no dated "added" event.
    """
    games = []
    for file_name, record in sorted(records.items()):
        if not isinstance(record, dict) or record.get("status") != "active":
            continue
        name, url, category = record.get("name"), record.get("url"), record.get("category")
        try:
            added = _added(record.get("history"))
        except ValueError as error:
            msg = f"{file_name} has a history date that is not YYYY-MM-DD ({error})"
            raise UpstreamError(msg) from error
        if not isinstance(name, str) or not isinstance(url, str) or added is None:
            msg = f"{file_name} is active but lacks a name, a url or an added date"
            raise UpstreamError(msg)
        games.append(Candidate(name, url, category if isinstance(category, str) else "", added))
    return games


def candidates(games: list[Candidate], catalog: dict[str, Any], since: date | None) -> list[Candidate]:
    """The games on a registrable domain no catalog entry has, added on or after `since`, newest first."""
    known = {registrable_domain(str(game.get("url", ""))) for game in catalog.get("games", [])}
    new = [
        game for game in games if registrable_domain(game.url) not in known and (since is None or game.added >= since)
    ]
    return sorted(new, key=lambda game: (-game.added.toordinal(), game.name.casefold()))


def render(found: list[Candidate], commit: str, since: date | None) -> str:
    """The Markdown report: what was read, then one table row per candidate."""
    window = f", added there on or after {since.isoformat()}" if since else ""
    lines = [
        f"Active games in {UPSTREAM} at {commit} whose site is not in the catalog{window}: {len(found)}.",
        "",
    ]
    if not found:
        lines.append("No candidates.")
        return "\n".join(lines) + "\n"
    lines += ["| Added | Name | Category | URL |", "| --- | --- | --- | --- |"]
    for game in found:
        category = table_cell(game.category) if game.category else ""
        lines.append(f"| {game.added.isoformat()} | {table_cell(game.name)} | {category} | {table_cell(game.url)} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, *, session: Session | None = None, resolve: Resolver = resolve_host) -> int:
    """Print the candidates for the commit named on the command line.

    Args:
        argv: The command-line arguments; sys.argv by default.
        session: Sends the HTTP requests; a public-address-only ``requests.Session`` by default.
        resolve: Resolves a host name to its IP addresses.

    Returns:
        0 after printing the table, 2 on a failed download or a malformed record.
    """
    parser = argparse.ArgumentParser(description=f"List the active games of {UPSTREAM} the catalog does not have.")
    parser.add_argument("--commit", type=commit_hash, required=True, help=f"full hash of the {UPSTREAM} commit")
    parser.add_argument("--since", type=date.fromisoformat, help="only games added there on or after YYYY-MM-DD")
    parser.add_argument("--catalog", type=Path, default=CATALOG, help="data/v1/games.json")
    args = parser.parse_args(argv)
    try:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
        with public_session() as default_session:
            archive = download(tarball_url(args.commit), session or default_session, resolve)
        found = candidates(active_games(read_records(archive)), catalog, args.since)
    except (CheckError, UpstreamError, OSError, ValueError) as error:
        sys.stderr.write(f"catalog_candidates: {error}\n")
        return 2
    sys.stdout.write(render(found, args.commit, args.since))
    return 0


if __name__ == "__main__":
    sys.exit(main())
