"""Facts the docs repeat in several places agree with the code that defines them (#293).

Each check is a function that returns a list of violations for one document; the tests at the top run them over the
repository's docs, the tests at the bottom feed each one an inline fixture that breaks it. The sources of truth are
the `release.yml` publish step (release assets), `AUTO_MERGE_JOBS` in `test_workflows.py` (who merges a bot pull
request), the data files `dailies/data/fetcher.py` requests, and the permissions and environments of every workflow.

Not covered, because prose cannot be checked mechanically: status and history sentences, and runbook error text. The
README "Installing" list is left out on purpose (it lists only the user-installable bundles), and the metainfo copy of
the download list is translatable and stays a manual check.
"""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from dailies.core import cache
from tests.tooling.test_workflows import (
    AUTO_MERGE_JOBS,
    ROOT,
    WORKFLOWS,
    environment_of,
    jobs_of,
    load_yaml,
    workflow_files,
)

README = ROOT / "README.md"
ARCHITECTURE = ROOT / "docs" / "architecture.md"
BAD_RELEASE = ROOT / "docs" / "runbooks" / "bad-release.md"
MULTI_AGENT = ROOT / "docs" / "multi-agent.md"
DATA_README = ROOT / "data" / "v1" / "README.md"
FETCHER = ROOT / "dailies" / "data" / "fetcher.py"

# Docs that describe the project today. Proposals and research notes record what was decided or found at the time.
HISTORICAL_DOCS = ("docs/proposals/", "docs/research/")

MERMAID = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
FENCE = re.compile(r"```.*?```", re.DOTALL)
MERMAID_NODE = re.compile(r"\b(?P<id>\w+)\[\"(?P<text>[^\"]*)\"\]")
MERMAID_EDGE = re.compile(r"\b(?P<source>\w+)(?:\[\"[^\"]*\"\])?\s*-->\|\"(?P<label>[^\"]*)\"\|")
HUMAN_MERGE = re.compile(
    r"\bhuman[- ]merge[sd]?\b|\b(?:a|the) (?:human|person) merges\b|\bmerged by a (?:human|person)\b", re.IGNORECASE
)

# The weekly shelves are the one pull request that merges itself; the catalog pull request is opened by this workflow.
CATALOG_WORKFLOW = "game-submission-approve.yml"
# What each requested data file is called in the README privacy bullet.
README_PHRASES = {"games.json": "game list", "popularity.json": "shelves", "icons/": "icons"}

WRITE_SCOPES = ("issues", "pull-requests")


def text_of(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def squash(text: str) -> str:
    return " ".join(text.split())


# --- 1. release assets ------------------------------------------------------------------------------------------------


def release_assets(workflow: dict) -> list[str]:
    """The file names the publish step attaches to the release (`with.files`, one path per line)."""
    assets: list[str] = []
    for step in jobs_of(workflow)["publish"]["steps"]:
        files = (step.get("with") or {}).get("files")
        if files:
            assets.extend(Path(line.strip()).name for line in str(files).splitlines() if line.strip())
    return assets


def release_diagram(markdown: str) -> str | None:
    return next((block for block in MERMAID.findall(markdown) if "GitHub Release" in block), None)


def asset_violations(name: str, text: str, assets: list[str]) -> list[str]:
    return [f"{name} does not name the release asset {asset}" for asset in assets if asset not in text]


# --- 2. who merges ----------------------------------------------------------------------------------------------------


def merging_workflows(reviewed: dict[tuple[str, str], str] = AUTO_MERGE_JOBS) -> set[str]:
    return {workflow for workflow, _ in reviewed}


def edge_workflow(node_text: str) -> str | None:
    """The workflow whose pull request a diagram node names, by the commit scope in its title."""
    if "data(popularity)" in node_text:
        return "popularity.yml"
    if "data(games)" in node_text:
        return CATALOG_WORKFLOW
    return None


def merge_edges(markdown: str) -> Iterator[tuple[str, str]]:
    """(workflow, label) for every diagram edge leaving a workflow's pull request whose label says who merges it."""
    for diagram in MERMAID.findall(markdown):
        nodes = {m["id"]: m["text"] for m in MERMAID_NODE.finditer(diagram)}
        for edge in MERMAID_EDGE.finditer(diagram):
            workflow = edge_workflow(nodes.get(edge["source"], ""))
            if workflow is not None and "merge" in edge["label"].lower():
                yield workflow, edge["label"]


def merge_edge_violations(name: str, markdown: str, merging: set[str]) -> list[str]:
    violations = []
    for workflow, label in merge_edges(markdown):
        says_human = bool(HUMAN_MERGE.search(label))
        if workflow in merging and says_human:
            violations.append(f"{name}: the {workflow} pull request merges itself, but an edge says {label!r}")
        if workflow not in merging and not says_human:
            violations.append(f"{name}: the {workflow} pull request waits for a person, but an edge says {label!r}")
    return violations


def merge_prose_violations(name: str, markdown: str, merging: set[str]) -> list[str]:
    """A paragraph or table row that names a self-merging workflow's pull request must not say a person merges it."""
    violations = []
    for paragraph in re.split(r"\n\s*\n|\n(?=\|)", FENCE.sub("", markdown)):
        flat = squash(paragraph)
        for workflow in sorted(merging):
            stem = workflow.removesuffix(".yml")
            if stem in flat.lower() and (said := HUMAN_MERGE.search(flat)):
                violations.append(f"{name}: {stem} merges itself, but a paragraph says {said.group(0)!r}: {flat[:60]}…")
    return violations


def checked_docs() -> list[Path]:
    docs = [README, *sorted((ROOT / "docs").rglob("*.md"))]
    return [path for path in docs if not str(path.relative_to(ROOT)).startswith(HISTORICAL_DOCS)]


# --- 3. what the app downloads ----------------------------------------------------------------------------------------


def fetched_files(source: str) -> list[str]:
    """The data files the fetcher asks for: the cache names it refreshes, and the icons it downloads."""
    files = [f"{getattr(cache, constant)}.json" for constant in re.findall(r"\bcache\.([A-Z_]+)\b", source)]
    if re.search(r"\bIcons\(", source):
        files.append("icons/")
    return files


def privacy_bullet(readme: str) -> str:
    match = re.search(r"^- \*\*No account, no tracking\.\*\*.*?(?=^- \*\*|^\S|\Z)", readme, re.DOTALL | re.MULTILINE)
    return squash(match.group(0)) if match else ""


def download_violations(name: str, text: str, phrases: dict[str, str]) -> list[str]:
    return [
        f"{name} does not name {phrase!r}, which the app downloads" for phrase in phrases.values() if phrase not in text
    ]


# --- 4. work the workflows generate -----------------------------------------------------------------------------------


def generating_workflows(workflows: dict[str, dict]) -> set[str]:
    """Workflows with a job that can open issues or pull requests, or that runs in the bot environment."""
    return {
        name
        for name, workflow in workflows.items()
        for job in jobs_of(workflow).values()
        if environment_of(job) == "bot"
        or any((job.get("permissions") or {}).get(scope) == "write" for scope in WRITE_SCOPES)
    }


def generated_work_rows(markdown: str) -> set[str]:
    section = re.search(r"^## Work the workflows generate\n(.*?)(?=^## )", markdown, re.DOTALL | re.MULTILINE)
    rows = [line for line in (section.group(1) if section else "").splitlines() if line.startswith("|")]
    return {name for row in rows for name in re.findall(r"`([\w.-]+\.ya?ml)`", row.split("|")[1])}


def work_table_violations(workflows: dict[str, dict], markdown: str) -> list[str]:
    rows = generated_work_rows(markdown)
    return [
        f"{name} can open issues or pull requests but has no row in 'Work the workflows generate'"
        for name in sorted(generating_workflows(workflows) - rows)
    ]


# --- the repository's files -------------------------------------------------------------------------------------------


def workflows() -> dict[str, dict]:
    return {path.name: load_yaml(text_of(path)) for path in workflow_files()}


def test_release_assets_are_named_in_every_diagram_and_runbook() -> None:
    assets = release_assets(load_yaml(text_of(WORKFLOWS / "release.yml")))
    assert assets
    for path in (README, ARCHITECTURE):
        diagram = release_diagram(text_of(path))
        assert diagram is not None, f"{path.name} has no release diagram"
        assert asset_violations(path.name, diagram, assets) == []
    assert asset_violations(BAD_RELEASE.name, text_of(BAD_RELEASE), assets) == []


def test_no_diagram_edge_misreports_who_merges() -> None:
    for path in (README, ARCHITECTURE):
        seen = {workflow for workflow, _ in merge_edges(text_of(path))}
        assert seen == {"popularity.yml", CATALOG_WORKFLOW}, f"{path.name}: merge edges found for {sorted(seen)}"
    merging = merging_workflows()
    violations = [
        v for path in checked_docs() for v in merge_edge_violations(str(path.relative_to(ROOT)), text_of(path), merging)
    ]
    assert violations == []


def test_no_paragraph_says_a_person_merges_a_self_merging_pull_request() -> None:
    merging = merging_workflows()
    violations = [
        v
        for path in checked_docs()
        for v in merge_prose_violations(str(path.relative_to(ROOT)), text_of(path), merging)
    ]
    assert violations == []


def test_every_downloaded_file_is_named_in_the_readme_and_the_data_readme() -> None:
    files = fetched_files(text_of(FETCHER))
    assert files
    assert sorted(files) == sorted(README_PHRASES), "a data file the fetcher requests has no README phrase"
    bullet = privacy_bullet(text_of(README))
    assert bullet
    assert download_violations("README.md", bullet, {file: README_PHRASES[file] for file in files}) == []
    assert download_violations("data/v1/README.md", text_of(DATA_README), {file: file for file in files}) == []


def test_every_generating_workflow_has_a_row_in_the_work_table() -> None:
    assert work_table_violations(workflows(), text_of(MULTI_AGENT)) == []


# --- fixtures: each check fails when its claim drifts -----------------------------------------------------------------

DIAGRAM = """```mermaid
flowchart TD
  PR1["PR: data(games): add a game"]
  PR2["PR: data(popularity): week WEEK"]
  PR1 -->|"{catalog}"| MAIN["main"]
  PR2 -->|"{popularity}"| MAIN
```
"""


def test_fixture_release_asset_missing_from_a_diagram_fails() -> None:
    assert asset_violations("d.md", "Dailies-x86_64.flatpak", ["Dailies-x86_64.flatpak", "SHA256SUMS"]) == [
        "d.md does not name the release asset SHA256SUMS"
    ]


def test_fixture_publish_step_files_are_read_by_base_name() -> None:
    workflow = load_yaml(
        "jobs:\n  publish:\n    steps:\n      - uses: x\n        with:\n          files: |\n"
        "            dist/A\n            dist/B\n"
    )
    assert release_assets(workflow) == ["A", "B"]


def test_fixture_self_merging_edge_labelled_human_fails() -> None:
    markdown = DIAGRAM.format(catalog="human merge", popularity="human merge")
    assert len(merge_edge_violations("d.md", markdown, {"popularity.yml"})) == 1


def test_fixture_person_merged_edge_labelled_automatic_fails() -> None:
    markdown = DIAGRAM.format(catalog="merges itself", popularity="merges itself")
    assert len(merge_edge_violations("d.md", markdown, {"popularity.yml"})) == 1


def test_fixture_matching_edges_pass() -> None:
    markdown = DIAGRAM.format(catalog="human merge", popularity="merges itself")
    assert merge_edge_violations("d.md", markdown, {"popularity.yml"}) == []


@pytest.mark.parametrize("says", ["that a human merges", "a human-merged one", "a person merges", "merged by a person"])
def test_fixture_prose_with_a_person_merging_the_popularity_pull_request_fails(says: str) -> None:
    text = f"The popularity job opens a pull request\n{says}.\n\nOther text."
    assert len(merge_prose_violations("d.md", text, {"popularity.yml"})) == 1


def test_fixture_prose_about_another_pull_request_passes() -> None:
    text = "A game submission opens a pull request a human merges.\n\nThe popularity pull request merges itself."
    assert merge_prose_violations("d.md", text, {"popularity.yml"}) == []


def test_fixture_fetched_files_follow_the_fetcher() -> None:
    assert fetched_files("names = [cache.CATALOG, cache.POPULARITY]\nself.icons = Icons(x)") == [
        "games.json",
        "popularity.json",
        "icons/",
    ]


def test_fixture_download_missing_from_a_doc_fails() -> None:
    assert download_violations("d.md", "the game list", {"popularity.json": "shelves"}) == [
        "d.md does not name 'shelves', which the app downloads"
    ]


def test_fixture_privacy_bullet_is_cut_at_the_next_bullet() -> None:
    readme = "- **No account, no tracking.** Downloads the list\n  and the icons.\n- **Next.** shelves\n"
    assert privacy_bullet(readme) == "- **No account, no tracking.** Downloads the list and the icons."


@pytest.mark.parametrize(
    "permissions",
    ["issues: write", "pull-requests: write"],
)
def test_fixture_workflow_with_a_write_scope_needs_a_row(permissions: str) -> None:
    workflow = load_yaml(f"jobs:\n  a:\n    permissions:\n      {permissions}\n")
    table = "## Work the workflows generate\n\n| Workflow |\n| --- |\n| `other.yml` |\n\n## Next\n"
    assert len(work_table_violations({"new.yml": workflow}, table)) == 1


def test_fixture_workflow_in_the_bot_environment_needs_a_row() -> None:
    workflow = load_yaml("jobs:\n  a:\n    environment: bot\n")
    assert len(work_table_violations({"new.yml": workflow}, "## Work the workflows generate\n\n## Next\n")) == 1


def test_fixture_workflow_with_a_row_passes() -> None:
    workflow = load_yaml("jobs:\n  a:\n    permissions:\n      issues: write\n")
    table = "## Work the workflows generate\n\n| Workflow |\n| --- |\n| `new.yml` (link check) | x |\n\n## Next\n"
    assert work_table_violations({"new.yml": workflow}, table) == []


def test_fixture_workflow_named_only_in_another_rows_second_column_needs_a_row() -> None:
    workflow = load_yaml("jobs:\n  a:\n    permissions:\n      issues: write\n")
    table = "## Work the workflows generate\n\n| Workflow |\n| --- |\n| `other.yml` | after `new.yml` |\n\n## Next\n"
    assert len(work_table_violations({"new.yml": workflow}, table)) == 1


def test_fixture_table_rows_are_checked_one_by_one() -> None:
    text = "| popularity.yml | merges itself |\n| other.yml | a human merges |\n"
    assert merge_prose_violations("d.md", text, {"popularity.yml"}) == []
