import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "quality-report.sh"
TUNER = ROOT / "scripts" / "auto-qa-tuner.sh"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "coverage"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or not all(shutil.which(tool) for tool in ("jq", "python3")), reason="needs bash, jq and python3"
)

# Stand-ins for the gate tools, so the report never runs the real suite (which runs this test). Each logs its
# arguments and reads its exit code from the environment; the pytest stub writes $FAKE_COVERAGE as the coverage report.
STUBS = {
    "ruff": 'echo "ruff $*" >>"$STUB_LOG"; [ "$1" = check ] && exit "${FAKE_RUFF_CHECK_RC:-0}"; '
    'exit "${FAKE_RUFF_FORMAT_RC:-0}"',
    "pytest": """echo "pytest $*" >>"$STUB_LOG"
for arg in "$@"; do
  case "$arg" in
    --cov-report=xml:*)
      if [ -n "${FAKE_COVERAGE:-}" ]; then cp "$FAKE_COVERAGE" "${arg#--cov-report=xml:}"; fi
      exit "${FAKE_COVERAGE_RC:-0}" ;;
  esac
done
echo "pytest output goes to stderr"
exit "${FAKE_PYTEST_RC:-0}"
""",
    "check-jsonschema": 'echo "check-jsonschema $*" >>"$STUB_LOG"; '
    'case "$3" in *"${FAKE_SCHEMA_FAIL:-none}"*) exit 1 ;; esac; exit 0',
}

GATE_ROWS = [
    "| `ruff check .` | ✅ pass |",
    "| `ruff format --check .` | ✅ pass |",
    "| `pytest` | ✅ pass |",
    "| `check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json` | ✅ pass |",
    "| `check-jsonschema --schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json` | ✅ pass |",
]


def checkout(tmp_path: Path) -> Path:
    """A tree holding the files fixtures/coverage/pass.xml measured, so its two source roots can be told apart."""
    tree = tmp_path / "tree"
    for name in (
        "dailies/core/__init__.py",
        "dailies/core/catalog.py",
        "dailies/core/search/__init__.py",
        "dailies/core/search/fold.py",
        "scripts/validate.py",
        "scripts/lib/catalog_io.py",
    ):
        (tree / name).parent.mkdir(parents=True, exist_ok=True)
        (tree / name).touch()
    return tree


def run(tmp_path: Path, **env: str) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name, body in STUBS.items():
        stub = bin_dir / name
        stub.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        stub.chmod(0o755)
    environment = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "GITHUB_SHA": "0123abc",
        "STUB_LOG": str(tmp_path / "calls.log"),
        "COVERAGE_XML": str(tmp_path / "coverage.xml"),
        "COVERAGE_ROOT": str(checkout(tmp_path)),
        "FAKE_COVERAGE": str(FIXTURES / "pass.xml"),
        **env,
    }
    return subprocess.run(  # noqa: S603 - fixed script, test-controlled environment
        [BASH, str(SCRIPT)], env=environment, capture_output=True, text=True, check=False, timeout=60
    )


def calls(tmp_path: Path) -> list[str]:
    return (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines()


def test_reports_every_gate_and_the_coverage_of_each_module(tmp_path: Path) -> None:
    result = run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "\n".join(
        [
            "# Quality report",
            "",
            "Commit: `0123abc`",
            "",
            "## Quality gates",
            "",
            "| Gate | Result |",
            "| ---- | ------ |",
            *GATE_ROWS,
            "",
            "## Unit-test coverage",
            "",
            "| Module | Lines | Branches |",
            "| ------ | ----- | -------- |",
            "| core | 80.00% | 75.00% |",
            "| scripts | 75.00% | 50.00% |",
            "",
        ]
    )
    # Tool output goes to stderr, so stdout stays a clean report.
    assert "pytest output goes to stderr" in result.stderr
    # One coverage run feeds both groups.
    assert calls(tmp_path) == [
        "ruff check .",
        "ruff format --check .",
        "pytest ",
        "check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json",
        "check-jsonschema --schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json",
        f"pytest --cov --cov-report=xml:{tmp_path / 'coverage.xml'}",
    ]


@pytest.mark.parametrize(
    ("env", "failed_gate"),
    [
        ({"FAKE_RUFF_CHECK_RC": "1"}, 0),
        ({"FAKE_RUFF_FORMAT_RC": "1"}, 1),
        ({"FAKE_PYTEST_RC": "1"}, 2),
        ({"FAKE_SCHEMA_FAIL": "games.json"}, 3),
        ({"FAKE_SCHEMA_FAIL": "popularity.json"}, 4),
    ],
)
def test_a_failed_gate_fails_the_report_but_everything_still_runs(
    tmp_path: Path, env: dict[str, str], failed_gate: int
) -> None:
    result = run(tmp_path, **env)

    assert result.returncode == 1
    for index, row in enumerate(GATE_ROWS):
        expected = row.replace("✅ pass", "❌ fail") if index == failed_gate else row
        assert expected in result.stdout
    assert "| core | 80.00% | 75.00% |" in result.stdout
    assert len(calls(tmp_path)) == 6


def test_a_failed_coverage_run_reports_n_a(tmp_path: Path) -> None:
    result = run(tmp_path, FAKE_COVERAGE_RC="1")

    assert result.returncode == 1
    assert "| core | ❌ n/a | ❌ n/a |" in result.stdout
    assert "| scripts | ❌ n/a | ❌ n/a |" in result.stdout


def test_a_report_left_by_an_earlier_run_is_not_used(tmp_path: Path) -> None:
    stale = tmp_path / "coverage.xml"
    shutil.copy(FIXTURES / "pass.xml", stale)

    # This run succeeds but writes no report.
    result = run(tmp_path, FAKE_COVERAGE="")

    assert result.returncode == 1
    assert "| core | ❌ n/a | ❌ n/a |" in result.stdout
    assert not stale.exists()


def test_a_malformed_coverage_report_reports_n_a(tmp_path: Path) -> None:
    result = run(tmp_path, FAKE_COVERAGE=str(FIXTURES / "malformed.xml"))

    assert result.returncode == 1
    assert "| core | ❌ n/a | ❌ n/a |" in result.stdout
    assert "not readable as XML" in result.stderr


def test_a_module_without_code_or_branches_has_no_percentage(tmp_path: Path) -> None:
    no_branches = tmp_path / "no-branches.xml"
    no_branches.write_text(
        '<?xml version="1.0" ?><coverage><sources><source>/w/Dailies/scripts</source></sources><packages>'
        '<package name="."><classes><class filename="validate.py"><lines>'
        '<line number="1" hits="1"/><line number="2" hits="0"/>'
        "</lines></class></classes></package></packages></coverage>",
        encoding="utf-8",
    )

    result = run(tmp_path, FAKE_COVERAGE=str(no_branches))

    # 0 of 0 is not a measurement: neither is a failure, and neither gives the tuner a number.
    assert result.returncode == 0, result.stderr
    assert "| core | no code yet | no code yet |" in result.stdout
    assert "| scripts | 50.00% | no branches |" in result.stdout


def test_a_floors_file_without_modules_is_an_error(tmp_path: Path) -> None:
    config = tmp_path / "floors.json"
    config.write_text('{"margin": 2, "floors": {}}', encoding="utf-8")

    result = run(tmp_path, QA_TUNING_CONFIG=str(config))

    assert result.returncode == 2
    assert "No modules in" in result.stderr
    assert result.stdout == ""


def test_the_tuner_reads_the_report(tmp_path: Path) -> None:
    report = tmp_path / "quality-report.md"
    report.write_text(run(tmp_path).stdout, encoding="utf-8")
    config = tmp_path / "auto-qa-tuning.json"
    floors = {"core": {"lines": 70, "branches": 50}, "scripts": {"lines": 70, "branches": 50}}
    config.write_text(json.dumps({"margin": 2, "floors": floors}), encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - fixed script, test-controlled arguments
        [BASH, str(TUNER), "--report", str(report), "--config", str(config)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "| core | lines | 70% | 80.00% | 78% ⬆️ |" in result.stdout
    assert "| core | branches | 50% | 75.00% | 73% ⬆️ |" in result.stdout
    assert "| scripts | lines | 70% | 75.00% | 73% ⬆️ |" in result.stdout
    assert "| scripts | branches | 50% | 50.00% | 50% |" in result.stdout
