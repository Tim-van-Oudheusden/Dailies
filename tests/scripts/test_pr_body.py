import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "popularity" / "pr_body.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pr_body", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pr_body = load_script()


def summary(popular: int = 7, failed: list[str] | None = None, unranked: list[str] | None = None) -> dict[str, Any]:
    failed = failed or []
    return {
        "week": "2026-W43",
        "generated_at": "2026-10-19T04:21:09Z",
        "method_version": 1,
        "sources": {
            "tranco": {
                "ok": 40 - len(failed),
                "failed": len(failed),
                "count": 40,
                "fetched_at": "2026-10-19T04:18:00Z",
                "failed_domains": failed,
                "unranked_domains": unranked or [],
            },
        },
        "popular": [
            {"id": f"game-{n}", "name": f"Game {n}", "score": round(1 - n / 10, 4)} for n in range(1, popular + 1)
        ],
        "trending": [],
        "top_movers": {"up": [], "down": []},
    }


def table_rows(body: str, header: str) -> list[str]:
    """The data rows of the first Markdown table after the given heading."""
    lines = body.split(header, 1)[1].splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("|"))
    end = next((i for i in range(start, len(lines)) if not lines[i].startswith("|")), len(lines))
    return lines[start + 2 : end]


def test_body_names_the_week_and_method() -> None:
    body = pr_body.render(summary())

    assert "2026-W43" in body
    assert "method_version 1" in body


def test_top_five_table_lists_only_the_five_most_popular_in_order() -> None:
    body = pr_body.render(summary(popular=7))

    rows = table_rows(body, "Top 5")
    assert [row.split("|")[1].strip() for row in rows[:5]] == ["1", "2", "3", "4", "5"]
    assert "Game 1" in rows[0]
    assert "`game-1`" in rows[0]
    assert "0.9" in rows[0]
    assert "Game 5" in rows[4]
    assert "Game 6" not in body


def test_top_table_has_fewer_rows_when_the_shelf_is_short() -> None:
    body = pr_body.render(summary(popular=3))

    assert "Game 3" in body
    assert "Game 4" not in body


def test_pipe_in_a_game_name_does_not_break_the_table() -> None:
    data = summary(popular=1)
    data["popular"][0]["name"] = "This | That"

    row = next(line for line in pr_body.render(data).splitlines() if "That" in line)

    assert row.count("|") - row.count("\\|") == 4


def test_source_health_reports_counts_and_problem_domains() -> None:
    body = pr_body.render(summary(failed=["broken.example", "down.example"], unranked=["tiny.example"]))

    health = body.split("Source health", 1)[1]
    row = next(line for line in health.splitlines() if line.startswith("| tranco"))
    cells = [cell.strip() for cell in row.split("|")[1:-1]]
    assert cells[:4] == ["tranco", "38", "2", "40"]
    assert "broken.example" in health
    assert "down.example" in health
    assert "tiny.example" in health


def test_healthy_source_lists_no_problem_domains() -> None:
    body = pr_body.render(summary())

    assert "Failed domains" not in body
    assert "Unranked domains" not in body


def test_run_url_is_linked_for_the_raw_signals() -> None:
    url = "https://github.com/Tim-van-Oudheusden/Dailies/actions/runs/123"

    assert url in pr_body.render(summary(), run_url=url)


def test_main_writes_the_body_file(tmp_path: Path) -> None:
    source = tmp_path / "summary.json"
    source.write_text(json.dumps(summary()), encoding="utf-8")
    out = tmp_path / "body.md"

    status = pr_body.main(["--summary", str(source), "--out", str(out), "--run-url", "https://example.invalid/run"])

    assert status == 0
    text = out.read_text(encoding="utf-8")
    assert text == pr_body.render(summary(), run_url="https://example.invalid/run")
    assert text.endswith("\n")


def test_main_fails_on_a_missing_summary(tmp_path: Path) -> None:
    status = pr_body.main(["--summary", str(tmp_path / "missing.json"), "--out", str(tmp_path / "body.md")])

    assert status == 2
    assert not (tmp_path / "body.md").exists()
