"""Tests for scripts/mutants_report.py (#368). `mutmut` is not installed in CI: a fake one on PATH plays its part.

The fake prints what the real command prints: `mutmut results --all true` (mutmut/__main__.py, `results`) and the
unified diff of `mutmut show` (mutmut/mutation/diff_apply.py, `get_diff_for_mutant`), as of mutmut 3.8.1.
"""

import importlib.util
import json
import os
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mutants_report.py"

FAKE_MUTMUT = """#!/bin/sh
echo "mutmut $*" >>"$STUB_LOG"
case "$1" in
  run)
    echo "mutmut run output"
    mkdir -p mutants
    [ -z "${FAKE_RUN_SIGNAL:-}" ] || kill -s "$FAKE_RUN_SIGNAL" $$
    exit "${FAKE_RUN_RC:-0}"
    ;;
  results)
    cat "$FAKE_RESULTS"
    exit "${FAKE_RESULTS_RC:-0}"
    ;;
  show)
    exec cat "$FAKE_SHOWN/$2"
    ;;
esac
exit 64
"""

MUTANT = "dailies.core.search.x__tier__mutmut_12"
KEY = "dailies.core.search.x__tier: - return a < b | + return a <= b"
OTHER = "dailies.core.web.x_title__mutmut_3"
OTHER_KEY = "dailies.core.web.x_title: - return name | + return None"
# mutmut's class separator, in a method's name. An escape, because ruff reads the letter as an ambiguous character.
SEPARATOR = "ǁ"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mutants_report", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mr = load_script()


def shown(removed: str = "return a < b", added: str = "return a <= b", *, line: int = 1) -> str:
    """What `mutmut show` prints for a mutant that replaces one line of a function."""
    lines = [
        "# a mutant: survived",
        "--- dailies/core/search.py",
        "+++ dailies/core/search.py",
        f"@@ -{line},3 +{line},3 @@",
        " def _tier(a, b):",
        f"-    {removed}",
        f"+    {added}",
        "     return None",
    ]
    return "\n".join(lines) + "\n"


class Run(NamedTuple):
    status: int
    stdout: str
    stderr: str


@dataclass
class Checkout:
    """A tree for the script to run in, what the fake `mutmut` answers in it, and the output it left."""

    root: Path
    baseline: Path
    calls: Path
    results: Path
    answers: Path
    capfd: pytest.CaptureFixture[str]

    def add(self, name: str, status: str, diff: str = "") -> None:
        with self.results.open("a", encoding="utf-8") as results:
            results.write(f"    {name}: {status}\n")
        if diff:
            (self.answers / name).write_text(diff, encoding="utf-8")

    def review(self, *keys: str) -> None:
        self.baseline.write_text(json.dumps({"survivors": list(keys)}), encoding="utf-8")

    def run(self, *args: str) -> Run:
        status = mr.main(["--root", str(self.root), *args])
        captured = self.capfd.readouterr()
        return Run(status, captured.out, captured.err)

    def called(self) -> list[str]:
        return self.calls.read_text(encoding="utf-8").splitlines() if self.calls.exists() else []


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]) -> Checkout:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "mutmut"
    fake.write_text(FAKE_MUTMUT, encoding="utf-8")
    fake.chmod(0o755)
    root = tmp_path / "root"
    (root / ".github").mkdir(parents=True)
    answers = tmp_path / "answers"
    answers.mkdir()
    results = tmp_path / "results.txt"
    results.touch()
    calls = tmp_path / "calls.log"
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("STUB_LOG", str(calls))
    monkeypatch.setenv("FAKE_RESULTS", str(results))
    monkeypatch.setenv("FAKE_SHOWN", str(answers))
    monkeypatch.setenv("GITHUB_SHA", "0123abc")
    tree = Checkout(root, root / ".github" / "mutants-baseline.json", calls, results, answers, capfd)
    tree.review()
    return tree


def test_reports_the_totals_and_a_new_survivor_and_fails(checkout: Checkout) -> None:
    checkout.add(MUTANT, "survived", shown())
    checkout.add("dailies.core.search.x__tier__mutmut_13", "killed")
    checkout.add("dailies.core.search.x__tier__mutmut_14", "killed")
    checkout.add("dailies.core.search.x__tier__mutmut_15", "timeout")

    result = checkout.run()

    assert result.status == 1
    expected = [
        "# Mutants report",
        "",
        "Commit: `0123abc`",
        "",
        "## Totals",
        "",
        "| Status | Mutants |",
        "| ------ | ------- |",
        "| killed | 2 |",
        "| survived | 1 |",
        "| timeout | 1 |",
        "| all | 4 |",
        "",
        "Known survivors, in the baseline: 0",
        "",
        "## New survivors: 1",
        "",
        "```text",
        KEY,
        "```",
        "",
        "## Baseline entries now killed or gone: 0",
        "",
        "None.",
        "",
    ]
    assert result.stdout == "\n".join(expected)
    assert checkout.called() == ["mutmut run", "mutmut results --all true", f"mutmut show {MUTANT}"]


def test_mutmut_progress_goes_to_stderr_so_stdout_stays_a_clean_report(checkout: Checkout) -> None:
    checkout.add(MUTANT, "killed")

    result = checkout.run()

    assert "mutmut run output" in result.stderr
    assert "mutmut run output" not in result.stdout


def test_new_survivors_are_listed_in_order(checkout: Checkout) -> None:
    checkout.add(OTHER, "survived", shown("return name", "return None"))
    checkout.add(MUTANT, "survived", shown())

    result = checkout.run()

    assert f"## New survivors: 2\n\n```text\n{KEY}\n{OTHER_KEY}\n```\n" in result.stdout


def test_a_known_survivor_is_counted_and_passes(checkout: Checkout) -> None:
    checkout.review(KEY)
    checkout.add(MUTANT, "survived", shown())

    result = checkout.run()

    assert result.status == 0
    assert "Known survivors, in the baseline: 1\n" in result.stdout
    assert "## New survivors: 0\n\nNone.\n" in result.stdout
    assert "## Baseline entries now killed or gone: 0\n\nNone.\n" in result.stdout


def test_a_known_survivor_stays_known_when_its_ordinal_and_line_shift(checkout: Checkout) -> None:
    # An edit elsewhere in the function renumbers its mutants and moves the line; the baseline must not notice.
    checkout.review(KEY)
    checkout.add("dailies.core.search.x__tier__mutmut_40", "survived", shown(line=90))

    result = checkout.run()

    assert result.status == 0
    assert "Known survivors, in the baseline: 1\n" in result.stdout


def test_a_known_survivor_stays_known_when_its_line_is_reindented(checkout: Checkout) -> None:
    checkout.review(KEY)
    checkout.add(MUTANT, "survived", shown("    return a < b", "    return a <= b"))

    assert checkout.run().status == 0


def test_the_same_function_with_another_changed_line_is_a_new_survivor(checkout: Checkout) -> None:
    checkout.review(KEY)
    checkout.add(MUTANT, "survived", shown("return a > b", "return a >= b"))

    result = checkout.run()

    assert result.status == 1
    assert "dailies.core.search.x__tier: - return a > b | + return a >= b" in result.stdout
    assert f"## Baseline entries now killed or gone: 1\n\n```text\n{KEY}\n```\n" in result.stdout


def test_a_mutant_of_a_line_starting_with_dashes_keeps_its_changes(checkout: Checkout) -> None:
    # A line of the hunk can look like the `---` and `+++` headers, which are skipped by position, not by their text.
    checkout.add(MUTANT, "survived", f"# {MUTANT}: survived\n--- a\n+++ a\n@@ -1 +1 @@\n--- x\n+++ x\n")

    assert "dailies.core.search.x__tier: - -- x | + ++ x" in checkout.run().stdout


def test_two_known_survivors_with_the_same_key_are_both_counted(checkout: Checkout) -> None:
    checkout.review(KEY, KEY)
    checkout.add(MUTANT, "survived", shown())
    checkout.add("dailies.core.search.x__tier__mutmut_30", "survived", shown())

    result = checkout.run()

    assert result.status == 0
    assert "Known survivors, in the baseline: 2\n" in result.stdout


def test_a_baseline_entry_now_killed_is_listed_and_passes(checkout: Checkout) -> None:
    checkout.review(KEY)
    checkout.add(MUTANT, "killed")

    result = checkout.run()

    assert result.status == 0
    assert f"## Baseline entries now killed or gone: 1\n\n```text\n{KEY}\n```\n" in result.stdout
    assert "Known survivors, in the baseline: 0\n" in result.stdout


def test_entries_now_gone_are_listed_in_order_as_often_as_the_baseline_holds_them(checkout: Checkout) -> None:
    checkout.review(OTHER_KEY, KEY, KEY)
    checkout.add(MUTANT, "killed")

    result = checkout.run()

    assert f"## Baseline entries now killed or gone: 3\n\n```text\n{KEY}\n{KEY}\n{OTHER_KEY}\n```\n" in result.stdout


def test_a_mutant_no_test_reaches_counts_as_a_survivor(checkout: Checkout) -> None:
    checkout.add(MUTANT, "no tests", shown())

    result = checkout.run()

    assert result.status == 1
    assert f"```text\n{KEY}\n```" in result.stdout
    assert "| no tests | 1 |" in result.stdout


@pytest.mark.parametrize(
    "status", ["killed", "timeout", "suspicious", "segfault", "skipped", "check was interrupted by user"]
)
def test_other_statuses_are_counted_but_are_not_survivors(checkout: Checkout, status: str) -> None:
    checkout.add(MUTANT, status)

    result = checkout.run()

    assert result.status == 0
    assert f"| {status} | 1 |" in result.stdout
    assert checkout.called() == ["mutmut run", "mutmut results --all true"]


def test_two_mutants_with_the_same_key_need_two_baseline_entries(checkout: Checkout) -> None:
    checkout.review(KEY)
    checkout.add(MUTANT, "survived", shown())
    checkout.add("dailies.core.search.x__tier__mutmut_30", "survived", shown())

    result = checkout.run()

    assert result.status == 1
    assert "Known survivors, in the baseline: 1\n" in result.stdout
    assert f"## New survivors: 1\n\n```text\n{KEY}\n```\n" in result.stdout


def test_a_method_keeps_its_class_in_the_key_and_in_the_written_baseline(checkout: Checkout) -> None:
    function = f"dailies.core.cache.x{SEPARATOR}CacheDir{SEPARATOR}read"
    checkout.add(f"{function}__mutmut_3", "survived", shown())

    result = checkout.run("--write")

    key = f"{function}: - return a < b | + return a <= b"
    assert key in result.stdout
    assert key in checkout.baseline.read_text(encoding="utf-8")


def test_a_failed_mutmut_run_is_reported_as_failed_not_as_no_survivors(
    checkout: Checkout, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_RUN_RC", "1")
    checkout.add(MUTANT, "survived", shown())

    result = checkout.run()

    assert result.status == 1
    expected = "# Mutants report\n\nCommit: `0123abc`\n\n❌ The mutmut run failed: `mutmut run` exited 1.\n"
    assert result.stdout == expected
    assert "`mutmut run` exited 1" in result.stderr
    # Whatever an earlier state of mutants/ holds, a failed run reads none of it.
    assert checkout.called() == ["mutmut run"]


def test_a_mutmut_run_killed_by_a_signal_is_reported_as_failed(
    checkout: Checkout, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A runner out of memory kills the process, and subprocess reports that as a negative status, not an exit code.
    monkeypatch.setenv("FAKE_RUN_SIGNAL", "KILL")
    checkout.add(MUTANT, "killed")

    result = checkout.run()

    assert result.status == 1
    assert "❌ The mutmut run failed: `mutmut run` exited -9.\n" in result.stdout


def test_a_failed_results_command_is_reported_as_failed(checkout: Checkout, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_RESULTS_RC", "3")
    checkout.add(MUTANT, "killed")

    result = checkout.run()

    assert result.status == 1
    assert "❌ The mutmut run failed: `mutmut results` exited 3." in result.stdout


def test_a_failed_show_command_is_reported_as_failed(checkout: Checkout) -> None:
    checkout.add(MUTANT, "survived")  # No answer for it, so the fake's `cat` fails.

    result = checkout.run()

    assert result.status == 1
    assert "`mutmut show` exited 1" in result.stdout
    assert "## New survivors" not in result.stdout


def test_a_mutant_with_no_changed_line_is_reported_as_failed(checkout: Checkout) -> None:
    checkout.add(MUTANT, "survived", f"# {MUTANT}: survived\n")

    result = checkout.run()

    assert result.status == 1
    assert f"`mutmut show {MUTANT}` shows no changed line" in result.stdout


def test_mutmut_that_cannot_start_is_reported_as_failed(
    checkout: Checkout, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    result = checkout.run()

    assert result.status == 1
    assert "❌ The mutmut run failed: could not start mutmut" in result.stdout


def test_mutmut_that_cannot_be_executed_is_reported_as_failed(
    checkout: Checkout, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_dir = tmp_path / "bin"
    (fake_dir / "mutmut").chmod(0o644)
    monkeypatch.setenv("PATH", str(fake_dir))

    result = checkout.run()

    assert result.status == 1
    assert "❌ The mutmut run failed: could not start mutmut" in result.stdout


def test_a_run_that_lists_no_mutants_is_reported_as_failed(checkout: Checkout) -> None:
    # `mutmut results` prints nothing and exits 0 when mutants/ holds no results.
    result = checkout.run()

    assert result.status == 1
    assert "❌ The mutmut run failed: mutmut listed no mutants." in result.stdout
    assert "## New survivors" not in result.stdout


def test_output_with_no_mutant_in_it_is_no_result(checkout: Checkout) -> None:
    checkout.results.write_text("Warning: nothing to see: here\n", encoding="utf-8")

    result = checkout.run()

    assert result.status == 1
    assert "mutmut listed no mutants" in result.stdout


def test_an_interrupted_run_that_exits_0_is_reported_as_failed(checkout: Checkout) -> None:
    # `mutmut run` swallows KeyboardInterrupt and exits 0, leaving the rest of the mutants unchecked.
    checkout.add(MUTANT, "killed")
    checkout.add(OTHER, "not checked")

    result = checkout.run()

    assert result.status == 1
    assert "❌ The mutmut run failed: 1 of 2 mutants were not checked." in result.stdout


def test_verdicts_left_by_an_earlier_run_are_removed_first(checkout: Checkout, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_RUN_RC", "1")
    stale = checkout.root / "mutants" / "dailies" / "core" / "search.py.meta"
    stale.parent.mkdir(parents=True)
    stale.touch()

    checkout.run()

    assert not stale.exists()


def test_mutants_that_cannot_be_deleted_fail_the_run_before_mutmut_starts(checkout: Checkout) -> None:
    # A plain file: rmtree raises a real OSError that is not FileNotFoundError, also for a test run as root.
    (checkout.root / "mutants").touch()
    checkout.add(MUTANT, "survived", shown())

    result = checkout.run()

    assert result.status == 1
    assert "❌ The mutmut run failed: could not delete mutants/" in result.stdout
    assert checkout.called() == []


@pytest.mark.parametrize("text", ["not json", "[]", "{}", '{"survivors": "x"}', '{"survivors": [1]}'])
def test_a_malformed_baseline_exits_2_before_mutmut_starts(checkout: Checkout, text: str) -> None:
    checkout.baseline.write_text(text, encoding="utf-8")

    result = checkout.run()

    assert result.status == 2
    assert str(checkout.baseline) in result.stderr
    assert result.stdout == ""
    assert checkout.called() == []


def test_a_missing_baseline_exits_2_before_mutmut_starts(checkout: Checkout) -> None:
    checkout.baseline.unlink()

    result = checkout.run()

    assert result.status == 2
    assert "cannot read" in result.stderr
    assert checkout.called() == []


def test_mutmut_runs_in_the_checkout_it_was_given(checkout: Checkout) -> None:
    checkout.add(MUTANT, "killed")

    assert checkout.run().status == 0
    assert (checkout.root / "mutants").is_dir()


def test_the_baseline_path_can_be_given(checkout: Checkout, tmp_path: Path) -> None:
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"survivors": [KEY]}), encoding="utf-8")
    checkout.add(MUTANT, "survived", shown())

    assert checkout.run("--baseline", str(other)).status == 0


def test_bad_arguments_exit_2() -> None:
    with pytest.raises(SystemExit) as stopped:
        mr.main(["--no-such-option"])

    assert stopped.value.code == 2


def test_without_a_commit_the_report_says_unknown(checkout: Checkout, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_SHA")
    checkout.add(MUTANT, "killed")

    assert "Commit: `unknown`\n" in checkout.run().stdout


def test_write_saves_the_survivors_of_the_run_sorted_and_keeps_the_exit_status(checkout: Checkout) -> None:
    checkout.review(KEY, "dailies.core.gone.x_function: - a | + b")
    checkout.add(OTHER, "survived", shown("return name", "return None"))
    checkout.add(MUTANT, "survived", shown())
    checkout.add("dailies.core.search.x__tier__mutmut_30", "survived", shown())
    checkout.add("dailies.core.search.x__tier__mutmut_31", "killed")

    result = checkout.run("--write")

    assert result.status == 1
    expected = ["{", '  "survivors": [', f'    "{KEY}",', f'    "{KEY}",', f'    "{OTHER_KEY}"', "  ]", "}", ""]
    assert checkout.baseline.read_text(encoding="utf-8") == "\n".join(expected)
    assert f"Wrote the proposed baseline to {checkout.baseline}" in result.stderr


def test_a_written_baseline_makes_the_same_run_pass(checkout: Checkout) -> None:
    checkout.add(MUTANT, "survived", shown())
    checkout.add(OTHER, "no tests", shown("return name", "return None"))

    first = checkout.run("--write")
    second = checkout.run()

    assert first.status == 1
    assert second.status == 0
    assert "Known survivors, in the baseline: 2\n" in second.stdout


def test_without_write_the_baseline_is_only_read(checkout: Checkout) -> None:
    before = checkout.baseline.read_bytes()
    checkout.add(MUTANT, "survived", shown())

    checkout.run()

    assert checkout.baseline.read_bytes() == before


def test_a_failed_run_never_touches_the_baseline(checkout: Checkout, monkeypatch: pytest.MonkeyPatch) -> None:
    checkout.review(KEY)
    before = checkout.baseline.read_bytes()
    monkeypatch.setenv("FAKE_RUN_RC", "1")

    result = checkout.run("--write")

    assert result.status == 1
    assert checkout.baseline.read_bytes() == before


def test_the_repositorys_baseline_is_readable_and_as_write_leaves_it() -> None:
    survivors = mr.load_baseline(ROOT / mr.BASELINE)

    assert survivors == sorted(survivors)
