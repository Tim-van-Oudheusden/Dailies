import importlib.util
import os
import tarfile
from pathlib import Path
from types import ModuleType

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
