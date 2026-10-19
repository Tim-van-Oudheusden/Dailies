#!/usr/bin/env bash
# Popularity report metric: how well the weekly popularity.yml pipeline runs
# without the maintainer. Reads three files and prints a Markdown table:
#
#   --runs FILE   JSON of `gh run list --workflow popularity.yml --json conclusion`
#   --prs FILE    JSON of `gh pr list --state merged --head data/popularity --json commits`
#   --weeks FILE  one `generated_at<TAB>valid_until` line per commit of data/v1/popularity.json, oldest first
#
# usage: popularity-report.sh --runs FILE --prs FILE --weeks FILE
# Cancelled, skipped and unfinished runs are not counted. A week is stale when its
# file was generated after the previous file's valid_until had passed.
set -uo pipefail

usage() {
  echo "usage: $0 --runs FILE --prs FILE --weeks FILE" >&2
  exit 2
}

runs=""
prs=""
weeks=""
while [ "$#" -gt 0 ]; do
  # A flag must have its value: `shift 2` with one argument left shifts nothing and the loop would never end.
  case "$1" in
    --runs) [ "$#" -ge 2 ] || usage; runs="$2"; shift 2 ;;
    --prs) [ "$#" -ge 2 ] || usage; prs="$2"; shift 2 ;;
    --weeks) [ "$#" -ge 2 ] || usage; weeks="$2"; shift 2 ;;
    *) usage ;;
  esac
done
if [ -z "$runs" ] || [ -z "$prs" ] || [ -z "$weeks" ]; then
  usage
fi

rate() {
  # rate PART TOTAL: a percentage with one decimal, or n/a when there is nothing to divide by.
  if [ "$2" -eq 0 ]; then
    echo "n/a"
  else
    awk -v p="$1" -v t="$2" 'BEGIN { r = int(p * 1000 / t + 0.5) / 10; print r "%" }'
  fi
}

run_counts="$(jq -r '
  if type != "array" then error("--runs: expected a JSON array of workflow runs") else . end
  | map(select((.conclusion // "") | IN("", "cancelled", "skipped") | not))
  | "\(map(select(.conclusion == "success")) | length) \(length)"
' "$runs")" || exit 1
read -r succeeded finished <<<"$run_counts"

pr_counts="$(jq -r '
  if type != "array" then error("--prs: expected a JSON array of pull requests") else . end
  | map(.commits | length)
  | "\(map(select(. == 1)) | length) \(map(select(. > 1)) | length)"
' "$prs")" || exit 1
read -r unchanged edited <<<"$pr_counts"

# The timestamps are compared as strings, which orders them correctly only in the one UTC form compute.py writes;
# anything else (an offset, fractional seconds) would compare wrongly, so it fails instead.
week_counts="$(awk -F '\t' '
  function utc(s) { return s ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z$/ }
  NF == 0 { next }
  !(NF == 2 && utc($1) && utc($2)) {
    printf "--weeks line %d: expected generated_at<TAB>valid_until as YYYY-MM-DDTHH:MM:SSZ, got \"%s\"\n", NR, $0 > "/dev/stderr"
    bad = 1
    exit 1
  }
  files > 0 && $1 > expiry { stale++ }
  { files++; expiry = $2 }
  END { if (!bad) print stale + 0, (files > 0 ? files - 1 : 0) }
' "$weeks")" || exit 1
read -r stale handovers <<<"$week_counts"

cat <<EOF
## Popularity report

| Measure | Count | Rate |
| --- | ---: | ---: |
| Runs succeeded, of finished runs | $succeeded of $finished | $(rate "$succeeded" "$finished") |
| Stale weeks, of week-to-week handovers | $stale of $handovers | $(rate "$stale" "$handovers") |
| Data PRs merged unchanged, of merged | $unchanged of $((unchanged + edited)) | $(rate "$unchanged" "$((unchanged + edited))") |

Cancelled and skipped runs are not counted. A stale week's shelves had expired before the next run replaced them. A
merged data PR with more than its one workflow commit was edited by the maintainer.
EOF
