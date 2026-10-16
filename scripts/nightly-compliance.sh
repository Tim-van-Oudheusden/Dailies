#!/usr/bin/env bash
# Print a Markdown nightly compliance report for the repository to stdout.
#
# Usage:
#   scripts/nightly-compliance.sh [--force-links] > nightly-compliance.md
#
# Checks that can go stale without a code change, so they run on a schedule
# (.github/workflows/nightly-compliance.yml) rather than only on push:
#   1. Dependabot alerts (high+): no open high or critical Dependabot alert,
#      except those in ALERTS_IGNORE below. Alerts come from
#      `gh api repos/$GITHUB_REPOSITORY/dependabot/alerts` (needs a token that
#      can read Dependabot alerts), or from the JSON array in the file named by
#      ALERTS_JSON when set.
#   2. Script dependencies (pip-audit): no known vulnerability in the
#      hash-pinned scripts/requirements.txt, except those in AUDIT_IGNORE
#      below. Needs pip-audit on PATH (it is pinned in that same file).
#   3. GNOME runtime support: `flatpak remote-info flathub <ref>` for the
#      runtime the app targets shows no End-of-life line. The ref is
#      RUNTIME_REF, default org.gnome.Platform//51; bump it together with
#      runtime-version in the Flatpak manifests. Needs the flathub remote.
#   4. ACMM codebase level: scripts/acmm-self-check.py finds the files Hive's
#      ACMM evaluation looks for, up to level ACMM_MIN_LEVEL (default 5).
#   5. External data checker image: scripts/check_checker_digest.py compares
#      the flatpak-external-data-checker digest pinned in
#      .github/workflows/external-data-checker.yml with the image's current
#      :latest on ghcr.io (anonymous). Dependabot does not update docker://
#      references, so drift fails this row; so does an unreachable ghcr.io.
#      CHECKER_DIGEST replaces the script; the tests use it.
#   6. Catalog links, Sundays (UTC) only, or any day with --force-links or
#      DAILIES_FORCE_LINKS=1: scripts/check_links.py checks every active
#      entry of data/v1/games.json with the submission validator's rules. In
#      GitHub Actions (GITHUB_ACTIONS=true) a failure also opens, or updates,
#      the one `data: N broken links (week W)` issue (needs GH_TOKEN with
#      issues: write). CHECK_LINKS replaces the script; the tests use it.
# Diagnostics go to stderr and to a Failures section in the report, so stdout
# stays a clean report. Every check runs even when an earlier one fails; the
# script exits non-zero if any failed, and 2 on a usage error. Needs jq and
# python3.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit

# Advisories accepted after review, one id per line with the reason and the
# date to revisit. Remove an entry once a fix ships and the lock picks it up.
# The ALERTS_IGNORE and AUDIT_IGNORE environment variables (space-separated
# ids) replace these lists; the tests use them.
# Dependabot alerts, by GHSA id:
#   (none yet)
DEFAULT_ALERTS_IGNORE=()
# pip-audit findings, by the id it prints (PYSEC-…, GHSA-… or CVE-…):
#   (none yet)
DEFAULT_AUDIT_IGNORE=()

commit="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"
runtime_ref="${RUNTIME_REF:-org.gnome.Platform//51}"
acmm_min_level="${ACMM_MIN_LEVEL:-5}"
failed=0
details=""
force_links="${DAILIES_FORCE_LINKS:-0}"

for arg in "$@"; do
  case "$arg" in
    --force-links) force_links=1 ;;
    *)
      echo "usage: nightly-compliance.sh [--force-links]" >&2
      exit 2
      ;;
  esac
done

row() {
  if [ "$2" -eq 0 ]; then
    echo "| $1 | ✅ pass |"
  else
    echo "| $1 | ❌ fail |"
    failed=1
  fi
}

# Appends a titled block of command output to the Failures section.
detail_block() {
  details+="### $1"$'\n\n''```text'$'\n'"$2"$'\n''```'$'\n\n'
}

# Prints the open Dependabot alerts as one JSON array on stdout.
read_alerts() {
  if [ -n "${ALERTS_JSON:-}" ]; then
    cat "$ALERTS_JSON"
    return
  fi
  local repo="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null)}"
  # --paginate prints one array per page; jq -s merges them.
  gh api --paginate "repos/${repo}/dependabot/alerts?state=open&per_page=100" | jq -s 'add // []'
}

if [ -n "${ALERTS_IGNORE+set}" ]; then
  read -ra alerts_ignore <<<"$ALERTS_IGNORE"
else
  alerts_ignore=("${DEFAULT_ALERTS_IGNORE[@]}")
fi
if [ -n "${AUDIT_IGNORE+set}" ]; then
  read -ra audit_ignore <<<"$AUDIT_IGNORE"
else
  audit_ignore=("${DEFAULT_AUDIT_IGNORE[@]}")
fi

echo "# Nightly compliance"
echo
echo "Commit: \`${commit}\`"
echo
echo "| Check | Result |"
echo "| ----- | ------ |"

# 1. Dependabot alerts.
alerts_check=1
if alerts="$(read_alerts)" && jq -e 'type == "array"' >/dev/null 2>&1 <<<"$alerts"; then
  blocking="$(jq -r --args '
    $ARGS.positional as $ignore
    | .[]
    | select(.state == "open")
    | select(.security_advisory.severity == "high" or .security_advisory.severity == "critical")
    | select(.security_advisory.ghsa_id as $id | $ignore | index($id) | not)
    | "- \(.security_advisory.ghsa_id) (\(.security_advisory.severity)) \(.dependency.package.name): \(.security_advisory.summary) \(.html_url)"
  ' "${alerts_ignore[@]}" <<<"$alerts")" && {
    if [ -z "$blocking" ]; then
      alerts_check=0
    else
      echo "Open high/critical Dependabot alerts:" >&2
      echo "$blocking" >&2
      details+="${blocking}"$'\n\n'
    fi
  }
else
  echo "Could not read Dependabot alerts (needs a token with Dependabot alerts read access): ${alerts:-no output}" >&2
  details+="- Dependabot alerts: could not read the alerts API; see the job log"$'\n\n'
fi
row "Dependabot alerts (high+)" "$alerts_check"

# 2. pip-audit on the CI scripts' lock. Every requirement is pinned and hashed, so pip-audit
# reads the versions straight from the file (--disable-pip) instead of resolving them.
audit_args=(--strict --disable-pip --progress-spinner off -r scripts/requirements.txt)
for id in "${audit_ignore[@]}"; do
  audit_args+=(--ignore-vuln "$id")
done
audit_out="$(pip-audit "${audit_args[@]}" 2>&1)"
audit_check=$?
if [ "$audit_check" -ne 0 ]; then
  echo "pip-audit failed:" >&2
  echo "$audit_out" >&2
  detail_block "pip-audit scripts/requirements.txt" "$audit_out"
fi
row "Script dependencies (pip-audit)" "$audit_check"

# 3. GNOME runtime end-of-life. C locale: the field names in the output are translated.
runtime_check=1
if runtime_out="$(LC_ALL=C flatpak remote-info flathub "$runtime_ref" 2>&1)"; then
  if grep -qi 'end-of-life' <<<"$runtime_out"; then
    echo "${runtime_ref} is end-of-life on Flathub:" >&2
    echo "$runtime_out" >&2
    detail_block "${runtime_ref} is end-of-life; move the manifests to a supported runtime" \
      "$(grep -i 'end-of-life' <<<"$runtime_out")"
  else
    runtime_check=0
  fi
else
  echo "Could not read ${runtime_ref} from the flathub remote:" >&2
  echo "$runtime_out" >&2
  detail_block "flatpak remote-info flathub ${runtime_ref} failed" "$runtime_out"
fi
row "GNOME runtime supported (${runtime_ref})" "$runtime_check"

# 4. ACMM codebase level, from the criteria list vendored in the script.
acmm_out="$(python3 scripts/acmm-self-check.py --min-level "$acmm_min_level" 2>&1)"
acmm_check=$?
if [ "$acmm_check" -ne 0 ]; then
  echo "$acmm_out" >&2
  details+="### ACMM self-check"$'\n\n'"${acmm_out}"$'\n\n'
fi
row "ACMM codebase level (L${acmm_min_level}+)" "$acmm_check"

# 5. The flatpak-external-data-checker image digest against the image's current :latest.
digest_out="$(python3 -I "${CHECKER_DIGEST:-scripts/check_checker_digest.py}" 2>&1)"
digest_check=$?
if [ "$digest_check" -ne 0 ]; then
  echo "$digest_out" >&2
  detail_block "flatpak-external-data-checker image digest" "$digest_out"
fi
row "External data checker image is :latest" "$digest_check"

# 6. Catalog links, weekly: every active catalog entry, with the submission validator's rules.
if [ "$force_links" = 1 ] || [ "$(date -u +%u)" = 7 ]; then
  links_md="$(mktemp)"
  links_args=(--catalog data/v1/games.json --out "$links_md")
  if [ "${GITHUB_ACTIONS:-}" = true ]; then
    links_args+=(--open-issue)
  fi
  # -I: ignore PYTHON* variables and the user site; the script finds scripts/lib by its own path.
  links_out="$(python3 -I "${CHECK_LINKS:-scripts/check_links.py}" "${links_args[@]}" 2>&1)"
  links_check=$?
  if [ "$links_check" -ne 0 ]; then
    echo "$links_out" >&2
    if [ -s "$links_md" ]; then
      details+="$(cat "$links_md")"$'\n\n'
    else
      detail_block "scripts/check_links.py failed" "$links_out"
    fi
  fi
  rm -f "$links_md"
  row "Catalog links (weekly)" "$links_check"
fi

if [ -n "$details" ]; then
  echo
  echo "## Failures"
  echo
  printf '%s' "$details"
fi

exit "$failed"
