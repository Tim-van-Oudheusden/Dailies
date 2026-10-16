import difflib
import importlib.util
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "apply_link_status.py"
CATALOG = ROOT / "data" / "v1" / "games.json"
NOW = datetime(2026, 10, 18, 3, 30, 5, tzinfo=UTC)


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("apply_link_status", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


als = load_script()


def setup(tmp_path: Path, changes: list[dict]) -> tuple[Path, Path]:
    catalog = tmp_path / "games.json"
    shutil.copyfile(CATALOG, catalog)
    changes_file = tmp_path / "changes.json"
    changes_file.write_text(json.dumps({"week": "2026-W42", "changes": changes}), encoding="utf-8")
    return catalog, changes_file


def run(catalog: Path, changes: Path) -> int:
    return als.main(["--changes", str(changes), "--catalog", str(catalog)], now=NOW)


def test_a_change_touches_only_its_entry_and_generated_at(tmp_path: Path) -> None:
    change = {"id": "worldle", "status": "broken", "event": "broken", "note": "link check: http-404"}
    catalog, changes = setup(tmp_path, [change])

    assert run(catalog, changes) == 0

    before_text = CATALOG.read_text(encoding="utf-8")
    before = before_text.splitlines()
    after = catalog.read_text(encoding="utf-8").splitlines()
    changed = [line for line in difflib.unified_diff(before, after, lineterm="", n=0) if line[:1] in "+-"]
    removed = [line for line in changed[2:] if line.startswith("-")]
    added = [line for line in changed[2:] if line.startswith("+")]
    # The live catalog's stamp changes with every data PR, so read it instead of pinning it.
    old_stamp = json.loads(before_text)["generated_at"]
    assert removed == [f'-  "generated_at": "{old_stamp}",', '-      "status": "active",']
    assert added == [
        '+  "generated_at": "2026-10-18T03:30:05Z",',
        '+      "status": "broken",',
        "+        },",
        "+        {",
        '+          "date": "2026-10-18",',
        '+          "event": "broken",',
        '+          "note": "link check: http-404"',
    ]
    worldle = next(game for game in json.loads(catalog.read_text(encoding="utf-8"))["games"] if game["id"] == "worldle")
    assert worldle["status"] == "broken"
    assert len(json.loads(catalog.read_text(encoding="utf-8"))["games"]) == len(
        json.loads(CATALOG.read_text())["games"]
    )


def test_nothing_to_change_leaves_the_file_alone(tmp_path: Path) -> None:
    change = {"id": "worldle", "status": "active", "event": "restored", "note": "link check: passes"}
    catalog, changes = setup(tmp_path, [change])

    assert run(catalog, changes) == 0
    assert catalog.read_bytes() == CATALOG.read_bytes()


def test_an_unknown_game_is_an_error_and_changes_nothing(tmp_path: Path) -> None:
    changes_list = [
        {"id": "worldle", "status": "broken", "event": "broken", "note": "n"},
        {"id": "no-such-game", "status": "broken", "event": "broken", "note": "n"},
    ]
    catalog, changes = setup(tmp_path, changes_list)

    assert run(catalog, changes) == 2
    assert catalog.read_bytes() == CATALOG.read_bytes()
