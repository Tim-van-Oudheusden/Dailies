#!/usr/bin/env python3
"""Check that applying the add job's catalog patch changed only the catalog and its icons, as regular files.

The pull-request job of .github/workflows/game-submission-approve.yml applies a patch made by the add job, which reads
the untrusted submission issue and fetches the submitted page, then opens the pull request with the bot App's token.
Before that, the checkout may differ from main only in data/v1/games.json and files under data/v1/icons/. Any other
changed path fails, and so does an allowed path that is a symlink or not a regular file: pages.yml copies data/v1 with
`cp -rL`, so a link there would publish whatever it points to on the Pages runner. The catalog must also still be a
regular file. The changed paths come from scripts/popularity/report_guard.py, the weekly report's guard. The patch
could rewrite either script, so the workflow copies both before applying it, keeping report_guard.py under popularity/.

Usage:
    python3 -I "$RUNNER_TEMP/trusted/catalog_guard.py" [--repo DIR]

Exits 0 when only allowed changes were found and 1 when the guard failed, with a ::error:: line per problem.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# report_guard.py is copied on its own into a trusted directory by popularity.yml, so it stays self-contained and this
# script imports it by path; `python -I` leaves the script's directory off sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent / "popularity"))
from report_guard import changed_paths

CATALOG = "data/v1/games.json"
ICONS = "data/v1/icons/"


def check(repo: Path) -> list[str]:
    """The guard's findings; empty when the checkout holds only the allowed changes."""
    changed = list(dict.fromkeys(changed_paths(repo)))
    problems = [f"Unexpected change: {path}" for path in changed if path != CATALOG and not path.startswith(ICONS)]
    for path in dict.fromkeys([CATALOG, *(path for path in changed if path.startswith(ICONS))]):
        file = repo / path
        # A deleted icon is fine; a deleted catalog is not.
        if file.is_symlink() or ((file.exists() or path == CATALOG) and not file.is_file()):
            problems.append(f"{path} is not a regular file")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Guard the checkout named on the command line.

    Args:
        argv: The command-line arguments; sys.argv by default.

    Returns:
        0 when only allowed changes were found, 1 when the guard failed.
    """
    parser = argparse.ArgumentParser(description="Check the catalog patch's changes before the pull request opens.")
    parser.add_argument("--repo", type=Path, default=Path(), help="the checkout; the current directory by default")
    args = parser.parse_args(argv)
    try:
        problems = check(args.repo)
    except (OSError, subprocess.CalledProcessError) as error:
        sys.stdout.write(f"::error::catalog guard failed: {error}\n")
        return 1
    if problems:
        sys.stdout.write("".join(f"::error::{problem}\n" for problem in problems))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
