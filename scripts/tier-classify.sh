#!/usr/bin/env bash
# Change classification: reads changed file paths (one per line) on stdin,
# prints each path with its risk tier, then the PR's overall tier as
# `tier=<low|medium|high>`. The highest tier of any changed file wins.
#
# Per-path tiers come from the policy file .github/policies/risk-tiers.policy
# (RISK_TIER_POLICY overrides the path): the first rule whose glob matches a
# path sets its tier, and unrecognised paths are medium. A missing or malformed
# policy exits 2 without printing a tier. Tiers are explained in
# docs/risk-tiers.md.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
policy="${RISK_TIER_POLICY:-$ROOT/.github/policies/risk-tiers.policy}"

names=(_ low medium high)
declare -A tier_rank=([low]=1 [medium]=2 [high]=3)

fail() {
  echo "tier-classify: $*" >&2
  exit 2
}

[ -r "$policy" ] || fail "cannot read policy file ${policy}"

rule_ranks=()
rule_globs=()
lineno=0
# CR counts as whitespace, so a policy saved with CRLF line endings still parses.
while IFS=$' \t\r' read -r tier glob extra || [ -n "${tier:-}" ]; do
  lineno=$((lineno + 1))
  [ -z "${tier:-}" ] || [[ $tier == \#* ]] && continue
  [ -n "${glob:-}" ] && [ -z "${extra:-}" ] \
    || fail "${policy}:${lineno}: expected '<tier> <glob>'"
  [ -n "${tier_rank[$tier]:-}" ] \
    || fail "${policy}:${lineno}: unknown tier '${tier}' (expected low, medium or high)"
  rule_ranks+=("${tier_rank[$tier]}")
  rule_globs+=("$glob")
done < "$policy"

max=1
while IFS= read -r path || [ -n "$path" ]; do
  [ -n "$path" ] || continue
  r=2
  for i in "${!rule_globs[@]}"; do
    # Unquoted right-hand side: the rule is a glob pattern, not a literal.
    # shellcheck disable=SC2053
    if [[ $path == ${rule_globs[i]} ]]; then
      r="${rule_ranks[i]}"
      break
    fi
  done
  printf '%-6s  %s\n' "${names[$r]}" "$path"
  [ "$r" -gt "$max" ] && max="$r"
done

echo "tier=${names[$max]}"
