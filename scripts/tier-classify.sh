#!/usr/bin/env bash
# Change classification: reads changed file paths (one per line) on stdin,
# prints each path with its risk tier, then the PR's overall tier as
# `tier=<low|medium|high>`. The highest tier of any changed file wins.
#
# With -z, paths are NUL-terminated, as `git diff -z --name-only` prints them.
# Without -z, git C-quotes any path holding non-ASCII, `"`, `\` or a control
# character (`"d\303\251ploy.yml"`); a line in exactly that form is decoded
# back to the path before it is matched, so the quoted path is not left to
# match no rule. A path holding a control character is printed %q-quoted, so
# a newline in a file name cannot forge a `tier=` line. Any other argument
# exits 2.
#
# Per-path tiers come from the risk assessment .github/risk-assessment.yml
# (RISK_TIER_POLICY overrides the path): the first rule whose glob matches a
# path sets its tier, and unrecognised paths are medium. The file is YAML, read
# here as a strict line subset: `rules:`, then one `- <tier> <glob>` item per
# line, plus blank and whole-line `#` comment lines. A missing or malformed
# file exits 2 without printing a tier. Tiers are explained in
# docs/risk-tiers.md.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
policy="${RISK_TIER_POLICY:-$ROOT/.github/risk-assessment.yml}"

names=(_ low medium high)
declare -A tier_rank=([low]=1 [medium]=2 [high]=3)

fail() {
  echo "tier-classify: $*" >&2
  exit 2
}

delim=$'\n'
case "$*" in
  "") ;;
  -z) delim='' ;;
  *) fail "usage: tier-classify.sh [-z] < paths" ;;
esac

[ -r "$policy" ] || fail "cannot read risk assessment file ${policy}"

rule_ranks=()
rule_globs=()
in_rules=
lineno=0
# CR counts as whitespace, so a file saved with CRLF line endings still parses.
while IFS=$' \t\r' read -r item tier glob extra || [ -n "${item:-}" ]; do
  lineno=$((lineno + 1))
  [ -z "${item:-}" ] || [[ $item == \#* ]] && continue
  if [ "$item" = rules: ] && [ -z "${tier:-}" ] && [ -z "$in_rules" ]; then
    in_rules=1
    continue
  fi
  [ -n "$in_rules" ] && [ "$item" = - ] && [ -n "${glob:-}" ] && [ -z "${extra:-}" ] \
    || fail "${policy}:${lineno}: expected one 'rules:' line, then '- <tier> <glob>' items"
  [ -n "${tier_rank[$tier]:-}" ] \
    || fail "${policy}:${lineno}: unknown tier '${tier}' (expected low, medium or high)"
  rule_ranks+=("${tier_rank[$tier]}")
  rule_globs+=("$glob")
done < "$policy"

# A git C-quoted path: `"`, then plain bytes and the escapes git writes
# (\" \\ \a \b \t \n \v \f \r and three-digit octal), then `"`.
git_quoted='^"(([^"\\]|\\[abtnvfr"\\]|\\[0-3][0-7][0-7])*)"$'

max=1
while IFS= read -r -d "$delim" path || [ -n "$path" ]; do
  [ -n "$path" ] || continue
  if [ -n "$delim" ] && [[ $path =~ $git_quoted ]]; then
    # printf's format decodes exactly these escapes; %% keeps a literal %.
    # shellcheck disable=SC2059
    printf -v path -- "${BASH_REMATCH[1]//%/%%}"
  fi
  r=2
  for i in "${!rule_globs[@]}"; do
    # Unquoted right-hand side: the rule is a glob pattern, not a literal.
    # shellcheck disable=SC2053
    if [[ $path == ${rule_globs[i]} ]]; then
      r="${rule_ranks[i]}"
      break
    fi
  done
  shown="$path"
  [[ $path == *[[:cntrl:]]* ]] && printf -v shown '%q' "$path"
  printf '%-6s  %s\n' "${names[$r]}" "$shown"
  [ "$r" -gt "$max" ] && max="$r"
done

echo "tier=${names[$max]}"
