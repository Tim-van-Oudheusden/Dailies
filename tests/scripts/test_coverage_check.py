import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("bash", "jq", "python3")), reason="needs bash, jq and python3"
)
def test_coverage_check_shell_suite_passes() -> None:
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(  # noqa: S603 - fixed command, no user input
        [bash, str(ROOT / "scripts" / "coverage-check.test.sh")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_tuning_config_has_line_and_branch_floors_per_group() -> None:
    # auto-qa-tuner.sh ratchets the numbers; the shape and the groups stay fixed.
    config = json.loads((ROOT / ".github" / "auto-qa-tuning.json").read_text(encoding="utf-8"))
    assert config["margin"] >= 0
    assert set(config["floors"]) == {"core", "scripts"}
    for floors in config["floors"].values():
        assert set(floors) == {"lines", "branches"}
        assert all(0 <= floor <= 100 for floor in floors.values())
