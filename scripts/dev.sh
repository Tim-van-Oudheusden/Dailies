#!/usr/bin/env bash
# Everyday Flatpak commands for the Devel build, modelled on Bazaar's Justfile recipes. Run from anywhere in the
# repository; every path is relative to its root.
#
#   scripts/dev.sh build-devel   build the Devel manifest, export it to repo/ and install it for your user
#   scripts/dev.sh run [ARGS]    run the installed Devel build
#   scripts/dev.sh bundle        export the Devel build as Dailies-Devel-<arch>.flatpak
#   scripts/dev.sh lint          flatpak-builder-lint on both manifests and on repo/
#
# Uses flatpak-builder and flatpak-builder-lint from PATH when present, else the org.flatpak.Builder Flatpak.
set -euo pipefail

readonly APP_ID=io.github.tim_van_oudheusden.Dailies
readonly DEVEL_ID="${APP_ID}.Devel"
readonly MANIFEST="build-aux/flatpak/${DEVEL_ID}.json"
readonly RELEASE_MANIFEST="build-aux/flatpak/${APP_ID}.json"
readonly EXCEPTIONS=build-aux/flatpak/lint-exceptions.json
readonly BUILD_DIR=_flatpak
readonly REPO_DIR=repo
readonly FLATHUB_REPO=https://dl.flathub.org/repo/flathub.flatpakrepo

cd "$(dirname "${BASH_SOURCE[0]}")/.."

usage() {
  sed -n '5,8s/^#   //p' "${BASH_SOURCE[0]}"
}

flatpak_builder() {
  if command -v flatpak-builder >/dev/null; then
    flatpak-builder "$@"
  else
    flatpak run org.flatpak.Builder "$@"
  fi
}

flatpak_builder_lint() {
  if command -v flatpak-builder-lint >/dev/null; then
    flatpak-builder-lint "$@"
  else
    flatpak run --command=flatpak-builder-lint org.flatpak.Builder "$@"
  fi
}

build_devel() {
  flatpak remote-add --user --if-not-exists flathub "$FLATHUB_REPO"
  flatpak_builder --user --install --force-clean --ccache --disable-rofiles-fuse \
    --install-deps-from=flathub --repo="$REPO_DIR" "$BUILD_DIR" "$MANIFEST"
}

# bundle and lint read repo/, so they build it first when it is missing.
ensure_repo() {
  if [[ ! -d "$REPO_DIR" ]]; then
    build_devel
  fi
}

bundle() {
  ensure_repo
  local arch
  arch="$(flatpak --default-arch)"
  flatpak build-bundle --arch="$arch" --runtime-repo="$FLATHUB_REPO" \
    "$REPO_DIR" "Dailies-Devel-${arch}.flatpak" "$DEVEL_ID"
  echo "Wrote Dailies-Devel-${arch}.flatpak"
}

# Runs every check, then fails if any of them did. The release ID gets no exceptions. --user-exceptions only takes
# effect together with --exceptions.
lint() {
  ensure_repo
  local status=0
  flatpak_builder_lint manifest "$RELEASE_MANIFEST" || status=1
  flatpak_builder_lint --exceptions --user-exceptions "$EXCEPTIONS" manifest "$MANIFEST" || status=1
  flatpak_builder_lint --exceptions --user-exceptions "$EXCEPTIONS" repo "$REPO_DIR" || status=1
  return "$status"
}

case "${1:-}" in
  build-devel) build_devel ;;
  run)
    shift
    flatpak run --user "$DEVEL_ID" "$@"
    ;;
  bundle) bundle ;;
  lint) lint ;;
  -h | --help | help) usage ;;
  *)
    usage >&2
    exit 2
    ;;
esac
