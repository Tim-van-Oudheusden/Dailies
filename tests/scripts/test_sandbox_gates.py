import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "sandbox-gates.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash")

# Stand-ins for the gate tools, so the script never runs the real suite (which runs this test). Each logs its
# arguments to $STUB_LOG and reads its exit code from the environment. `meson test` also logs XDG_DATA_DIRS, which
# decides whether the installed app finds its GSettings schema.
STUBS = {
    "ruff": 'echo "ruff $*" >>"$STUB_LOG"; [ "$1" = check ] && exit "${FAKE_RUFF_CHECK_RC:-0}"; '
    'exit "${FAKE_RUFF_FORMAT_RC:-0}"',
    "pytest": 'echo "pytest $*" >>"$STUB_LOG"; exit "${FAKE_PYTEST_RC:-0}"',
    "check-jsonschema": """echo "check-jsonschema $*" >>"$STUB_LOG"
case "$*" in
  *games.json) exit "${FAKE_GAMES_SCHEMA_RC:-0}" ;;
  *) exit "${FAKE_POPULARITY_SCHEMA_RC:-0}" ;;
esac
""",
    "shellcheck": 'echo "shellcheck $*" >>"$STUB_LOG"; exit "${FAKE_SHELLCHECK_RC:-0}"',
    "actionlint": 'echo "actionlint $*" >>"$STUB_LOG"; exit "${FAKE_ACTIONLINT_RC:-0}"',
    "meson": """echo "meson $*" >>"$STUB_LOG"
case "$1" in
  setup) exit "${FAKE_MESON_SETUP_RC:-0}" ;;
  install) exit "${FAKE_MESON_INSTALL_RC:-0}" ;;
  test)
    echo "XDG_DATA_DIRS=$XDG_DATA_DIRS" >>"$STUB_LOG"
    exit "${FAKE_MESON_TEST_RC:-0}"
    ;;
esac
""",
    "coverage-check": 'echo "coverage-check $*" >>"$STUB_LOG"; exit "${FAKE_COVERAGE_CHECK_RC:-0}"',
}


def run(tmp_path: Path, **env: str) -> tuple[subprocess.CompletedProcess[str], str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name, body in STUBS.items():
        stub = bin_dir / name
        stub.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        stub.chmod(0o755)
    log = tmp_path / "calls.log"
    log.touch()
    environment = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "STUB_LOG": str(log),
        "COVERAGE_CHECK": str(bin_dir / "coverage-check"),
        "XDG_DATA_DIRS": "/usr/share",
        **env,
    }
    result = subprocess.run(  # noqa: S603 - fixed script path, test-controlled environment
        [BASH, str(SCRIPT)], capture_output=True, text=True, env=environment, check=False, cwd=tmp_path
    )
    return result, log.read_text(encoding="utf-8")


def test_every_gate_passing_exits_zero(tmp_path: Path) -> None:
    result, _ = run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "FAIL" not in result.stdout
    assert "PASS  meson setup, install and test" in result.stdout


def test_a_failed_gate_fails_the_run_but_the_later_gates_still_run(tmp_path: Path) -> None:
    result, calls = run(tmp_path, FAKE_RUFF_CHECK_RC="1")

    assert result.returncode == 1
    assert "FAIL  ruff check ." in result.stdout
    assert "PASS  meson setup, install and test" in result.stdout
    assert "meson test" in calls


def test_a_failed_meson_test_fails_the_run(tmp_path: Path) -> None:
    result, _ = run(tmp_path, FAKE_MESON_TEST_RC="1")

    assert result.returncode == 1
    assert "FAIL  meson setup, install and test" in result.stdout


@pytest.mark.parametrize(
    ("failing_stub", "label"),
    [
        ("FAKE_RUFF_FORMAT_RC", "ruff format --check ."),
        ("FAKE_PYTEST_RC", "pytest with coverage floors"),
        ("FAKE_COVERAGE_CHECK_RC", "pytest with coverage floors"),
        ("FAKE_GAMES_SCHEMA_RC", "check-jsonschema data/v1/games.json"),
        ("FAKE_POPULARITY_SCHEMA_RC", "check-jsonschema data/v1/popularity.json"),
        ("FAKE_SHELLCHECK_RC", "shellcheck -x scripts/*.sh scripts/lib/*.sh build-aux/windows/*.sh"),
        ("FAKE_ACTIONLINT_RC", "actionlint"),
        ("FAKE_MESON_SETUP_RC", "meson setup, install and test"),
        ("FAKE_MESON_INSTALL_RC", "meson setup, install and test"),
    ],
)
def test_a_failed_gate_is_reported_under_its_own_label(tmp_path: Path, failing_stub: str, label: str) -> None:
    result, _ = run(tmp_path, **{failing_stub: "1"})

    assert result.returncode == 1
    assert [line for line in result.stdout.splitlines() if line.startswith("FAIL")] == [f"FAIL  {label}"]


def test_every_gate_runs_the_command_ci_runs_from_the_repository_root(tmp_path: Path) -> None:
    # The stubs see relative paths and the expanded globs, so a run from any other directory shows up here too.
    _, calls = run(tmp_path)

    prefix = re.search(r"--prefix=(\S+)/prefix", calls)
    assert prefix is not None, calls
    work = prefix.group(1)
    scripts = [
        str(path.relative_to(ROOT))
        for pattern in ("scripts/*.sh", "scripts/lib/*.sh", "build-aux/windows/*.sh")
        for path in sorted(ROOT.glob(pattern))
    ]
    assert [line.rstrip() for line in calls.splitlines()] == [
        "ruff check .",
        "ruff format --check .",
        f"pytest --cov --cov-report=xml:{work}/coverage.xml",
        f"coverage-check {work}/coverage.xml {ROOT}/.github/auto-qa-tuning.json",
        "check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json",
        "check-jsonschema --schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json",
        f"shellcheck -x {' '.join(scripts)}",
        "actionlint",
        f"meson setup {work}/build -Dprofile=development --prefix={work}/prefix",
        f"meson install -C {work}/build --quiet",
        f"meson test -C {work}/build --print-errorlogs",
        f"XDG_DATA_DIRS={work}/prefix/share:/usr/share",
    ]


def test_the_temporary_directory_is_removed_on_exit(tmp_path: Path) -> None:
    _, calls = run(tmp_path)

    prefix = re.search(r"--prefix=(\S+)/prefix", calls)
    assert prefix is not None, calls
    work = Path(prefix.group(1))
    assert work.parent == tmp_path
    assert not work.exists()


@pytest.mark.skipif(shutil.which("jq") is None, reason="coverage-check.sh needs jq")
def test_the_coverage_gate_defaults_to_the_repository_script(tmp_path: Path) -> None:
    # The pytest stub writes no report, so the real script's complaint shows that it, and nothing else, ran.
    result, _ = run(tmp_path, COVERAGE_CHECK="")

    assert "FAIL  pytest with coverage floors" in result.stdout
    assert "coverage.xml" in result.stdout + result.stderr
    assert "No such file or directory" not in result.stderr


def test_meson_tests_fall_back_to_the_default_data_path(tmp_path: Path) -> None:
    _, calls = run(tmp_path, XDG_DATA_DIRS="")

    prefix = re.search(r"--prefix=(\S+)", calls)
    assert prefix is not None, calls
    assert f"XDG_DATA_DIRS={prefix.group(1)}/share:/usr/local/share:/usr/share" in calls


def test_the_coverage_floors_are_checked_against_the_report_pytest_wrote(tmp_path: Path) -> None:
    _, calls = run(tmp_path)

    report = re.search(r"--cov-report=xml:(\S+)", calls)
    assert report is not None, calls
    assert f"coverage-check {report.group(1)} {ROOT}/.github/auto-qa-tuning.json" in calls


def test_meson_tests_run_against_the_installed_app(tmp_path: Path) -> None:
    # The e2e smoke test starts the installed launcher, which needs its GSettings schema from the install prefix.
    _, calls = run(tmp_path)

    prefix = re.search(r"--prefix=(\S+)", calls)
    assert prefix is not None, calls
    assert "meson install" in calls
    assert f"XDG_DATA_DIRS={prefix.group(1)}/share:/usr/share" in calls
