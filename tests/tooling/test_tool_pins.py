"""Every copy of a dev-tool pin names the same version, so a bump in one place cannot leave the others behind.

ruff, pytest and pytest-cov are pinned in five workflows' `pip install` lines, in .pre-commit-config.yaml and in the
`ARG`s of Dockerfile.sandbox; shellcheck and actionlint in the `Static checks` job and in Dockerfile.sandbox. Dependabot
reads none of them, and `pre-commit autoupdate` bumps only its own file. A missed copy fails nothing on its own: CI
keeps linting with the old ruff while pre-commit formats with the new one, and the sandbox stops running the gates at
the versions CI installs, as docs/testing.md says it does.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
PRE_COMMIT = ROOT / ".pre-commit-config.yaml"
DOCKERFILE = ROOT / "Dockerfile.sandbox"
CI = WORKFLOWS / "ci.yml"

# `pytest-cov` before `pytest`, so the alternation does not stop at the shorter name.
_PIP_PIN = re.compile(r"(?<![\w-])(?P<tool>ruff|pytest-cov|pytest)==(?P<version>[^\s\"']+)")
_RUFF_HOOK = re.compile(r"repo:\s*https://github\.com/astral-sh/ruff-pre-commit\s*\n\s*rev:\s*v(?P<version>\S+)")
_DOCKER_ARG = re.compile(r"^ARG (?P<name>\w+)=(?P<value>\S+)$", re.MULTILINE)
_ENV_PIN = re.compile(r"^\s+(?P<name>(?:SHELLCHECK|ACTIONLINT)_(?:VERSION|SHA256)):\s*(?P<value>\S+)\s*$", re.MULTILINE)

# Dockerfile.sandbox ARG -> the name the other files pin it under.
DOCKER_ARGS = {
    "RUFF_VERSION": "ruff",
    "PYTEST_VERSION": "pytest",
    "PYTEST_COV_VERSION": "pytest-cov",
    "SHELLCHECK_VERSION": "SHELLCHECK_VERSION",
    "SHELLCHECK_SHA256": "SHELLCHECK_SHA256",
    "ACTIONLINT_VERSION": "ACTIONLINT_VERSION",
    "ACTIONLINT_SHA256": "ACTIONLINT_SHA256",
}


def collect_pins(
    workflows: dict[str, str], pre_commit: str, dockerfile: str, ci: str
) -> dict[str, dict[str, set[str]]]:
    """Pin name -> {file: versions it names}, from every place a dev tool is pinned."""
    pins: dict[str, dict[str, set[str]]] = {}

    def add(name: str, where: str, version: str) -> None:
        pins.setdefault(name, {}).setdefault(where, set()).add(version)

    for name, text in workflows.items():
        for match in _PIP_PIN.finditer(text):
            add(match.group("tool"), name, match.group("version"))
    for match in _RUFF_HOOK.finditer(pre_commit):
        add("ruff", ".pre-commit-config.yaml", match.group("version"))
    for match in _DOCKER_ARG.finditer(dockerfile):
        if match.group("name") in DOCKER_ARGS:
            add(DOCKER_ARGS[match.group("name")], "Dockerfile.sandbox", match.group("value"))
    for match in _ENV_PIN.finditer(ci):
        add(match.group("name"), "ci.yml", match.group("value"))
    return pins


def mismatches(pins: dict[str, dict[str, set[str]]]) -> list[str]:
    return [
        f"{name}: " + ", ".join(f"{where} {'/'.join(sorted(versions))}" for where, versions in sorted(sites.items()))
        for name, sites in sorted(pins.items())
        if len(set().union(*sites.values())) > 1
    ]


def repository_pins() -> dict[str, dict[str, set[str]]]:
    workflows = {path.name: path.read_text(encoding="utf-8") for path in sorted(WORKFLOWS.glob("*.yml"))}
    return collect_pins(
        workflows,
        PRE_COMMIT.read_text(encoding="utf-8"),
        DOCKERFILE.read_text(encoding="utf-8"),
        CI.read_text(encoding="utf-8"),
    )


def test_every_copy_of_a_tool_pin_names_the_same_version() -> None:
    assert mismatches(repository_pins()) == []


def test_every_pin_site_is_read() -> None:
    # A reworded pip line, hook or ARG that the patterns no longer match would make the check above pass vacuously.
    pins = repository_pins()
    assert set(pins["ruff"]) >= {
        "ci.yml",
        "claude.yml",
        "quality-report.yml",
        ".pre-commit-config.yaml",
        "Dockerfile.sandbox",
    }
    assert set(pins["pytest"]) >= {"ci.yml", "coverage-gate.yml", "game-submission-approve.yml", "Dockerfile.sandbox"}
    assert set(pins["pytest-cov"]) >= {"ci.yml", "coverage-gate.yml", "Dockerfile.sandbox"}
    for name in ("SHELLCHECK_VERSION", "SHELLCHECK_SHA256", "ACTIONLINT_VERSION", "ACTIONLINT_SHA256"):
        assert set(pins[name]) == {"ci.yml", "Dockerfile.sandbox"}, name


PRE_COMMIT_FIXTURE = "repos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.18.0\n"
DOCKERFILE_FIXTURE = "FROM x\nARG RUFF_VERSION=0.17.1\nARG PYTEST_VERSION=9.1.1\nARG ACTIONLINT_VERSION=1.7.12\n"
CI_FIXTURE = "jobs:\n  static:\n    env:\n      ACTIONLINT_VERSION: 1.7.13\n"


def test_an_autoupdated_pre_commit_hook_is_reported() -> None:
    pins = collect_pins(
        {"ci.yml": "run: python -m pip install ruff==0.17.1 pytest==9.1.1 pytest-cov==7.1.0\n"},
        PRE_COMMIT_FIXTURE,
        DOCKERFILE_FIXTURE,
        CI_FIXTURE,
    )
    assert mismatches(pins) == [
        "ACTIONLINT_VERSION: Dockerfile.sandbox 1.7.12, ci.yml 1.7.13",
        "ruff: .pre-commit-config.yaml 0.18.0, Dockerfile.sandbox 0.17.1, ci.yml 0.17.1",
    ]


def test_two_versions_in_one_workflow_are_reported() -> None:
    workflows = {"claude.yml": "pip install pytest==9.1.1\n...\npip install pytest==9.2.0 pytest-cov==7.1.0\n"}
    assert mismatches(collect_pins(workflows, "", "", "")) == ["pytest: claude.yml 9.1.1/9.2.0"]


def test_pytest_cov_is_not_read_as_pytest() -> None:
    pins = collect_pins({"a.yml": 'pip install "pytest-cov==7.1.0" pytest==9.1.1'}, "", "", "")
    assert pins == {"pytest-cov": {"a.yml": {"7.1.0"}}, "pytest": {"a.yml": {"9.1.1"}}}
