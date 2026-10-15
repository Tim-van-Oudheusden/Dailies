import importlib.util
from collections import Counter
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "acmm-self-check.py"


def load_script() -> ModuleType:
    # The file name has dashes, so it is loaded from its path rather than imported.
    spec = importlib.util.spec_from_file_location("acmm_self_check", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


acmm = load_script()


def create(root: Path, *patterns: str) -> None:
    for pattern in patterns:
        path = root / pattern.rstrip("/")
        if pattern.endswith("/"):
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()


def satisfy(root: Path, level: int, count: int | None = None) -> None:
    """Create the first path of the first `count` criteria of a level (all of them by default)."""
    at_level = [criterion for criterion in acmm.CRITERIA if criterion.level == level]
    for criterion in at_level[:count]:
        create(root, criterion.patterns[0])


def level_of(root: Path) -> int:
    return acmm.codebase_level(acmm.evaluate(root))


# The file layout docs/proposals/mvp-first.md section 2 plans for Dailies, one path per criterion it targets.
DAILIES_LAYOUT = (
    "pyproject.toml",
    "tests/e2e/",
    ".github/workflows/ci.yml",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/issue.yml",
    "CONTRIBUTING.md",
    ".editorconfig",
    ".github/workflows/coverage-gate.yml",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
    "AGENTS.md",
    ".cursor/rules/agent-guidance.mdc",
    "prompts/README.md",
    ".claude/skills/github-issue-flow/SKILL.md",
    ".claude/memory/corrections.tsv",
    ".github/workflows/pr-metrics.yml",
    ".github/workflows/review.yml",
    ".github/workflows/quality-report.yml",
    ".claude/settings.json",
    ".claude/session-summary.md",
    ".github/auto-qa-tuning.json",
    ".github/workflows/nightly-compliance.yml",
    ".github/workflows/auto-review.yml",
    ".github/labeler.yml",
    ".github/workflows/claude.yml",
    ".github/workflows/tier-classifier.yml",
    "docs/risk-tiers.md",
    "docs/security/SECURITY-AI.md",
    "docs/reflections/README.md",
    "docs/metrics/README.md",
    ".github/policies/risk-tiers.policy",
)


def test_the_vendored_list_has_hives_50_criteria_per_level() -> None:
    assert len(acmm.CRITERIA) == 50
    assert Counter(criterion.level for criterion in acmm.CRITERIA) == {0: 8, 2: 8, 3: 8, 4: 9, 5: 5, 6: 12}
    assert len({criterion.key for criterion in acmm.CRITERIA}) == 50
    assert all(criterion.key.startswith(f"{criterion.source}:") for criterion in acmm.CRITERIA)
    assert all(criterion.patterns for criterion in acmm.CRITERIA)


def test_the_header_records_the_hive_commit_it_was_vendored_from() -> None:
    assert "hivecommons/hive" in SCRIPT.read_text(encoding="utf-8")
    assert "3fcbd6d1b5d40fc7658202ac66cb28149f9a81c7" in SCRIPT.read_text(encoding="utf-8")


def test_an_empty_tree_has_unmet_prerequisites(tmp_path: Path) -> None:
    results = acmm.evaluate(tmp_path)
    assert [result.level for result in results] == [0, 2, 3, 4, 5, 6]
    assert not any(result.met for result in results)
    assert acmm.codebase_level(results) == 0


def test_a_directory_pattern_needs_a_directory(tmp_path: Path) -> None:
    (tmp_path / "tests").touch()
    assert not acmm.pattern_exists(tmp_path, "tests/")
    assert acmm.pattern_exists(tmp_path, "tests")


def test_a_file_pattern_matches_a_directory_too(tmp_path: Path) -> None:
    # .cursor/rules is a directory of .mdc files in the owner's repositories and passes in Hive.
    create(tmp_path, ".cursor/rules/agent-guidance.mdc")
    assert acmm.pattern_exists(tmp_path, ".cursor/rules")


def test_any_one_pattern_meets_a_criterion(tmp_path: Path) -> None:
    test_suite = next(criterion for criterion in acmm.CRITERIA if criterion.key == "acmm:prereq-test-suite")
    assert not acmm.criterion_met(tmp_path, test_suite)
    create(tmp_path, "spec/")
    assert acmm.criterion_met(tmp_path, test_suite)


def test_passing_l0_alone_gives_l1(tmp_path: Path) -> None:
    satisfy(tmp_path, 0)
    assert level_of(tmp_path) == 1


@pytest.mark.parametrize(("level", "met", "passed"), [(0, 6, True), (0, 5, False), (4, 7, True), (4, 6, False)])
def test_a_level_passes_at_70_percent(tmp_path: Path, level: int, met: int, passed: bool) -> None:
    satisfy(tmp_path, level, met)
    result = next(result for result in acmm.evaluate(tmp_path) if result.level == level)
    assert len(result.met) == met
    assert result.passed is passed


def test_levels_must_pass_consecutively(tmp_path: Path) -> None:
    for level in (0, 3, 4, 5):
        satisfy(tmp_path, level)
    assert level_of(tmp_path) == 1
    satisfy(tmp_path, 2)
    assert level_of(tmp_path) == 5


def test_higher_levels_do_not_count_without_prerequisites(tmp_path: Path) -> None:
    for level in (2, 3, 4, 5, 6):
        satisfy(tmp_path, level)
    assert level_of(tmp_path) == 0


def test_every_level_passing_gives_l6(tmp_path: Path) -> None:
    for level in (0, 2, 3, 4, 5, 6):
        satisfy(tmp_path, level)
    assert level_of(tmp_path) == 6


def test_the_planned_dailies_layout_reaches_l5(tmp_path: Path) -> None:
    create(tmp_path, *DAILIES_LAYOUT)
    results = acmm.evaluate(tmp_path)
    assert acmm.codebase_level(results) == 5
    assert all(not result.missing for result in results if result.level < 6)


def test_main_passes_at_the_minimum_level(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    create(tmp_path, *DAILIES_LAYOUT)
    assert acmm.main(["--root", str(tmp_path)]) == 0
    report = capsys.readouterr().out
    assert report.startswith("ACMM codebase level: L5 Semi-Autonomous (required: L5 Semi-Autonomous): ok")
    assert "- L5 Semi-Autonomous: 5/5 (100%) pass" in report
    # L6 fails, and its missing criteria are still listed.
    assert "- L6 Fully Autonomous: 3/12 (25%) FAIL" in report
    assert "missing `acmm:merge-queue` (Merge queue)" in report


def test_main_fails_below_the_minimum_and_lists_the_gaps(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    satisfy(tmp_path, 0, 7)
    assert acmm.main(["--root", str(tmp_path)]) == 1
    report = capsys.readouterr().out
    assert report.startswith("ACMM codebase level: L1 Inception (required: L5 Semi-Autonomous): BELOW REQUIRED LEVEL")
    assert "- L0 Prerequisites: 7/8 (88%) pass" in report
    assert "missing `acmm:prereq-coverage-gate` (Coverage gate): none of codecov.yml, .codecov.yml" in report
    assert "- L2 Advisory: 0/8 (0%) FAIL" in report


def test_min_level_is_configurable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    satisfy(tmp_path, 0)
    assert acmm.main(["--root", str(tmp_path), "--min-level", "1"]) == 0
    assert acmm.main(["--root", str(tmp_path), "--min-level", "2"]) == 1
    assert acmm.main(["--root", str(tmp_path), "--min-level", "0"]) == 0
    capsys.readouterr()


@pytest.mark.parametrize("argv", [["--min-level", "7"], ["--min-level", "x"], ["--root", "/nonexistent/acmm-root"]])
def test_bad_arguments_are_rejected(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        acmm.main(argv)
    assert exit_info.value.code == 2
    assert "error" in capsys.readouterr().err


def test_root_defaults_to_this_checkout() -> None:
    assert acmm.parse_args([]).root == ROOT
