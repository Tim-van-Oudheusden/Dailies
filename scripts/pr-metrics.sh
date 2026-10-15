#!/usr/bin/env bash
# PR acceptance metric: of the pull requests closed in the reporting window,
# how many were merged vs. closed without merging, split by agent-authored vs.
# other PRs. Reads the JSON of `gh pr list --json number,mergedAt,headRefName,author`
# on stdin and prints a Markdown table.
#
# usage: pr-metrics.sh --since YYYY-MM-DD --days N
# Agent-authored: head branch claude/* or author hive-forge-app (gh pr list reports
# a GitHub App as app/<slug>, the REST API as <slug>[bot]; both are accepted).
set -uo pipefail

since=""
days=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --since) since="${2:-}"; shift 2 ;;
    --days) days="${2:-}"; shift 2 ;;
    *) echo "usage: $0 --since YYYY-MM-DD --days N" >&2; exit 2 ;;
  esac
done
if [ -z "$since" ] || [ -z "$days" ]; then
  echo "usage: $0 --since YYYY-MM-DD --days N" >&2
  exit 2
fi

jq -r --arg since "$since" --arg days "$days" '
  def agent: ((.headRefName // "") | startswith("claude/"))
    or ((.author.login // "") | IN("app/hive-forge-app", "hive-forge-app[bot]"));
  def row($label; $set):
    ($set | length) as $total
    | ($set | map(select(.mergedAt != null)) | length) as $merged
    | "| \($label) | \($total) | \($merged) | \($total - $merged) | "
      + (if $total == 0 then "n/a"
         else "\(($merged * 1000 / $total | round) / 10)%" end)
      + " |";
  if type != "array" then error("expected a JSON array of pull requests") else . end
  | map(select(agent)) as $agent
  | map(select(agent | not)) as $other
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
    "Agent: head branch `claude/*` or author `hive-forge-app` (GitHub App)."
'
