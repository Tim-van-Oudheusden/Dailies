#!/usr/bin/env bash
# AI audit trail: every pull request merged into main since a date, attributed to
# its source (a Hive agent and model, Claude Code in CI, Dependabot, or other),
# with who opened it and who merged it. Reads the JSON of
# `gh pr list --state merged --json number,title,author,headRefName,mergedAt,mergedBy,body`
# on stdin and prints a Markdown report.
#
# usage: ai-audit-report.sh --since YYYY-MM-DD
# scripts/lib/pr-source.jq defines the sources.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "usage: $0 --since YYYY-MM-DD" >&2
  exit 2
}

since=""
while [ "$#" -gt 0 ]; do
  # A flag must have its value: `shift 2` with one argument left shifts nothing and the loop would never end.
  case "$1" in
    --since) [ "$#" -ge 2 ] || usage; since="$2"; shift 2 ;;
    *) usage ;;
  esac
done
# mergedAt is compared as text, which orders correctly only against a YYYY-MM-DD date.
[[ "$since" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || usage

jq -r -L "$HERE/lib" --arg since "$since" '
  include "pr-source";
  def none: "—";
  def fields($line):
    if $line == null then {}
    else [$line | scan("([A-Za-z_]+)=([^ ]+)")] | map({(.[0]): .[1]}) | add // {} end;
  def attribution:
    fields(signature) as $sig
    | {source: source, agent: ($sig.agent // none), model: ($sig.model // none)};
  # Escapes | so text from a PR cannot add or shift table columns.
  def cell: tostring | split("|") | join("\\|");

  if type != "array" then error("expected a JSON array of pull requests") else . end
  | map(select(.mergedAt != null and .mergedAt >= $since) | . + {attribution: attribution})
  | sort_by(.mergedAt, .number) as $merged
  | "# AI audit trail",
    "",
    "Pull requests merged into `main` since \($since) (UTC).",
    "",
    "## By source",
    "",
    "| Source | Merged PRs |",
    "| --- | ---: |",
    (sources[] as $source | "| \($source) | \($merged | map(select(.attribution.source == $source)) | length) |"),
    "| **All** | \($merged | length) |",
    "",
    "## Merged by",
    "",
    "| Account | Merged PRs |",
    "| --- | ---: |",
    # Most merges first; a merge with no recorded merger is listed last so it stands out.
    ($merged
      | group_by(.mergedBy.login)
      | map({account: .[0].mergedBy.login, count: length})
      | sort_by((.account == null), -.count, .account)[]
      | "| \(if .account == null then "Unknown (no merger recorded)" else (.account | cell) end) | \(.count) |"),
    "",
    "## Ledger",
    "",
    "| PR | Merged (UTC) | Source | Agent | Model | Author | Merged by | Branch | Title |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ($merged[]
      | "| #\(.number) | \(.mergedAt[0:10]) \(.mergedAt[11:16]) | \(.attribution.source)"
        + " | \(.attribution.agent | cell) | \(.attribution.model | cell) | \(.author.login // none | cell)"
        + " | \(.mergedBy.login // none | cell) | `\(.headRefName | cell)` | \(.title | cell) |")
'
