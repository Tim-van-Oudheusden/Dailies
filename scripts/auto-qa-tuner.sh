#!/usr/bin/env bash
# Self-tune the unit-test coverage floors from observed coverage.
#
# Usage:
#   scripts/auto-qa-tuner.sh [--config <path>] [--report <path>] [--write]
#
# Reads the floors from the tuning config (default .github/auto-qa-tuning.json) and the observed coverage from a
# scripts/quality-report.sh report (default quality-report.md), then prints a Markdown table proposing, per module and
# metric (lines, branches), the floor raised to the observed coverage minus the config's margin, rounded down to a
# whole percent. Floors are never lowered, and a metric without an observed percentage (its run failed: n/a; or there
# was nothing to measure: no code yet, no branches) keeps its floor. Coverage exactly at floor + margin proposes no
# change. With --write the proposed floors are saved back to the config.
#
# Exit status: 0 on success, 2 for bad arguments, a missing report, or a malformed config.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  echo "usage: auto-qa-tuner.sh [--config <path>] [--report <path>] [--write]" >&2
  exit 2
}

config="$ROOT/.github/auto-qa-tuning.json"
report="quality-report.md"
write=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --config)
      [ "$#" -ge 2 ] || usage
      config="$2"
      shift 2
      ;;
    --report)
      [ "$#" -ge 2 ] || usage
      report="$2"
      shift 2
      ;;
    --write)
      write=1
      shift
      ;;
    *) usage ;;
  esac
done

if [ ! -f "$report" ]; then
  echo "No quality report at $report; run scripts/quality-report.sh > $report first" >&2
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
  echo "Malformed $config: expected {\"margin\": N, \"floors\": {\"<module>\": {\"lines\": N, \"branches\": N}}}" \
    "with percentages between 0 and 100" >&2
  exit 2
fi

# Coverage rows look like `| core | 97.50% | 93.10% |` (module, lines, branches). A cell without a percentage (a
# failed run's `❌ n/a`, `no code yet`, `no branches`) leaves that metric unobserved.
# Proposals are computed in hundredths and rounded before flooring, so float error (70.1 - 0.1 = 69.999...) cannot
# drop a value below a whole percent. Only the proposal is rounded down, never the current floor, so a fractional floor
# (79.99) is kept rather than lowered to 79.
tune="$(
  cat <<'JQ'
def percent: capture("^(?<value>[0-9]+(\\.[0-9]+)?)%$").value? // null;
($report | split("\n")
  | map(capture("^\\| (?<module>\\S+) \\| (?<lines>[^|]*\\S) \\| (?<branches>[^|]*\\S) \\|$")
    | {key: .module, value: {lines: (.lines | percent), branches: (.branches | percent)}})
  | from_entries) as $observed
| .margin as $margin
| [.floors | to_entries[] | .key as $module | .value as $floors | ("lines", "branches") as $metric
    | $floors[$metric] as $floor
    | $observed[$module][$metric] as $seen
    | {
        module: $module,
        metric: $metric,
        floor: $floor,
        observed: $seen,
        proposed: (if $seen == null then $floor
          else [$floor, (((($seen | tonumber) - $margin) * 100 | round) / 100 | floor)] | max end)
      }] as $rows
| {rows: $rows, config: (reduce $rows[] as $r (.; .floors[$r.module][$r.metric] = $r.proposed))}
JQ
)"
if ! tuned="$(jq --rawfile report "$report" "$tune" "$config")"; then
  echo "Could not tune $config from $report" >&2
  exit 2
fi

jq -r '
  "## Coverage floor tuning",
  "",
  "Margin: \(.config.margin) percentage points below observed coverage.",
  "",
  "| Module | Metric | Floor | Observed | Proposed |",
  "| ------ | ------ | ----- | -------- | -------- |",
  (.rows[] | "| \(.module) | \(.metric) | \(.floor)% | \(if .observed == null then "n/a" else "\(.observed)%" end)"
    + " | \(.proposed)%\(if .proposed > .floor then " ⬆️" else "" end) |")
' <<<"$tuned"

if [ "$write" -eq 1 ]; then
  # Keys and their order are kept; only the floors change.
  if ! jq '.config' <<<"$tuned" >"$config"; then
    echo "Could not write $config" >&2
    exit 2
  fi
  echo "Wrote the proposed floors to $config" >&2
fi
