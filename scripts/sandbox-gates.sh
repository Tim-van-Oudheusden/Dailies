#!/usr/bin/env bash
# Runs every quality gate except the Flatpak build, the way CI runs it, then prints one PASS/FAIL line per gate.
# Made for the agent sandbox (Dockerfile.sandbox, started by scripts/sandbox.sh), whose root filesystem is the GNOME 51
# SDK; it works on any host with the same tools on PATH. docs/testing.md#agent-sandbox-what-runs-where says why the
# Flatpak build is left out.
#
#   scripts/sandbox-gates.sh
#
# Gates: `ruff check .`, `ruff format --check .`, `pytest` with coverage and then the coverage floors
# (scripts/coverage-check.sh), `check-jsonschema` on both data files, `shellcheck -x` on scripts/, `actionlint`, and
# the Meson build: setup, install into a throwaway prefix and `meson test`. Installing first is what
# `flatpak-builder --run-tests` does too, so the e2e smoke test runs against the installed app instead of skipping.
# Every gate runs even when an earlier one fails. The build directory, the prefix and the coverage report live in a
# temporary directory that is removed on exit.
#
# Environment: $COVERAGE_CHECK replaces scripts/coverage-check.sh (the tests use it).
#
# Exit status: 0 when every gate passed, 1 when any failed.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

summary=()
failed=0
label=""

# begin <label> prints a gate's heading; end <status> records the exit status of the gate's command under that label.
begin() {
  label="$1"
  echo "==> $label"
}
end() {
  if [ "$1" -eq 0 ]; then
    summary+=("PASS  $label")
  else
    summary+=("FAIL  $label")
    failed=1
  fi
}

begin "ruff check ."
ruff check .
end "$?"

begin "ruff format --check ."
ruff format --check .
end "$?"

begin "pytest with coverage floors"
pytest --cov=dailies/core --cov=scripts "--cov-report=xml:$work/coverage.xml" &&
  "${COVERAGE_CHECK:-$ROOT/scripts/coverage-check.sh}" "$work/coverage.xml" "$ROOT/.github/auto-qa-tuning.json"
end "$?"

begin "check-jsonschema data/v1/games.json"
check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json
end "$?"

begin "check-jsonschema data/v1/popularity.json"
check-jsonschema --schemafile data/v1/schema/popularity.schema.json data/v1/popularity.json
end "$?"

begin "shellcheck -x scripts/*.sh scripts/lib/*.sh build-aux/windows/*.sh"
shellcheck -x scripts/*.sh scripts/lib/*.sh build-aux/windows/*.sh
end "$?"

begin "actionlint"
actionlint
end "$?"

# The installed app reads its GSettings schema from the prefix, which is not on the default data path.
begin "meson setup, install and test"
meson setup "$work/build" -Dprofile=development "--prefix=$work/prefix" &&
  meson install -C "$work/build" --quiet &&
  XDG_DATA_DIRS="$work/prefix/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}" \
    meson test -C "$work/build" --print-errorlogs
end "$?"

echo
printf '%s\n' "${summary[@]}"
exit "$failed"
