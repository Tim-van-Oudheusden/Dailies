import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / ".github" / "policies" / "risk-tiers.policy"
DOC = ROOT / "docs" / "risk-tiers.md"


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_tier_classify_shell_suite_passes() -> None:
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(  # noqa: S603 - fixed command, no user input
        [bash, str(ROOT / "scripts" / "tier-classify.test.sh")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def policy_rules() -> list[tuple[str, str]]:
    rules = []
    for line in POLICY.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            tier, glob = line.split()
            rules.append((tier, glob))
    return rules


def doc_sections() -> dict[str, str]:
    """The text under each `## Tier: <name>` heading of docs/risk-tiers.md."""
    _, *parts = re.split(r"^## Tier: (\w+)$", DOC.read_text(encoding="utf-8"), flags=re.MULTILINE)
    tiers, bodies = parts[0::2], parts[1::2]
    return {tier: re.split(r"^## ", body, flags=re.MULTILINE)[0] for tier, body in zip(tiers, bodies, strict=True)}


def test_risk_tiers_doc_lists_every_policy_rule_under_its_tier() -> None:
    sections = doc_sections()
    assert set(sections) == {"high", "medium", "low"}
    for tier, glob in policy_rules():
        # The doc writes a directory rule `dir/*` as `dir/**`, the glob syntax readers know from .gitignore.
        shown = glob[:-1] + "**" if glob.endswith("/*") else glob
        assert f"`{shown}`" in sections[tier], f"docs/risk-tiers.md lists no `{shown}` under 'Tier: {tier}'"
