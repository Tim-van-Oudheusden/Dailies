#!/usr/bin/env python3
"""Write the body of the weekly popularity pull request from compute.py's summary.json.

The body is numbers only: the five most popular games and each source's health (failed and unranked domains), so a
reviewer can spot a broken week before merging. Game names come from the maintainer-approved catalog.

Usage:
    python -I scripts/popularity/pr_body.py --summary "$RUNNER_TEMP/result/summary.json" \
        --out "$RUNNER_TEMP/result/pr-body.md" --run-url "$RUN_URL"

Exits 0 when the body was written, 2 on a usage error or an unreadable summary.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOP = 5


def _cell(text: object) -> str:
    """Table-cell text: a pipe would end the cell, a newline the row."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _domains(label: str, domains: list[str]) -> list[str]:
    return [f"{label}: {', '.join(f'`{domain}`' for domain in domains)}", ""] if domains else []


def render(summary: dict[str, Any], run_url: str | None = None) -> str:
    """The pull-request body for one week's summary.json.

    Args:
        summary: The summary.json written by compute.py.
        run_url: The workflow run whose artifacts hold the raw signals.

    Returns:
        Markdown ending in a newline.
    """
    lines = [
        (
            f"Weekly Popular and Trending shelves for **{summary['week']}** "
            f"(method_version {summary['method_version']}), generated {summary['generated_at']}."
        ),
        "",
        f"### Top {TOP} popular",
        "",
        "| # | Game | Score |",
        "|---:|---|---:|",
    ]
    lines += [
        f"| {rank} | {_cell(game['name'])} (`{_cell(game['id'])}`) | {game['score']} |"
        for rank, game in enumerate(summary["popular"][:TOP], start=1)
    ]
    lines += [
        "",
        "### Source health",
        "",
        "| Source | OK | Failed | Domains | Fetched |",
        "|---|---:|---:|---:|---|",
    ]
    sources = summary["sources"]
    lines += [
        f"| {_cell(name)} | {health['ok']} | {health['failed']} | {health['count']} | {health['fetched_at']} |"
        for name, health in sorted(sources.items())
    ]
    lines.append("")
    for name, health in sorted(sources.items()):
        lines += _domains(f"Failed domains ({name})", health.get("failed_domains", []))
        lines += _domains(f"Unranked domains ({name})", health.get("unranked_domains", []))
    raw = "Raw signals and summary.json are attached to the workflow run as artifacts (kept 90 days)"
    lines.append(f"{raw}: {run_url}" if run_url else f"{raw}.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Render the body for the summary named on the command line.

    Args:
        argv: The command-line arguments; sys.argv by default.

    Returns:
        0 when the body was written, 2 on a usage error or an unreadable summary.
    """
    parser = argparse.ArgumentParser(description="Write the weekly popularity pull-request body.")
    parser.add_argument("--summary", type=Path, required=True, help="compute.py's summary.json")
    parser.add_argument("--out", type=Path, required=True, help="where to write the Markdown body")
    parser.add_argument("--run-url", help="the workflow run that holds the raw-signal artifacts")
    args = parser.parse_args(argv)
    try:
        body = render(json.loads(args.summary.read_text(encoding="utf-8")), args.run_url)
        args.out.write_text(body, encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"pr_body: {error}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
