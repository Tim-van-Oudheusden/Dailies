#!/usr/bin/env python3
"""Validate a game submission from the "Add a game" issue form and build its catalog entry.

Reads the JSON that stefanbuck/github-issue-parser writes for .github/ISSUE_TEMPLATE/new-game.yml (one key per field
id) and checks it as docs/research/data-pipeline.md section 1.4 and Appendix A6 describe:

1. The form maps to an entry: category label to enum id, lower-case difficulty, a description of at least 20
   characters, comma-separated tags slugified, language defaulting to "en".
2. The URL is https and its host resolves only to public IP addresses, so the runner never fetches an internal
   address. Every redirect hop is held to the same rule.
3. The page answers 2xx to HEAD (GET when HEAD gets 403 or 405), within 10 s per request and at most 5 redirects.
4. The registrable domain of the final URL equals that of the submitted URL: hijacked dle domains redirect elsewhere.
5. The page title holds no gambling keyword from scripts/data/title-blocklist.txt.
6. The game is not in the catalog yet (same host and path, or same slug as an id or alias); a similar name is only a
   warning.
7. The candidate entry validates against data/v1/schema/catalog.schema.json.

Form values are data: they are never evaluated or passed to a shell.

Usage:
    python -I scripts/validate_submission.py --parsed PARSED.json --catalog data/v1/games.json \
        --schema data/v1/schema/catalog.schema.json --issue N --out result.json --report report.md

Writes result.json ({ok, entry, errors, warnings}) and report.md (a Markdown comment that starts with
REPORT_MARKER), then exits 0 when the submission is valid, 1 when it is not and 2 on a usage or internal error.
"""

import argparse
import html.parser
import ipaddress
import json
import logging
import re
import socket
import sys
import unicodedata
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from difflib import SequenceMatcher
from http import HTTPStatus
from pathlib import Path
from time import monotonic
from typing import Any, Protocol
from urllib.parse import urljoin, urlsplit

import jsonschema
import requests
import requests.adapters
import tldextract
import urllib3
import urllib3.connection

REPORT_MARKER = "<!-- dailies-submission-check -->"
BLOCKLIST = Path(__file__).resolve().parent / "data" / "title-blocklist.txt"
USER_AGENT = "DailiesSubmissionCheck/1.0 (+https://github.com/Tim-van-Oudheusden/Dailies)"
TIMEOUT = 10
MAX_REDIRECTS = 5
MIN_DESCRIPTION = 20
SIMILAR_NAME = 0.9
# Enough of the page to find its <title>; the rest is never read.
MAX_BODY = 512 * 1024
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

# The "Category" dropdown labels of new-game.yml -> catalog enum ids (keep both lists in sync).
CATEGORIES = {
    "Words": "words",
    "Geography": "geography",
    "Music": "music",
    "Movies & TV": "movies-tv",
    "Video Games": "video-games",
    "Numbers & Logic": "numbers-logic",
    "Trivia": "trivia",
    "Pictures & Colors": "visual",
    "Food": "food",
    "Sports": "sports",
}

# The bundled public suffix list snapshot: no download, and the same answer on every run. Private suffixes count, so
# two github.io or vercel.app sites are different sites, as the catalog's domain field records them.
_EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)

Resolver = Callable[[str], list[str]]


class Response(Protocol):
    """The part of ``requests.Response`` the validator reads."""

    status_code: int
    headers: Any
    encoding: str | None

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        """Yield the body in chunks."""

    def close(self) -> None:
        """Release the connection."""


class Session(Protocol):
    """The part of ``requests.Session`` the validator uses."""

    def request(self, method: str, url: str, **kwargs: Any) -> Response:
        """Send one request."""


class CheckError(Exception):
    """A check failed; the message is shown to the submitter."""


@dataclass
class Result:
    """The outcome of validating one submission.

    Attributes:
        entry: The candidate catalog entry, as far as the form could be mapped.
        checks: (check name, passed, detail) per check, in order; passed is None when the check was skipped.
        errors: Why the submission is invalid; empty when it is valid.
        warnings: Things a maintainer should look at that do not make the submission invalid.
    """

    entry: dict[str, Any] = field(default_factory=dict)
    checks: list[tuple[str, bool | None, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether the submission passed every check."""
        return not self.errors

    def record(self, name: str, errors: list[str], skipped: bool = False) -> None:
        """Record the outcome of one check."""
        if skipped:
            self.checks.append((name, None, "skipped: an earlier check failed"))
            return
        self.checks.append((name, not errors, "; ".join(errors)))
        self.errors.extend(errors)


def slugify(text: str) -> str:
    """Lower-case ASCII words joined by single hyphens, e.g. "Movies & TV" -> "movies-tv"."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def registrable_domain(url: str) -> str:
    """The registrable domain (eTLD+1) of a URL, e.g. "https://www.example.co.uk/x" -> "example.co.uk"."""
    return _EXTRACT(url).top_domain_under_public_suffix


def _text(parsed: dict[str, Any], key: str) -> str:
    value = parsed.get(key)
    return value.strip() if isinstance(value, str) else ""


def map_form(parsed: dict[str, Any], issue: int, today: date) -> tuple[dict[str, Any], list[str]]:
    """Map the parsed issue form to a catalog entry.

    Returns:
        The entry and the problems found in the form.
    """
    errors: list[str] = []
    name = _text(parsed, "name")
    url = _text(parsed, "url")
    label = _text(parsed, "category")
    category = CATEGORIES.get(label)
    if category is None:
        errors.append(f'unknown category "{label}"; pick one of: {", ".join(CATEGORIES)}')
    description = _text(parsed, "description")
    if len(description) < MIN_DESCRIPTION:
        errors.append(f"the description must be at least {MIN_DESCRIPTION} characters (it has {len(description)})")
    tags = list(dict.fromkeys(slug for slug in (slugify(tag) for tag in _text(parsed, "tags").split(",")) if slug))
    entry: dict[str, Any] = {
        "id": slugify(name),
        "name": name,
        "url": url,
        "category": category,
        "difficulty": _text(parsed, "difficulty").lower(),
        "description": description,
    }
    if tags:
        entry["tags"] = tags
    entry["language"] = _text(parsed, "language") or "en"
    entry["added"] = today.isoformat()
    entry["status"] = "active"
    entry["domain"] = registrable_domain(url)
    entry["source_issue"] = issue
    entry["history"] = [{"date": today.isoformat(), "event": "added", "note": f"issue #{issue}"}]
    return entry, errors


def resolve_host(host: str) -> list[str]:
    """Every IP address a host name resolves to."""
    return [str(info[4][0]) for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)]


def is_public(address: str) -> bool:
    """Whether an IP address is global unicast: not private, loopback, link-local, CGNAT, ULA or multicast."""
    ip = ipaddress.ip_address(address)
    return ip.is_global and not ip.is_multicast


def check_url(url: str, resolve: Resolver) -> None:
    """Require an https URL whose host resolves only to public addresses.

    Raises:
        CheckError: The URL is malformed or not https, has no host or a non-ASCII one, does not resolve, or resolves to
            a non-public address.
    """
    try:
        parts = urlsplit(url)
        host = parts.hostname
        _ = parts.port  # raises on a port that is not a number from 0 to 65535
    except ValueError as error:
        msg = f"{url} is not a valid URL ({error})"
        raise CheckError(msg) from error
    if parts.scheme != "https" or not host:
        msg = f"the URL must start with https:// ({url})"
        raise CheckError(msg)
    # Only ASCII hosts: socket and requests encode international names differently, so the name resolved here could
    # differ from the one requests connects to.
    if not host.isascii():
        msg = f"{host} is not ASCII; give the host in its xn-- (punycode) form"
        raise CheckError(msg)
    try:
        addresses = resolve(host)
    except (OSError, ValueError) as error:
        msg = f"{host} does not resolve ({error})"
        raise CheckError(msg) from error
    for address in addresses:
        if not is_public(address):
            msg = f"{host} resolves to a non-public address ({address})"
            raise CheckError(msg)


class _PublicHTTPSConnection(urllib3.connection.HTTPSConnection):
    """An HTTPS connection that refuses a non-public peer after the TCP connect, before TLS or any request byte.

    check_url vets the addresses a host resolves to, but urllib3 resolves the name again when it connects (DNS
    rebinding). Checking the connected socket's peer closes that gap.
    """

    def _new_conn(self) -> socket.socket:
        sock = super()._new_conn()
        address = str(sock.getpeername()[0])
        if not is_public(address):
            sock.close()
            msg = f"{self.host} connected to a non-public address ({address})"
            raise CheckError(msg)
        return sock


class _PublicHTTPSConnectionPool(urllib3.HTTPSConnectionPool):
    ConnectionCls = _PublicHTTPSConnection


class _PublicAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {"https": _PublicHTTPSConnectionPool}


def public_session() -> requests.Session:
    """A requests session that only connects to public addresses over https, and never through a proxy."""
    session = requests.Session()
    # A proxy would be the connected peer, which defeats the peer check.
    session.trust_env = False
    session.mount("https://", _PublicAdapter())
    return session


def fetch(session: Session, method: str, url: str, resolve: Resolver) -> tuple[str, Response]:
    """Send a request and follow up to MAX_REDIRECTS redirects, checking every hop with check_url.

    Returns:
        The final URL and its response.

    Raises:
        CheckError: A hop is not a public https URL, there are too many redirects, or the request fails.
    """
    for _ in range(MAX_REDIRECTS + 1):
        check_url(url, resolve)
        try:
            response = session.request(
                method,
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException as error:
            msg = f"{url} is unreachable ({type(error).__name__})"
            raise CheckError(msg) from error
        location = response.headers.get("location")
        if response.status_code not in REDIRECT_STATUSES or not location:
            return url, response
        response.close()
        try:
            url = urljoin(url, location)
        except ValueError as error:
            msg = f"{url} redirects to {location}, which is not a valid URL"
            raise CheckError(msg) from error
    msg = f"more than {MAX_REDIRECTS} redirects"
    raise CheckError(msg)


class _TitleParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self._parts: list[str] | None = None

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title" and self.title is None:
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._parts is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._parts is not None:
            self.title = " ".join("".join(self._parts).split())
            self._parts = None


def page_title(response: Response) -> str:
    """The text of the first <title> in the first MAX_BODY bytes of a response, or "" without one.

    Raises:
        CheckError: Reading the body took longer than TIMEOUT seconds in total.
    """
    # The request timeout bounds each socket read, not the whole body: a server can trickle bytes forever.
    deadline = monotonic() + TIMEOUT
    body = bytearray()
    try:
        for chunk in response.iter_content(64 * 1024):
            body.extend(chunk)
            if len(body) >= MAX_BODY:
                break
            if monotonic() > deadline:
                msg = f"the page did not load within {TIMEOUT} s"
                raise CheckError(msg)
    finally:
        response.close()
    data = bytes(body[:MAX_BODY])
    try:
        text = data.decode(response.encoding or "utf-8", errors="replace")
    except LookupError:  # an unknown charset in Content-Type
        text = data.decode("utf-8", errors="replace")
    parser = _TitleParser()
    parser.feed(text)
    return parser.title or ""


def reach(url: str, session: Session, resolve: Resolver) -> str:
    """Check that a URL answers 2xx to HEAD, or to GET when the server refuses HEAD.

    Returns:
        The final URL after redirects.

    Raises:
        CheckError: The URL or a redirect is unsafe, the site is unreachable, or it does not answer 2xx.
    """
    final_url, response = fetch(session, "HEAD", url, resolve)
    response.close()
    if response.status_code in {HTTPStatus.FORBIDDEN, HTTPStatus.METHOD_NOT_ALLOWED}:
        final_url, response = fetch(session, "GET", url, resolve)
        response.close()
    if not HTTPStatus.OK <= response.status_code < HTTPStatus.MULTIPLE_CHOICES:
        msg = f"{final_url} answered HTTP {response.status_code}"
        raise CheckError(msg)
    return final_url


def read_title(url: str, session: Session, resolve: Resolver) -> tuple[str, str]:
    """GET a page and return where it ended up and its title.

    Returns:
        The final URL after redirects and the page title.

    Raises:
        CheckError: The page cannot be fetched or does not answer 2xx.
    """
    final_url, response = fetch(session, "GET", url, resolve)
    if not HTTPStatus.OK <= response.status_code < HTTPStatus.MULTIPLE_CHOICES:
        response.close()
        msg = f"{final_url} answered HTTP {response.status_code} to GET"
        raise CheckError(msg)
    return final_url, page_title(response)


def load_blocklist(path: Path = BLOCKLIST) -> list[str]:
    """The keywords of a blocklist file: one per line, without blank lines and "#" comments."""
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def blocked_keyword(title: str, keywords: Iterable[str]) -> str | None:
    """The first keyword that occurs in a title as a whole word, case-insensitively, or None.

    Whole words keep "bet" from matching "Alphabet"; the spaces of a phrase match any run of whitespace.
    """
    for keyword in keywords:
        pattern = r"\s+".join(re.escape(word) for word in keyword.split())
        if re.search(rf"\b{pattern}\b", title, re.IGNORECASE):
            return keyword
    return None


def _other_site(url: str, entry: dict[str, Any]) -> str | None:
    """Why a URL is not on the entry's site, or None when it is."""
    domain = registrable_domain(url)
    return None if domain == entry["domain"] else f"redirects to another site ({domain or url})"


def check_site(
    result: Result, entry: dict[str, Any], session: Session, resolve: Resolver, blocklist: Iterable[str]
) -> None:
    """Record whether the site is reachable, still the submitted site, and not a gambling page.

    Both the HEAD chain and the GET chain that reads the title must end on the submitted site: a site can answer HEAD
    itself and redirect GET elsewhere.
    """
    try:
        final_url = reach(entry["url"], session, resolve)
    except CheckError as error:
        result.record("Reachable", [str(error)])
        result.record("Same site", [], skipped=True)
        result.record("Page title", [], skipped=True)
        return
    result.record("Reachable", [])
    other_site = _other_site(final_url, entry)
    title = ""
    title_errors: list[str] = []
    if other_site is None:
        try:
            title_url, title = read_title(final_url, session, resolve)
        except CheckError as error:
            title_errors.append(str(error))
        else:
            other_site = _other_site(title_url, entry)
    if other_site is not None:
        result.record("Same site", [other_site])
        result.record("Page title", [], skipped=True)
        return
    result.record("Same site", [])
    keyword = None if title_errors else blocked_keyword(title, blocklist)
    if keyword:
        title_errors.append(f'the page title "{title}" contains the gambling keyword "{keyword}"')
    result.record("Page title", title_errors)


def normalise_url(url: str) -> str:
    """Host and path of a URL for duplicate checks: lower-case host without "www.", no trailing slash, no query.

    Dropping the query also drops utm_* tracking parameters. A malformed URL (check_url reports it) is compared as is.
    """
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").removeprefix("www.")
    except ValueError:
        return url
    return host + parts.path.rstrip("/")


def check_duplicates(entry: dict[str, Any], catalog: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Compare an entry with the catalog by URL, slug and name.

    Returns:
        Errors for a game that is already listed (same host and path, or the slug of the name equals an id or the slug
        of an alias) and warnings for names at least SIMILAR_NAME alike.
    """
    errors: list[str] = []
    warnings: list[str] = []
    url = normalise_url(entry["url"])
    name = entry["name"].casefold()
    for game in catalog.get("games", []):
        game_id = game.get("id", "")
        game_name = game.get("name", "")
        known_names = [game_name, *game.get("aliases", [])]
        if normalise_url(game.get("url", "")) == url:
            errors.append(f"the URL is already in the catalog as {game_id}")
        elif entry["id"] in {game_id, *(slugify(known) for known in known_names)}:
            errors.append(f"the name is already in the catalog as {game_id}")
        elif any(SequenceMatcher(None, name, known.casefold()).ratio() >= SIMILAR_NAME for known in known_names):
            warnings.append(f'the name is close to "{game_name}" ({game_id}); check it is not the same game')
    return errors, warnings


def check_schema(entry: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Validate an entry against the catalog schema's game definition.

    Returns:
        One message per schema violation.
    """
    game_schema = {"$schema": schema.get("$schema"), "$defs": schema["$defs"], "$ref": "#/$defs/game"}
    validator = jsonschema.Draft202012Validator(
        game_schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    return [
        f"{'/'.join(str(part) for part in error.absolute_path) or 'entry'}: {error.message}"
        for error in sorted(validator.iter_errors(entry), key=lambda error: list(error.absolute_path))
    ]


@dataclass(frozen=True)
class Validator:
    """Checks submissions against one catalog.

    Attributes:
        catalog: The current data/v1/games.json.
        schema: data/v1/schema/catalog.schema.json.
        session: Sends the HTTP requests.
        resolve: Resolves a host name to its IP addresses.
        blocklist: Gambling keywords for the page title; scripts/data/title-blocklist.txt by default.
    """

    catalog: dict[str, Any]
    schema: dict[str, Any]
    session: Session
    resolve: Resolver = resolve_host
    blocklist: tuple[str, ...] = field(default_factory=lambda: tuple(load_blocklist()))

    def validate(self, parsed: dict[str, Any], issue: int, today: date) -> Result:
        """Run every check on a parsed submission.

        Args:
            parsed: The issue-parser output, one string per form field id.
            issue: The submission's issue number.
            today: The date the entry is added.

        Returns:
            The result, with the candidate entry.
        """
        result = Result()
        entry, form_errors = map_form(parsed, issue, today)
        result.entry = entry
        result.record("Form fields", form_errors)
        try:
            check_url(entry["url"], self.resolve)
        except CheckError as error:
            result.record("Safe URL", [str(error)])
        else:
            result.record("Safe URL", [])
            check_site(result, entry, self.session, self.resolve, self.blocklist)
        duplicate_errors, duplicate_warnings = check_duplicates(entry, self.catalog)
        result.record("Not a duplicate", duplicate_errors)
        result.warnings.extend(duplicate_warnings)
        result.record("Catalog schema", check_schema(entry, self.schema), skipped=bool(form_errors))
        return result


def _code(text: str) -> str:
    """Text as one inline code span, so Markdown, HTML, @mentions and links in it render inert.

    Details and warnings quote the submission and the fetched page, so they are never rendered as Markdown. The fence
    is one backtick longer than any run of backticks in the text, so the text cannot close it.
    """
    text = " ".join(text.split())
    if not text:
        return ""
    fence = "`" * max([1, *(len(run) + 1 for run in re.findall(r"`+", text))])
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{padding}{text}{padding}{fence}"


def _cell(text: str) -> str:
    """Text as an inert code span that stays inside one table cell (GitHub tables split on "|" even in code)."""
    return _code(text).replace("|", r"\|")


def render_report(result: Result) -> str:
    """The Markdown comment for the submission issue: REPORT_MARKER, a pass/fail table and the candidate entry."""
    verdict = {True: "✅ pass", False: "❌ fail", None: "⏭️ skipped"}
    lines = [
        REPORT_MARKER,
        "## Submission check: " + ("✅ passed" if result.ok else "❌ needs changes"),
        "",
        "| Check | Result | Details |",
        "| --- | --- | --- |",
    ]
    lines += [f"| {name} | {verdict[passed]} | {_cell(detail)} |" for name, passed, detail in result.checks]
    if result.warnings:
        lines += ["", "**Warnings**", ""]
        lines += [f"- {_code(warning)}" for warning in result.warnings]
    candidate = json.dumps(result.entry, indent=2, ensure_ascii=False)
    # A fence longer than any backtick run in the JSON, so a value cannot close it.
    fence = "`" * max([3, *(len(run) + 1 for run in re.findall(r"`+", candidate))])
    lines += ["", "Candidate entry:", "", f"{fence}json", candidate, fence, ""]
    return "\n".join(lines)


def _load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = f"{path} does not hold a JSON object"
        raise TypeError(msg)
    return data


def _issue_number(text: str) -> int:
    number = int(text)
    if number < 1:
        msg = "must be a positive issue number"
        raise argparse.ArgumentTypeError(msg)
    return number


def main(
    argv: list[str] | None = None,
    *,
    session: Session | None = None,
    resolve: Resolver = resolve_host,
    today: date | None = None,
) -> int:
    """Validate the submission named on the command line and write its result and report.

    Args:
        argv: The command-line arguments; sys.argv by default.
        session: Sends the HTTP requests; a new ``requests.Session`` by default.
        resolve: Resolves a host name to its IP addresses.
        today: The date the entry is added; today in UTC by default.

    Returns:
        0 when the submission is valid, 1 when it is not, 2 on a usage or internal error.
    """
    parser = argparse.ArgumentParser(description="Validate a game submission from the 'Add a game' issue form.")
    parser.add_argument("--parsed", type=Path, required=True, help="github-issue-parser output (JSON)")
    parser.add_argument("--catalog", type=Path, required=True, help="data/v1/games.json")
    parser.add_argument("--schema", type=Path, required=True, help="data/v1/schema/catalog.schema.json")
    parser.add_argument("--issue", type=_issue_number, required=True, help="the submission's issue number")
    parser.add_argument("--out", type=Path, required=True, help="where to write result.json")
    parser.add_argument("--report", type=Path, required=True, help="where to write report.md")
    args = parser.parse_args(argv)
    try:
        parsed = _load_object(args.parsed)
        catalog = _load_object(args.catalog)
        schema = _load_object(args.schema)
        with public_session() as default_session:
            validator = Validator(catalog, schema, session or default_session, resolve)
            result = validator.validate(parsed, args.issue, today or datetime.now(UTC).date())
        output = {"ok": result.ok, "entry": result.entry, "errors": result.errors, "warnings": result.warnings}
        args.out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        args.report.write_text(render_report(result), encoding="utf-8")
    except (OSError, TypeError, ValueError) as error:
        sys.stderr.write(f"validate_submission: {error}\n")
        return 2
    except Exception:
        # A bug or a malformed catalog or schema: exit 2, so the submission is not reported as invalid.
        logging.getLogger(__name__).exception("validate_submission: internal error")
        return 2
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
