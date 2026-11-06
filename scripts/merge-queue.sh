#!/usr/bin/env bash
# Merge queue for main: merges ready pull requests one at a time, each after
# re-running the Build, lint, test gate on top of the latest main. Driven by
# .github/workflows/merge-queue.yml; see docs/multi-agent.md#merge-queue.
#
# Usage:
#   scripts/merge-queue.sh next
#       From a full-history checkout of main: pick the oldest pull request that
#       is ready to merge and write number=, head= and main= to $GITHUB_OUTPUT.
#       Writes nothing when none is ready.
#   scripts/merge-queue.sh land <number> <head-sha> <verified-main-sha>
#       Merge the pull request at <head-sha> if main is still the commit it was
#       verified on and the pull request is still ready, close the issues it
#       links, then start main's push workflows (a merge made with GITHUB_TOKEN
#       starts none) and the next run. Fails, after starting the others, if one
#       of them would not start.
#   scripts/merge-queue.sh reject <number> <run-url>
#       Hold a pull request that failed verification, link the run, move on.
#
# Ready means: from this repository (not a fork), not a draft, none of the
# KEEP_OUT_LABELS, merge state CLEAN (no failing check, required or not, so
# UNSTABLE stays out; review threads resolved), and not high risk by
# scripts/tier-classify.sh: high-risk changes wait for the maintainer.
# Needs gh authenticated (GH_TOKEN) and pointed at the repository (GH_REPO, or
# run from a checkout).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Labels that keep a pull request out of the queue; reject adds the first.
#   hold           the maintainer's stop sign, and what reject sets
#   blocked        waiting on something outside this repository
#   sentinel-alert Hive's flag on a sensitive change; a maintainer removes it
#   automated      opened by a workflow: the weekly popularity pull request
#                  merges itself, catalog and link-status ones are merged by the
#                  maintainer (#79)
# merge-queue.yml restates them in its concurrency group and pick job, and
# tests/tooling/test_merge_queue_workflow.py fails when either list differs
# from this one.
KEEP_OUT_LABELS=(hold blocked sentinel-alert automated)
HOLD_LABEL="${KEEP_OUT_LABELS[0]}"
# jq test that a pull request carries no label that keeps it out.
UNHELD="all(.labels[]; $(printf '.name != "%s" and ' "${KEEP_OUT_LABELS[@]}")true)"
# Every workflow that runs on a push to main (release.yml runs on tags only);
# each needs a workflow_dispatch trigger, which tests/scripts/test_merge_queue.py
# checks against the workflows' own triggers.
MAIN_PUSH_WORKFLOWS=(ci.yml coverage-gate.yml pages.yml quality-report.yml windows.yml)

# GitHub's workflow dispatch answers HTTP 500 now and then, so one failure is
# not final. The last failure names the workflow and how to start it by hand.
start_workflow() {
  local attempt
  for attempt in 1 2 3; do
    gh workflow run "$1" --ref main && return 0
    [ "$attempt" -lt 3 ] && sleep 10
  done
  echo "::error title=Merge queue::could not start $1; start it by hand: gh workflow run $1 --ref main"
  return 1
}

# Picks up runs that land, reject or skip a pull request, so each merge is
# verified against the main it lands on.
queue_next_run() {
  start_workflow merge-queue.yml
}

# GitHub computes the merge state lazily and answers UNKNOWN until it has.
merge_state() {
  local state attempt
  for attempt in 1 2 3; do
    state="$(gh pr view "$1" --json mergeStateStatus --jq .mergeStateStatus)"
    [ "$state" != UNKNOWN ] && break
    [ "$attempt" -lt 3 ] && sleep 5
  done
  echo "$state"
}

# Prints the risk tier of the change from main to <sha>, as tier-classifier.yml
# rates it: renames listed under their old path too.
tier_of() {
  git diff -z --name-only --no-renames "HEAD...$1" | "$HERE/tier-classify.sh" -z | sed -n 's/^tier=//p'
}

# GitHub does not act on `Fixes #N` when GITHUB_TOKEN merges a pull request,
# so close the issues it links ourselves. By URL, so a link to another
# repository closes that issue, not this repository's issue with the same
# number. The merge has landed by now: failing to read the links or to close
# an issue is a warning, not a reason to skip main's workflows or the next run.
# The links are read into a variable first: bash drops the exit status of a
# `< <(...)` process, so a failed lookup would look like a PR that links none.
close_linked_issues() {
  local number="$1" issues issue
  if ! issues="$(gh pr view "$number" --json closingIssuesReferences --jq '.closingIssuesReferences[].url')"; then
    echo "::warning title=Merge queue::could not read the issues #${number} closes; close them by hand"
    return 0
  fi
  while read -r issue; do
    [ -n "$issue" ] || continue
    gh issue close "$issue" --reason completed \
      --comment "Closed by #${number}, which the merge queue merged." \
      || echo "::warning title=Merge queue::could not close ${issue} after merging #${number}"
  done <<< "$issues"
}

next() {
  local candidates number head tier
  # gh lists open pull requests by default; --jq runs gh's built-in jq, so the
  # runner needs no jq. Listed into a variable so a failed listing fails the
  # job (set -e) instead of passing for an empty queue. gh lists newest first,
  # so the limit sits far above the number of pull requests ever open at once.
  candidates="$(gh pr list --base main --limit 1000 \
    --json number,headRefOid,isDraft,isCrossRepository,labels \
    --jq "sort_by(.number) | .[]
      | select((.isDraft or .isCrossRepository) | not)
      | select(${UNHELD})
      | \"\\(.number) \\(.headRefOid)\"")"
  while read -r number head; do
    # An empty listing still reads one empty line.
    [ -n "$number" ] || continue
    [ "$(merge_state "$number")" = CLEAN ] || continue
    git fetch --no-tags --quiet origin "refs/pull/${number}/head"
    # A push since the listing: the run its checks start sees it.
    [ "$(git rev-parse FETCH_HEAD)" = "$head" ] || continue
    tier="$(tier_of "$head")"
    if [ "$tier" = high ]; then
      echo "::notice title=Merge queue::#${number} is high risk (docs/risk-tiers.md); the maintainer merges it"
      continue
    fi
    {
      echo "number=${number}"
      echo "head=${head}"
      echo "main=$(git rev-parse HEAD)"
    } >> "$GITHUB_OUTPUT"
    return 0
  done <<< "$candidates"
}

land() {
  local number="$1" head="$2" verified_main="$3" main ready workflow failed=0
  main="$(git ls-remote origin refs/heads/main | cut -f1)"
  if [ "$main" != "$verified_main" ]; then
    echo "::notice title=Merge queue::main moved since #${number} was verified; verifying again"
    queue_next_run
    return 0
  fi

  ready="$(gh pr view "$number" --json isDraft,labels --jq "(.isDraft | not) and ${UNHELD}")"
  if [ "$ready" != true ] || [ "$(merge_state "$number")" != CLEAN ]; then
    echo "::notice title=Merge queue::#${number} stopped being ready during verification; skipped"
    queue_next_run
    return 0
  fi

  # --match-head-commit refuses the merge if the branch moved past what was verified.
  gh pr merge "$number" --merge --match-head-commit "$head"
  close_linked_issues "$number"
  # The merge has landed, so a workflow that will not start must not stop the
  # others or the next run. The run still fails: a gate that never ran on main
  # leaves no other trace, unlike an issue left open.
  for workflow in "${MAIN_PUSH_WORKFLOWS[@]}"; do
    start_workflow "$workflow" || failed=1
  done
  queue_next_run || failed=1
  return "$failed"
}

reject() {
  local number="$1" run_url="$2"
  gh pr edit "$number" --add-label "$HOLD_LABEL"
  gh pr comment "$number" --body "The merge queue held this pull request: the Build, lint, test gate failed on it merged with the latest main (${run_url}). Fix it and remove the \`${HOLD_LABEL}\` label to queue it again."
  queue_next_run
}

usage() {
  echo "usage: $0 next | land <number> <head-sha> <verified-main-sha> | reject <number> <run-url>" >&2
  exit 2
}

case "${1:-}" in
  next) [ "$#" -eq 1 ] || usage; next ;;
  land) [ "$#" -eq 4 ] || usage; land "$2" "$3" "$4" ;;
  reject) [ "$#" -eq 3 ] || usage; reject "$2" "$3" ;;
  *) usage ;;
esac
