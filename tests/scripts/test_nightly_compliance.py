import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "nightly-compliance.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("jq") is None, reason="needs bash and jq")

# Stand-ins for the tools the script calls; each reads its exit code and output from the environment.
STUBS = {
    "pip-audit": 'echo "${FAKE_AUDIT_OUTPUT:-No known vulnerabilities}"; echo "args: $*"; exit "${FAKE_AUDIT_RC:-0}"',
    "flatpak": 'echo "${FAKE_FLATPAK_OUTPUT:-Ref: runtime/org.gnome.Platform/x86_64/51}"; exit "${FAKE_FLATPAK_RC:-0}"',
}

HIGH_ALERT = {
    "state": "open",
    "html_url": "https://github.com/o/r/security/dependabot/1",
    "dependency": {"package": {"name": "requests"}},
    "security_advisory": {"ghsa_id": "GHSA-aaaa-bbbb-cccc", "severity": "high", "summary": "Bad thing"},
}


def run(tmp_path: Path, alerts: list[dict], **env: str) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name, body in STUBS.items():
        stub = bin_dir / name
        stub.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        stub.chmod(0o755)
    alerts_file = tmp_path / "alerts.json"
    alerts_file.write_text(json.dumps(alerts), encoding="utf-8")
    environment = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "GITHUB_SHA": "0123abc",
        "ALERTS_JSON": str(alerts_file),
        "ALERTS_IGNORE": "",
        "AUDIT_IGNORE": "",
        "ACMM_MIN_LEVEL": "0",
        **env,
    }
    return subprocess.run(  # noqa: S603 - fixed script, test-controlled environment
        [BASH, str(SCRIPT)], env=environment, capture_output=True, text=True, check=False, timeout=60
    )


def test_all_checks_pass(tmp_path: Path) -> None:
    result = run(tmp_path, [])
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("# Nightly compliance\n\nCommit: `0123abc`\n")
    assert "| Dependabot alerts (high+) | ✅ pass |" in result.stdout
    assert "| Script dependencies (pip-audit) | ✅ pass |" in result.stdout
    assert "| GNOME runtime supported (org.gnome.Platform//51) | ✅ pass |" in result.stdout
    assert "| ACMM codebase level (L0+) | ✅ pass |" in result.stdout
    assert "## Failures" not in result.stdout


def test_a_high_dependabot_alert_fails_unless_ignored(tmp_path: Path) -> None:
    result = run(tmp_path, [HIGH_ALERT])
    assert result.returncode == 1
    assert "| Dependabot alerts (high+) | ❌ fail |" in result.stdout
    assert "- GHSA-aaaa-bbbb-cccc (high) requests: Bad thing" in result.stdout
    # The other checks still run.
    assert "| ACMM codebase level (L0+) | ✅ pass |" in result.stdout

    assert run(tmp_path, [HIGH_ALERT], ALERTS_IGNORE="GHSA-aaaa-bbbb-cccc").returncode == 0
    moderate = {**HIGH_ALERT, "security_advisory": {**HIGH_ALERT["security_advisory"], "severity": "moderate"}}
    assert run(tmp_path, [moderate]).returncode == 0


def test_unreadable_alerts_fail(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{}", encoding="utf-8")
    result = run(tmp_path, [], ALERTS_JSON=str(tmp_path / "broken.json"))
    assert result.returncode == 1
    assert "| Dependabot alerts (high+) | ❌ fail |" in result.stdout


def test_pip_audit_findings_fail_and_ignores_are_passed_on(tmp_path: Path) -> None:
    result = run(tmp_path, [], FAKE_AUDIT_RC="1", FAKE_AUDIT_OUTPUT="requests 2.0 PYSEC-2099-1")
    assert result.returncode == 1
    assert "| Script dependencies (pip-audit) | ❌ fail |" in result.stdout
    assert "requests 2.0 PYSEC-2099-1" in result.stdout
    assert "-r scripts/requirements.txt" in result.stdout

    ignored = run(tmp_path, [], FAKE_AUDIT_RC="1", AUDIT_IGNORE="PYSEC-2099-1 GHSA-x")
    assert "--ignore-vuln PYSEC-2099-1 --ignore-vuln GHSA-x" in ignored.stdout


def test_an_end_of_life_runtime_fails(tmp_path: Path) -> None:
    eol = "Ref: runtime/org.gnome.Platform/x86_64/48\nEnd-of-life: The GNOME 48 runtime is no longer supported"
    result = run(tmp_path, [], FAKE_FLATPAK_OUTPUT=eol, RUNTIME_REF="org.gnome.Platform//48")
    assert result.returncode == 1
    assert "| GNOME runtime supported (org.gnome.Platform//48) | ❌ fail |" in result.stdout
    assert "End-of-life: The GNOME 48 runtime is no longer supported" in result.stdout


def test_an_unreachable_remote_fails(tmp_path: Path) -> None:
    result = run(tmp_path, [], FAKE_FLATPAK_RC="1", FAKE_FLATPAK_OUTPUT='error: Remote "flathub" not found')
    assert result.returncode == 1
    assert "| GNOME runtime supported (org.gnome.Platform//51) | ❌ fail |" in result.stdout


def test_an_acmm_level_below_the_minimum_fails_with_the_gaps(tmp_path: Path) -> None:
    # No checkout reaches L6 (Hive's own guidance is not to chase it), so this row fails.
    result = run(tmp_path, [], ACMM_MIN_LEVEL="6")
    assert result.returncode == 1
    assert "| ACMM codebase level (L6+) | ❌ fail |" in result.stdout
    assert "### ACMM self-check" in result.stdout
    assert "missing `acmm:merge-queue` (Merge queue)" in result.stdout
