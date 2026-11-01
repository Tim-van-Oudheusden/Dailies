#!/usr/bin/env bash
# Strategy report: where the project is heading rather than how one change
# fared. Prints four Markdown tables: issue and PR flow since a date, the open
# backlog per pipeline stage (Hive's stage/* labels), the open backlog per
# milestone (milestone::* labels) and the ACMM maturity gaps per level.
#
# usage: strategy-report.sh --since YYYY-MM-DD --issues FILE --prs FILE
# --issues is the JSON of `gh issue list --state all --json
# number,title,state,labels,createdAt,closedAt`; --prs that of `gh pr list
# --state merged --json mergedAt`. The window runs from <since> (UTC midnight)
# to now. Exits 2 on bad usage, 1 when an input cannot be read.
set -uo pipefail

usage() {
  echo "usage: $0 --since YYYY-MM-DD --issues FILE --prs FILE" >&2
  exit 2
}

since=""
issues=""
prs=""
while [ "$#" -gt 0 ]; do
  # A flag must have its value: `shift 2` with one argument left shifts nothing and the loop would never end.
  case "$1" in
    --since) [ "$#" -ge 2 ] || usage; since="$2"; shift 2 ;;
    --issues) [ "$#" -ge 2 ] || usage; issues="$2"; shift 2 ;;
    --prs) [ "$#" -ge 2 ] || usage; prs="$2"; shift 2 ;;
    *) usage ;;
  esac
done
if [ -z "$since" ] || [ -z "$issues" ] || [ -z "$prs" ]; then
  usage
fi
for input in "$issues" "$prs"; do
  if [ ! -r "$input" ]; then
    echo "strategy-report: cannot read $input" >&2
    exit 1
  fi
done

# gh prints UTC timestamps (2026-10-01T08:00:00Z), which order as strings, so
# a timestamp is in the window when it sorts at or after the bare date.
jq -nr --arg since "$since" --slurpfile issues "$issues" --slurpfile prs "$prs" '
  def list($what): if type != "array" then error("expected a JSON array of \($what)") else . end;
  def inwindow: . != null and . >= $since;
  def signed: if . > 0 then "+\(.)" else "\(.)" end;
  def cell: gsub("\\|"; "\\|");
  # Open issues per label with the given prefix, in name order, then those without one.
  def backlog($open; $prefix; $none):
    ($open | map(.labels[].name | select(startswith($prefix))) | group_by(.)[] | "| \(.[0]) | \(length) |"),
    "| \($none) | \($open | map(select(all(.labels[]; .name | startswith($prefix) | not))) | length) |";
  ($issues[0] | list("issues")) as $all
  | ($prs[0] | list("pull requests")) as $merged
  | ($all | map(select(.state == "OPEN"))) as $open
  | ($all | map(select(.createdAt | inwindow)) | length) as $opened
  | ($all | map(select(.closedAt | inwindow)) | length) as $closed
  # The Hive ACMM evaluation files one `acmm` issue per missing criterion,
  # titled "[ACMM L<level>] Add <criterion>" (the dashboard prepends
  # "[dashboard] "); the PR that fills the gap closes it.
  | ($all
      | map(select(any(.labels[]; .name == "acmm"))
        | . as $issue
        | .title
        | capture("\\[ACMM L(?<level>[0-9]+)\\] (?:Add )?(?<criterion>.+)$")
        | {level: (.level | tonumber), criterion, number: $issue.number, state: $issue.state})
      | group_by(.level)) as $acmm
  | "# Strategy report",
    "",
    "Since \($since).",
    "",
    "## Flow",
    "",
    "| Measure | Count |",
    "| --- | ---: |",
    "| Issues opened | \($opened) |",
    "| Issues closed | \($closed) |",
    "| Net backlog change | \($opened - $closed | signed) |",
    "| PRs merged | \($merged | map(select(.mergedAt | inwindow)) | length) |",
    "| Open issues now | \($open | length) |",
    "",
    "## Backlog by stage",
    "",
    "| Stage | Open issues |",
    "| --- | ---: |",
    # Stage labels carry a numeric prefix (stage/010-actionable), so name order is pipeline order.
    backlog($open; "stage/"; "No stage"),
    "",
    "## Backlog by milestone",
    "",
    "| Milestone | Open issues |",
    "| --- | ---: |",
    backlog($open; "milestone::"; "No milestone"),
    "",
    "## ACMM progress",
    "",
    "Gap issues the Hive ACMM evaluation filed, per maturity level.",
    "",
    "| Level | Closed gaps | Open gaps | Still open |",
    "| --- | ---: | ---: | --- |",
    ($acmm[]
      | (map(select(.state == "OPEN")) | sort_by(.number)) as $gaps
      | "| L\(.[0].level) | \(length - ($gaps | length)) | \($gaps | length) | "
        + (if $gaps == [] then "—" else $gaps | map("#\(.number) \(.criterion | cell)") | join(", ") end)
        + " |")
'
