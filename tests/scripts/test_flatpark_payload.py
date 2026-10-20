import importlib.util
import os
import subprocess
import sys
import tarfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "flatpark_payload.py"
EPOCH = 1_792_000_000


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("flatpark_payload", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fp = load_script()


def make_tree(root: Path, mtime: int) -> Path:
    """An install tree with every file the payload must carry, all stamped with `mtime`."""
    files = {
        "bin/dailies": "#!/usr/bin/python3\n",
        "share/dailies/dailies/config.py": 'APP_ID = "io.github.tim_van_oudheusden.Dailies"\n',
        "share/dailies/dailies.gresource": "GVariant",
        "share/glib-2.0/schemas/gschemas.compiled": "GVariant",
        "share/locale/nl/LC_MESSAGES/dailies.mo": "mo",
    }
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    (root / "bin" / "dailies").chmod(0o755)
    for path in [root, *root.rglob("*")]:
        os.utime(path, (mtime, mtime))
    return root


def test_the_archive_is_byte_identical_whatever_the_tree_s_timestamps(tmp_path: Path) -> None:
    first = make_tree(tmp_path / "first", mtime=1_700_000_000)
    second = make_tree(tmp_path / "second", mtime=1_800_000_000)

    fp.write_archive(first, tmp_path / "first.tar.xz", EPOCH)
    fp.write_archive(second, tmp_path / "second.tar.xz", EPOCH)

    assert (tmp_path / "first.tar.xz").read_bytes() == (tmp_path / "second.tar.xz").read_bytes()


def test_members_are_root_owned_stamped_with_the_epoch_and_keep_the_launcher_executable(tmp_path: Path) -> None:
    tree = make_tree(tmp_path / "tree", mtime=1_700_000_000)

    fp.write_archive(tree, tmp_path / "payload.tar.xz", EPOCH)

    with tarfile.open(tmp_path / "payload.tar.xz") as archive:
        members = {member.name: member for member in archive.getmembers()}
    assert {(m.uid, m.gid, m.uname, m.gname, m.mtime) for m in members.values()} == {(0, 0, "", "", EPOCH)}
    assert members["bin/dailies"].mode == 0o755
    assert members["share/dailies/dailies/config.py"].mode == 0o644
    assert members["share/dailies"].isdir()


def test_a_complete_tree_misses_nothing(tmp_path: Path) -> None:
    assert fp.missing_files(make_tree(tmp_path / "tree", mtime=EPOCH)) == []


def test_a_tree_without_compiled_schemas_or_launcher_names_both(tmp_path: Path) -> None:
    tree = make_tree(tmp_path / "tree", mtime=EPOCH)
    (tree / "share/glib-2.0/schemas/gschemas.compiled").unlink()
    (tree / "bin/dailies").unlink()

    assert fp.missing_files(tree) == ["bin/dailies", "share/glib-2.0/schemas/gschemas.compiled"]


def fake_build(
    tree_files: dict[str, str] | None = None,
) -> tuple[list[tuple[Path, Path]], Callable[[Path, Path], Path]]:
    """A build_tree stand-in that installs `tree_files` (default: a complete tree) under the workdir it is given."""
    calls: list[tuple[Path, Path]] = []

    def build_tree(source: Path, work: Path) -> Path:
        calls.append((source, work))
        tree = work / "sandbox" / "files" / "extra" / "dailies"
        if tree_files is None:
            return make_tree(tree, mtime=1_700_000_000)
        for name, text in tree_files.items():
            (tree / name).parent.mkdir(parents=True, exist_ok=True)
            (tree / name).write_text(text)
        return tree

    return calls, build_tree


def test_main_builds_this_checkout_in_a_fresh_workdir_and_writes_the_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    work = Path("work")
    (work / "stale").mkdir(parents=True)
    (work / "stale" / "old.txt").write_text("from the last run")
    calls, build_tree = fake_build()
    monkeypatch.setattr(fp, "build_tree", build_tree)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", str(EPOCH))
    output = tmp_path / "dist" / "nested" / "Dailies-flatpark.tar.xz"

    status = fp.main(["--output", str(output), "--workdir", str(work)])

    assert status == 0
    assert calls == [(fp.ROOT, tmp_path / "work")]
    assert not (work / "stale").exists()
    assert capsys.readouterr().out == f"{output}\n"
    with tarfile.open(output) as archive:
        members = archive.getmembers()
    assert "share/glib-2.0/schemas/gschemas.compiled" in {member.name for member in members}
    assert {member.mtime for member in members} == {EPOCH}


@pytest.mark.parametrize(
    "error",
    [OSError("flatpak is not on PATH"), subprocess.CalledProcessError(1, ["flatpak", "build"])],
    ids=["tool-missing", "tool-failed"],
)
def test_main_exits_1_and_writes_no_payload_when_the_build_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], error: Exception
) -> None:
    def build_tree(_source: Path, _work: Path) -> Path:
        raise error

    monkeypatch.setattr(fp, "build_tree", build_tree)
    output = tmp_path / "Dailies-flatpark.tar.xz"

    status = fp.main(["--output", str(output), "--workdir", str(tmp_path / "work")])

    assert status == 1
    assert not output.exists()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"flatpark_payload: the build failed: {error}\n"


def test_main_exits_1_when_the_checkout_has_no_commit_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    not_a_checkout = tmp_path / "source"
    not_a_checkout.mkdir()
    _, build_tree = fake_build()
    monkeypatch.setattr(fp, "build_tree", build_tree)
    monkeypatch.setattr(fp, "ROOT", not_a_checkout)
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    output = tmp_path / "Dailies-flatpark.tar.xz"

    status = fp.main(["--output", str(output), "--workdir", str(tmp_path / "work")])

    assert status == 1
    assert not output.exists()
    assert capsys.readouterr().err.startswith("flatpark_payload: the build failed: ")


def test_main_exits_1_naming_what_the_install_tree_lacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, build_tree = fake_build({"bin/dailies": "#!/usr/bin/python3\n", "share/dailies/dailies.gresource": "GVariant"})
    monkeypatch.setattr(fp, "build_tree", build_tree)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", str(EPOCH))
    output = tmp_path / "Dailies-flatpark.tar.xz"

    status = fp.main(["--output", str(output), "--workdir", str(tmp_path / "work")])

    assert status == 1
    assert not output.exists()
    assert capsys.readouterr().err == (
        "flatpark_payload: the install tree lacks share/dailies/dailies/config.py, "
        "share/glib-2.0/schemas/gschemas.compiled\n"
    )


def test_build_tree_installs_a_release_build_for_the_flatpark_prefix_inside_the_sdk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[tuple[str, ...]] = []

    def run(*argv: str | Path) -> str:
        commands.append(tuple(map(str, argv)))
        return ""

    monkeypatch.setattr(fp, "run", run)
    source, work = tmp_path / "source", tmp_path / "work"

    tree = fp.build_tree(source, work)

    sandbox = str(work / "sandbox")
    shell = ("flatpak", "build", f"--filesystem={source}", f"--filesystem={work}", sandbox)
    assert commands == [
        ("flatpak", "build-init", sandbox, fp.APP_ID, "org.gnome.Sdk", "org.gnome.Platform", "51"),
        (
            *shell,
            "meson",
            "setup",
            "-Dprofile=release",
            "--prefix=/app/extra/dailies",
            str(work / "meson"),
            str(source),
        ),
        (*shell, "meson", "install", "-C", str(work / "meson")),
    ]
    assert tree == work / "sandbox" / "files" / "extra" / "dailies"


def test_source_date_epoch_prefers_the_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1234567890")

    assert fp.source_date_epoch(tmp_path) == 1_234_567_890


def commit_at(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `repo` a git checkout whose HEAD was committed at EPOCH and authored earlier; unset SOURCE_DATE_EPOCH."""
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    monkeypatch.setenv("GIT_AUTHOR_DATE", "@1600000000 +0000")
    monkeypatch.setenv("GIT_COMMITTER_DATE", f"@{EPOCH} +0000")
    identity = ("-c", "user.name=Test", "-c", "user.email=test@example.org")
    fp.run("git", "init", "--quiet", repo)
    fp.run("git", *identity, "-C", repo, "commit", "--quiet", "--allow-empty", "-m", "seed")


def test_source_date_epoch_falls_back_to_the_head_commit_time(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    commit_at(tmp_path, monkeypatch)

    assert fp.source_date_epoch(tmp_path) == EPOCH


def test_source_date_epoch_trusts_a_checkout_another_user_owns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # CI builds in a container whose uid does not own the checkout; git then refuses it unless it is a safe.directory.
    commit_at(tmp_path, monkeypatch)
    monkeypatch.setenv("GIT_TEST_ASSUME_DIFFERENT_OWNER", "1")

    assert fp.source_date_epoch(tmp_path) == EPOCH


def test_run_returns_the_tool_s_stdout() -> None:
    assert fp.run(sys.executable, "-c", "print('payload')") == "payload\n"


def test_run_names_a_tool_that_is_not_on_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))

    with pytest.raises(OSError, match=r"^flatpak is not on PATH$"):
        fp.run("flatpak", "build-init")
