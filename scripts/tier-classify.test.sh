#!/usr/bin/env bash
# Tests for tier-classify.sh: the policy engine against throwaway policies (first matching rule wins, unmatched paths
# are medium, the highest tier wins, malformed policies exit 2), then the shipped .github/policies/risk-tiers.policy
# against paths of this repository.
# Usage: scripts/tier-classify.test.sh (exits 1 if any case fails).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
classify="$ROOT/scripts/tier-classify.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
failures=0

ok() { echo "ok: $1"; }
not_ok() {
  echo "FAIL: $1"
  failures=$((failures + 1))
}

# policy <name> <content>: writes a policy file and prints its path.
policy() {
  printf '%s' "$2" >"$tmp/$1.policy"
  echo "$tmp/$1.policy"
}

# expect <description> <policy file, or '' for the shipped one> <changed paths> <expected stdout>
expect() {
  local output status
  if [ -n "$2" ]; then
    output="$(printf '%s' "$3" | RISK_TIER_POLICY="$2" bash "$classify" 2>&1)"
  else
    output="$(printf '%s' "$3" | env -u RISK_TIER_POLICY bash "$classify" 2>&1)"
  fi
  status=$?
  if [ "$status" -ne 0 ]; then
    not_ok "$1 (exit $status): $output"
  elif [ "$output" != "$4" ]; then
    not_ok "$1 (expected:"$'\n'"$4"$'\n'"got:"$'\n'"$output)"
  else
    ok "$1"
  fi
}

# tier_of <description> <path> <tier>: the shipped policy gives one changed path this tier.
tier_of() {
  expect "$1" '' "$2" "$(printf '%-6s  %s\ntier=%s' "$3" "$2" "$3")"
}

# rejects <description> <policy file> <expected stderr fragment>: exit 2, no tier printed.
rejects() {
  local output status
  output="$(printf 'docs/a.md\n' | RISK_TIER_POLICY="$2" bash "$classify" 2>&1)"
  status=$?
  if [ "$status" -ne 2 ]; then
    not_ok "$1 (expected exit 2, got $status): $output"
  elif grep -q '^tier=' <<<"$output"; then
    not_ok "$1 (printed a tier): $output"
  elif ! grep -qF -- "$3" <<<"$output"; then
    not_ok "$1 (output lacks '$3'): $output"
  else
    ok "$1"
  fi
}

# Engine.
rules="$(policy rules $'# comment\n\nhigh    a/special.txt\nlow     a/*\nhigh    *.cfg\n')"
expect 'first matching rule wins (high before broad low)' "$rules" 'a/special.txt' $'high    a/special.txt\ntier=high'
expect 'later rule applies when the earlier does not match' "$rules" 'a/other.txt' $'low     a/other.txt\ntier=low'
expect 'first match wins even over a later higher rule' "$rules" 'a/x.cfg' $'low     a/x.cfg\ntier=low'
expect '* matches across /' "$rules" 'b/c/d.cfg' $'high    b/c/d.cfg\ntier=high'
expect 'a path matching no rule is medium' "$rules" 'b/unknown.txt' $'medium  b/unknown.txt\ntier=medium'
expect 'highest tier of any file wins' "$rules" $'a/one.txt\nb/x.cfg\na/two.txt\n' \
  $'low     a/one.txt\nhigh    b/x.cfg\nlow     a/two.txt\ntier=high'
expect 'medium beats low' "$rules" $'a/one.txt\nb/new.txt\n' $'low     a/one.txt\nmedium  b/new.txt\ntier=medium'
expect 'no changed paths is low' "$rules" '' 'tier=low'
expect 'blank input lines are skipped' "$rules" $'\na/one.txt\n\n' $'low     a/one.txt\ntier=low'
expect 'last path without a trailing newline' "$rules" $'a/one.txt\nx.cfg' $'low     a/one.txt\nhigh    x.cfg\ntier=high'
expect 'policy with CRLF line endings' "$(policy crlf $'# c\r\nlow docs/*\r\n')" 'docs/a.md' \
  $'low     docs/a.md\ntier=low'
expect 'policy without a trailing newline' "$(policy no-eol 'high docs/*')" 'docs/a.md' $'high    docs/a.md\ntier=high'
rejects 'missing policy file' "$tmp/missing.policy" 'cannot read policy file'
rejects 'unknown tier' "$(policy unknown $'critical docs/*\n')" "unknown tier 'critical'"
rejects 'rule without a glob' "$(policy no-glob $'high\n')" "expected '<tier> <glob>'"
rejects 'rule with an extra field' "$(policy extra $'low docs/* now\n')" "expected '<tier> <glob>'"

# The shipped policy (.github/policies/risk-tiers.policy).
tier_of 'Flatpak manifest is high' 'build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.Devel.json' high
tier_of 'Flatpak lint exceptions are high' 'build-aux/flatpak/lint-exceptions.json' high
tier_of 'workflow is high' '.github/workflows/ci.yml' high
tier_of 'the policy itself is high' '.github/policies/risk-tiers.policy' high
tier_of 'PR template (Markdown under .github) is high' '.github/pull_request_template.md' high
tier_of 'gate script is high' 'scripts/tier-classify.sh' high
tier_of 'popularity pipeline is high' 'scripts/popularity/compute.py' high
tier_of 'meson.build is high' 'meson.build' high
tier_of 'meson_options.txt is high' 'meson_options.txt' high
tier_of 'metainfo is high' 'data/io.github.tim_van_oudheusden.Dailies.metainfo.xml.in' high
tier_of 'GSettings schema is high' 'data/io.github.tim_van_oudheusden.Dailies.gschema.xml.in' high
tier_of 'catalog schema is high' 'data/v1/schema/catalog.schema.json' high
tier_of 'AGENTS.md is high although *.md is low' 'AGENTS.md' high
tier_of 'CLAUDE.md is high' 'CLAUDE.md' high
tier_of 'Claude settings are high' '.claude/settings.json' high
tier_of 'Cursor rules are high' '.cursor/rules/agent-guidance.mdc' high
tier_of 'prompts are high' 'prompts/code-review.md' high
tier_of 'app code is medium' 'dailies/core/catalog.py' medium
tier_of 'catalog data is medium' 'data/v1/games.json' medium
tier_of 'tests are unmatched, so medium' 'tests/core/test_catalog.py' medium
tier_of 'Blueprint file is unmatched, so medium' 'data/ui/window.blp' medium
tier_of 'desktop file is unmatched, so medium' 'data/io.github.tim_van_oudheusden.Dailies.desktop.in' medium
tier_of 'pyproject.toml is unmatched, so medium' 'pyproject.toml' medium
tier_of 'docs are low' 'docs/architecture.md' low
tier_of 'README.md is low' 'README.md' low
tier_of 'nested Markdown outside high paths is low' 'tests/README.md' low
expect 'a manifest change makes a docs PR high' '' $'docs/testing.md\nbuild-aux/flatpak/lint-exceptions.json\n' \
  $'low     docs/testing.md\nhigh    build-aux/flatpak/lint-exceptions.json\ntier=high'

if [ "$failures" -ne 0 ]; then
  echo "$failures case(s) failed"
  exit 1
fi
echo 'all cases passed'
