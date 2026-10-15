#!/usr/bin/env python3
"""Check a release tag against the version metadata and write the GitHub Release body.

Used by .github/workflows/release.yml (see CONTRIBUTING.md, "Releasing"). Two commands:

- `verify --tag vX.Y.Z` checks that the tag without its `v` equals `version:` in meson.build's project() and the
  newest (first) <release version> in the metainfo, and that the newest release's date is not in the future. It
  prints the step outputs `version`, `prerelease` (true for a tag with a `-` suffix, such as v0.2.0-beta.1) and
  `pinned_commit` (the commit the release manifest builds) as key=value lines for $GITHUB_OUTPUT.
- `notes` prints the release body in Markdown: the newest metainfo release's description, then the install
  instructions. GitHub appends the notes it generates from merged pull requests (.github/release.yml) below it.

Exit status: 0 on success, 1 when a check fails or a file is missing or malformed (the reason goes to stderr), 2 on a
usage error. Standard library only.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar

APP_ID = "io.github.tim_van_oudheusden.Dailies"
METAINFO = Path("data") / f"{APP_ID}.metainfo.xml.in"
MANIFEST = Path("build-aux") / "flatpak" / f"{APP_ID}.json"
MODULE = "dailies"

# Release versions only; a pre-release adds a SemVer-style `-` suffix. `+build` metadata is not used.
TAG = re.compile(r"v(?P<version>\d+\.\d+\.\d+(?P<pre>-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?)")
PROJECT = re.compile(r"\bproject\s*\((?P<args>[^)]*)\)")
PROJECT_VERSION = re.compile(r"(?<![\w])version\s*:\s*'(?P<version>[^']*)'")

# A release date is only "in the future" once it has not begun anywhere on Earth: UTC+14 is the first time zone to
# reach a new day, so a tag pushed early on the release day, local time, still passes.
EARLIEST_ZONE = timezone(timedelta(hours=14))


class ReleaseError(Exception):
    """A release check failed; the message says why."""


@dataclass(frozen=True)
class Release:
    """The newest metainfo release: its version, date and notes in Markdown."""

    version: str
    date: date
    notes: str


@dataclass(frozen=True)
class Verified:
    """The outcome of a passed `verify`: the step outputs."""

    version: str
    prerelease: bool
    pinned_commit: str


def parse_tag(tag: str) -> tuple[str, bool]:
    """Return the version a `vX.Y.Z[-suffix]` tag names and whether it is a pre-release."""
    match = TAG.fullmatch(tag)
    if match is None:
        msg = f"tag {tag!r} is not vX.Y.Z or vX.Y.Z-<pre-release>"
        raise ReleaseError(msg)
    return match["version"], match["pre"] is not None


def meson_version(text: str) -> str:
    """Return the `version:` of meson.build's project() call."""
    project = PROJECT.search(text)
    version = PROJECT_VERSION.search(project["args"]) if project else None
    if version is None:
        msg = "meson.build has no project(..., version: '...')"
        raise ReleaseError(msg)
    return version["version"]


class _NewestRelease(HTMLParser):
    """Collects the first <release> of a metainfo file, its description turned into Markdown blocks."""

    INLINE: ClassVar[dict[str, str]] = {"em": "*", "code": "`"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.attrs: dict[str, str | None] | None = None
        self.blocks: list[tuple[str, str]] = []
        self._state = "before"  # before -> release -> description -> done
        self._lists: list[list[int | str]] = []  # [kind, items so far] per open <ul>/<ol>
        self._kind = ""
        self._text: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._state == "before" and tag == "release":
            self.attrs = dict(attrs)
            self._state = "release"
        elif self._state == "release" and tag == "description":
            self._state = "description"
        elif self._state == "description":
            if tag == "p":
                self._open("p", "")
            elif tag in {"ul", "ol"}:
                self._lists.append([tag, 0])
            elif tag == "li" and self._lists:
                kind, count = self._lists[-1]
                self._lists[-1][1] = int(count) + 1
                self._open("li", "- " if kind == "ul" else f"{int(count) + 1}. ")
            elif tag in self.INLINE and self._text is not None:
                self._text.append(self.INLINE[tag])

    def handle_endtag(self, tag: str) -> None:
        if self._state == "description":
            if tag in {"p", "li"} and self._text is not None:
                self.blocks.append((self._kind, " ".join("".join(self._text).split())))
                self._text = None
            elif tag in {"ul", "ol"} and self._lists:
                self._lists.pop()
            elif tag in self.INLINE and self._text is not None:
                self._text.append(self.INLINE[tag])
            elif tag == "description":
                self._state = "release"
        if self._state == "release" and tag == "release":
            self._state = "done"

    def handle_data(self, data: str) -> None:
        if self._state == "description" and self._text is not None:
            self._text.append(data)

    def _open(self, kind: str, prefix: str) -> None:
        self._kind = kind
        self._text = [prefix]


def newest_release(text: str) -> Release:
    """Return the newest (first) <release> of a metainfo file, its description as Markdown."""
    parser = _NewestRelease()
    parser.feed(text)
    parser.close()
    if parser.attrs is None:
        msg = "the metainfo has no <release> entry"
        raise ReleaseError(msg)
    version = parser.attrs.get("version")
    if not version:
        msg = "the newest metainfo <release> has no version"
        raise ReleaseError(msg)
    try:
        released = date.fromisoformat(parser.attrs.get("date") or "")
    except ValueError:
        msg = f'the newest metainfo <release> needs date="YYYY-MM-DD", not {parser.attrs.get("date")!r}'
        raise ReleaseError(msg) from None
    notes = ""
    for index, (kind, block) in enumerate(parser.blocks):
        if index:
            notes += "\n" if kind == "li" and parser.blocks[index - 1][0] == "li" else "\n\n"
        notes += block
    return Release(version, released, notes)


def pinned_commit(manifest: dict) -> str:
    """Return the commit the release manifest's dailies module builds."""
    for module in manifest.get("modules", []):
        if isinstance(module, dict) and module.get("name") == MODULE:
            for source in module.get("sources", []):
                if source.get("type") == "git" and source.get("commit"):
                    return source["commit"]
    msg = f"the release manifest's {MODULE!r} module has no git source with a commit"
    raise ReleaseError(msg)


def _read(root: Path, path: Path) -> str:
    try:
        return (root / path).read_text(encoding="utf-8")
    except OSError as error:
        msg = f"cannot read {path}: {error.strerror}"
        raise ReleaseError(msg) from None


def _manifest(root: Path) -> dict:
    try:
        return json.loads(_read(root, MANIFEST))
    except json.JSONDecodeError as error:
        msg = f"{MANIFEST} is not valid JSON: {error}"
        raise ReleaseError(msg) from None


def verify(root: Path, tag: str, today: date) -> Verified:
    """Check that the tag, meson.build and the newest metainfo release name the same, already released version."""
    version, prerelease = parse_tag(tag)
    meson = meson_version(_read(root, Path("meson.build")))
    newest = newest_release(_read(root, METAINFO))
    if not version == meson == newest.version:
        msg = (
            f"tag {tag} names version {version}, meson.build has {meson} and the newest metainfo release is "
            f"{newest.version}; all three must be equal"
        )
        raise ReleaseError(msg)
    if newest.date > today:
        msg = f"the newest metainfo release is dated {newest.date.isoformat()}, which is in the future"
        raise ReleaseError(msg)
    return Verified(version, prerelease, pinned_commit(_manifest(root)))


def release_body(root: Path) -> str:
    """Return the GitHub Release body: the newest release's notes, then how to install a bundle."""
    notes = newest_release(_read(root, METAINFO)).notes
    runtime = _manifest(root).get("runtime-version", "")
    install = f"""## Install

```sh
# Prerequisite: the Flathub remote, for the GNOME {runtime} runtime
flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user ./Dailies-x86_64.flatpak     # or Dailies-aarch64.flatpak
```

Bundles do not update themselves. Watch this repository's Releases for new versions.
"""
    return f"{notes}\n\n{install}" if notes else install


def main(argv: list[str] | None = None) -> int:
    """Run the command line; see the module docstring."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="repository root")
    commands = parser.add_subparsers(dest="command", required=True)
    verify_parser = commands.add_parser("verify", help="check the tag against meson.build and the metainfo")
    verify_parser.add_argument("--tag", required=True, help="the pushed tag, such as v0.1.0")
    commands.add_parser("notes", help="print the release body")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            result = verify(args.root, args.tag, datetime.now(UTC).astimezone(EARLIEST_ZONE).date())
            sys.stdout.write(
                f"version={result.version}\n"
                f"prerelease={'true' if result.prerelease else 'false'}\n"
                f"pinned_commit={result.pinned_commit}\n"
            )
        else:
            sys.stdout.write(release_body(args.root))
    except ReleaseError as error:
        sys.stderr.write(f"release_check: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
