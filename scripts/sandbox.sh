#!/usr/bin/env bash
# Runs a command in the agent sandbox (Dockerfile.sandbox): the GNOME 51 SDK in an unprivileged rootless podman
# container, with this checkout mounted at /workspace. Builds the image first; podman's layer cache makes that a no-op
# when Dockerfile.sandbox and scripts/requirements.txt are unchanged. Run it from anywhere in the checkout.
#
#   scripts/sandbox.sh                every gate except the Flatpak build (scripts/sandbox-gates.sh)
#   scripts/sandbox.sh CMD [ARGS]     any command, e.g. `pytest tests/core` or `bash` for a shell
#
# --userns=keep-id maps your user to the same uid inside, so files the gates write stay yours. In a git worktree,
# `.git` points outside the mount and git sees no repository inside; the gates do not need one.
#
# Exit status: the command's; podman's when the image build fails.
set -euo pipefail

readonly IMAGE=localhost/dailies-sandbox

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

# The build context is scripts/: the image takes only requirements.txt from it, and a context of the whole checkout
# would upload _build/ and _flatpak/ on every run.
podman build --quiet --tag "$IMAGE" --file "$ROOT/Dockerfile.sandbox" "$ROOT/scripts" >/dev/null

if [ "$#" -eq 0 ]; then
  set -- scripts/sandbox-gates.sh
fi
tty=()
if [ -t 0 ] && [ -t 1 ]; then
  tty=(--interactive --tty)
fi
exec podman run --rm "${tty[@]}" --userns=keep-id -v "$ROOT:/workspace:z" --workdir /workspace "$IMAGE" "$@"
