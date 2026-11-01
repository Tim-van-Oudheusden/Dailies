"""`.github/CODEOWNERS` makes the maintainer the owner of exactly the paths `.github/risk-assessment.yml` rates high.

The two files use different glob dialects (`*` crosses `/` in the risk rules, not in CODEOWNERS), so the tests compare
what each selects among the tracked files rather than the patterns themselves.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
GIT = shutil.which("git")
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(GIT is None or BASH is None, reason="needs git and bash")


def rules() -> list[str]:
    """The pattern lines of CODEOWNERS: no blank lines, no comments."""
    lines = (line.strip() for line in CODEOWNERS.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def git(*args: str, stdin: bytes | None = None) -> bytes:
    assert GIT is not None
    result = subprocess.run(  # noqa: S603 - fixed git command, no user input
        [GIT, *args], cwd=ROOT, input=stdin, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr.decode()
    return result.stdout


def nul_separated(data: bytes) -> list[str]:
    return sorted(path.decode() for path in data.split(b"\0") if path)


def owned_files(tmp_path: Path) -> list[str]:
    """Tracked files a CODEOWNERS pattern owns. Its patterns follow .gitignore syntax, so git itself applies them."""
    patterns = tmp_path / "patterns"
    patterns.write_text("".join(f"{rule.split()[0]}\n" for rule in rules()), encoding="utf-8")
    return nul_separated(git("ls-files", "-z", "--cached", "--ignored", f"--exclude-from={patterns}"))


def high_risk_files() -> list[str]:
    """Tracked files scripts/tier-classify.sh rates high."""
    assert BASH is not None
    result = subprocess.run(  # noqa: S603 - fixed script, no user input
        [BASH, str(ROOT / "scripts" / "tier-classify.sh"), "-z"],
        input=git("ls-files", "-z"),
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    return sorted(
        line.removeprefix("high").strip() for line in result.stdout.decode().splitlines() if line.startswith("high ")
    )


def test_codeowners_owns_exactly_the_tracked_files_rated_high(tmp_path: Path) -> None:
    owned = owned_files(tmp_path)
    high = high_risk_files()

    assert high, "no tracked file is rated high"
    assert sorted(set(high) - set(owned)) == [], "high risk but unowned"
    assert sorted(set(owned) - set(high)) == [], "owned but not high risk"


def test_codeowners_gives_every_pattern_an_owner() -> None:
    assert rules(), "no rules"
    for rule in rules():
        assert re.fullmatch(r"\S+(\s+@[\w-]+(/[\w-]+)?)+", rule), rule
