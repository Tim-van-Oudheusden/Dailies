#!/usr/bin/env python3
"""Create the Dailies backlog on GitHub from the drafts in docs/issues/.

Each draft is `NN-slug.md` with a small front matter block:

    ---
    key: 26
    title: data: catalog and popularity JSON Schemas ...
    type: Task                      # GitHub issue type (Task | Feature)
    labels: milestone::M0, data, type::task, priority::high
    parent: 2                       # epic this issue is a sub-issue of (optional)
    blocked_by: 10, 20              # keys of blocking issues (optional)
    ---

`key` is the issue number the drafts expect (they were written for an empty
repository, so key N becomes #N). Inside bodies, `#N` with N a known key is a
reference to another draft. The script works in two passes so it is correct
even if GitHub hands out different numbers:

1. create every issue (title + placeholder body) in key order and record
   key -> number in `.created.json`;
2. render each body (remap `#N`, append the generated Dependencies section,
   expand {{TABLE}} / {{CHILDREN}}), then edit the issue, set its type, link
   it to its parent epic as a sub-issue and record native "blocked by"
   dependencies.

Re-running resumes from `.created.json`. Needs `gh` authenticated with
issues:write on the repository.

    python3 docs/issues/create_issues.py --repo Tim-van-Oudheusden/Dailies [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = HERE / ".created.json"

LABELS = {
    "epic": ("3e4b9e", "Tracking issue that groups sub-issues"),
    "decision": ("d93f0b", "Owner decision needed (proposal §18)"),
    "spike": ("fbca04", "Time-boxed investigation that de-risks later work"),
    "milestone::M0": ("0e8a16", "M0 Scaffold"),
    "milestone::M1": ("1d76db", "M1 Usable launcher -> v0.1.0"),
    "milestone::M2": ("5319e7", "M2 Data pipeline -> v0.2.0"),
    "milestone::M3": ("b60205", "M3 Agentic report and hygiene -> v0.3.0"),
    "milestone::M4": ("c5def5", "M4 Distribution"),
    "milestone::M5": ("bfdadc", "M5 Growth"),
    "type::feature": ("a2eeef", "New user-facing capability"),
    "type::task": ("ededed", "Engineering task"),
    "type::chore": ("ededed", "Repository or tooling upkeep"),
    "type::bug": ("d73a4a", "Something is broken"),
    "priority::critical": ("b60205", "Drop everything"),
    "priority::high": ("d93f0b", "On the critical path"),
    "priority::medium": (
        "fbca04",
        "Needed for the milestone, not on the critical path",
    ),
    "priority::low": ("0e8a16", "Nice to have"),
    "app": ("1d76db", "dailies/** application code and UI"),
    "data": ("0e8a16", "data/v1/** catalog, popularity and data scripts"),
    "flatpak": ("5319e7", "build-aux/** manifests and packaging"),
    "ci": ("000000", ".github/** workflows and repo automation"),
    "documentation": ("0075ca", "Docs and prose"),
    "game-submission": ("c2e0c6", "A DLE submitted through the new-game form"),
    "validated": ("0e8a16", "Submission passed automated validation"),
    "needs-changes": ("e99695", "Submission failed validation"),
    "approved": ("0e8a16", "Maintainer approved; stage B opens the PR"),
    "automated": ("ededed", "Opened by a workflow"),
    "ai-fix-requested": ("7057ff", "Hand this issue to Claude Code (claude.yml)"),
}


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        raise SystemExit(f"{path.name}: missing front matter")
    meta: dict = {"file": path.name, "body": m.group(2).strip() + "\n"}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition(":")
        v = v.split("  #", 1)[0].strip()
        meta[k.strip()] = v
    meta["key"] = int(meta["key"])
    meta["labels"] = [s.strip() for s in meta.get("labels", "").split(",") if s.strip()]
    meta["blocked_by"] = [
        int(s) for s in meta.get("blocked_by", "").replace(" ", "").split(",") if s
    ]
    meta["parent"] = int(meta["parent"]) if meta.get("parent") else None
    return meta


def load() -> dict[int, dict]:
    drafts = {}
    for p in sorted(HERE.glob("[0-9][0-9]-*.md")):
        d = parse(p)
        if d["key"] in drafts:
            raise SystemExit(f"duplicate key {d['key']}")
        drafts[d["key"]] = d
    keys = set(drafts)
    for d in drafts.values():
        for b in d["blocked_by"] + ([d["parent"]] if d["parent"] else []):
            if b not in keys:
                raise SystemExit(f"{d['file']}: unknown reference {b}")
    # cycle check
    state: dict[int, int] = {}

    def visit(k: int) -> None:
        if state.get(k) == 1:
            raise SystemExit(f"dependency cycle through {k}")
        if state.get(k) == 2:
            return
        state[k] = 1
        for b in drafts[k]["blocked_by"]:
            visit(b)
        state[k] = 2

    for k in drafts:
        visit(k)
    for d in drafts.values():
        d["blocks"] = sorted(
            k for k, o in drafts.items() if d["key"] in o["blocked_by"]
        )
        d["children"] = sorted(k for k, o in drafts.items() if o["parent"] == d["key"])
    return drafts


def remap(text: str, num: dict[int, int]) -> str:
    return re.sub(
        r"(?<![\w/&])#(\d{1,3})\b",
        lambda m: f"#{num.get(int(m.group(1)), int(m.group(1)))}",
        text,
    )


def milestone(d: dict) -> str:
    for label in d["labels"]:
        if label.startswith("milestone::"):
            return label.split("::", 1)[1]
    return "—"


def render(d: dict, drafts: dict[int, dict], num: dict[int, int]) -> str:
    def ref(k: int) -> str:
        return f"#{num.get(k, k)} {drafts[k]['title']}"

    # Remap draft keys to real numbers first; the generated parts below already
    # use real numbers and must not be remapped a second time.
    body = remap(d["body"], num)
    if "{{TABLE}}" in body:
        rows = ["| # | Milestone | Title | Blocked by |", "|---|---|---|---|"]
        for k in sorted(drafts):
            o = drafts[k]
            if "epic" in o["labels"]:
                continue
            blockers = ", ".join(f"#{num.get(b, b)}" for b in o["blocked_by"]) or "—"
            rows.append(
                f"| #{num.get(k, k)} | {milestone(o)} | {o['title'].replace('|', '/')} | {blockers} |"
            )
        body = body.replace("{{TABLE}}", "\n".join(rows))
    if "{{CHILDREN}}" in body:
        lines = []
        for k in d["children"]:
            o = drafts[k]
            blockers = ", ".join(f"#{num.get(b, b)}" for b in o["blocked_by"])
            lines.append(
                f"- [ ] #{num.get(k, k)} — blocked by {blockers}"
                if blockers
                else f"- [ ] #{num.get(k, k)} — no blockers, can start now"
            )
        body = body.replace("{{CHILDREN}}", "\n".join(lines))
    if "epic" not in d["labels"]:
        dep = ["## Dependencies", ""]
        dep.append("**Blocked by** (finish these first):")
        dep += [f"- [ ] {ref(b)}" for b in d["blocked_by"]] or [
            "- nothing, this can start immediately"
        ]
        dep.append("")
        dep.append("**Blocks** (these wait for this issue):")
        dep += [f"- {ref(b)}" for b in d["blocks"]] or ["- nothing directly"]
        if d["parent"]:
            dep += ["", f"**Epic:** #{num.get(d['parent'], d['parent'])}"]
        body = body.rstrip() + "\n\n" + "\n".join(dep) + "\n"
    return (
        body.rstrip()
        + "\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_\n"
    )


def gh(*args: str, input_: str | None = None, check: bool = True) -> str:
    r = subprocess.run(
        ["gh", *args],
        input=input_ if input_ is not None else "",
        capture_output=True,
        text=True,
        check=False,
    )
    if check and r.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} failed:\n{r.stderr}")
    return r.stdout.strip()


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--repo", required=True, help="OWNER/REPO")
    ap.add_argument(
        "--dry-run", action="store_true", help="render bodies to stdout, call nothing"
    )
    args = ap.parse_args()
    drafts = load()

    if args.dry_run:
        ident = {k: k for k in drafts}
        for k in sorted(drafts):
            print(
                f"===== #{k} {drafts[k]['title']}\n{render(drafts[k], drafts, ident)}"
            )
        print(f"{len(drafts)} drafts OK", file=sys.stderr)
        return

    for name, (color, desc) in LABELS.items():
        gh(
            "label",
            "create",
            name,
            "--repo",
            args.repo,
            "--color",
            color,
            "--description",
            desc,
            "--force",
        )

    num: dict[int, int] = (
        {int(k): v for k, v in json.loads(STATE.read_text()).items()}
        if STATE.exists()
        else {}
    )
    for k in sorted(drafts):
        if k in num:
            continue
        d = drafts[k]
        cmd = [
            "issue",
            "create",
            "--repo",
            args.repo,
            "--title",
            d["title"],
            "--body",
            "Body is being filled in…",
        ]
        for label in d["labels"]:
            cmd += ["--label", label]
        url = gh(*cmd)
        num[k] = int(url.rstrip("/").rsplit("/", 1)[1])
        STATE.write_text(json.dumps(num, indent=2))
        print(f"created #{num[k]} (draft {k}) {d['title']}")

    owner_repo = args.repo
    ids = {
        k: int(gh("api", f"repos/{owner_repo}/issues/{n}", "--jq", ".id"))
        for k, n in num.items()
    }
    for k in sorted(drafts):
        d = drafts[k]
        n = num[k]
        gh(
            "issue",
            "edit",
            str(n),
            "--repo",
            args.repo,
            "--body-file",
            "-",
            input_=render(d, drafts, num),
        )
        if d.get("type"):
            gh(
                "api",
                "-X",
                "PATCH",
                f"repos/{owner_repo}/issues/{n}",
                "-f",
                f"type={d['type']}",
                check=False,
            )
        if d["parent"]:
            gh(
                "api",
                "-X",
                "POST",
                f"repos/{owner_repo}/issues/{num[d['parent']]}/sub_issues",
                "-F",
                f"sub_issue_id={ids[k]}",
                check=False,
            )
        for b in d["blocked_by"]:
            gh(
                "api",
                "-X",
                "POST",
                f"repos/{owner_repo}/issues/{n}/dependencies/blocked_by",
                "-F",
                f"issue_id={ids[b]}",
                check=False,
            )
        print(f"filled #{n} {d['title']}")


if __name__ == "__main__":
    main()
