import importlib.util
import json
from datetime import date
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "release_check.py"
TODAY = date(2026, 10, 16)
PINNED = "0123456789abcdef0123456789abcdef01234567"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_check", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rc = load_script()

MESON = """project(
  'dailies',
  version: '{version}',
  meson_version: '>= 1.4',
)

dependency('gtk4', version: '>= 4.24')
"""

METAINFO = """<?xml version="1.0" encoding="UTF-8"?>
<!-- Copyright -->
<component type="desktop-application">
  <id>@APP_ID@</id>
  <description>
    <p>The app description, not release notes.</p>
  </description>
  <content_rating type="oars-1.1"/>
  <releases>
{releases}
  </releases>
</component>
"""


def release(version: str, day: str = "2026-10-15", description: str = "<p>Notes.</p>") -> str:
    entry = f'<release version="{version}" date="{day}">\n      <description>{description}</description>\n'
    return f"    {entry}    </release>"


def manifest(commit: str = PINNED) -> dict:
    return {
        "id": "io.github.tim_van_oudheusden.Dailies",
        "runtime-version": "51",
        "modules": [
            {"name": "blueprint", "sources": [{"type": "git", "url": "https://example.org/b.git", "commit": "f" * 40}]},
            {"name": "dailies", "sources": [{"type": "git", "url": "https://example.org/d.git", "commit": commit}]},
        ],
    }


def make_repo(root: Path, meson: str = "0.1.0", releases: str | None = None, manifest_data: dict | None = None) -> Path:
    (root / "data").mkdir(parents=True)
    (root / "build-aux" / "flatpak").mkdir(parents=True)
    (root / "meson.build").write_text(MESON.format(version=meson), encoding="utf-8")
    metainfo = METAINFO.format(releases=releases if releases is not None else release("0.1.0"))
    (root / rc.METAINFO).write_text(metainfo, encoding="utf-8")
    (root / rc.MANIFEST).write_text(json.dumps(manifest_data or manifest()), encoding="utf-8")
    return root


# Tags


@pytest.mark.parametrize(
    ("tag", "version", "prerelease"),
    [
        ("v0.1.0", "0.1.0", False),
        ("v10.20.30", "10.20.30", False),
        ("v0.2.0-beta.1", "0.2.0-beta.1", True),
        ("v1.0.0-rc1", "1.0.0-rc1", True),
    ],
)
def test_tag_gives_version_and_prerelease(tag: str, version: str, prerelease: bool) -> None:
    assert rc.parse_tag(tag) == (version, prerelease)


@pytest.mark.parametrize("tag", ["0.1.0", "v0.1", "vfoo", "v0.1.0-", "v0.1.0+build", "release-0.1.0", ""])
def test_malformed_tag_is_rejected(tag: str) -> None:
    with pytest.raises(rc.ReleaseError, match="tag"):
        rc.parse_tag(tag)


# meson.build


def test_meson_version_is_the_project_version_not_a_dependency_version() -> None:
    assert rc.meson_version(MESON.format(version="0.3.1")) == "0.3.1"


def test_meson_version_on_one_line() -> None:
    assert rc.meson_version("project('dailies', version: '2.0.0', license: 'GPL-3.0-or-later')\n") == "2.0.0"


def test_meson_without_project_version_is_an_error() -> None:
    with pytest.raises(rc.ReleaseError, match=r"meson\.build"):
        rc.meson_version("project('dailies')\ndependency('gtk4', version: '>= 4.24')\n")


# Metainfo


def test_newest_release_is_the_first_entry() -> None:
    releases = "\n".join([release("0.2.0", "2026-11-01", "<p>Second.</p>"), release("0.1.0", "2026-10-01")])
    newest = rc.newest_release(METAINFO.format(releases=releases))
    assert newest.version == "0.2.0"
    assert newest.date == date(2026, 11, 1)
    assert newest.notes == "Second."


def test_notes_become_markdown() -> None:
    description = """
        <p>First   paragraph,
          wrapped.</p>
        <ul>
          <li>An <em>emphasised</em> item</li>
          <li>Runs <code>flatpak</code> &amp; more</li>
        </ul>
        <p>Then:</p>
        <ol>
          <li>one</li>
          <li>two</li>
        </ol>
    """
    newest = rc.newest_release(METAINFO.format(releases=release("0.1.0", description=description)))
    assert newest.notes == (
        "First paragraph, wrapped.\n\n- An *emphasised* item\n- Runs `flatpak` & more\n\nThen:\n\n1. one\n2. two"
    )


def test_release_without_description_has_empty_notes() -> None:
    metainfo = METAINFO.format(releases='    <release version="0.1.0" date="2026-10-15"/>')
    assert rc.newest_release(metainfo).notes == ""


def test_metainfo_without_releases_is_an_error() -> None:
    with pytest.raises(rc.ReleaseError, match="<release>"):
        rc.newest_release(METAINFO.format(releases=""))


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ('<release date="2026-10-15"/>', "version"),
        ('<release version="0.1.0"/>', "date"),
        ('<release version="0.1.0" date="15 October"/>', "date"),
    ],
)
def test_incomplete_release_entry_is_an_error(entry: str, message: str) -> None:
    with pytest.raises(rc.ReleaseError, match=message):
        rc.newest_release(METAINFO.format(releases=entry))


# Release manifest


def test_pinned_commit_is_the_dailies_module_source() -> None:
    assert rc.pinned_commit(manifest()) == PINNED


def test_manifest_without_a_pinned_dailies_commit_is_an_error() -> None:
    data = manifest()
    del data["modules"][1]["sources"][0]["commit"]
    with pytest.raises(rc.ReleaseError, match="commit"):
        rc.pinned_commit(data)


def test_malformed_manifest_is_an_error(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / rc.MANIFEST).write_text("{", encoding="utf-8")
    with pytest.raises(rc.ReleaseError, match="not valid JSON"):
        rc.verify(root, "v0.1.0", TODAY)


# verify


def test_matching_versions_verify(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    assert rc.verify(root, "v0.1.0", TODAY) == rc.Verified("0.1.0", prerelease=False, pinned_commit=PINNED)


def test_prerelease_verifies_when_all_three_agree(tmp_path: Path) -> None:
    root = make_repo(tmp_path, meson="0.2.0-beta.1", releases=release("0.2.0-beta.1"))
    assert rc.verify(root, "v0.2.0-beta.1", TODAY).prerelease is True


def test_tag_that_differs_from_meson_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    with pytest.raises(rc.ReleaseError, match=r"9\.9\.9.*meson\.build.*0\.1\.0"):
        rc.verify(root, "v9.9.9", TODAY)


def test_metainfo_that_lags_behind_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path, meson="0.2.0", releases=release("0.1.0"))
    with pytest.raises(rc.ReleaseError, match=r"metainfo.*0\.1\.0"):
        rc.verify(root, "v0.2.0", TODAY)


def test_release_dated_today_verifies(tmp_path: Path) -> None:
    root = make_repo(tmp_path, releases=release("0.1.0", TODAY.isoformat()))
    assert rc.verify(root, "v0.1.0", TODAY).version == "0.1.0"


def test_release_dated_tomorrow_fails(tmp_path: Path) -> None:
    root = make_repo(tmp_path, releases=release("0.1.0", "2026-10-17"))
    with pytest.raises(rc.ReleaseError, match="future"):
        rc.verify(root, "v0.1.0", TODAY)


# Release body


def test_body_has_notes_then_install_instructions(tmp_path: Path) -> None:
    root = make_repo(tmp_path, releases=release("0.1.0", description="<p>First release.</p>"))
    body = rc.release_body(root)
    assert body.startswith("First release.\n")
    assert "flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo" in body
    assert "flatpak install --user ./Dailies-x86_64.flatpak     # or Dailies-aarch64.flatpak" in body
    assert "GNOME 51 runtime" in body
    assert "Bundles do not update themselves. Watch this repository's Releases for new versions." in body
    assert body.index("First release.") < body.index("flatpak install")


def test_body_without_notes_starts_with_install(tmp_path: Path) -> None:
    root = make_repo(tmp_path, releases='    <release version="0.1.0" date="2026-10-15"/>')
    assert rc.release_body(root).startswith("## Install")


# Command line


def test_cli_verify_prints_step_outputs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make_repo(tmp_path)
    assert rc.main(["--root", str(root), "verify", "--tag", "v0.1.0"]) == 0
    assert capsys.readouterr().out == f"version=0.1.0\nprerelease=false\npinned_commit={PINNED}\n"


def test_cli_verify_mismatch_exits_1_with_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make_repo(tmp_path)
    assert rc.main(["--root", str(root), "verify", "--tag", "v9.9.9"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "9.9.9" in captured.err
    assert "0.1.0" in captured.err


def test_cli_verify_rejects_a_future_date(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make_repo(tmp_path, releases=release("0.1.0", "2999-01-01"))
    assert rc.main(["--root", str(root), "verify", "--tag", "v0.1.0"]) == 1
    assert "future" in capsys.readouterr().err


def test_cli_missing_file_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert rc.main(["--root", str(tmp_path), "verify", "--tag", "v0.1.0"]) == 1
    assert "meson.build" in capsys.readouterr().err


def test_cli_notes_prints_the_release_body(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make_repo(tmp_path, releases=release("0.1.0", description="<p>First release.</p>"))
    assert rc.main(["--root", str(root), "notes"]) == 0
    assert capsys.readouterr().out == rc.release_body(root)
