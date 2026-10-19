#!/usr/bin/env python3
"""Build the FlatPark payload: Dailies' install tree for /app/extra/dailies, as a reproducible tar.xz (#205).

FlatPark (https://flatpark.org) builds nothing from source. Its package pins this release asset as Flatpak extra-data,
and its apply_extra unpacks it into /app/extra/dailies on the user's machine, offline, inside org.gnome.Platform. The
.flatpak bundles cannot be unpacked there: the runtime has no ostree and no flatpak.

The tree is a release-profile Meson install of this checkout with prefix /app/extra/dailies, built inside
org.gnome.Sdk//51 with `flatpak build`, so the launcher's interpreter (/usr/bin/python3) and the PKGDATADIR and
LOCALEDIR it bakes in are the runtime's and FlatPark's paths. gnome.post_install() compiles the GSettings schemas
into the tree. It holds no compiled code, so one payload serves x86_64 and aarch64.

Usage: flatpark_payload.py [--output Dailies-flatpark.tar.xz] [--workdir _flatpark]

Needs flatpak with org.gnome.Sdk//51 and org.gnome.Platform//51 installed. Every member's mtime is
$SOURCE_DATE_EPOCH, or the checkout's commit time without it, so the same commit gives the same bytes. The workdir is
deleted and rebuilt on every run. Exit status: 0 on success, 1 when the build fails or the tree misses a file the
FlatPark package starts from. Standard library only.
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

APP_ID = "io.github.tim_van_oudheusden.Dailies"
RUNTIME_BRANCH = "51"
PREFIX = "/app/extra/dailies"
ASSET = "Dailies-flatpark.tar.xz"
ROOT = Path(__file__).resolve().parents[1]

# What FlatPark's apply_extra checks before it hands the tree to its wrapper: the launcher, the package's configured
# paths, the UI resources and the compiled settings schema. Without any of them the app installs and cannot start.
REQUIRED = (
    "bin/dailies",
    "share/dailies/dailies.gresource",
    "share/dailies/dailies/config.py",
    "share/glib-2.0/schemas/gschemas.compiled",
)


def missing_files(tree: Path) -> list[str]:
    """The REQUIRED files that `tree` lacks, in REQUIRED's order."""
    return [name for name in REQUIRED if not (tree / name).is_file()]


def write_archive(tree: Path, output: Path, mtime: int) -> None:
    """Write `tree` to `output` as tar.xz, with the same bytes for the same files whatever their timestamps.

    Members are sorted, owned by uid/gid 0 with no names (a system-wide FlatPark install unpacks as root with every
    capability dropped, so recorded owners could not be restored), stamped with `mtime`, and get mode 0755 if any
    execute bit is set, 0644 otherwise.
    """

    def normalise(member: tarfile.TarInfo) -> tarfile.TarInfo:
        member.uid = member.gid = 0
        member.uname = member.gname = ""
        member.mtime = mtime
        member.mode = 0o755 if member.isdir() or member.mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) else 0o644
        return member

    with tarfile.open(output, "w:xz", format=tarfile.PAX_FORMAT) as archive:
        for path in sorted(tree.rglob("*")):
            archive.add(path, arcname=path.relative_to(tree).as_posix(), recursive=False, filter=normalise)


def run(*argv: str | Path) -> str:
    """Run a fixed tool with `argv`, return its stdout; raise OSError if the tool is not on PATH."""
    tool = shutil.which(argv[0])
    if tool is None:
        msg = f"{argv[0]} is not on PATH"
        raise OSError(msg)
    command = [tool, *map(str, argv[1:])]
    return subprocess.run(  # noqa: S603 - fixed tools; the paths are this checkout and its scratch directory
        command, check=True, stdout=subprocess.PIPE, text=True
    ).stdout


def build_tree(source: Path, work: Path) -> Path:
    """Meson-install `source` for PREFIX inside org.gnome.Sdk; return where the installed tree is on the host.

    `flatpak build` mounts `work/sandbox/files` at /app, so PREFIX lands in `work/sandbox/files/extra/dailies`.
    """
    sandbox = work / "sandbox"
    builddir = work / "meson"
    run("flatpak", "build-init", sandbox, APP_ID, "org.gnome.Sdk", "org.gnome.Platform", RUNTIME_BRANCH)
    shell = ("flatpak", "build", f"--filesystem={source}", f"--filesystem={work}", sandbox)
    run(*shell, "meson", "setup", "-Dprofile=release", f"--prefix={PREFIX}", builddir, source)
    run(*shell, "meson", "install", "-C", builddir)
    return sandbox / "files" / Path(PREFIX).relative_to("/app")


def source_date_epoch(source: Path) -> int:
    """$SOURCE_DATE_EPOCH, or the commit time of `source`'s HEAD.

    `source` is this script's own checkout, so it is trusted on the command line: in CI's container the checkout
    belongs to another uid, and actions/checkout adds its safe.directory entry to a temporary HOME only.
    """
    if epoch := os.environ.get("SOURCE_DATE_EPOCH"):
        return int(epoch)
    return int(run("git", "-c", f"safe.directory={source}", "-C", source, "log", "-1", "--format=%ct"))


def main(argv: list[str] | None = None) -> int:
    """Build the payload of this checkout and write it to --output."""
    parser = argparse.ArgumentParser(description="Build the FlatPark payload tree of this checkout.")
    parser.add_argument("--output", type=Path, default=Path(ASSET), help=f"archive to write (default: {ASSET})")
    parser.add_argument("--workdir", type=Path, default=ROOT / "_flatpark", help="scratch build directory")
    args = parser.parse_args(argv)

    work = args.workdir.resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    try:
        tree = build_tree(ROOT, work)
        epoch = source_date_epoch(ROOT)
    except (OSError, subprocess.CalledProcessError) as error:
        sys.stderr.write(f"flatpark_payload: the build failed: {error}\n")
        return 1
    if missing := missing_files(tree):
        sys.stderr.write(f"flatpark_payload: the install tree lacks {', '.join(missing)}\n")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_archive(tree, args.output, epoch)
    sys.stdout.write(f"{args.output}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
