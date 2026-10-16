import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_pr_review_check_shell_suite_passes() -> None:
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(  # noqa: S603 - fixed command, no user input
        [bash, str(ROOT / "scripts" / "pr-review-check.test.sh")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
