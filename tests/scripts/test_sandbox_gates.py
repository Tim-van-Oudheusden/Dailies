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
    "ruff": 'echo "ruff $*" >>"$STUB_LOG"; [ "$1" = check ] && exit "${FAKE_RUFF_CHECK_RC:-0}"; exit 0',
    "pytest": 'echo "pytest $*" >>"$STUB_LOG"; exit "${FAKE_PYTEST_RC:-0}"',
    "check-jsonschema": 'echo "check-jsonschema $*" >>"$STUB_LOG"',
    "shellcheck": 'echo "shellcheck $*" >>"$STUB_LOG"',
    "actionlint": 'echo "actionlint $*" >>"$STUB_LOG"',
    "meson": """echo "meson $*" >>"$STUB_LOG"
if [ "$1" = test ]; then
  echo "XDG_DATA_DIRS=$XDG_DATA_DIRS" >>"$STUB_LOG"
  exit "${FAKE_MESON_TEST_RC:-0}"
fi
""",
    "coverage-check": 'echo "coverage-check $*" >>"$STUB_LOG"',
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
