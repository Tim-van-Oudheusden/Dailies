#!/usr/bin/env bash
# PR acceptance metric: of the pull requests closed in the reporting window,
# how many were merged vs. closed without merging, split by agent-authored vs.
# other PRs. Reads the JSON of `gh pr list --json number,mergedAt,headRefName,author,body`
# on stdin and prints a Markdown table.
#
# usage: pr-metrics.sh --since YYYY-MM-DD --days N
# Agent-authored: the sources Hive and Claude Code (CI) of scripts/lib/pr-source.jq.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "usage: $0 --since YYYY-MM-DD --days N" >&2
  exit 2
}

since=""
days=""
while [ "$#" -gt 0 ]; do
  # A flag must have its value: `shift 2` with one argument left shifts nothing and the loop would never end.
  case "$1" in
    --since) [ "$#" -ge 2 ] || usage; since="$2"; shift 2 ;;
    --days) [ "$#" -ge 2 ] || usage; days="$2"; shift 2 ;;
    *) usage ;;
  esac
done
if [ -z "$since" ] || [ -z "$days" ]; then
  usage
fi

jq -r -L "$HERE/lib" --arg since "$since" --arg days "$days" '
  include "pr-source";
  def row($label; $set):
    ($set | length) as $total
    | ($set | map(select(.mergedAt != null)) | length) as $merged
    | "| \($label) | \($total) | \($merged) | \($total - $merged) | "
      + (if $total == 0 then "n/a"
         else "\(($merged * 1000 / $total | round) / 10)%" end)
      + " |";
  if type != "array" then error("expected a JSON array of pull requests") else . end
  | map(select(agent_authored)) as $agent
  | map(select(agent_authored | not)) as $other
  | "## PR acceptance metric",
    "",
    "PRs closed since \($since) (last \($days) days).",
    "",
    "| Source | Closed | Merged | Rejected | Acceptance |",
    "| --- | ---: | ---: | ---: | ---: |",
    row("Agent"; $agent),
    row("Other"; $other),
    row("**All**"; .),
    "",
    "Agent: head branch `claude/*`, author `hive-worker-bee` (GitHub App, formerly `hive-forge-app`), or a Hive signature in the PR body."
'
