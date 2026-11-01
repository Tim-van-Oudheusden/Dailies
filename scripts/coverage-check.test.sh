#!/usr/bin/env bash
# Tests for coverage-check.sh and lib/coverage.sh: runs the gate against the Cobertura fixtures in
# tests/scripts/fixtures/coverage and checks each exit status (0 pass, 1 below a floor, 2 usage or parse error) and
# the message that explains it.
# Usage: scripts/coverage-check.test.sh (exits 1 if any case fails).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/coverage.sh
. "$ROOT/scripts/lib/coverage.sh"

check="$ROOT/scripts/coverage-check.sh"
fixtures="$ROOT/tests/scripts/fixtures/coverage"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
failures=0

ok() { echo "ok: $1"; }
not_ok() {
  echo "FAIL: $1"
  failures=$((failures + 1))
}

# A checkout holding the files pass.xml and below-floor.xml measured; reports are attributed to roots through it.
tree="$tmp/tree"
mkdir -p "$tree/dailies/core/search" "$tree/scripts/lib"
touch "$tree/dailies/core/__init__.py" "$tree/dailies/core/catalog.py" "$tree/dailies/core/search/__init__.py" \
  "$tree/dailies/core/search/fold.py" "$tree/scripts/validate.py" "$tree/scripts/lib/catalog_io.py"
empty="$tmp/empty"
mkdir -p "$empty"

# floors <name> <json>: writes a tuning config and prints its path.
floors() {
  printf '%s\n' "$2" >"$tmp/$1.json"
  echo "$tmp/$1.json"
}
config="$(floors default '{"margin": 2, "floors": {"core": {"lines": 70, "branches": 50}, "scripts": {"lines": 70, "branches": 50}}}')"

# report <name> <xml>: writes a report and prints its path.
report() {
  printf '%s\n' "$2" >"$tmp/$1.xml"
  echo "$tmp/$1.xml"
}

# expect <status> <description> <coverage-root> <expected output, or ''> <coverage-check.sh arguments...>
expect() {
  local want="$1" description="$2" root="$3" pattern="$4" got output
  shift 4
  output="$(COVERAGE_ROOT="$root" bash "$check" "$@" 2>&1)"
  got=$?
  if [ "$got" != "$want" ]; then
    not_ok "$description (expected exit $want, got $got): $output"
  elif [ -n "$pattern" ] && ! grep -qF -- "$pattern" <<<"$output"; then
    not_ok "$description (output lacks '$pattern'): $output"
  else
    ok "$description"
  fi
}

# counters_are <description> <coverage-root> <report> <group> <expected counters>
counters_are() {
  local got
  got="$(COVERAGE_ROOT="$2" coverage_counters "$3" "$4" 2>&1)"
  if [ "$got" = "$5" ]; then
    ok "$1"
  else
    not_ok "$1 (expected '$5', got '$got')"
  fi
}

# Aggregation: counts are summed over every package of a group, including files of both roots in package ".".
counters_are 'core counters summed across packages' "$tree" "$fixtures/pass.xml" core '2 8 1 3'
counters_are 'scripts counters summed across packages' "$tree" "$fixtures/pass.xml" scripts '2 6 2 2'
counters_are 'single-root report needs no checkout' "$empty" "$fixtures/core-only.xml" core '1 3 1 1'
counters_are 'group missing from the report has no lines' "$empty" "$fixtures/core-only.xml" scripts '0 0 0 0'

# Pass.
expect 0 'pass.xml meets the floors' "$tree" 'Coverage (core): lines 80.00% (floor 70%), branches 75.00% (floor 50%)' \
  "$fixtures/pass.xml" "$config"
expect 0 'coverage exactly at a floor passes' "$tree" \
  'Coverage (scripts): lines 75.00% (floor 70%), branches 50.00% (floor 50%)' "$fixtures/pass.xml" "$config"
expect 0 'fractional floor met' "$tree" '' "$fixtures/pass.xml" \
  "$(floors fractional '{"margin": 2, "floors": {"core": {"lines": 79.99, "branches": 75}}}')"
expect 0 'group absent from the report has no code yet' "$empty" 'Coverage (scripts): no code yet' \
  "$fixtures/core-only.xml" "$config"
expect 0 'report without files: every group has no code yet' "$empty" 'Coverage (core): no code yet' \
  "$(report no-files '<?xml version="1.0" ?><coverage lines-valid="0" lines-covered="0"><sources/><packages/></coverage>')" \
  "$config"
expect 0 'no report and no Python anywhere (the scaffold)' "$empty" 'Coverage (scripts): no code yet (no report' \
  "$tmp/missing.xml" "$config"
shell_only="$tmp/shell-only"
mkdir -p "$shell_only/scripts/lib"
touch "$shell_only/scripts/coverage-check.sh" "$shell_only/scripts/lib/coverage.sh"
expect 0 'no report and only shell scripts' "$shell_only" 'Coverage (core): no code yet' "$tmp/missing.xml" "$config"
expect 2 'Python under a root but no measured lines (a root missing from coverage source)' "$tree" \
  'scripts has Python files but no measured lines; is it in [tool.coverage.run] source in pyproject.toml?' \
  "$fixtures/core-only.xml" "$config"

# Fail: below a floor, naming the group and the floor.
expect 1 'scripts lines below the floor' "$tree" '::error::scripts lines coverage 50.00% is below its floor of 70%' \
  "$fixtures/below-floor.xml" "$config"
expect 1 'core branches below the floor' "$tree" '::error::core branches coverage 25.00% is below its floor of 50%' \
  "$fixtures/below-floor.xml" "$config"
expect 1 'just above the coverage is below' "$tree" '::error::core lines coverage 80.00% is below its floor of 80.01%' \
  "$fixtures/pass.xml" "$(floors strict '{"margin": 2, "floors": {"core": {"lines": 80.01, "branches": 50}}}')"
expect 1 'a 100% floor is not met by 75%' "$empty" '::error::core lines coverage 75.00% is below its floor of 100%' \
  "$fixtures/core-only.xml" "$(floors full '{"margin": 0, "floors": {"core": {"lines": 100, "branches": 0}}}')"

# Malformed or unusable report.
expect 2 'truncated XML' "$tree" 'not readable as XML' "$fixtures/malformed.xml" "$config"
expect 2 'empty file' "$tree" 'not readable as XML' "$(report blank '')" "$config"
expect 2 'JaCoCo report instead of Cobertura' "$tree" "not Cobertura's <coverage>" \
  "$(report jacoco '<report name="core"><counter type="LINE" missed="1" covered="3"/></report>')" "$config"
expect 2 'non-numeric hits' "$tree" "has hits='x'" \
  "$(report bad-hits "$(sed 's/<line number="7" hits="0"/<line number="7" hits="x"/' "$fixtures/pass.xml")")" "$config"
expect 2 'branch line without counts' "$tree" 'branch without condition-coverage counts' \
  "$(report bad-branch "$(sed 's/ condition-coverage="100% (2\/2)"//' "$fixtures/pass.xml")")" "$config"
expect 2 'files but no source roots' "$tree" 'no <sources> roots' \
  "$(report no-sources "$(sed '/<source>/d' "$fixtures/pass.xml")")" "$config"
expect 2 'file not in this checkout' "$empty" 'is under none of the <source> roots' "$fixtures/pass.xml" "$config"
ambiguous="$tmp/ambiguous"
cp -R "$tree" "$ambiguous"
touch "$ambiguous/scripts/__init__.py"
expect 2 'file under both roots' "$ambiguous" 'exists under several <source> roots' "$fixtures/pass.xml" "$config"
expect 2 'no report although there is Python code' "$tree" 'No coverage report at' "$tmp/missing.xml" "$config"

# Usage and config errors.
expect 2 'no arguments' "$tree" 'usage: coverage-check.sh'
expect 2 'one argument' "$tree" 'usage: coverage-check.sh' "$fixtures/pass.xml"
expect 2 'missing config' "$tree" 'No tuning config' "$fixtures/pass.xml" "$tmp/missing.json"
expect 2 'config is not JSON' "$tree" 'Malformed' "$fixtures/pass.xml" "$(floors not-json 'margin: 2')"
expect 2 'floor above 100' "$tree" 'Malformed' "$fixtures/pass.xml" \
  "$(floors over '{"margin": 2, "floors": {"core": {"lines": 120, "branches": 50}}}')"
expect 2 'floor without branches (functions/lines contract)' "$tree" 'Malformed' "$fixtures/pass.xml" \
  "$(floors kover '{"margin": 2, "floors": {"core": {"functions": 70, "lines": 70}}}')"
expect 2 'negative margin' "$tree" 'Malformed' "$fixtures/pass.xml" \
  "$(floors margin '{"margin": -1, "floors": {"core": {"lines": 70, "branches": 50}}}')"
expect 2 'no groups' "$tree" 'Malformed' "$fixtures/pass.xml" "$(floors none '{"margin": 2, "floors": {}}')"
expect 2 'unknown group' "$tree" "Unknown coverage group 'app' in $tmp/app.json; known groups: core, scripts" \
  "$fixtures/pass.xml" "$(floors app '{"margin": 2, "floors": {"app": {"lines": 70, "branches": 50}}}')"

# The repository's own config is valid and every group in it is known (whatever the tuner has raised the floors to).
expect 0 'repository config is valid' "$empty" 'no code yet' "$tmp/no-files.xml" "$ROOT/.github/auto-qa-tuning.json"

if [ "$failures" -ne 0 ]; then
  echo "$failures case(s) failed"
  exit 1
fi
echo 'all cases passed'
