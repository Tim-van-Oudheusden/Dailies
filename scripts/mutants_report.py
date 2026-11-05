#!/usr/bin/env python3
"""Run mutmut over dailies/core and report the survivors that are not in the baseline (#368).

Run as `scripts/mutants_report.py [--baseline <path>] [--write] > mutants-report.md`. [tool.mutmut] in pyproject.toml
configures mutmut, which is taken from PATH; it is not in scripts/requirements.txt. Every run starts from an empty
mutants/, so verdicts left by an earlier run never stand in for this one's.

The Markdown report goes to stdout: the count per status, the new survivors, and the baseline entries that are now
killed or gone. mutmut's progress goes to stderr. A survivor is a mutant with the status `survived` or `no tests`.
mutmut's own names end in an ordinal that shifts when the function is edited, so the baseline
(.github/mutants-baseline.json) keys a survivor on its function and the lines it changes; docs/testing.md#python-mutants
gives the limits of that key. With --write the survivors of a finished run replace the baseline, for a maintainer to
review and commit. A run that failed never touches it.

The run has failed, and the report says so instead of counting survivors, when mutmut cannot start, a mutmut command
exits non-zero, mutmut lists no mutants, or any mutant is left `not checked` (an interrupted `mutmut run` exits 0).

$GITHUB_SHA names the commit.

Exit status: 0 when the run finished with no new survivor, 1 when there are new survivors or the run failed, 2 for bad
arguments or a missing or malformed baseline, which is checked before mutmut starts. Standard library only.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path(".github") / "mutants-baseline.json"
# `no tests` counts: a mutant no test even reaches is the weakest case of one no test catches.
SURVIVOR_STATUSES = ("survived", "no tests")
NOT_CHECKED = "not checked"
# Every mutant's name holds this between the function and the ordinal.
ORDINAL_MARK = "__mutmut_"
CHANGE_SEPARATOR = " | "
# A file descriptor rather than sys.stderr, which pytest's capture replaces with an object that has none.
STDERR = 2


class MutantsError(Exception):
    """The mutmut run failed; the message says how."""


class BaselineError(Exception):
    """The baseline file is missing or malformed; the message says how."""


@dataclass(frozen=True)
class Comparison:
    """The survivors of a run set against the baseline, which may hold the same key more than once."""

    new: list[str]
    known: int
    gone: list[str]


def load_baseline(path: Path) -> list[str]:
    """Return the survivor keys in the baseline file."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        msg = f"cannot read {path}: {error}"
        raise BaselineError(msg) from error
    survivors = document.get("survivors") if isinstance(document, dict) else None
    if not isinstance(survivors, list) or not all(isinstance(entry, str) for entry in survivors):
        msg = f'malformed {path}: expected {{"survivors": ["<key>", ...]}}'
        raise BaselineError(msg)
    return survivors


def mutmut(root: Path, *args: str, stdout: int = subprocess.PIPE) -> str:
    """Run one mutmut command in `root` and return what it printed."""
    command = ["mutmut", *args]
    try:
        result = subprocess.run(  # noqa: S603 - a fixed tool; the arguments are built here or are its own mutant names
            command, cwd=root, stdout=stdout, encoding="utf-8", check=False
        )
    except OSError as error:
        msg = f"could not start mutmut: {error}"
        raise MutantsError(msg) from error
    if result.returncode != 0:
        msg = f"`mutmut {args[0]}` exited {result.returncode}"
        raise MutantsError(msg)
    return result.stdout or ""


def parse_results(output: str) -> dict[str, str]:
    """Return the status of each mutant named in `mutmut results`, which prints `    <mutant>: <status>` lines."""
    rows = (line.strip().partition(": ") for line in output.split("\n"))
    return {name: status for name, _, status in rows if ORDINAL_MARK in name}


def run_mutants(root: Path) -> dict[str, str]:
    """Run mutmut from an empty mutants/ and return the status of every mutant."""
    shutil.rmtree(root / "mutants", ignore_errors=True)
    mutmut(root, "run", stdout=STDERR)
    found = parse_results(mutmut(root, "results", "--all", "true"))
    if not found:
        msg = "mutmut listed no mutants"
        raise MutantsError(msg)
    unchecked = sum(status == NOT_CHECKED for status in found.values())
    if unchecked:
        msg = f"{unchecked} of {len(found)} mutants were not checked"
        raise MutantsError(msg)
    return found


def survivor_key(root: Path, name: str) -> str:
    """Return the baseline key of a mutant: its function and the lines `mutmut show` says it changes."""
    _, _, hunks = mutmut(root, "show", name).partition("\n@@")
    changes = [f"{line[0]} {line[1:].strip()}" for line in hunks.split("\n") if line.startswith(("-", "+"))]
    if not changes:
        msg = f"`mutmut show {name}` shows no changed line"
        raise MutantsError(msg)
    function = name.partition(ORDINAL_MARK)[0]
    return f"{function}: {CHANGE_SEPARATOR.join(changes)}"


def compare(survivors: list[str], baseline: list[str]) -> Comparison:
    """Set the keys of a run against the baseline's, counting a key as often as it occurs."""
    current, reviewed = Counter(survivors), Counter(baseline)
    return Comparison(
        new=sorted((current - reviewed).elements()),
        known=(current & reviewed).total(),
        gone=sorted((reviewed - current).elements()),
    )


def fenced(entries: list[str]) -> list[str]:
    """Return the lines of a code block for `entries`, whose source text may hold any Markdown character."""
    return ["```text", *entries, "```"] if entries else ["None."]


def render(commit: str, found: dict[str, str], comparison: Comparison) -> str:
    """Return the report of a finished run."""
    rows = sorted(Counter(found.values()).items())
    lines = [
        "# Mutants report",
        "",
        f"Commit: `{commit}`",
        "",
        "## Totals",
        "",
        "| Status | Mutants |",
        "| ------ | ------- |",
        *(f"| {status} | {count} |" for status, count in rows),
        f"| all | {len(found)} |",
        "",
        f"Known survivors, in the baseline: {comparison.known}",
        "",
        f"## New survivors: {len(comparison.new)}",
        "",
        *fenced(comparison.new),
        "",
        f"## Baseline entries now killed or gone: {len(comparison.gone)}",
        "",
        *fenced(comparison.gone),
        "",
    ]
    return "\n".join(lines)


def render_failure(commit: str, reason: str) -> str:
    """Return the report of a run that failed, which has no survivors to count."""
    lines = ["# Mutants report", "", f"Commit: `{commit}`", "", f"❌ The mutmut run failed: {reason}.", ""]
    return "\n".join(lines)


def write_baseline(path: Path, survivors: list[str]) -> None:
    """Save the survivor keys as the baseline, sorted so that a new baseline diffs cleanly against the old one."""
    document = {"survivors": sorted(survivors)}
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stderr.write(f"Wrote the proposed baseline to {path}\n")


def main(argv: list[str] | None = None) -> int:
    """Run the report and return the exit status."""
    parser = argparse.ArgumentParser(description="Report the mutmut survivors in dailies/core not in the baseline.")
    parser.add_argument("--root", type=Path, default=ROOT, help="the checkout to run in (default: this repository)")
    parser.add_argument("--baseline", type=Path, help=f"the baseline file (default: {BASELINE} under --root)")
    parser.add_argument("--write", action="store_true", help="save the survivors of a finished run as the baseline")
    args = parser.parse_args(argv)

    baseline_path = args.baseline or args.root / BASELINE
    try:
        baseline = load_baseline(baseline_path)
    except BaselineError as error:
        sys.stderr.write(f"mutants_report: {error}\n")
        return 2

    commit = os.environ.get("GITHUB_SHA", "unknown")
    try:
        found = run_mutants(args.root)
        survivors = [survivor_key(args.root, name) for name, status in found.items() if status in SURVIVOR_STATUSES]
    except MutantsError as error:
        sys.stderr.write(f"mutants_report: {error}\n")
        sys.stdout.write(render_failure(commit, str(error)))
        return 1

    comparison = compare(survivors, baseline)
    sys.stdout.write(render(commit, found, comparison))
    if args.write:
        write_baseline(baseline_path, survivors)
    return 1 if comparison.new else 0


if __name__ == "__main__":
    sys.exit(main())
