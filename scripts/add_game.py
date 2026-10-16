#!/usr/bin/env python3
"""Add an approved game submission to the catalog.

Stage B of the submission IssueOps (docs/research/data-pipeline.md section 1.4): .github/workflows/
game-submission-approve.yml re-runs scripts/validate_submission.py when a maintainer adds `approved`, then calls this
script with the validator's result.json ({ok, entry, errors, warnings}). It:

1. refuses a result that did not pass validation, or whose id is already in the catalog (two approvals racing);
2. inserts the entry into data/v1/games.json sorted by id and sets `generated_at` to now (UTC, whole seconds);
3. writes the catalog back in its committed formatting (2-space JSON, UTF-8 unescaped, trailing newline), so the diff
   shows only the new entry and `generated_at`;
4. optionally writes the pull request body (`Closes #N` and the entry) and the step outputs `slug` and `name`.

Icons are not fetched yet (decision #17).

Usage:
    python -I scripts/add_game.py --entry result.json --catalog data/v1/games.json \
        [--pr-body body.md] [--github-output "$GITHUB_OUTPUT"]

Exits 0 when the entry was added, 1 when it was refused (the catalog is left untouched) and 2 on a usage or input error.
"""

import argparse
import bisect
import json
import re
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RefusedError(Exception):
    """The entry must not be added; the message says why."""


def add_entry(catalog: dict[str, Any], entry: dict[str, Any]) -> None:
    """Insert an entry into the catalog's games, keeping them sorted by id.

    Raises:
        RefusedError: The id is already in the catalog.
    """
    games = catalog["games"]
    if any(game["id"] == entry["id"] for game in games):
        msg = f'"{entry["id"]}" is already in the catalog'
        raise RefusedError(msg)
    games.insert(bisect.bisect(games, entry["id"], key=lambda game: game["id"]), entry)


def serialise(catalog: dict[str, Any]) -> str:
    """The catalog as data/v1/games.json stores it: 2-space indent, UTF-8 text unescaped, a trailing newline."""
    return json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"


def timestamp(now: datetime) -> str:
    """`generated_at` for a moment: UTC, whole seconds, a "Z" suffix."""
    return now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pr_body(entry: dict[str, Any]) -> str:
    """The pull request body: what it adds, `Closes #N` for the submission issue and the entry as JSON."""
    candidate = json.dumps(entry, indent=2, ensure_ascii=False)
    # A fence longer than any backtick run in the JSON, so a value cannot close it.
    fence = "`" * max([3, *(len(run) + 1 for run in re.findall(r"`+", candidate))])
    issue = entry["source_issue"]
    summary = f"Adds `{entry['id']}` from the game submission #{issue}, which the validator accepted again on approval."
    return "\n".join(
        [
            summary,
            "",
            f"Closes #{issue}",
            "",
            "Candidate entry:",
            "",
            f"{fence}json",
            candidate,
            fence,
            "",
        ]
    )


def github_outputs(entry: dict[str, Any]) -> str:
    """Step outputs `slug` and `name`, each in a delimited block so a value cannot start another output."""
    lines = []
    for key, value in (("slug", entry["id"]), ("name", entry["name"])):
        delimiter = f"ghadelimiter_{secrets.token_hex(16)}"
        lines += [f"{key}<<{delimiter}", value, delimiter]
    return "\n".join(lines) + "\n"


def accepted_entry(result: dict[str, Any]) -> dict[str, Any]:
    """The candidate entry of a validator result.

    Raises:
        RefusedError: The submission did not pass validation.
    """
    entry = result.get("entry")
    if result.get("ok") is not True or not isinstance(entry, dict):
        msg = "the submission did not pass validation"
        raise RefusedError(msg)
    return entry


def _load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = f"{path} does not hold a JSON object"
        raise TypeError(msg)
    return data


def main(argv: list[str] | None = None, *, now: datetime | None = None) -> int:
    """Add the entry named on the command line to the catalog file.

    Args:
        argv: The command-line arguments; sys.argv by default.
        now: The moment written to `generated_at`; the current time by default.

    Returns:
        0 when the entry was added, 1 when it was refused, 2 on a usage or input error.
    """
    parser = argparse.ArgumentParser(description="Add an approved game submission to the catalog.")
    parser.add_argument("--entry", type=Path, required=True, help="scripts/validate_submission.py result (JSON)")
    parser.add_argument("--catalog", type=Path, required=True, help="data/v1/games.json, updated in place")
    parser.add_argument("--pr-body", type=Path, help="where to write the pull request body (Markdown)")
    parser.add_argument("--github-output", type=Path, help="step output file to append slug and name to")
    args = parser.parse_args(argv)
    try:
        entry = accepted_entry(_load_object(args.entry))
        catalog = _load_object(args.catalog)
        add_entry(catalog, entry)
        catalog["generated_at"] = timestamp(now or datetime.now(UTC))
        text = serialise(catalog)
        body = pr_body(entry)
        outputs = github_outputs(entry)
    except RefusedError as error:
        sys.stderr.write(f"add_game: refused: {error}\n")
        return 1
    except (OSError, TypeError, ValueError, KeyError) as error:
        sys.stderr.write(f"add_game: {error!r}\n")
        return 2
    args.catalog.write_text(text, encoding="utf-8")
    if args.pr_body:
        args.pr_body.write_text(body, encoding="utf-8")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(outputs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
