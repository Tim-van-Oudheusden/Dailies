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
    # The ISO weekday (`date -u +%u`); a Wednesday unless a test picks another day.
    "date": 'echo "${FAKE_WEEKDAY:-3}"',
}

# Stands in for scripts/check_links.py: records its arguments, writes FAKE_LINKS_REPORT to --out.
CHECK_LINKS_STUB = """
import os
import sys
from pathlib import Path

args = sys.argv[1:]
Path(os.environ["LINKS_ARGS"]).write_text(" ".join(args), encoding="utf-8")
Path(args[args.index("--out") + 1]).write_text(os.environ.get("FAKE_LINKS_REPORT", "All passed."), encoding="utf-8")
print("check_links: moviedle: redirected-cross-domain", file=sys.stderr)
sys.exit(int(os.environ.get("FAKE_LINKS_RC", "0")))
"""

# Stands in for scripts/check_checker_digest.py: prints FAKE_DIGEST_OUTPUT, exits FAKE_DIGEST_RC.
CHECKER_DIGEST_STUB = """
import os
import sys

print(os.environ.get("FAKE_DIGEST_OUTPUT", "flathub/flatpak-external-data-checker pin is up to date: sha256:aa"))
sys.exit(int(os.environ.get("FAKE_DIGEST_RC", "0")))
"""

HIGH_ALERT = {
    "state": "open",
    "html_url": "https://github.com/o/r/security/dependabot/1",
    "dependency": {"package": {"name": "requests"}},
    "security_advisory": {"ghsa_id": "GHSA-aaaa-bbbb-cccc", "severity": "high", "summary": "Bad thing"},
}


def run(tmp_path: Path, alerts: list[dict], *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name, body in STUBS.items():
        stub = bin_dir / name
        stub.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        stub.chmod(0o755)
    check_links = tmp_path / "check_links.py"
    check_links.write_text(CHECK_LINKS_STUB, encoding="utf-8")
    checker_digest = tmp_path / "check_checker_digest.py"
    checker_digest.write_text(CHECKER_DIGEST_STUB, encoding="utf-8")
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
        "CHECK_LINKS": str(check_links),
        "CHECKER_DIGEST": str(checker_digest),
        "LINKS_ARGS": str(tmp_path / "links-args.txt"),
        **env,
    }
    return subprocess.run(  # noqa: S603 - fixed script, test-controlled environment
        [BASH, str(SCRIPT), *args], env=environment, capture_output=True, text=True, check=False, timeout=60
    )


def links_args(tmp_path: Path) -> str | None:
    path = tmp_path / "links-args.txt"
    return path.read_text(encoding="utf-8") if path.exists() else None


def test_all_checks_pass(tmp_path: Path) -> None:
    result = run(tmp_path, [])
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("# Nightly compliance\n\nCommit: `0123abc`\n")
    assert "| Dependabot alerts (high+) | ✅ pass |" in result.stdout
    assert "| Script dependencies (pip-audit) | ✅ pass |" in result.stdout
    assert "| GNOME runtime supported (org.gnome.Platform//51) | ✅ pass |" in result.stdout
    assert "| ACMM codebase level (L0+) | ✅ pass |" in result.stdout
    assert "| External data checker image is :latest | ✅ pass |" in result.stdout
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


def test_a_drifted_checker_image_digest_fails_with_both_digests(tmp_path: Path) -> None:
    drift = "flathub/flatpak-external-data-checker:latest moved on.\npinned: sha256:aa\nlatest: sha256:bb"
    result = run(tmp_path, [], FAKE_DIGEST_RC="1", FAKE_DIGEST_OUTPUT=drift)
    assert result.returncode == 1
    assert "| External data checker image is :latest | ❌ fail |" in result.stdout
    assert "latest: sha256:bb" in result.stdout


def test_an_unreachable_registry_fails_the_checker_image_row(tmp_path: Path) -> None:
    result = run(tmp_path, [], FAKE_DIGEST_RC="2", FAKE_DIGEST_OUTPUT="could not read ghcr.io: timed out")
    assert result.returncode == 1
    assert "| External data checker image is :latest | ❌ fail |" in result.stdout
    assert "could not read ghcr.io: timed out" in result.stdout


def test_an_acmm_level_below_the_minimum_fails_with_the_gaps(tmp_path: Path) -> None:
    # No checkout reaches L6 (Hive's own guidance is not to chase it), so this row fails.
    result = run(tmp_path, [], ACMM_MIN_LEVEL="6")
    assert result.returncode == 1
    assert "| ACMM codebase level (L6+) | ❌ fail |" in result.stdout
    assert "### ACMM self-check" in result.stdout
    assert "missing `acmm:merge-queue` (Merge queue)" in result.stdout


def test_links_are_not_checked_on_weekdays(tmp_path: Path) -> None:
    result = run(tmp_path, [], FAKE_WEEKDAY="6")

    assert result.returncode == 0, result.stderr
    assert "Catalog links" not in result.stdout
    assert links_args(tmp_path) is None


def test_links_are_checked_on_sundays(tmp_path: Path) -> None:
    result = run(tmp_path, [], FAKE_WEEKDAY="7")

    assert result.returncode == 0, result.stderr
    assert "| Catalog links (weekly) | ✅ pass |" in result.stdout
    args = links_args(tmp_path)
    assert args is not None
    assert args.startswith("--catalog data/v1/games.json --out ")
    assert "--open-issue" not in args


@pytest.mark.parametrize(("args", "env"), [(["--force-links"], {}), ([], {"DAILIES_FORCE_LINKS": "1"})])
def test_links_check_can_be_forced_on_any_day(tmp_path: Path, args: list[str], env: dict[str, str]) -> None:
    result = run(tmp_path, [], *args, **env)

    assert result.returncode == 0, result.stderr
    assert "| Catalog links (weekly) | ✅ pass |" in result.stdout


def test_force_flag_0_does_not_force(tmp_path: Path) -> None:
    result = run(tmp_path, [], DAILIES_FORCE_LINKS="0")

    assert "Catalog links" not in result.stdout


def test_broken_links_fail_with_the_report_and_open_the_issue_in_actions(tmp_path: Path) -> None:
    report = "### Link check: 1 broken links\n\n| `moviedle` | ❌ redirected-cross-domain |"

    result = run(tmp_path, [], FAKE_WEEKDAY="7", FAKE_LINKS_RC="1", FAKE_LINKS_REPORT=report, GITHUB_ACTIONS="true")

    assert result.returncode == 1
    assert "| Catalog links (weekly) | ❌ fail |" in result.stdout
    assert "## Failures" in result.stdout
    assert report in result.stdout
    assert "moviedle: redirected-cross-domain" in result.stderr
    assert (links_args(tmp_path) or "").endswith(" --open-issue")


def test_a_links_check_error_fails_with_its_log(tmp_path: Path) -> None:
    result = run(tmp_path, [], "--force-links", FAKE_LINKS_RC="2", FAKE_LINKS_REPORT="")

    assert result.returncode == 1
    assert "| Catalog links (weekly) | ❌ fail |" in result.stdout
    assert "check_links: moviedle" in result.stdout


def test_an_unknown_argument_is_a_usage_error(tmp_path: Path) -> None:
    result = run(tmp_path, [], "--nope")

    assert result.returncode == 2
    assert "usage" in result.stderr
