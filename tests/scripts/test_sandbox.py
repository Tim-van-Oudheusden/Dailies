import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "sandbox.sh"
BASH = shutil.which("bash")
IMAGE = "localhost/dailies-sandbox"

pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash")

# Stands in for podman: one log line per call, `podman build` exits $FAKE_BUILD_RC.
PODMAN_STUB = """#!/bin/sh
echo "podman $*" >>"$STUB_LOG"
[ "$1" = build ] && exit "${FAKE_BUILD_RC:-0}"
exit 0
"""


def run(tmp_path: Path, *args: str, **env: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    podman = bin_dir / "podman"
    podman.write_text(PODMAN_STUB, encoding="utf-8")
    podman.chmod(0o755)
    log = tmp_path / "calls.log"
    log.touch()
    environment = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "STUB_LOG": str(log),
        **env,
    }
    # From a subdirectory: the script mounts the checkout root wherever it is started.
    result = subprocess.run(  # noqa: S603 - fixed script path, test-controlled environment
        [BASH, str(SCRIPT), *args], capture_output=True, text=True, env=environment, check=False, cwd=ROOT / "tests"
    )
    return result, log.read_text(encoding="utf-8").splitlines()


def test_without_arguments_it_builds_the_image_then_runs_the_gates_on_the_checkout(tmp_path: Path) -> None:
    result, calls = run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert len(calls) == 2, calls
    assert calls[0].startswith("podman build ")
    assert f"--file {ROOT}/Dockerfile.sandbox" in calls[0]
    assert f"--tag {IMAGE}" in calls[0]
    assert calls[1].startswith("podman run ")
    assert f"-v {ROOT}:/workspace:z" in calls[1]
    assert calls[1].endswith(f"{IMAGE} scripts/sandbox-gates.sh")


def test_arguments_are_the_command_run_in_the_sandbox(tmp_path: Path) -> None:
    result, calls = run(tmp_path, "pytest", "tests/core", "-k", "search")

    assert result.returncode == 0, result.stderr
    assert calls[-1].endswith(f"{IMAGE} pytest tests/core -k search")


def test_a_failed_image_build_stops_before_anything_runs(tmp_path: Path) -> None:
    result, calls = run(tmp_path, FAKE_BUILD_RC="125")

    assert result.returncode == 125
    assert not [call for call in calls if call.startswith("podman run")]
