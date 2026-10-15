import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "auto-qa-tuner.sh"
REPO_CONFIG = ROOT / ".github" / "auto-qa-tuning.json"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("jq") is None, reason="needs bash and jq")

DEFAULT_FLOORS = {"core": {"lines": 70, "branches": 50}, "scripts": {"lines": 70, "branches": 50}}


def tune(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed script, test-controlled arguments
        [BASH, str(SCRIPT), *args], capture_output=True, text=True, check=False, timeout=60
    )


def write_report(tmp_path: Path, rows: dict[str, tuple[str, str]]) -> Path:
    """Write a quality report in the format of scripts/quality-report.sh with the given coverage cells."""
    lines = [
        "# Quality report",
        "",
        "Commit: `0123abc`",
        "",
        "## Quality gates",
        "",
        "| Gate | Result |",
        "| ---- | ------ |",
        "| `pytest` | ✅ pass |",
        "",
        "## Unit-test coverage",
        "",
        "| Module | Lines | Branches |",
        "| ------ | ----- | -------- |",
        *(f"| {module} | {lines} | {branches} |" for module, (lines, branches) in rows.items()),
    ]
    report = tmp_path / "quality-report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def write_config(tmp_path: Path, floors: dict | None = None, margin: float = 2, **extra: object) -> Path:
    config = tmp_path / "auto-qa-tuning.json"
    content = {"margin": margin, "floors": DEFAULT_FLOORS if floors is None else floors, **extra}
    config.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    return config


def number(value: float) -> str:
    """Render a number the way jq prints it in the tuning table."""
    return str(int(value)) if float(value).is_integer() else str(value)


def test_coverage_at_floor_plus_margin_proposes_no_change(tmp_path: Path) -> None:
    # Dry run against the repository's own floors file (#28): observed coverage of exactly floor + margin keeps every
    # floor and leaves the file untouched.
    before = REPO_CONFIG.read_bytes()
    config = json.loads(before)
    margin = config["margin"]
    observed = {
        module: (f"{floors['lines'] + margin:.2f}%", f"{floors['branches'] + margin:.2f}%")
        for module, floors in config["floors"].items()
    }
    result = tune("--report", str(write_report(tmp_path, observed)))

    assert result.returncode == 0, result.stderr
    assert "⬆️" not in result.stdout
    assert f"Margin: {number(margin)} percentage points below observed coverage." in result.stdout
    for module, floors in config["floors"].items():
        for metric in ("lines", "branches"):
            floor = number(floors[metric])
            seen = f"{floors[metric] + margin:.2f}"
            assert f"| {module} | {metric} | {floor}% | {seen}% | {floor}% |" in result.stdout
    assert REPO_CONFIG.read_bytes() == before


def test_write_at_floor_plus_margin_keeps_the_floors(tmp_path: Path) -> None:
    config = write_config(tmp_path)
    report = write_report(tmp_path, {"core": ("72.00%", "52.00%"), "scripts": ("72.00%", "52.00%")})

    result = tune("--report", str(report), "--config", str(config), "--write")

    assert result.returncode == 0, result.stderr
    assert json.loads(config.read_text(encoding="utf-8")) == {"margin": 2, "floors": DEFAULT_FLOORS}


def test_raises_floors_to_observed_minus_margin_rounded_down(tmp_path: Path) -> None:
    config = write_config(tmp_path)
    report = write_report(tmp_path, {"core": ("85.67%", "61.99%"), "scripts": ("72.99%", "100.00%")})

    result = tune("--report", str(report), "--config", str(config))

    assert result.returncode == 0, result.stderr
    assert "| core | lines | 70% | 85.67% | 83% ⬆️ |" in result.stdout
    assert "| core | branches | 50% | 61.99% | 59% ⬆️ |" in result.stdout
    assert "| scripts | lines | 70% | 72.99% | 70% |" in result.stdout
    assert "| scripts | branches | 50% | 100.00% | 98% ⬆️ |" in result.stdout
    # Without --write the config is only read.
    assert json.loads(config.read_text(encoding="utf-8"))["floors"] == DEFAULT_FLOORS


def test_never_lowers_a_floor(tmp_path: Path) -> None:
    config = write_config(tmp_path, {"core": {"lines": 90, "branches": 79.99}})
    report = write_report(tmp_path, {"core": ("40.00%", "80.50%")})

    result = tune("--report", str(report), "--config", str(config), "--write")

    assert result.returncode == 0, result.stderr
    assert "| core | lines | 90% | 40.00% | 90% |" in result.stdout
    # A fractional floor is kept, not rounded down along with the proposal (78).
    assert "| core | branches | 79.99% | 80.50% | 79.99% |" in result.stdout
    assert json.loads(config.read_text(encoding="utf-8"))["floors"] == {"core": {"lines": 90, "branches": 79.99}}


def test_float_error_does_not_drop_a_proposal_below_a_whole_percent(tmp_path: Path) -> None:
    config = write_config(tmp_path, {"core": {"lines": 0, "branches": 0}}, margin=0.1)
    report = write_report(tmp_path, {"core": ("70.10%", "70.10%")})

    result = tune("--report", str(report), "--config", str(config))

    assert result.returncode == 0, result.stderr
    assert "| core | lines | 0% | 70.10% | 70% ⬆️ |" in result.stdout


def test_metrics_without_a_percentage_keep_their_floors(tmp_path: Path) -> None:
    floors = {
        "core": {"lines": 70, "branches": 50},
        "scripts": {"lines": 70, "branches": 50},
        "data": {"lines": 60, "branches": 40},
    }
    config = write_config(tmp_path, floors)
    # A failed run, a module with no code yet, and one with lines but no branches; "data" has no row at all.
    report = write_report(tmp_path, {"core": ("❌ n/a", "❌ n/a"), "scripts": ("95.00%", "no branches")})

    result = tune("--report", str(report), "--config", str(config), "--write")

    assert result.returncode == 0, result.stderr
    assert "| core | lines | 70% | n/a | 70% |" in result.stdout
    assert "| core | branches | 50% | n/a | 50% |" in result.stdout
    assert "| scripts | lines | 70% | 95.00% | 93% ⬆️ |" in result.stdout
    assert "| scripts | branches | 50% | n/a | 50% |" in result.stdout
    assert "| data | lines | 60% | n/a | 60% |" in result.stdout
    assert json.loads(config.read_text(encoding="utf-8"))["floors"] == {
        **floors,
        "scripts": {"lines": 93, "branches": 50},
    }


def test_no_code_yet_keeps_the_floors(tmp_path: Path) -> None:
    config = write_config(tmp_path)
    report = write_report(tmp_path, {"core": ("no code yet", "no code yet"), "scripts": ("80.00%", "70.00%")})

    result = tune("--report", str(report), "--config", str(config))

    assert result.returncode == 0, result.stderr
    assert "| core | lines | 70% | n/a | 70% |" in result.stdout
    assert "| scripts | branches | 50% | 70.00% | 68% ⬆️ |" in result.stdout


def test_write_keeps_every_other_key(tmp_path: Path) -> None:
    config = write_config(tmp_path, comment="ratcheted by scripts/auto-qa-tuner.sh")
    report = write_report(tmp_path, {"core": ("80.00%", "75.00%"), "scripts": ("75.00%", "50.00%")})

    result = tune("--report", str(report), "--config", str(config), "--write")

    assert result.returncode == 0, result.stderr
    assert f"Wrote the proposed floors to {config}" in result.stderr
    assert json.loads(config.read_text(encoding="utf-8")) == {
        "margin": 2,
        "floors": {"core": {"lines": 78, "branches": 73}, "scripts": {"lines": 73, "branches": 50}},
        "comment": "ratcheted by scripts/auto-qa-tuner.sh",
    }


def test_missing_report_fails_and_leaves_the_config(tmp_path: Path) -> None:
    config = write_config(tmp_path)
    before = config.read_bytes()

    result = tune("--report", str(tmp_path / "missing.md"), "--config", str(config), "--write")

    assert result.returncode == 2
    assert "No quality report at" in result.stderr
    assert config.read_bytes() == before


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("margin: 2", id="not JSON"),
        pytest.param('{"floors": {"core": {"lines": 70, "branches": 50}}}', id="no margin"),
        pytest.param('{"margin": -1, "floors": {"core": {"lines": 70, "branches": 50}}}', id="negative margin"),
        pytest.param('{"margin": 2, "floors": {"core": {"lines": 120, "branches": 50}}}', id="floor above 100"),
        pytest.param('{"margin": 2, "floors": {"core": {"lines": 70, "branches": -1}}}', id="floor below 0"),
        pytest.param('{"margin": 2, "floors": {}}', id="no modules"),
        pytest.param('{"margin": 2, "floors": {"core": {"functions": 70, "lines": 70}}}', id="functions contract"),
    ],
)
def test_malformed_config_fails_and_is_left_untouched(tmp_path: Path, content: str) -> None:
    config = tmp_path / "auto-qa-tuning.json"
    config.write_text(content, encoding="utf-8")
    report = write_report(tmp_path, {"core": ("90.00%", "90.00%")})

    result = tune("--report", str(report), "--config", str(config), "--write")

    assert result.returncode == 2
    assert "Malformed" in result.stderr
    assert config.read_text(encoding="utf-8") == content


@pytest.mark.parametrize("args", [["--report"], ["--config"], ["--bogus"]])
def test_bad_arguments_fail(args: list[str]) -> None:
    result = tune(*args)

    assert result.returncode == 2
    assert "usage: auto-qa-tuner.sh" in result.stderr
