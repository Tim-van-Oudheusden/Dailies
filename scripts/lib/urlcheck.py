"""Check that a game's URL is still the game: the rules the submission validator and the link checker share.

1. The URL is https and its host resolves only to public IP addresses, so the runner never fetches an internal
   address. Every redirect hop is held to the same rule, and the connected peer is checked again (DNS rebinding).
2. The page answers 2xx to HEAD (GET when HEAD gets 403 or 405), within 10 s per request and at most 5 redirects.
3. The registrable domain of the final URL equals the entry's domain: hijacked dle domains redirect elsewhere.
4. The page title holds no gambling keyword from scripts/data/title-blocklist.txt.

Used by scripts/validate_submission.py and scripts/check_links.py, which import it by path (scripts/lib), so both run
under ``python -I``.
"""

import html.parser
import ipaddress
import re
import socket
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from time import monotonic
from typing import Any, Protocol
from urllib.parse import urljoin, urlsplit

import requests
import requests.adapters
import tldextract
import urllib3
import urllib3.connection

BLOCKLIST = Path(__file__).resolve().parent.parent / "data" / "title-blocklist.txt"
USER_AGENT = "DailiesSubmissionCheck/1.0 (+https://github.com/Tim-van-Oudheusden/Dailies)"
TIMEOUT = 10
MAX_REDIRECTS = 5
# Enough of the page to find its <title>; the rest is never read.
MAX_BODY = 512 * 1024
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
# The statuses a bot challenge answers with (Cloudflare's "Just a moment..." page is a 403 or a 503).
BOT_WALL_STATUSES = frozenset({HTTPStatus.FORBIDDEN, HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.SERVICE_UNAVAILABLE})

# The bundled public suffix list snapshot: no download, and the same answer on every run. Private suffixes count, so
# two github.io or vercel.app sites are different sites, as the catalog's domain field records them.
_EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)

Resolver = Callable[[str], list[str]]


class Response(Protocol):
    """The part of ``requests.Response`` the checks read."""

    status_code: int
    headers: Any
    encoding: str | None

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        """Yield the body in chunks."""

    def close(self) -> None:
        """Release the connection."""


class Session(Protocol):
    """The part of ``requests.Session`` the checks use."""

    def request(self, method: str, url: str, **kwargs: Any) -> Response:
        """Send one request."""


class CheckError(Exception):
    """A check failed; the message says why in words a submitter or maintainer understands.

    Attributes:
        url: The URL that failed the check, when it is known; a redirect hop may be on another site.
        status: The HTTP status the site answered, when that is why.
        timed_out: The request or the page body took too long.
        bot_wall: The answer is a bot challenge (Cloudflare): the site is likely live but a script cannot prove it.
    """

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        status: int | None = None,
        timed_out: bool = False,
        bot_wall: bool = False,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status = status
        self.timed_out = timed_out
        self.bot_wall = bot_wall


def registrable_domain(url: str) -> str:
    """The registrable domain (eTLD+1) of a URL, e.g. "https://www.example.co.uk/x" -> "example.co.uk"."""
    return _EXTRACT(url).top_domain_under_public_suffix


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
        raise CheckError(msg, url=url) from error
    if parts.scheme != "https" or not host:
        msg = f"the URL must start with https:// ({url})"
        raise CheckError(msg, url=url)
    # Only ASCII hosts: socket and requests encode international names differently, so the name resolved here could
    # differ from the one requests connects to.
    if not host.isascii():
        msg = f"{host} is not ASCII; give the host in its xn-- (punycode) form"
        raise CheckError(msg, url=url)
    try:
        addresses = resolve(host)
    except (OSError, ValueError) as error:
        msg = f"{host} does not resolve ({error})"
        raise CheckError(msg, url=url) from error
    for address in addresses:
        if not is_public(address):
            msg = f"{host} resolves to a non-public address ({address})"
            raise CheckError(msg, url=url)


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
            raise CheckError(msg, url=url, timed_out=isinstance(error, requests.Timeout)) from error
        location = response.headers.get("location")
        if response.status_code not in REDIRECT_STATUSES or not location:
            return url, response
        response.close()
        try:
            url = urljoin(url, location)
        except ValueError as error:
            msg = f"{url} redirects to {location}, which is not a valid URL"
            raise CheckError(msg, url=url) from error
    msg = f"more than {MAX_REDIRECTS} redirects"
    raise CheckError(msg, url=url)


def is_bot_wall(response: Response) -> bool:
    """Whether a response is a Cloudflare bot challenge rather than the page."""
    if response.status_code not in BOT_WALL_STATUSES:
        return False
    if str(response.headers.get("cf-mitigated", "")).lower() == "challenge":
        return True
    return "cloudflare" in str(response.headers.get("server", "")).lower()


def _status_error(message: str, url: str, response: Response) -> CheckError:
    return CheckError(message, url=url, status=response.status_code, bot_wall=is_bot_wall(response))


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
                raise CheckError(msg, timed_out=True)
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
        raise _status_error(msg, final_url, response)
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
        raise _status_error(msg, final_url, response)
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


@dataclass(frozen=True)
class SiteCheck:
    """What check_site found; at most one of unreachable, other_site and title_error is set.

    Attributes:
        unreachable: Why the site did not answer 2xx (rule 2); the later checks were not run.
        other_site: Why the site is not the entry's site any more (rule 3); the title was not checked.
        other_url: The URL on the other site where the link ended up, set with other_site.
        title_error: Why the page could not be read for its title.
        title: The page title, when it was read.
        keyword: The gambling keyword in the title (rule 4), or None.
    """

    unreachable: CheckError | None = None
    other_site: str | None = None
    other_url: str | None = None
    title_error: CheckError | None = None
    title: str = ""
    keyword: str | None = None


def _other_site(url: str, domain: str) -> str | None:
    """Why a URL is not on the site with this registrable domain, or None when it is."""
    final_domain = registrable_domain(url)
    return None if final_domain == domain else f"redirects to another site ({final_domain or url})"


def check_site(url: str, domain: str, session: Session, resolve: Resolver, blocklist: Iterable[str]) -> SiteCheck:
    """Check that a site is reachable, still on its registrable domain, and not a gambling page.

    Both the HEAD chain and the GET chain that reads the title must end on the site: a site can answer HEAD itself and
    redirect GET elsewhere.
    """
    try:
        final_url = reach(url, session, resolve)
    except CheckError as error:
        return SiteCheck(unreachable=error)
    other_site = _other_site(final_url, domain)
    if other_site is not None:
        return SiteCheck(other_site=other_site, other_url=final_url)
    try:
        title_url, title = read_title(final_url, session, resolve)
    except CheckError as error:
        return SiteCheck(title_error=error)
    other_site = _other_site(title_url, domain)
    if other_site is not None:
        return SiteCheck(other_site=other_site, other_url=title_url)
    return SiteCheck(title=title, keyword=blocked_keyword(title, blocklist))


def code_span(text: str) -> str:
    """Text as one inline code span, so Markdown, HTML, @mentions and links in it render inert.

    Reports quote submissions and fetched pages, so that text is never rendered as Markdown. The fence is one backtick
    longer than any run of backticks in the text, so the text cannot close it.
    """
    text = " ".join(text.split())
    if not text:
        return ""
    fence = "`" * max([1, *(len(run) + 1 for run in re.findall(r"`+", text))])
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{padding}{text}{padding}{fence}"


def table_cell(text: str) -> str:
    """Text as an inert code span that stays inside one table cell (GitHub tables split on "|" even in code)."""
    return code_span(text).replace("|", r"\|")
