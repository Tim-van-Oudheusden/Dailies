"""Decisions of the built-in browser that need no WebKit: the host shown in its header and which data a site owns."""

from urllib.parse import urlsplit


def display_host(uri: str | None) -> str:
    """Return the host of `uri` as the header shows it: lower case, ASCII, without port or user name; or ""."""
    if not uri:
        return ""
    try:
        return urlsplit(uri).hostname or ""
    except ValueError:
        return ""


def site_matches(name: str, host: str) -> bool:
    """Whether website data stored under `name` (a domain, as WebKit groups it) belongs to the site at `host`."""
    name = name.lower().lstrip(".")
    host = host.lower()
    return bool(name and host) and (host == name or host.endswith(f".{name}"))
