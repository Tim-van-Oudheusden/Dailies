import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "add_game.py"
CATALOG = ROOT / "data" / "v1" / "games.json"
NOW = datetime(2026, 10, 20, 9, 30, 15, tzinfo=UTC)


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("add_game", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ag = load_script()


def candidate(game_id: str = "bandle-test", name: str = "Bandle Test") -> dict:
    """An entry shaped like the one scripts/validate_submission.py builds."""
    return {
        "id": game_id,
        "name": name,
        "url": f"https://{game_id}.example/",
        "category": "music",
        "difficulty": "medium",
        "description": "Guess the song from a few bars, adding an instrument after each wrong guess.",
        "tags": ["songs"],
        "language": "en",
        "added": "2026-10-20",
        "status": "active",
        "domain": f"{game_id}.example",
        "source_issue": 123,
        "history": [{"date": "2026-10-20", "event": "added", "note": "issue #123"}],
    }


def write_result(tmp_path: Path, entry: dict, *, ok: bool = True) -> Path:
    path = tmp_path / "result.json"
    result = {"ok": ok, "entry": entry, "errors": [] if ok else ["broken"], "warnings": []}
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def copy_catalog(tmp_path: Path) -> Path:
    path = tmp_path / "games.json"
    path.write_bytes(CATALOG.read_bytes())
    return path


def ids(path: Path) -> list[str]:
    return [game["id"] for game in json.loads(path.read_text(encoding="utf-8"))["games"]]


def test_entry_is_inserted_in_id_order(tmp_path: Path) -> None:
    catalog = copy_catalog(tmp_path)
    before = ids(catalog)

    status = ag.main(["--entry", str(write_result(tmp_path, candidate())), "--catalog", str(catalog)], now=NOW)

    assert status == 0
    after = ids(catalog)
    assert after == sorted([*before, "bandle-test"])
    assert len(after) == len(before) + 1


def test_diff_against_the_real_catalog_is_only_the_new_entry_and_generated_at(tmp_path: Path) -> None:
    catalog = copy_catalog(tmp_path)
    before = catalog.read_text(encoding="utf-8")
    entry = candidate()

    ag.main(["--entry", str(write_result(tmp_path, entry)), "--catalog", str(catalog)], now=NOW)

    after = catalog.read_text(encoding="utf-8")
    entry_block = "".join(f"    {line}\n" for line in json.dumps(entry, indent=2).splitlines())
    entry_block = entry_block[:-1] + ",\n"
    assert after.count(entry_block) == 1
    # The live catalog's stamp changes with every data PR, so read it instead of pinning it.
    old_stamp = f'  "generated_at": "{json.loads(before)["generated_at"]}",\n'
    new_stamp = '  "generated_at": "2026-10-20T09:30:15Z",\n'
    assert after.replace(entry_block, "", 1) == before.replace(old_stamp, new_stamp, 1)
    assert before.count(old_stamp) == 1


def test_existing_id_is_refused_and_the_catalog_left_untouched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    catalog = copy_catalog(tmp_path)
    before = catalog.read_bytes()

    status = ag.main(["--entry", str(write_result(tmp_path, candidate("wordle", "Wordle"))), "--catalog", str(catalog)])

    assert status == 1
    assert catalog.read_bytes() == before
    assert '"wordle" is already in the catalog' in capsys.readouterr().err


def test_failed_validation_result_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    catalog = copy_catalog(tmp_path)
    before = catalog.read_bytes()

    status = ag.main(["--entry", str(write_result(tmp_path, candidate(), ok=False)), "--catalog", str(catalog)])

    assert status == 1
    assert catalog.read_bytes() == before
    assert "did not pass validation" in capsys.readouterr().err


def test_pr_body_closes_the_issue_and_shows_the_entry(tmp_path: Path) -> None:
    catalog = copy_catalog(tmp_path)
    body = tmp_path / "body.md"
    entry = candidate(name="Bandle ```Test")

    args = ["--entry", str(write_result(tmp_path, entry)), "--catalog", str(catalog), "--pr-body", str(body)]
    assert ag.main(args, now=NOW) == 0

    text = body.read_text(encoding="utf-8")
    assert "Closes #123" in text
    candidate_json = json.dumps(entry, indent=2, ensure_ascii=False)
    assert f"\n````json\n{candidate_json}\n````\n" in text


def read_outputs(path: Path) -> dict[str, str]:
    """Parse a $GITHUB_OUTPUT file the way the runner does (name=value and name<<DELIMITER blocks)."""
    outputs: dict[str, str] = {}
    lines = iter(path.read_text(encoding="utf-8").splitlines())
    for line in lines:
        if "<<" in line:
            key, delimiter = line.split("<<", 1)
            value: list[str] = []
            for inner in lines:
                if inner == delimiter:
                    break
                value.append(inner)
            outputs[key] = "\n".join(value)
        else:
            key, value_text = line.split("=", 1)
            outputs[key] = value_text
    return outputs


def test_step_outputs_hold_id_and_name_without_injection(tmp_path: Path) -> None:
    catalog = copy_catalog(tmp_path)
    outputs = tmp_path / "github_output"
    outputs.write_text("earlier=1\n", encoding="utf-8")
    name = "Bandle\nslug=evil\nEOF"

    args = ["--entry", str(write_result(tmp_path, candidate(name=name))), "--catalog", str(catalog)]
    assert ag.main([*args, "--github-output", str(outputs)], now=NOW) == 0

    assert read_outputs(outputs) == {"earlier": "1", "slug": "bandle-test", "name": name}


def test_unreadable_entry_is_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    catalog = copy_catalog(tmp_path)
    before = catalog.read_bytes()
    broken = tmp_path / "result.json"
    broken.write_text("{not json", encoding="utf-8")

    assert ag.main(["--entry", str(broken), "--catalog", str(catalog)]) == 2
    assert catalog.read_bytes() == before
    assert "add_game:" in capsys.readouterr().err
