"""Hand mutants of the shell scripts, which neither pytest-cov nor a mutation tool measures (#331).

Each row changes one string in a script and names the test that must fail on the result. A mutant that survives marks a
branch that runs but that no assertion pins (#198, #329). When a hand mutation pass finds one, add the test that kills
it and a row here; see docs/testing.md "Shell mutants".
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GIT = shutil.which("git")
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    GIT is None or BASH is None or shutil.which("jq") is None, reason="needs git, bash and jq"
)


@dataclass(frozen=True)
class Mutant:
    """`old` in `script` replaced by `new`: the test `killed_by` must fail on the result."""

    name: str
    script: str
    old: str
    new: str
    killed_by: str


POPULARITY_REPORT = "scripts/popularity-report.sh"
POPULARITY_REPORT_TESTS = "tests/scripts/test_popularity_report.py"
NIGHTLY_COMPLIANCE = "scripts/nightly-compliance.sh"
NIGHTLY_COMPLIANCE_TESTS = "tests/scripts/test_nightly_compliance.py"
MERGE_QUEUE = "scripts/merge-queue.sh"
MERGE_QUEUE_TESTS = "tests/scripts/test_merge_queue.py"
STRATEGY_REPORT = "scripts/strategy-report.sh"
STRATEGY_REPORT_TESTS = "tests/scripts/test_strategy_report.py"
AI_AUDIT_REPORT = "scripts/ai-audit-report.sh"
AI_AUDIT_REPORT_TESTS = "tests/scripts/test_ai_audit_report.py"
PR_METRICS = "scripts/pr-metrics.sh"
PR_SOURCE = "scripts/lib/pr-source.jq"
PR_METRICS_TESTS = "tests/scripts/test_pr_metrics.py"
APPLY_REVIEW_SUGGESTIONS = "scripts/apply-review-suggestions.sh"
APPLY_REVIEW_SUGGESTIONS_TESTS = "tests/scripts/test_apply_review_suggestions.py"
SANDBOX_GATES = "scripts/sandbox-gates.sh"
SANDBOX_GATES_TESTS = "tests/scripts/test_sandbox_gates.py"
QUALITY_REPORT = "scripts/quality-report.sh"
QUALITY_REPORT_TESTS = "tests/scripts/test_quality_report.py"
AUTO_QA_TUNER = "scripts/auto-qa-tuner.sh"
AUTO_QA_TUNER_TESTS = "tests/scripts/test_auto_qa_tuner.py"
COVERAGE_CHECK = "scripts/coverage-check.sh"
COVERAGE_LIB = "scripts/lib/coverage.sh"
# coverage-check.test.sh holds the cases for coverage-check.sh and lib/coverage.sh; this test runs it.
COVERAGE_CHECK_SUITE = "tests/scripts/test_coverage_check.py::test_coverage_check_shell_suite_passes"

MUTANTS = [
    Mutant(
        "a timed_out, startup_failure or action_required run does not count as succeeded (#198)",
        POPULARITY_REPORT,
        '.conclusion == "success"',
        '.conclusion != "failure"',
        f"{POPULARITY_REPORT_TESTS}::test_a_finished_run_that_did_not_succeed_counts_against_the_rate",
    ),
    Mutant(
        "a valid_until in another form fails instead of being compared as text (#198)",
        POPULARITY_REPORT,
        "NF == 2 && utc($1) && utc($2)",
        "NF == 2 && utc($1)",
        f"{POPULARITY_REPORT_TESTS}::test_a_timestamp_it_cannot_compare_fails",
    ),
    Mutant(
        "--runs with no value is a usage error (#198)",
        POPULARITY_REPORT,
        '--runs) [ "$#" -ge 2 ] || usage; ',
        "--runs) ",
        f"{POPULARITY_REPORT_TESTS}::test_usage_errors",
    ),
    Mutant(
        "--prs with no value is a usage error (#198)",
        POPULARITY_REPORT,
        '--prs) [ "$#" -ge 2 ] || usage; ',
        "--prs) ",
        f"{POPULARITY_REPORT_TESTS}::test_usage_errors",
    ),
    Mutant(
        "--weeks with no value is a usage error (#191)",
        POPULARITY_REPORT,
        '--weeks) [ "$#" -ge 2 ] || usage; ',
        "--weeks) ",
        f"{POPULARITY_REPORT_TESTS}::test_usage_errors",
    ),
    Mutant(
        "a links check error after the links were checked shows their report (#331)",
        NIGHTLY_COMPLIANCE,
        '    if [ -s "$links_md" ]; then\n      details+=',
        "    if false; then\n      details+=",
        f"{NIGHTLY_COMPLIANCE_TESTS}::test_a_links_check_error_with_a_report_puts_the_report_under_failures",
    ),
    Mutant(
        "a links check error puts its report under Failures, not Warnings (#331)",
        NIGHTLY_COMPLIANCE,
        'details+="$(cat "$links_md")"',
        'warnings+="$(cat "$links_md")"',
        f"{NIGHTLY_COMPLIANCE_TESTS}::test_a_links_check_error_with_a_report_puts_the_report_under_failures",
    ),
    Mutant(
        "the queue asks again while GitHub answers UNKNOWN for the merge state",
        MERGE_QUEUE,
        '[ "$state" != UNKNOWN ] && break',
        "break",
        f"{MERGE_QUEUE_TESTS}::test_next_asks_again_while_github_is_still_computing_the_merge_state",
    ),
    Mutant(
        "the queue stops asking for the merge state after three answers",
        MERGE_QUEUE,
        "for attempt in 1 2 3; do",
        "for attempt in 1 2 3 4; do",
        f"{MERGE_QUEUE_TESTS}::test_next_gives_up_on_a_merge_state_still_unknown_after_three_asks",
    ),
    Mutant(
        "the queue rates a pull request from the merge base, as tier-classifier.yml does",
        MERGE_QUEUE,
        '"HEAD...$1"',
        '"HEAD..$1"',
        f"{MERGE_QUEUE_TESTS}::test_next_rates_only_the_pull_requests_own_changes_when_main_moved_since_it_branched",
    ),
    Mutant(
        "a linked issue the queue could not close is named in a warning",
        MERGE_QUEUE,
        '|| echo "::warning title=Merge queue::could not close',
        '|| true "::warning title=Merge queue::could not close',
        f"{MERGE_QUEUE_TESTS}::test_land_still_starts_main_push_workflows_and_the_next_run_when_closing_an_issue_fails",
    ),
    Mutant(
        "--since with no value is a usage error",
        STRATEGY_REPORT,
        '--since) [ "$#" -ge 2 ] || usage; ',
        "--since) ",
        f"{STRATEGY_REPORT_TESTS}::test_rejects_missing_or_valueless_flags_with_a_usage_line",
    ),
    Mutant(
        "--issues with no value is a usage error",
        STRATEGY_REPORT,
        '--issues) [ "$#" -ge 2 ] || usage; ',
        "--issues) ",
        f"{STRATEGY_REPORT_TESTS}::test_rejects_missing_or_valueless_flags_with_a_usage_line",
    ),
    Mutant(
        "an unknown flag is a usage error, even after a complete command",
        STRATEGY_REPORT,
        "*) usage ;;",
        "*) shift ;;",
        f"{STRATEGY_REPORT_TESTS}::test_rejects_missing_or_valueless_flags_with_a_usage_line",
    ),
    Mutant(
        "--since is required",
        STRATEGY_REPORT,
        '[ -z "$since" ] || ',
        "",
        f"{STRATEGY_REPORT_TESTS}::test_rejects_missing_or_valueless_flags_with_a_usage_line",
    ),
    Mutant(
        "--issues is required",
        STRATEGY_REPORT,
        '[ -z "$issues" ] || ',
        "",
        f"{STRATEGY_REPORT_TESTS}::test_rejects_missing_or_valueless_flags_with_a_usage_line",
    ),
    Mutant(
        "an input that is not a JSON array fails naming what it expected",
        STRATEGY_REPORT,
        'if type != "array" then error',
        "if false then error",
        f"{STRATEGY_REPORT_TESTS}::test_fails_on_input_that_is_not_a_list",
    ),
    Mutant(
        "an ACMM gap title may leave out Add",
        STRATEGY_REPORT,
        "(?:Add )?",
        "Add ",
        f"{STRATEGY_REPORT_TESTS}::test_counts_an_acmm_gap_whose_title_leaves_out_add",
    ),
    Mutant(
        "a --since date with trailing text is a usage error",
        AI_AUDIT_REPORT,
        "[0-9]{2}$ ]]",
        "[0-9]{2} ]]",
        f"{AI_AUDIT_REPORT_TESTS}::test_usage_errors",
    ),
    Mutant(
        "a --since date with leading text is a usage error",
        AI_AUDIT_REPORT,
        "=~ ^[0-9]{4}",
        "=~ [0-9]{4}",
        f"{AI_AUDIT_REPORT_TESTS}::test_usage_errors",
    ),
    Mutant(
        "a pull request with a null body is attributed, not an error",
        PR_SOURCE,
        '(.body // "")',
        ".body",
        f"{AI_AUDIT_REPORT_TESTS}::test_a_pr_with_no_body_is_attributed_by_its_branch",
    ),
    Mutant(
        "an omp signature counts only at the start of a line",
        PR_SOURCE,
        'test("^— omp',
        'test("— omp',
        f"{AI_AUDIT_REPORT_TESTS}::test_a_signature_counts_only_at_the_start_of_a_line",
    ),
    Mutant(
        "a claude/ branch prefix includes its slash",
        PR_SOURCE,
        'startswith("claude/")',
        'startswith("claude")',
        f"{AI_AUDIT_REPORT_TESTS}::test_a_source_branch_prefix_includes_its_slash",
    ),
    Mutant(
        "a dependabot/ branch prefix includes its slash",
        PR_SOURCE,
        'startswith("dependabot/")',
        'startswith("dependabot")',
        f"{AI_AUDIT_REPORT_TESTS}::test_a_source_branch_prefix_includes_its_slash",
    ),
    Mutant(
        "merges at the same time are listed by pull request number",
        AI_AUDIT_REPORT,
        "sort_by(.mergedAt, .number)",
        "sort_by(.mergedAt)",
        f"{AI_AUDIT_REPORT_TESTS}::test_ledger_lists_prs_merged_at_the_same_time_by_number",
    ),
    Mutant(
        "a merge with no recorded merger shows a dash in the ledger",
        AI_AUDIT_REPORT,
        ".mergedBy.login // none | cell",
        ".mergedBy.login | cell",
        f"{AI_AUDIT_REPORT_TESTS}::test_a_merge_with_no_recorded_merger_shows_a_dash_in_the_ledger",
    ),
    Mutant(
        "a claude/ branch prefix includes its slash",
        PR_SOURCE,
        'startswith("claude/")',
        'startswith("claude")',
        f"{PR_METRICS_TESTS}::test_a_branch_named_like_claude_without_the_slash_is_not_an_agent",
    ),
    Mutant(
        "the acceptance rate is rounded, not truncated",
        PR_METRICS,
        "($merged * 1000 / $total | round) / 10",
        "($merged * 1000 / $total | floor) / 10",
        f"{PR_METRICS_TESTS}::test_the_rate_is_rounded_to_the_nearest_tenth",
    ),
    Mutant(
        "the coverage run's output goes to stderr",
        QUALITY_REPORT,
        'pytest --cov "--cov-report=xml:$report" >&2',
        'pytest --cov "--cov-report=xml:$report"',
        f"{QUALITY_REPORT_TESTS}::test_reports_every_gate_and_the_coverage_of_each_module",
    ),
    Mutant(
        "a proposal is rounded to hundredths before it is floored",
        AUTO_QA_TUNER,
        "* 100 | round) / 100 | floor",
        "* 100) / 100 | floor",
        f"{AUTO_QA_TUNER_TESTS}::test_float_error_does_not_drop_a_proposal_below_a_whole_percent",
    ),
    Mutant(
        "the tuner rejects a margin that is not a number",
        AUTO_QA_TUNER,
        '(.margin | type == "number" and . >= 0)',
        "(.margin | . >= 0)",
        f"{AUTO_QA_TUNER_TESTS}::test_malformed_config_fails_and_is_left_untouched",
    ),
    Mutant(
        "the tuner rejects floors that are not an object",
        AUTO_QA_TUNER,
        '(.floors | type == "object" and length > 0',
        "(.floors | length > 0",
        f"{AUTO_QA_TUNER_TESTS}::test_malformed_config_fails_and_is_left_untouched",
    ),
    Mutant(
        "the coverage gate rejects a margin that is not a number",
        COVERAGE_CHECK,
        '(.margin | type == "number" and . >= 0)',
        "(.margin | . >= 0)",
        COVERAGE_CHECK_SUITE,
    ),
    Mutant(
        "the coverage gate rejects floors that are not an object",
        COVERAGE_CHECK,
        '(.floors | type == "object" and length > 0',
        "(.floors | length > 0",
        COVERAGE_CHECK_SUITE,
    ),
    Mutant(
        "the coverage gate rejects a floor below 0",
        COVERAGE_CHECK,
        'type == "number" and . >= 0 and . <= 100',
        'type == "number" and . <= 100',
        COVERAGE_CHECK_SUITE,
    ),
    Mutant(
        "a group with no code yet does not end the coverage check",
        COVERAGE_CHECK,
        'apply once it has code"\n    continue',
        'apply once it has code"\n    exit 0',
        COVERAGE_CHECK_SUITE,
    ),
    Mutant(
        "branch coverage below its floor fails the gate",
        COVERAGE_CHECK,
        'below its floor of ${floor_branches}%" >&2\n    failed=1',
        'below its floor of ${floor_branches}%" >&2',
        COVERAGE_CHECK_SUITE,
    ),
    Mutant(
        "a relative <source> (relative_files) is its group's root",
        COVERAGE_LIB,
        "return source == group_dir or source.endswith",
        "return source.endswith",
        COVERAGE_CHECK_SUITE,
    ),
    Mutant(
        "a <source> with a trailing slash is normalised",
        COVERAGE_LIB,
        "os.path.normpath(s.text.strip())",
        "s.text.strip()",
        COVERAGE_CHECK_SUITE,
    ),
    Mutant(
        "a Windows <source> is matched by its trailing path",
        COVERAGE_LIB,
        '.replace("\\\\", "/")',
        "",
        COVERAGE_CHECK_SUITE,
    ),
    Mutant(
        "a <class> without a filename is a malformed report",
        COVERAGE_LIB,
        "if not filename:",
        "if False:",
        COVERAGE_CHECK_SUITE,
    ),
    Mutant(
        "lines without branches is 100% branch coverage",
        COVERAGE_LIB,
        'if (m + c == 0) print "100.00"',
        'if (0) print "100.00"',
        COVERAGE_CHECK_SUITE,
    ),
    Mutant(
        "an OWNER counts as having write access",
        APPLY_REVIEW_SUGGESTIONS,
        '"OWNER", "MEMBER"',
        '"MEMBER"',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_applies_a_suggestion_from_anyone_with_write_access",
    ),
    Mutant(
        "a COLLABORATOR counts as having write access",
        APPLY_REVIEW_SUGGESTIONS,
        '"MEMBER", "COLLABORATOR"',
        '"MEMBER"',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_applies_a_suggestion_from_anyone_with_write_access",
    ),
    Mutant(
        "a suggestion fence counts only at the start of a line",
        APPLY_REVIEW_SUGGESTIONS,
        'scan("\\n(`{3,})suggestion',
        'scan("(`{3,})suggestion',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_only_a_fence_of_three_backticks_at_the_start_of_a_line_opens_a_suggestion",
    ),
    Mutant(
        "two backticks open no suggestion",
        APPLY_REVIEW_SUGGESTIONS,
        "(`{3,})suggestion",
        "(`{2,})suggestion",
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_only_a_fence_of_three_backticks_at_the_start_of_a_line_opens_a_suggestion",
    ),
    Mutant(
        "blanks after the opening fence are ignored",
        APPLY_REVIEW_SUGGESTIONS,
        "suggestion[ \\t]*\\n",
        "suggestion\\n",
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_blanks_after_the_opening_fence_are_ignored",
    ),
    Mutant(
        "suggestions are grouped per file, so overlaps are found across another file's range",
        APPLY_REVIEW_SUGGESTIONS,
        "sort_by(.path, -.start)",
        "sort_by(-.start)",
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_each_file_has_its_own_line_count_and_overlaps",
    ),
    Mutant(
        "each file gets its own line count and overlap floor",
        APPLY_REVIEW_SUGGESTIONS,
        'if [ "$path" != "$current_path" ]; then',
        'if [ -z "$current_path" ]; then',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_each_file_has_its_own_line_count_and_overlaps",
    ),
    Mutant(
        "the checkout is compared by its real path",
        APPLY_REVIEW_SUGGESTIONS,
        'checkout="$(realpath .)"',
        'checkout="$PWD"',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_a_checkout_entered_through_a_symlink_is_still_the_checkout",
    ),
    Mutant(
        "a sibling directory sharing the checkout's name is outside it",
        APPLY_REVIEW_SUGGESTIONS,
        '[[ "$resolved" != "$checkout"/* ]]',
        '[[ "$resolved" != "$checkout"* ]]',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_a_directory_named_like_the_checkout_is_outside_it",
    ),
    Mutant(
        "a directory in the checkout is skipped",
        APPLY_REVIEW_SUGGESTIONS,
        ' || [ ! -f "$resolved" ]',
        "",
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_skips_a_directory",
    ),
    Mutant(
        "a symlink to a workflow file counts as a workflow file",
        APPLY_REVIEW_SUGGESTIONS,
        'if [[ "$resolved" == "$checkout"/.github/workflows/* ]]',
        'if [[ "$path" == .github/workflows/* ]]',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_skips_a_symlink_to_a_workflow_file",
    ),
    Mutant(
        "only .github/workflows is refused, not all of .github",
        APPLY_REVIEW_SUGGESTIONS,
        '"$checkout"/.github/workflows/*',
        '"$checkout"/.github/*',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_applies_to_other_files_under_dot_github",
    ),
    Mutant(
        "a path starting with a dash is not a realpath option",
        APPLY_REVIEW_SUGGESTIONS,
        "realpath -e -- ",
        "realpath -e ",
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_a_file_name_starting_with_a_dash_is_not_an_option",
    ),
    Mutant(
        "a last line without a newline counts as a line",
        APPLY_REVIEW_SUGGESTIONS,
        'lines="$(awk \'END { print NR }\' "$resolved")"',
        'lines="$(wc -l < "$resolved")"',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_applies_to_a_last_line_without_a_trailing_newline",
    ),
    Mutant(
        "the last line is below the overlap floor",
        APPLY_REVIEW_SUGGESTIONS,
        "floor=$((lines + 1))",
        "floor=$lines",
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_applies_to_a_last_line_without_a_trailing_newline",
    ),
    Mutant(
        "the last line is in the file",
        APPLY_REVIEW_SUGGESTIONS,
        '[ "$end" -gt "$lines" ]',
        '[ "$end" -ge "$lines" ]',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_applies_to_a_last_line_without_a_trailing_newline",
    ),
    Mutant(
        "line 0 is not in the file",
        APPLY_REVIEW_SUGGESTIONS,
        '[ "$start" -lt 1 ]',
        '[ "$start" -lt 0 ]',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_skips_suggestions_it_must_not_apply",
    ),
    Mutant(
        "a range ending before it starts is not in the file",
        APPLY_REVIEW_SUGGESTIONS,
        '[ "$end" -lt "$start" ] || ',
        "",
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_skips_suggestions_it_must_not_apply",
    ),
    Mutant(
        "the edit keeps the file's mode",
        APPLY_REVIEW_SUGGESTIONS,
        'cat "$tmp" > "$resolved"\n  rm -f "$tmp"',
        'mv "$tmp" "$resolved"',
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_keeps_the_mode_of_the_file",
    ),
    Mutant(
        "the edit removes its temporary file",
        APPLY_REVIEW_SUGGESTIONS,
        '  rm -f "$tmp"\n',
        "",
        f"{APPLY_REVIEW_SUGGESTIONS_TESTS}::test_leaves_no_temporary_file_behind",
    ),
    Mutant(
        "the gates run from the repository root",
        SANDBOX_GATES,
        'cd "$ROOT" || exit 1\n',
        "",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "the whole work directory is removed, not just the build",
        SANDBOX_GATES,
        'rm -rf "$work"',
        'rm -rf "$work/build"',
        f"{SANDBOX_GATES_TESTS}::test_the_temporary_directory_is_removed_on_exit",
    ),
    Mutant(
        "meson test runs in the build directory",
        SANDBOX_GATES,
        'meson test -C "$work/build"',
        'meson test -C "$work"',
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "the work directory is removed on exit",
        SANDBOX_GATES,
        "trap 'rm -rf \"$work\"' EXIT\n",
        "",
        f"{SANDBOX_GATES_TESTS}::test_the_temporary_directory_is_removed_on_exit",
    ),
    Mutant(
        "the format gate runs",
        SANDBOX_GATES,
        "\nruff format --check .\n",
        "\ntrue\n",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "the format gate checks instead of rewriting",
        SANDBOX_GATES,
        "\nruff format --check .\n",
        "\nruff format .\n",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "a format failure counts",
        SANDBOX_GATES,
        'ruff format --check .\nend "$?"',
        "ruff format --check .\nend 0",
        f"{SANDBOX_GATES_TESTS}::test_a_failed_gate_is_reported_under_its_own_label",
    ),
    Mutant(
        "pytest measures coverage",
        SANDBOX_GATES,
        'pytest --cov "--cov-report',
        'pytest "--cov-report',
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "a pytest failure counts even if the floors would pass",
        SANDBOX_GATES,
        '"--cov-report=xml:$work/coverage.xml" &&',
        '"--cov-report=xml:$work/coverage.xml";',
        f"{SANDBOX_GATES_TESTS}::test_a_failed_gate_is_reported_under_its_own_label",
    ),
    Mutant(
        "the coverage gate defaults to scripts/coverage-check.sh",
        SANDBOX_GATES,
        "$ROOT/scripts/coverage-check.sh}",
        "$ROOT/scripts/coverage.sh}",
        f"{SANDBOX_GATES_TESTS}::test_the_coverage_gate_defaults_to_the_repository_script",
    ),
    Mutant(
        "a coverage floor failure counts",
        SANDBOX_GATES,
        'auto-qa-tuning.json"\nend "$?"',
        'auto-qa-tuning.json"\nend 0',
        f"{SANDBOX_GATES_TESTS}::test_a_failed_gate_is_reported_under_its_own_label",
    ),
    Mutant(
        "the catalog is checked against its own schema",
        SANDBOX_GATES,
        "--schemafile data/v1/schema/catalog.schema.json data/v1/games.json",
        "--schemafile data/v1/schema/popularity.schema.json data/v1/games.json",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "the popularity data is checked against its own schema",
        SANDBOX_GATES,
        "--schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json",
        "--schemafile data/v1/schema/catalog.schema.json data/v1/popularity.json",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "a catalog schema failure counts",
        SANDBOX_GATES,
        'data/v1/games.json\nend "$?"',
        "data/v1/games.json\nend 0",
        f"{SANDBOX_GATES_TESTS}::test_a_failed_gate_is_reported_under_its_own_label",
    ),
    Mutant(
        "a popularity schema failure counts",
        SANDBOX_GATES,
        'data/v1/popularity.json\nend "$?"',
        "data/v1/popularity.json\nend 0",
        f"{SANDBOX_GATES_TESTS}::test_a_failed_gate_is_reported_under_its_own_label",
    ),
    Mutant(
        "shellcheck follows sourced files",
        SANDBOX_GATES,
        "\nshellcheck -x scripts/*.sh",
        "\nshellcheck scripts/*.sh",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "shellcheck covers scripts/lib",
        SANDBOX_GATES,
        "\nshellcheck -x scripts/*.sh scripts/lib/*.sh",
        "\nshellcheck -x scripts/*.sh",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "shellcheck covers build-aux/windows",
        SANDBOX_GATES,
        "scripts/lib/*.sh build-aux/windows/*.sh\nend",
        "scripts/lib/*.sh\nend",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "a shellcheck failure counts",
        SANDBOX_GATES,
        'build-aux/windows/*.sh\nend "$?"',
        "build-aux/windows/*.sh\nend 0",
        f"{SANDBOX_GATES_TESTS}::test_a_failed_gate_is_reported_under_its_own_label",
    ),
    Mutant(
        "actionlint runs",
        SANDBOX_GATES,
        "\nactionlint\n",
        "\ntrue\n",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "an actionlint failure counts",
        SANDBOX_GATES,
        '\nactionlint\nend "$?"',
        "\nactionlint\nend 0",
        f"{SANDBOX_GATES_TESTS}::test_a_failed_gate_is_reported_under_its_own_label",
    ),
    Mutant(
        "meson builds the development profile",
        SANDBOX_GATES,
        " -Dprofile=development",
        "",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
    Mutant(
        "a failed meson setup counts",
        SANDBOX_GATES,
        '"--prefix=$work/prefix" &&',
        '"--prefix=$work/prefix";',
        f"{SANDBOX_GATES_TESTS}::test_a_failed_gate_is_reported_under_its_own_label",
    ),
    Mutant(
        "a failed meson install counts",
        SANDBOX_GATES,
        'meson install -C "$work/build" --quiet &&',
        'meson install -C "$work/build" --quiet;',
        f"{SANDBOX_GATES_TESTS}::test_a_failed_gate_is_reported_under_its_own_label",
    ),
    Mutant(
        "an unset XDG_DATA_DIRS falls back to the XDG default",
        SANDBOX_GATES,
        "${XDG_DATA_DIRS:-/usr/local/share:/usr/share}",
        "${XDG_DATA_DIRS:-/usr/share}",
        f"{SANDBOX_GATES_TESTS}::test_meson_tests_fall_back_to_the_default_data_path",
    ),
    Mutant(
        "meson test prints the logs of failed tests",
        SANDBOX_GATES,
        " --print-errorlogs",
        "",
        f"{SANDBOX_GATES_TESTS}::test_every_gate_runs_the_command_ci_runs_from_the_repository_root",
    ),
]


def copy_repo(dest: Path) -> Path:
    """Copies the files git sees (tracked, and untracked but not ignored) to `dest`, so the mutant never touches ROOT.

    The tests find their script relative to their own file, so the copied test runs the copied script.
    """
    assert GIT is not None
    listed = subprocess.run(  # noqa: S603 - fixed git command, no user input
        [GIT, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    for name in filter(None, listed.decode().split("\0")):
        source = ROOT / name
        if not source.is_file():  # tracked but deleted in the working tree
            continue
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return dest


def run_pytest(repo: Path, node: str, basetemp: Path) -> subprocess.CompletedProcess[str]:
    """Runs one test node in `repo` with its own temporary directory and none of the outer run's pytest or coverage
    settings."""
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith(("PYTEST_", "COV_CORE_", "COVERAGE_"))
    }
    return subprocess.run(  # noqa: S603 - this interpreter, node ids from the table above
        [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", f"--basetemp={basetemp}", node],
        cwd=repo,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


# Without this control, a harness that cannot run the copied test at all (a node id that names no test, a test that
# needs something the copy lacks) would count every mutant as killed.
@pytest.mark.parametrize("node", sorted({mutant.killed_by for mutant in MUTANTS}))
def test_the_killing_test_passes_on_an_unmutated_copy(tmp_path: Path, node: str) -> None:
    repo = copy_repo(tmp_path / "repo")

    result = run_pytest(repo, node, tmp_path / "basetemp")

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("mutant", MUTANTS, ids=[mutant.name for mutant in MUTANTS])
def test_the_mutant_is_killed(tmp_path: Path, mutant: Mutant) -> None:
    source = (ROOT / mutant.script).read_text(encoding="utf-8")
    # A row the script has moved away from must fail here, not pass by mutating nothing.
    assert source.count(mutant.old) == 1, f"{mutant.old!r} must occur exactly once in {mutant.script}"
    repo = copy_repo(tmp_path / "repo")
    (repo / mutant.script).write_text(source.replace(mutant.old, mutant.new), encoding="utf-8")

    result = run_pytest(repo, mutant.killed_by, tmp_path / "basetemp")

    # Exit 1 is "tests failed"; 2-5 (interrupted, internal error, usage error, nothing collected) are not a kill.
    assert result.returncode == 1, f"the mutant survived {mutant.killed_by}:\n{result.stdout}{result.stderr}"
