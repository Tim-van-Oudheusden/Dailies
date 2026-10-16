#!/usr/bin/env python3
"""Check what the weekly report step changed, then link the report from popularity.json.

The model that writes docs/popularity/<week>.md runs in the publish job's checkout. Afterwards the checkout may differ
from main in two paths only: data/v1/popularity.json, which must be byte-identical to the compute job's artifact (the
model never changes a number), and the week's report, a regular file. Anything else, including a changed .git/config
(which could make `git status` run a command), fails the job with a ::error:: line and leaves popularity.json as it is.
When the checks pass and the report exists, popularity.json gets `"report": "../popularity/<week>.md"`, the report's
URL relative to popularity.json on GitHub Pages; without a report the file stays byte-identical to the artifact.

Usage:
    python3 -I "$RUNNER_TEMP/trusted/report_guard.py" --week 2026-W43 \
        --reference "$RUNNER_TEMP/reference/popularity.json" --git-config "$RUNNER_TEMP/trusted/git-config"

Exits 0 when only allowed changes were found, 1 when the guard failed, 2 on a usage error.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

POPULARITY = "data/v1/popularity.json"
WEEK = re.compile(r"^\d{4}-W\d{2}$")


def report_path(week: str) -> str:
    """The week's report, relative to the repository root."""
    return f"docs/popularity/{week}.md"


def changed_paths(repo: Path) -> list[str]:
    """Every path `git status` reports as changed, staged or untracked; both sides of a rename."""
    git = shutil.which("git")
    if git is None:
        msg = "git is not on PATH"
        raise OSError(msg)
    # core.fsmonitor=false: a hostile repository config cannot make `git status` run a command.
    command = [git, "-C", str(repo), "-c", "core.fsmonitor=false", "status", "--porcelain=v1", "-z", "-uall"]
    status = subprocess.run(  # noqa: S603 - fixed command, the repository path comes from the workflow
        command, check=True, capture_output=True
    ).stdout.decode("utf-8", errors="replace")
    fields = status.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(fields) and fields[index]:
        entry = fields[index]
        paths.append(entry[3:])
        if entry[0] in "RC":
            # -z lists a rename or copy as "XY new\0old".
            index += 1
            paths.append(fields[index])
        index += 1
    return paths


def check(repo: Path, week: str, reference: Path, git_config: Path | None) -> list[str]:
    """The guard's findings; empty when the checkout holds only the allowed changes."""
    if git_config is not None and (repo / ".git" / "config").read_bytes() != git_config.read_bytes():
        return [".git/config changed while the report was written"]
    report = report_path(week)
    problems = [
        f"Unexpected change outside the weekly report: {path}"
        for path in dict.fromkeys(changed_paths(repo))
        if path not in (POPULARITY, report)
    ]
    for path in (POPULARITY, report):
        file = repo / path
        if file.is_symlink() or (file.exists() and not file.is_file()):
            problems.append(f"{path} is not a regular file")
    popularity = repo / POPULARITY
    if not popularity.is_symlink() and popularity.read_bytes() != reference.read_bytes():
        problems.append(f"{POPULARITY} is not byte-identical to the compute artifact; the numbers were changed")
    return problems


def link(repo: Path, week: str) -> bool:
    """Point popularity.json at the week's report when there is one, in compute.py's stable JSON format."""
    if not (repo / report_path(week)).is_file():
        return False
    popularity = repo / POPULARITY
    document = json.loads(popularity.read_text(encoding="utf-8"))
    document["report"] = f"../popularity/{week}.md"
    popularity.write_text(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    """Guard the checkout named on the command line and link the report.

    Args:
        argv: The command-line arguments; sys.argv by default.

    Returns:
        0 when only allowed changes were found, 1 when the guard failed, 2 on a usage error.
    """
    parser = argparse.ArgumentParser(description="Check the weekly report step's changes and link the report.")
    parser.add_argument("--week", required=True, help="the ISO week, e.g. 2026-W43")
    parser.add_argument("--reference", type=Path, required=True, help="popularity.json from the compute artifact")
    parser.add_argument("--git-config", type=Path, help="a copy of .git/config taken before the report step")
    parser.add_argument("--repo", type=Path, default=Path(), help="the checkout; the current directory by default")
    args = parser.parse_args(argv)
    if not WEEK.match(args.week):
        sys.stderr.write(f"report_guard: not an ISO week: {args.week!r}\n")
        return 2
    try:
        problems = check(args.repo, args.week, args.reference, args.git_config)
        if problems:
            sys.stdout.write("".join(f"::error::{problem}\n" for problem in problems))
            return 1
        if link(args.repo, args.week):
            sys.stdout.write(f"Linked {report_path(args.week)} from {POPULARITY}\n")
        else:
            sys.stdout.write(f"No report for {args.week}; {POPULARITY} is the compute artifact unchanged\n")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.stdout.write(f"::error::report guard failed: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
