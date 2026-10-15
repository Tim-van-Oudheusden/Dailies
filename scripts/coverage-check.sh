#!/usr/bin/env bash
# Enforce the unit-test coverage floors.
#
# Usage:
#   scripts/coverage-check.sh <coverage.xml> <tuning.json>
#
# Reads the Cobertura XML that `pytest --cov=dailies/core --cov=scripts --cov-report=xml` writes and the floors from
# the tuning config (.github/auto-qa-tuning.json: {"margin": N, "floors": {"<group>": {"lines": N, "branches": N}}}),
# and fails if any group's line or branch coverage is below its floor, in percent. Groups map to measured roots in
# scripts/lib/coverage.sh: `core` is dailies/core, `scripts` is scripts. The margin is only read by the floor tuner.
#
# No code yet: a group with no measured lines (its root is absent, holds no Python, or is not in the report) passes
# and is reported as "no code yet"; its floors apply from the first measured line. When there is no Python at all
# under any group's root, coverage.py writes no report, and a missing report then passes the same way. A missing
# report while Python code exists is an error. A group with lines but no branches has 100% branch coverage.
#
# Exit status: 0 when every group is at or above both floors (or has no code yet), 1 when a group is below a floor,
# 2 for bad arguments, a malformed config, an unknown group, or a missing, unreadable or malformed report.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/coverage.sh
. "$ROOT/scripts/lib/coverage.sh"

if [ "$#" -ne 2 ]; then
  echo "usage: coverage-check.sh <coverage.xml> <tuning.json>" >&2
  exit 2
fi
report="$1"
config="$2"

if ! command -v jq >/dev/null; then
  echo "coverage-check.sh needs jq" >&2
  exit 2
fi
if [ ! -f "$config" ]; then
  echo "No tuning config at $config" >&2
  exit 2
fi

# A floor is a percentage; the margin is a non-negative number of percentage points.
valid='
  def percent: type == "number" and . >= 0 and . <= 100;
  (.margin | type == "number" and . >= 0)
  and (.floors | type == "object" and length > 0
    and all(.[]; type == "object" and (.lines | percent) and (.branches | percent)))
'
if ! jq -e "$valid" "$config" >/dev/null 2>&1; then
  echo "Malformed $config: expected {\"margin\": N, \"floors\": {\"<group>\": {\"lines\": N, \"branches\": N}}}" \
    "with percentages between 0 and 100" >&2
  exit 2
fi
groups="$(jq -r '.floors | keys[]' "$config")"
for group in $groups; do
  if ! coverage_group_dir "$group" >/dev/null; then
    echo "Unknown coverage group '$group' in $config; known groups: core, scripts" >&2
    exit 2
  fi
done

# has_python <group>: whether the group's root holds any Python file.
has_python() {
  local dir
  dir="${COVERAGE_ROOT:-$ROOT}/$(coverage_group_dir "$1")"
  [ -d "$dir" ] && [ -n "$(find "$dir" -name '*.py' -print -quit)" ]
}

if [ ! -f "$report" ]; then
  for group in $groups; do
    if has_python "$group"; then
      echo "No coverage report at $report, but $(coverage_group_dir "$group") has Python code;" \
        "run pytest --cov=dailies/core --cov=scripts --cov-report=xml first" >&2
      exit 2
    fi
  done
  for group in $groups; do
    echo "Coverage ($group): no code yet (no report, and no Python under $(coverage_group_dir "$group"))"
  done
  exit 0
fi

# Compare the exact ratio: a rounded 100.00% may still be below a 100% floor.
meets() {
  awk -v m="$1" -v c="$2" -v f="$3" 'BEGIN { exit !(c * 100 >= f * (m + c)) }'
}

failed=0
for group in $groups; do
  floor_lines="$(jq -r --arg g "$group" '.floors[$g].lines' "$config")"
  floor_branches="$(jq -r --arg g "$group" '.floors[$g].branches' "$config")"
  if ! counters="$(coverage_counters "$report" "$group")"; then
    exit 2
  fi
  read -r lines_missed lines_covered branches_missed branches_covered <<<"$counters"

  if [ "$((lines_missed + lines_covered))" -eq 0 ]; then
    echo "Coverage ($group): no code yet (no measured lines under $(coverage_group_dir "$group"));" \
      "floors lines ${floor_lines}%, branches ${floor_branches}% apply once it has code"
    continue
  fi

  lines="$(coverage_percent "$lines_missed" "$lines_covered")"
  branches="$(coverage_percent "$branches_missed" "$branches_covered")"
  echo "Coverage ($group): lines ${lines}% (floor ${floor_lines}%), branches ${branches}% (floor ${floor_branches}%)"
  if ! meets "$lines_missed" "$lines_covered" "$floor_lines"; then
    echo "::error::$group lines coverage ${lines}% is below its floor of ${floor_lines}%" >&2
    failed=1
  fi
  if ! meets "$branches_missed" "$branches_covered" "$floor_branches"; then
    echo "::error::$group branches coverage ${branches}% is below its floor of ${floor_branches}%" >&2
    failed=1
  fi
done
exit "$failed"
