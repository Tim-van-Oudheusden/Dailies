#!/usr/bin/env bash
# Print a Markdown quality report for the repository to stdout.
#
# Usage:
#   scripts/quality-report.sh > quality-report.md
#
# Runs every gate of CI's `Build, lint, test` job separately (`ruff check .`, `ruff format --check .`, `pytest`, and
# `check-jsonschema` on each data file in data/v1 against its schema), then one coverage run,
# `pytest --cov=dailies/core --cov=scripts --cov-report=xml`, whose Cobertura report gives the line and branch coverage
# of every module (floor group) in .github/auto-qa-tuning.json, and reports pass/fail per gate and the coverage per
# module. Tool output goes to stderr so stdout stays a clean report. Every gate and the coverage run happen even when
# an earlier one fails; a failed coverage run, or one that leaves no report, reports n/a. A module with no measured
# lines reports "no code yet", and one with lines but no branches reports "no branches" for them; neither is a failure.
# The coverage floors themselves are enforced by scripts/coverage-check.sh, and scripts/auto-qa-tuner.sh reads the
# coverage rows printed here.
#
# Environment: $QA_TUNING_CONFIG replaces the floors file, $COVERAGE_XML the path the coverage report is written to
# (default coverage.xml at the repository root), $COVERAGE_ROOT the root the report's files are looked up under (see
# scripts/lib/coverage.sh); $GITHUB_SHA names the commit. The tools are taken from PATH.
#
# Exit status: 0 when everything passed, 1 when a gate or the coverage run failed, 2 when the floors file lists no
# module.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/coverage.sh
. "$ROOT/scripts/lib/coverage.sh"
cd "$ROOT" || exit 2

config="${QA_TUNING_CONFIG:-$ROOT/.github/auto-qa-tuning.json}"
report="${COVERAGE_XML:-$ROOT/coverage.xml}"

if ! modules="$(jq -er '.floors | keys[]' "$config" 2>/dev/null)"; then
  echo "No modules in $config: expected {\"floors\": {\"<module>\": {...}}}" >&2
  exit 2
fi

commit="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"
failed=0

# gate <command...>: runs one gate and prints its row, labelled with the command.
gate() {
  local result
  if "$@" >&2; then
    result="✅ pass"
  else
    result="❌ fail"
    failed=1
  fi
  echo "| \`$*\` | ${result} |"
}

echo "# Quality report"
echo
echo "Commit: \`${commit}\`"
echo
echo "## Quality gates"
echo
echo "| Gate | Result |"
echo "| ---- | ------ |"
gate ruff check .
gate ruff format --check .
gate pytest
gate check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json
gate check-jsonschema --schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json

echo
echo "## Unit-test coverage"
echo
echo "| Module | Lines | Branches |"
echo "| ------ | ----- | -------- |"
# A report left by an earlier run must not stand in for this run's.
rm -f "$report"
measured=0
if pytest --cov=dailies/core --cov=scripts "--cov-report=xml:$report" >&2 && [ -f "$report" ]; then
  measured=1
fi
for module in $modules; do
  counters=""
  if [ "$measured" -eq 1 ]; then
    counters="$(coverage_counters "$report" "$module")" || counters=""
  fi
  # A failed run makes its numbers meaningless: report n/a rather than a partial measurement.
  if [ -z "$counters" ]; then
    echo "| ${module} | ❌ n/a | ❌ n/a |"
    failed=1
    continue
  fi
  read -r lines_missed lines_covered branches_missed branches_covered <<<"$counters"
  # 0 of 0 is not 100%: with nothing measured there is no number for the tuner to raise a floor to.
  if [ "$((lines_missed + lines_covered))" -eq 0 ]; then
    echo "| ${module} | no code yet | no code yet |"
    continue
  fi
  lines="$(coverage_percent "$lines_missed" "$lines_covered")%"
  if [ "$((branches_missed + branches_covered))" -eq 0 ]; then
    branches="no branches"
  else
    branches="$(coverage_percent "$branches_missed" "$branches_covered")%"
  fi
  echo "| ${module} | ${lines} | ${branches} |"
done

exit "$failed"
