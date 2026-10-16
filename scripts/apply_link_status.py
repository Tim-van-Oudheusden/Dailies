#!/usr/bin/env python3
"""Apply the link check's proposed status changes to the catalog, for the `data/link-status` pull request.

scripts/check_links.py --status-out DIR writes DIR/changes.json in the compliance job; the pull-request job checks out
the newest main and runs this script on it, so changes merged in between are kept. Each change sets an entry's
`status` and appends its `history` event; `generated_at` becomes the current time. Entries are never removed. The file
is written in the committed format, so the diff holds only the changed lines; it is not written when nothing changed.

Usage:
    python -I scripts/apply_link_status.py --changes DIR/changes.json --catalog data/v1/games.json

Exits 0 on success (also when every change was already made) and 2 on an error, leaving the catalog as it was.
Stdlib only.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# scripts/lib is not a package and `python -I` leaves the script's directory off sys.path, so add it by path.
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import linkstatus


def main(argv: list[str] | None = None, *, now: datetime | None = None) -> int:
    """Apply the changes named on the command line to the catalog file.

    Args:
        argv: The command-line arguments; sys.argv by default.
        now: The time recorded in `generated_at` and the history dates; the current UTC time by default.

    Returns:
        0 on success, 2 on an error.
    """
    parser = argparse.ArgumentParser(description="Apply the link check's status changes to the catalog.")
    parser.add_argument("--changes", type=Path, required=True, help="changes.json from check_links.py --status-out")
    parser.add_argument("--catalog", type=Path, required=True, help="data/v1/games.json, rewritten in place")
    args = parser.parse_args(argv)
    try:
        changes = linkstatus.load_changes(args.changes)
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
        applied = linkstatus.apply_changes(catalog, changes, now or datetime.now(UTC))
        if applied:
            args.catalog.write_text(linkstatus.dump_catalog(catalog), encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"apply_link_status: {error}\n")
        return 2
    sys.stderr.write(f"apply_link_status: changed {', '.join(applied) or 'nothing'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
