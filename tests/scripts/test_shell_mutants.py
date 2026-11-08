"""Hand mutants of the shell and Python scripts, which no mutation tool reaches (#331, #409).

pytest-cov does not see a shell script, and of a Python script it only shows which lines ran. Each row changes one
string in a script and names the test that must fail on the result. A mutant that survives marks a branch that runs but
that no assertion pins (#198, #329). When a hand mutation pass finds one, add the test that kills it and a row here; see
docs/testing.md "Shell mutants". The table pins those known kills: it does not find new ones.
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
TIER_CLASSIFY = "scripts/tier-classify.sh"
TIER_CLASSIFY_SUITE = "tests/tooling/test_tier_classify.py::test_tier_classify_shell_suite_passes"
PR_REVIEW_CHECK = "scripts/pr-review-check.sh"
PR_REVIEW_CHECK_SUITE = "tests/scripts/test_pr_review_check.py::test_pr_review_check_shell_suite_passes"
SANDBOX = "scripts/sandbox.sh"
SANDBOX_TESTS = "tests/scripts/test_sandbox.py"
URLCHECK = "scripts/lib/urlcheck.py"
VALIDATE_SUBMISSION = "scripts/validate_submission.py"
# test_validate_submission.py holds the cases for validate_submission.py and lib/urlcheck.py.
VALIDATE_SUBMISSION_TESTS = "tests/scripts/test_validate_submission.py"
APPLY_LINK_STATUS = "scripts/apply_link_status.py"
APPLY_LINK_STATUS_TESTS = "tests/scripts/test_apply_link_status.py"
COLLECT = "scripts/popularity/collect.py"
COLLECT_TESTS = "tests/scripts/test_collect.py"
COMPLIANCE_ISSUE = "scripts/compliance_issue.py"
COMPLIANCE_ISSUE_TESTS = "tests/scripts/test_compliance_issue.py"
COMPUTE = "scripts/popularity/compute.py"
COMPUTE_TESTS = "tests/scripts/test_compute.py"
FLATPARK_PAYLOAD = "scripts/flatpark_payload.py"
FLATPARK_PAYLOAD_TESTS = "tests/scripts/test_flatpark_payload.py"
LINK_STATUS = "scripts/lib/linkstatus.py"
LINK_STATUS_TESTS = "tests/scripts/test_link_status.py"
PR_BODY = "scripts/popularity/pr_body.py"
PR_BODY_TESTS = "tests/scripts/test_pr_body.py"
RELEASE_CHECK = "scripts/release_check.py"
RELEASE_CHECK_TESTS = "tests/scripts/test_release_check.py"
REPORT_GUARD = "scripts/popularity/report_guard.py"
REPORT_GUARD_TESTS = "tests/scripts/test_report_guard.py"
CHECK_PAGES = "scripts/check_pages.py"
CHECK_PAGES_TESTS = "tests/scripts/test_check_pages.py"

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
        "the Pages row captures why check_pages.py could not run, which it writes to stderr (#435)",
        NIGHTLY_COMPLIANCE,
        'scripts/check_pages.py}" 2>&1)"',
        'scripts/check_pages.py}")"',
        f"{NIGHTLY_COMPLIANCE_TESTS}::test_an_unreadable_checkout_fails_the_pages_row",
    ),
    Mutant(
        "the Pages row runs scripts/check_pages.py when the tests do not replace it (#435)",
        NIGHTLY_COMPLIANCE,
        "${PAGES_CHECK:-scripts/check_pages.py}",
        "${PAGES_CHECK:-scripts/check_page.py}",
        f"{NIGHTLY_COMPLIANCE_TESTS}::test_each_script_the_tests_replace_defaults_to_one_in_the_repository",
    ),
    Mutant(
        "the queue says why it skips an UNSTABLE pull request",
        MERGE_QUEUE,
        'if [ "$state" = UNSTABLE ]; then',
        "if false; then",
        f"{MERGE_QUEUE_TESTS}::test_next_reports_a_pull_request_held_back_by_a_check_that_is_not_required",
    ),
    Mutant(
        "the queue leaves an UNSTABLE pull request out",
        MERGE_QUEUE,
        '[ "$state" = CLEAN ] || continue',
        '[ "$state" = CLEAN ] || [ "$state" = UNSTABLE ] || continue',
        f"{MERGE_QUEUE_TESTS}::test_next_reports_a_pull_request_held_back_by_a_check_that_is_not_required",
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
        "for attempt in 1 2 3; do\n    state=",
        "for attempt in 1 2 3 4; do\n    state=",
        f"{MERGE_QUEUE_TESTS}::test_next_gives_up_on_a_merge_state_still_unknown_after_three_asks",
    ),
    Mutant(
        "the queue waits before it asks for the merge state again",
        MERGE_QUEUE,
        '[ "$attempt" -lt 3 ] && sleep 5',
        '[ "$attempt" -lt 3 ] && true',
        f"{MERGE_QUEUE_TESTS}::test_next_asks_again_while_github_is_still_computing_the_merge_state",
    ),
    Mutant(
        "the queue does not wait after the last ask for the merge state",
        MERGE_QUEUE,
        '[ "$attempt" -lt 3 ] && sleep 5',
        '[ "$attempt" -lt 4 ] && sleep 5',
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
        "a dispatch that fails once is tried again",
        MERGE_QUEUE,
        "for attempt in 1 2 3; do\n    gh workflow run",
        "for attempt in 1; do\n    gh workflow run",
        f"{MERGE_QUEUE_TESTS}::test_land_tries_again_when_a_workflow_does_not_start_the_first_time",
    ),
    Mutant(
        "a dispatch that failed waits before it is tried again",
        MERGE_QUEUE,
        '[ "$attempt" -lt 3 ] && sleep 10',
        '[ "$attempt" -lt 3 ] && true',
        f"{MERGE_QUEUE_TESTS}::test_land_tries_again_when_a_workflow_does_not_start_the_first_time",
    ),
    Mutant(
        "there is no wait after the last try of a dispatch",
        MERGE_QUEUE,
        '[ "$attempt" -lt 3 ] && sleep 10',
        '[ "$attempt" -lt 4 ] && sleep 10',
        f"{MERGE_QUEUE_TESTS}::test_land_starts_the_rest_names_the_workflow_that_would_not_start_and_fails",
    ),
    Mutant(
        "a workflow that will not start does not stop the others or the next run",
        MERGE_QUEUE,
        'start_workflow "$workflow" || failed=1',
        'start_workflow "$workflow"',
        f"{MERGE_QUEUE_TESTS}::test_land_starts_the_rest_names_the_workflow_that_would_not_start_and_fails",
    ),
    Mutant(
        "a run that left a main push workflow unstarted fails",
        MERGE_QUEUE,
        'return "$failed"',
        "return 0",
        f"{MERGE_QUEUE_TESTS}::test_land_starts_the_rest_names_the_workflow_that_would_not_start_and_fails",
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
    Mutant(
        "a rejected policy prints nothing on stdout",
        TIER_CLASSIFY,
        'echo "tier-classify: $*" >&2',
        'echo "tier-classify: $*"',
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "a tab separates the fields of a policy item",
        TIER_CLASSIFY,
        "IFS=$' \\t\\r' read",
        "IFS=$' \\r' read",
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "a backslash in a rule reaches the glob",
        TIER_CLASSIFY,
        "read -r item tier glob extra",
        "read item tier glob extra",
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "a rules: line with a value is malformed",
        TIER_CLASSIFY,
        '[ "$item" = rules: ] && [ -z "${tier:-}" ] &&',
        '[ "$item" = rules: ] &&',
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "a rule needs its dash",
        TIER_CLASSIFY,
        '[ -n "$in_rules" ] && [ "$item" = - ] &&',
        '[ -n "$in_rules" ] &&',
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "git's \\a escape is decoded before the path is matched",
        TIER_CLASSIFY,
        '[abtnvfr"\\\\]',
        '[btnvfr"\\\\]',
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "git's \\b escape is decoded before the path is matched",
        TIER_CLASSIFY,
        '[abtnvfr"\\\\]',
        '[atnvfr"\\\\]',
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "git's \\v escape is decoded before the path is matched",
        TIER_CLASSIFY,
        '[abtnvfr"\\\\]',
        '[abtnfr"\\\\]',
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "git's \\f escape is decoded before the path is matched",
        TIER_CLASSIFY,
        '[abtnvfr"\\\\]',
        '[abtnvr"\\\\]',
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "git's \\r escape is decoded before the path is matched",
        TIER_CLASSIFY,
        '[abtnvfr"\\\\]',
        '[abtnvf"\\\\]',
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "spaces around a path stay part of the path",
        TIER_CLASSIFY,
        'IFS= read -r -d "$delim" path',
        'read -r -d "$delim" path',
        TIER_CLASSIFY_SUITE,
    ),
    Mutant(
        "a title must start with its type",
        PR_REVIEW_CHECK,
        "=~ ^($types)",
        "=~ ($types)",
        PR_REVIEW_CHECK_SUITE,
    ),
    Mutant(
        "a title scope may hold digits",
        PR_REVIEW_CHECK,
        "[a-z0-9._/-]+",
        "[a-z._/-]+",
        PR_REVIEW_CHECK_SUITE,
    ),
    Mutant(
        "a title scope may hold an underscore",
        PR_REVIEW_CHECK,
        "[a-z0-9._/-]+",
        "[a-z0-9./-]+",
        PR_REVIEW_CHECK_SUITE,
    ),
    Mutant(
        "a title scope may hold a dash",
        PR_REVIEW_CHECK,
        "[a-z0-9._/-]+",
        "[a-z0-9._/]+",
        PR_REVIEW_CHECK_SUITE,
    ),
    Mutant(
        "a digit before the keyword means it is no whole word",
        PR_REVIEW_CHECK,
        "(^|[^[:alnum:]_])",
        "(^|[^[:alpha:]_])",
        PR_REVIEW_CHECK_SUITE,
    ),
    Mutant(
        "the keyword may be followed by several spaces",
        PR_REVIEW_CHECK,
        ":?[[:space:]]+",
        ":?[[:space:]]",
        PR_REVIEW_CHECK_SUITE,
    ),
    Mutant(
        "the keyword needs a space before the number",
        PR_REVIEW_CHECK,
        ":?[[:space:]]+",
        ":?[[:space:]]*",
        PR_REVIEW_CHECK_SUITE,
    ),
    Mutant(
        "the repository of a long-form link may hold dots, dashes and underscores",
        PR_REVIEW_CHECK,
        "/[[:alnum:]_.-]+)?#",
        "/[[:alnum:]]+)?#",
        PR_REVIEW_CHECK_SUITE,
    ),
    Mutant(
        "the container keeps your uid",
        SANDBOX,
        " --userns=keep-id -v",
        " -v",
        f"{SANDBOX_TESTS}::test_the_container_keeps_your_uid_starts_in_the_checkout_and_is_removed",
    ),
    Mutant(
        "the container starts in the checkout",
        SANDBOX,
        "--workdir /workspace ",
        "",
        f"{SANDBOX_TESTS}::test_the_container_keeps_your_uid_starts_in_the_checkout_and_is_removed",
    ),
    Mutant(
        "the container is removed when it exits",
        SANDBOX,
        "podman run --rm ",
        "podman run ",
        f"{SANDBOX_TESTS}::test_the_container_keeps_your_uid_starts_in_the_checkout_and_is_removed",
    ),
    Mutant(
        "the image is built from scripts/, not the whole checkout",
        SANDBOX,
        '"$ROOT/scripts" >/dev/null',
        '"$ROOT" >/dev/null',
        f"{SANDBOX_TESTS}::test_the_build_context_is_scripts_not_the_whole_checkout",
    ),
    Mutant(
        "no terminal is requested without one",
        SANDBOX,
        "[ -t 0 ] && [ -t 1 ]",
        "true",
        f"{SANDBOX_TESTS}::test_without_a_terminal_the_container_asks_for_none",
    ),
    # Python scripts: the behaviour #406 and #408 pinned after a hand sweep found it unasserted (#409).
    Mutant(
        "a public session ignores a proxy in the environment",
        URLCHECK,
        "session.trust_env = False",
        "session.trust_env = True",
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_public_session_ignores_a_proxy_in_the_environment",
    ),
    Mutant(
        "a page is requested as a stream, so its body is not read in full",
        URLCHECK,
        "stream=True,",
        "stream=False,",
        f"{VALIDATE_SUBMISSION_TESTS}::test_requests_send_a_descriptive_user_agent_and_a_timeout",
    ),
    Mutant(
        "a 308 is followed and checked like the other redirects",
        URLCHECK,
        "frozenset({301, 302, 303, 307, 308})",
        "frozenset({301, 302, 303, 307})",
        f"{VALIDATE_SUBMISSION_TESTS}::test_every_redirect_status_is_followed_and_checked",
    ),
    Mutant(
        "a Location header on a normal answer is not a redirect",
        URLCHECK,
        "if response.status_code not in REDIRECT_STATUSES or not location:",
        "if not location:",
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_location_header_on_a_normal_answer_is_not_a_redirect",
    ),
    Mutant(
        "two sites on a shared hosting domain are different sites",
        URLCHECK,
        "include_psl_private_domains=True",
        "include_psl_private_domains=False",
        f"{VALIDATE_SUBMISSION_TESTS}::test_two_sites_on_a_shared_hosting_domain_are_different_sites",
    ),
    Mutant(
        "a page is read up to MAX_BODY and no further",
        URLCHECK,
        "if len(body) >= MAX_BODY:",
        "if len(body) > MAX_BODY:",
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_page_that_never_ends_is_read_up_to_512_kib_and_no_further",
    ),
    Mutant(
        "the first title of a page wins over a later one",
        URLCHECK,
        'if tag == "title" and self.title is None:',
        'if tag == "title":',
        f"{VALIDATE_SUBMISSION_TESTS}::test_the_first_title_wins_over_a_later_one",
    ),
    Mutant(
        "a stray closing title tag does not stop the real title",
        URLCHECK,
        'if tag == "title" and self._parts is not None:',
        'if tag == "title":',
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_stray_closing_title_tag_does_not_stop_the_real_title",
    ),
    Mutant(
        "a page title is decoded with the charset the response names",
        URLCHECK,
        'data.decode(response.encoding or "utf-8", errors="replace")',
        'data.decode("utf-8", errors="replace")',
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_page_title_is_decoded_with_the_charset_the_response_names",
    ),
    Mutant(
        "bytes that do not fit the named charset do not stop the check",
        URLCHECK,
        'response.encoding or "utf-8", errors="replace"',
        'response.encoding or "utf-8", errors="strict"',
        f"{VALIDATE_SUBMISSION_TESTS}::test_bytes_a_page_got_wrong_in_its_title_do_not_stop_the_check",
    ),
    Mutant(
        "bytes that do not fit the fallback charset do not stop the check",
        URLCHECK,
        'text = data.decode("utf-8", errors="replace")',
        'text = data.decode("utf-8", errors="strict")',
        f"{VALIDATE_SUBMISSION_TESTS}::test_bytes_a_page_got_wrong_in_its_title_do_not_stop_the_check",
    ),
    Mutant(
        "a page with no charset is read as UTF-8",
        URLCHECK,
        'response.encoding or "utf-8"',
        'response.encoding or "latin-1"',
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_page_with_no_charset_is_read_as_utf_8",
    ),
    Mutant(
        "a page that trickles past the deadline is given up on",
        URLCHECK,
        "if monotonic() > deadline:",
        "if False:",
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_page_that_trickles_past_the_deadline_counts_as_a_timeout",
    ),
    Mutant(
        "a page that trickles past the deadline counts as a timeout",
        URLCHECK,
        "raise CheckError(msg, timed_out=True)",
        "raise CheckError(msg)",
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_page_that_trickles_past_the_deadline_counts_as_a_timeout",
    ),
    Mutant(
        "a 429 from Cloudflare is a bot wall",
        URLCHECK,
        "HTTPStatus.TOO_MANY_REQUESTS, ",
        "",
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_challenge_status_from_cloudflare_is_a_bot_wall",
    ),
    Mutant(
        "a dead page behind Cloudflare is not a bot wall",
        URLCHECK,
        "if response.status_code not in BOT_WALL_STATUSES:",
        "if False:",
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_dead_page_behind_cloudflare_is_not_a_bot_wall",
    ),
    Mutant(
        "empty text gets no code span",
        URLCHECK,
        '    if not text:\n        return ""\n',
        "",
        f"{VALIDATE_SUBMISSION_TESTS}::test_code_span_pads_only_a_span_that_touches_a_backtick",
    ),
    Mutant(
        "a code span that starts with a backtick is padded",
        URLCHECK,
        'text.startswith("`") or text.endswith("`")',
        'text.endswith("`")',
        f"{VALIDATE_SUBMISSION_TESTS}::test_code_span_pads_only_a_span_that_touches_a_backtick",
    ),
    Mutant(
        "a code span that ends with a backtick is padded",
        URLCHECK,
        'text.startswith("`") or text.endswith("`")',
        'text.startswith("`")',
        f"{VALIDATE_SUBMISSION_TESTS}::test_code_span_pads_only_a_span_that_touches_a_backtick",
    ),
    Mutant(
        "a code span that touches no backtick is not padded",
        URLCHECK,
        'padding = " " if text.startswith("`") or text.endswith("`") else ""',
        'padding = " "',
        f"{VALIDATE_SUBMISSION_TESTS}::test_code_span_pads_only_a_span_that_touches_a_backtick",
    ),
    Mutant(
        "a description of exactly the minimum length is ok",
        VALIDATE_SUBMISSION,
        "if len(description) < MIN_DESCRIPTION:",
        "if len(description) <= MIN_DESCRIPTION:",
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_description_of_exactly_the_minimum_length_is_ok",
    ),
    Mutant(
        "a field the issue parser left as a list counts as empty",
        VALIDATE_SUBMISSION,
        'return value.strip() if isinstance(value, str) else ""',
        "return str(value).strip()",
        f"{VALIDATE_SUBMISSION_TESTS}::test_a_field_the_issue_parser_left_as_a_list_counts_as_empty",
    ),
    Mutant(
        "every form category maps to a catalog category",
        VALIDATE_SUBMISSION,
        '"Food": "food",',
        '"Food": "meals",',
        f"{VALIDATE_SUBMISSION_TESTS}::test_every_form_category_maps_to_a_catalog_category",
    ),
    Mutant(
        "the category labels are the ones the form offers",
        VALIDATE_SUBMISSION,
        '"Sports": "sports",',
        '"Sport": "sports",',
        f"{VALIDATE_SUBMISSION_TESTS}::test_every_form_category_maps_to_a_catalog_category",
    ),
    Mutant(
        "the report of a valid submission says it passed",
        VALIDATE_SUBMISSION,
        '"✅ passed" if result.ok',
        '"❌ needs changes" if result.ok',
        f"{VALIDATE_SUBMISSION_TESTS}::test_cli_writes_result_and_report_for_a_valid_submission",
    ),
    Mutant(
        "the report of an invalid submission says it needs changes",
        VALIDATE_SUBMISSION,
        'else "❌ needs changes"',
        'else "✅ passed"',
        f"{VALIDATE_SUBMISSION_TESTS}::test_cli_exits_1_and_explains_an_invalid_submission",
    ),
    Mutant(
        "the report's table has its separator row",
        VALIDATE_SUBMISSION,
        '        "| --- | --- | --- |",\n',
        "",
        f"{VALIDATE_SUBMISSION_TESTS}::test_cli_writes_result_and_report_for_a_valid_submission",
    ),
    Mutant(
        "a report with no warnings has no Warnings heading",
        VALIDATE_SUBMISSION,
        "if result.warnings:",
        "if True:",
        f"{VALIDATE_SUBMISSION_TESTS}::test_cli_writes_result_and_report_for_a_valid_submission",
    ),
    Mutant(
        "an unreachable site's report lists the same-site check as skipped",
        VALIDATE_SUBMISSION,
        '[str(site.unreachable)])\n        result.record("Same site", [], skipped=True)\n',
        "[str(site.unreachable)])\n",
        f"{VALIDATE_SUBMISSION_TESTS}::test_cli_marks_the_checks_an_unreachable_site_could_not_run_as_skipped",
    ),
    Mutant(
        "an unreachable site's report lists the page-title check as skipped",
        VALIDATE_SUBMISSION,
        'result.record("Page title", [], skipped=True)\n        return\n    result.record("Reachable", [])',
        'return\n    result.record("Reachable", [])',
        f"{VALIDATE_SUBMISSION_TESTS}::test_cli_marks_the_checks_an_unreachable_site_could_not_run_as_skipped",
    ),
    Mutant(
        "a skipped check says an earlier check failed",
        VALIDATE_SUBMISSION,
        '"skipped: an earlier check failed"',
        '"skipped"',
        f"{VALIDATE_SUBMISSION_TESTS}::test_cli_marks_the_checks_an_unreachable_site_could_not_run_as_skipped",
    ),
    Mutant(
        "non-ASCII text stays readable in the result file",
        VALIDATE_SUBMISSION,
        "json.dumps(output, indent=2, ensure_ascii=False)",
        "json.dumps(output, indent=2, ensure_ascii=True)",
        f"{VALIDATE_SUBMISSION_TESTS}::test_cli_keeps_non_ascii_text_readable_in_the_result_and_the_report",
    ),
    Mutant(
        "non-ASCII text stays readable in the report",
        VALIDATE_SUBMISSION,
        "json.dumps(result.entry, indent=2, ensure_ascii=False)",
        "json.dumps(result.entry, indent=2, ensure_ascii=True)",
        f"{VALIDATE_SUBMISSION_TESTS}::test_cli_keeps_non_ascii_text_readable_in_the_result_and_the_report",
    ),
    Mutant(
        "the result file has a two-space indent",
        VALIDATE_SUBMISSION,
        "json.dumps(output, indent=2,",
        "json.dumps(output, indent=4,",
        f"{VALIDATE_SUBMISSION_TESTS}::test_cli_writes_the_result_with_a_two_space_indent",
    ),
    Mutant(
        "nothing to change leaves the catalog's format alone",
        APPLY_LINK_STATUS,
        "if applied:",
        "if True:",
        f"{APPLY_LINK_STATUS_TESTS}::test_nothing_to_change_does_not_reformat_the_file",
    ),
    Mutant(
        "a plain 500 is retried like the other server errors",
        COLLECT,
        "response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR",
        "response.status_code > HTTPStatus.INTERNAL_SERVER_ERROR",
        f"{COLLECT_TESTS}::test_retries_once_on_a_server_error",
    ),
    Mutant(
        "a rank entry that is not an object is a malformed answer",
        COLLECT,
        '(item.get("date"), item.get("rank")) if isinstance(item, dict) else (None, None)',
        '(item.get("date"), item.get("rank"))',
        f"{COLLECT_TESTS}::test_malformed_body_marks_the_domain_failed",
    ),
    Mutant(
        "the top-ranked domain is a valid Tranco answer",
        COLLECT,
        "type(rank) is not int or rank < 1",
        "type(rank) is not int or rank <= 1",
        f"{COLLECT_TESTS}::test_the_top_ranked_domain_is_a_valid_answer",
    ),
    Mutant(
        "a Wikipedia item that is not an object is a malformed answer",
        COLLECT,
        "value = body.get(key) if isinstance(body, dict) else None",
        "value = body.get(key)",
        f"{COLLECT_TESTS}::test_wikipedia_malformed_body_is_a_failed_entry",
    ),
    Mutant(
        "a Radar answer that is not an object is a malformed answer",
        COLLECT,
        'if isinstance(body, dict) and body.get("success") is True else None',
        'if body.get("success") is True else None',
        f"{COLLECT_TESTS}::test_radar_malformed_body_is_a_failed_entry",
    ),
    Mutant(
        "a Radar answer without success is malformed even with a result",
        COLLECT,
        'if isinstance(body, dict) and body.get("success") is True else None',
        "if isinstance(body, dict) else None",
        f"{COLLECT_TESTS}::test_radar_malformed_body_is_a_failed_entry",
    ),
    Mutant(
        "a Radar bucket that is not a digit string is a malformed answer",
        COLLECT,
        "not (isinstance(bucket, str) and bucket.isdigit())",
        "not str(bucket).isdigit()",
        f"{COLLECT_TESTS}::test_radar_malformed_body_is_a_failed_entry",
    ),
    Mutant(
        "a boolean Radar rank is a malformed answer",
        COLLECT,
        "(isinstance(rank, bool) or not isinstance(rank, int | float) or rank < 1)",
        "(not isinstance(rank, int | float) or rank < 1)",
        f"{COLLECT_TESTS}::test_radar_malformed_body_is_a_failed_entry",
    ),
    Mutant(
        "a Radar rank of zero is a malformed answer",
        COLLECT,
        "int | float) or rank < 1)",
        "int | float) or rank < 0)",
        f"{COLLECT_TESTS}::test_radar_malformed_body_is_a_failed_entry",
    ),
    Mutant(
        "a Radar rank of one is a valid answer",
        COLLECT,
        "int | float) or rank < 1)",
        "int | float) or rank <= 1)",
        f"{COLLECT_TESTS}::test_radar_rank_one_is_a_valid_answer",
    ),
    Mutant(
        "the open issue is found by its marker after its title was edited",
        COMPLIANCE_ISSUE,
        'MARKER in (issue.get("body") or "") or bool(',
        "bool(",
        f"{COMPLIANCE_ISSUE_TESTS}::test_the_open_issue_is_found_by_its_marker_after_its_title_was_edited",
    ),
    Mutant(
        "a short report goes in the issue whole",
        COMPLIANCE_ISSUE,
        "if len(report) > room:",
        "if True:",
        f"{COMPLIANCE_ISSUE_TESTS}::test_a_short_report_goes_in_whole",
    ),
    Mutant(
        "a plain 200 from GitHub is accepted",
        COMPLIANCE_ISSUE,
        "if not http.HTTPStatus.OK <= response.status",
        "if not http.HTTPStatus.OK < response.status",
        f"{COMPLIANCE_ISSUE_TESTS}::test_github_api_accepts_a_plain_200",
    ),
    Mutant(
        "a weight of exactly zero is valid",
        COMPUTE,
        "not 0 <= weight <= 1",
        "not 0 < weight <= 1",
        f"{COMPUTE_TESTS}::test_a_weight_of_exactly_zero_or_one_is_valid",
    ),
    Mutant(
        "a weight of exactly one is valid",
        COMPUTE,
        "not 0 <= weight <= 1",
        "not 0 <= weight < 1",
        f"{COMPUTE_TESTS}::test_a_weight_of_exactly_zero_or_one_is_valid",
    ),
    Mutant(
        "the sixth most popular game can trend",
        COMPUTE,
        "TRENDING_EXCLUDES_TOP = 5",
        "TRENDING_EXCLUDES_TOP = 6",
        f"{COMPUTE_TESTS}::test_the_sixth_most_popular_game_can_trend",
    ),
    Mutant(
        "exactly the minimum of risers gets no backfill",
        COMPUTE,
        "TRENDING_MINIMUM = 3",
        "TRENDING_MINIMUM = 4",
        f"{COMPUTE_TESTS}::test_exactly_the_minimum_of_risers_gets_no_backfill",
    ),
    Mutant(
        "a failed domain with no history is not reported as carried forward",
        COMPUTE,
        'reasons[game_id] = "carried_forward" if prior else "score"',
        'reasons[game_id] = "carried_forward"',
        f"{COMPUTE_TESTS}::test_a_failed_domain_with_no_history_is_not_reported_as_carried_forward",
    ),
    Mutant(
        "the summary lists at most five risers",
        COMPUTE,
        "[mover(g) for g in up[:TOP_MOVERS]]",
        "[mover(g) for g in up]",
        f"{COMPUTE_TESTS}::test_summary_lists_at_most_five_movers_each_way",
    ),
    Mutant(
        "the written file is one Pages can serve",
        COMPUTE,
        "    temporary.chmod(0o644)\n",
        "",
        f"{COMPUTE_TESTS}::test_main_writes_a_file_pages_can_serve",
    ),
    Mutant(
        "the weights are read from beside the catalog by default",
        COMPUTE,
        'args.catalog.parent / "domain_weights.json"',
        'args.raw / "domain_weights.json"',
        f"{COMPUTE_TESTS}::test_main_reads_the_weights_beside_the_catalog_by_default",
    ),
    Mutant(
        "each path is in the FlatPark archive once",
        FLATPARK_PAYLOAD,
        "recursive=False",
        "recursive=True",
        f"{FLATPARK_PAYLOAD_TESTS}::test_each_path_is_in_the_archive_once",
    ),
    Mutant(
        "a hijacked game does not stop the games after it",
        LINK_STATUS,
        '_note(f"link check {week}: {seen.reason}")))\n            continue',
        '_note(f"link check {week}: {seen.reason}")))\n            break',
        f"{LINK_STATUS_TESTS}::test_a_hijacked_game_does_not_stop_the_games_after_it",
    ),
    Mutant(
        "a first failure does not stop the games after it",
        LINK_STATUS,
        "if since == week:\n            continue",
        "if since == week:\n            break",
        f"{LINK_STATUS_TESTS}::test_a_first_failure_does_not_stop_the_games_after_it",
    ),
    Mutant(
        "a note of exactly the longest length is kept whole",
        LINK_STATUS,
        "return text if len(text) <= MAX_NOTE else",
        "return text if len(text) < MAX_NOTE else",
        f"{LINK_STATUS_TESTS}::test_a_note_of_exactly_the_longest_length_is_kept_whole",
    ),
    Mutant(
        "a malformed week is refused",
        LINK_STATUS,
        r"-W(\d{2})$",
        r"-W?(\d{2})$",
        f"{LINK_STATUS_TESTS}::test_a_malformed_week_is_refused",
    ),
    Mutant(
        "a change already made does not stop the ones after it",
        LINK_STATUS,
        'if entry.get("status") == change.status:\n            continue',
        'if entry.get("status") == change.status:\n            break',
        f"{LINK_STATUS_TESTS}::test_a_change_already_made_does_not_stop_the_ones_after_it",
    ),
    Mutant(
        "the statuses are the ones the catalog schema allows",
        LINK_STATUS,
        'frozenset({"active", "broken", "retired"})',
        'frozenset({"active", "broken"})',
        f"{LINK_STATUS_TESTS}::test_statuses_are_the_ones_the_catalog_schema_allows",
    ),
    Mutant(
        "a change with a bad event changes nothing",
        LINK_STATUS,
        "if not EVENT.match(change.event) or len(change.note) > MAX_NOTE:",
        "if len(change.note) > MAX_NOTE:",
        f"{LINK_STATUS_TESTS}::test_a_change_with_a_bad_event_or_an_oversized_note_changes_nothing",
    ),
    Mutant(
        "a change with an oversized note changes nothing",
        LINK_STATUS,
        "if not EVENT.match(change.event) or len(change.note) > MAX_NOTE:",
        "if not EVENT.match(change.event):",
        f"{LINK_STATUS_TESTS}::test_a_change_with_a_bad_event_or_an_oversized_note_changes_nothing",
    ),
    Mutant(
        "a note of exactly the longest length is applied",
        LINK_STATUS,
        "or len(change.note) > MAX_NOTE:",
        "or len(change.note) >= MAX_NOTE:",
        f"{LINK_STATUS_TESTS}::test_a_note_of_exactly_the_longest_length_is_applied",
    ),
    Mutant(
        "a pipe in a game name is escaped",
        PR_BODY,
        r'.replace("|", "\\|")',
        '.replace("|", "/")',
        f"{PR_BODY_TESTS}::test_pipe_in_a_game_name_does_not_break_the_table",
    ),
    Mutant(
        "a newline in a game name stays on its table row",
        PR_BODY,
        r'.replace("\n", " ")',
        "",
        f"{PR_BODY_TESTS}::test_newline_in_a_game_name_stays_on_its_table_row",
    ),
    Mutant(
        "a body without a run URL ends the sentence with no link",
        PR_BODY,
        'f"{raw}: {run_url}" if run_url else f"{raw}."',
        'f"{raw}: {run_url}"',
        f"{PR_BODY_TESTS}::test_a_body_without_a_run_url_ends_the_sentence_with_no_link",
    ),
    Mutant(
        "meson.build without a project call is an error",
        RELEASE_CHECK,
        'PROJECT_VERSION.search(project["args"]) if project else None',
        'PROJECT_VERSION.search(project["args"])',
        f"{RELEASE_CHECK_TESTS}::test_meson_without_a_project_call_is_an_error",
    ),
    Mutant(
        "older release notes stay out of the newest release",
        RELEASE_CHECK,
        'self._state = "done"',
        'self._state = "release"',
        f"{RELEASE_CHECK_TESTS}::test_older_release_notes_stay_out_of_the_newest_release",
    ),
    Mutant(
        "verify tells the workflow a tag is a prerelease",
        RELEASE_CHECK,
        "{'true' if result.prerelease else 'false'}",
        "false",
        f"{RELEASE_CHECK_TESTS}::test_cli_verify_tells_the_workflow_a_tag_is_a_prerelease",
    ),
    Mutant(
        "the report link leaves non-ASCII text unescaped",
        REPORT_GUARD,
        "sort_keys=True, ensure_ascii=False",
        "sort_keys=True, ensure_ascii=True",
        f"{REPORT_GUARD_TESTS}::test_the_link_leaves_non_ascii_text_unescaped",
    ),
    Mutant(
        "check_pages.py reads the last commit of a file, not every commit's time (#435)",
        CHECK_PAGES,
        '"log", "-1", ',
        '"log", ',
        f"{CHECK_PAGES_TESTS}::test_last_commit_reads_the_committer_time_of_the_file",
    ),
    Mutant(
        "check_pages.py reads the last commit that touched the file, not the last commit (#435)",
        CHECK_PAGES,
        '"--format=%cI", "--", path]',
        '"--format=%cI"]',
        f"{CHECK_PAGES_TESTS}::test_last_commit_reads_the_committer_time_of_the_file",
    ),
    Mutant(
        "an age of one to two days reads in days (#435)",
        CHECK_PAGES,
        "if age.days >= 1:",
        "if age.days > 1:",
        f"{CHECK_PAGES_TESTS}::test_age_text_names_the_largest_whole_unit",
    ),
    Mutant(
        "one day is singular (#435)",
        CHECK_PAGES,
        "{'s' * (age.days != 1)}",
        "s",
        f"{CHECK_PAGES_TESTS}::test_age_text_names_the_largest_whole_unit",
    ),
    Mutant(
        "hours are plural (#435)",
        CHECK_PAGES,
        "{'s' * (hours != 1)}",
        "",
        f"{CHECK_PAGES_TESTS}::test_age_text_names_the_largest_whole_unit",
    ),
    Mutant(
        "one minute is singular (#435)",
        CHECK_PAGES,
        "{'s' * (minutes != 1)}",
        "s",
        f"{CHECK_PAGES_TESTS}::test_age_text_names_the_largest_whole_unit",
    ),
    Mutant(
        "a commit time git does not print is an error, not a traceback (#435)",
        CHECK_PAGES,
        "except (OSError, ValueError, subprocess.CalledProcessError)",
        "except (OSError, subprocess.CalledProcessError)",
        f"{CHECK_PAGES_TESTS}::test_a_commit_time_that_cannot_be_read_is_an_error",
    ),
    Mutant(
        "git missing from PATH is an error, not a traceback (#435)",
        CHECK_PAGES,
        "except (OSError, ValueError, subprocess.CalledProcessError)",
        "except (ValueError, subprocess.CalledProcessError)",
        f"{CHECK_PAGES_TESTS}::test_a_commit_time_that_cannot_be_read_is_an_error",
    ),
    Mutant(
        "the default clock is in UTC, as git's commit times carry an offset (#435)",
        CHECK_PAGES,
        "dt.datetime.now(dt.UTC)",
        "dt.datetime.now()",
        f"{CHECK_PAGES_TESTS}::test_the_defaults_compare_this_repository_against_the_clock_in_utc",
    ),
    Mutant(
        "the default --repo is the repository the script is in (#435)",
        CHECK_PAGES,
        "default=Path(__file__).resolve().parents[1]",
        "default=Path(__file__).resolve().parents[0]",
        f"{CHECK_PAGES_TESTS}::test_the_defaults_compare_this_repository_against_the_clock_in_utc",
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
