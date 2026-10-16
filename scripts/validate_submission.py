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

Checks 2 to 5 live in scripts/lib/urlcheck.py, shared with the weekly link checker scripts/check_links.py.

Form values are data: they are never evaluated or passed to a shell.

Usage:
    python -I scripts/validate_submission.py --parsed PARSED.json --catalog data/v1/games.json \
        --schema data/v1/schema/catalog.schema.json --issue N --out result.json --report report.md

Writes result.json ({ok, entry, errors, warnings}) and report.md (a Markdown comment that starts with
REPORT_MARKER), then exits 0 when the submission is valid, 1 when it is not and 2 on a usage or internal error.
"""

import argparse
import json
import logging
import re
import sys
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import jsonschema

# scripts/lib is not a package and `python -I` leaves the script's directory off sys.path, so add it by path.
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from urlcheck import (
    CheckError,
    Resolver,
    Session,
    check_url,
    code_span,
    load_blocklist,
    public_session,
    registrable_domain,
    resolve_host,
    table_cell,
)
from urlcheck import check_site as check_live_site

REPORT_MARKER = "<!-- dailies-submission-check -->"
MIN_DESCRIPTION = 20
SIMILAR_NAME = 0.9

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


def check_site(
    result: Result, entry: dict[str, Any], session: Session, resolve: Resolver, blocklist: Iterable[str]
) -> None:
    """Record whether the site is reachable, still the submitted site, and not a gambling page."""
    site = check_live_site(entry["url"], entry["domain"], session, resolve, blocklist)
    if site.unreachable is not None:
        result.record("Reachable", [str(site.unreachable)])
        result.record("Same site", [], skipped=True)
        result.record("Page title", [], skipped=True)
        return
    result.record("Reachable", [])
    if site.other_site is not None:
        result.record("Same site", [site.other_site])
        result.record("Page title", [], skipped=True)
        return
    result.record("Same site", [])
    title_errors = [str(site.title_error)] if site.title_error is not None else []
    if site.keyword:
        title_errors.append(f'the page title "{site.title}" contains the gambling keyword "{site.keyword}"')
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
    lines += [f"| {name} | {verdict[passed]} | {table_cell(detail)} |" for name, passed, detail in result.checks]
    if result.warnings:
        lines += ["", "**Warnings**", ""]
        lines += [f"- {code_span(warning)}" for warning in result.warnings]
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
