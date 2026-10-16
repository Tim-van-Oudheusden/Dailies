import importlib.util
import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts" / "lib" / "linkstatus.py"
CATALOG = ROOT / "data" / "v1" / "games.json"
W41, W42, W43, W44 = "2026-W41", "2026-W42", "2026-W43", "2026-W44"
SUNDAY = date(2026, 10, 18)
NOW = datetime(2026, 10, 18, 3, 30, 5, tzinfo=UTC)


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("linkstatus", MODULE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ls = load_module()


def seen(game_id: str, outcome: str, *, status: str = "active", reason: str = "") -> object:
    return ls.Observation(game_id, status, outcome, reason or f"{game_id} {outcome}")


def run_weeks(weeks: list[tuple[str, list[object]]]) -> tuple[dict, list[list[object]]]:
    """Track each week's observations in turn, carrying the state; return the last state and every week's changes."""
    state: dict = {}
    changes = []
    for week, observations in weeks:
        state, week_changes = ls.track(observations, state, week)
        changes.append(week_changes)
    return state, changes


def test_iso_week_names_the_year_and_week() -> None:
    assert ls.iso_week(SUNDAY) == W42
    assert ls.iso_week(date(2027, 1, 1)) == "2026-W53"


def test_a_single_failure_changes_nothing() -> None:
    _, changes = run_weeks([(W42, [seen("moviedle", "http-404")])])

    assert changes == [[]]


def test_the_same_failure_in_two_consecutive_weeks_marks_the_game_broken() -> None:
    _, changes = run_weeks(
        [
            (W41, [seen("moviedle", "http-404")]),
            (W42, [seen("moviedle", "http-404", reason="https://moviedle.app/ answered HTTP 404")]),
        ]
    )

    assert changes[0] == []
    assert changes[1] == [
        ls.Change(
            "moviedle",
            "broken",
            "broken",
            "link check: http-404 in 2026-W41 and 2026-W42 (https://moviedle.app/ answered HTTP 404)",
        )
    ]


def test_a_different_failure_the_next_week_starts_over() -> None:
    _, changes = run_weeks([(W41, [seen("moviedle", "http-404")]), (W42, [seen("moviedle", "timeout")])])

    assert changes == [[], []]


def test_a_skipped_week_starts_over() -> None:
    _, changes = run_weeks([(W41, [seen("moviedle", "http-404")]), (W43, [seen("moviedle", "http-404")])])

    assert changes == [[], []]


def test_a_pass_in_between_starts_over() -> None:
    _, changes = run_weeks(
        [
            (W41, [seen("moviedle", "http-404")]),
            (W42, [seen("moviedle", "ok")]),
            (W43, [seen("moviedle", "http-404")]),
        ]
    )

    assert changes == [[], [], []]


def test_a_bot_walled_answer_in_between_starts_over() -> None:
    _, changes = run_weeks(
        [
            (W41, [seen("artle", "http-404")]),
            (W42, [seen("artle", "bot-walled")]),
            (W43, [seen("artle", "http-404")]),
        ]
    )

    assert changes == [[], [], []]


def test_a_second_run_in_the_same_week_is_not_a_second_week() -> None:
    _, changes = run_weeks([(W42, [seen("moviedle", "http-404")]), (W42, [seen("moviedle", "http-404")])])

    assert changes == [[], []]


def test_a_game_failing_for_a_third_week_is_still_proposed() -> None:
    # The pull request was not merged yet: the next run proposes the change again.
    _, changes = run_weeks([(week, [seen("moviedle", "http-404")]) for week in (W41, W42, W43)])

    assert [change.status for change in changes[2]] == ["broken"]
    assert "2026-W41 and 2026-W43" in changes[2][0].note


def test_a_broken_game_that_passes_two_weeks_in_a_row_is_restored() -> None:
    _, changes = run_weeks(
        [(W41, [seen("flagle", "ok", status="broken")]), (W42, [seen("flagle", "ok", status="broken")])]
    )

    assert changes[0] == []
    assert changes[1] == [ls.Change("flagle", "active", "restored", "link check: passes in 2026-W41 and 2026-W42")]


def test_a_broken_game_that_still_fails_stays_broken() -> None:
    _, changes = run_weeks([(week, [seen("flagle", "http-404", status="broken")]) for week in (W41, W42, W43, W44)])

    assert changes == [[], [], [], []]


def test_a_broken_game_that_passes_once_then_fails_is_not_restored() -> None:
    _, changes = run_weeks(
        [
            (W41, [seen("flagle", "ok", status="broken")]),
            (W42, [seen("flagle", "http-404", status="broken")]),
            (W43, [seen("flagle", "ok", status="broken")]),
        ]
    )

    assert changes == [[], [], []]


@pytest.mark.parametrize("status", ["active", "broken"])
def test_a_hijacked_game_is_retired_at_once(status: str) -> None:
    reason = 'redirects to another site (lucky-spin-777.net); its page title "Lucky Casino" contains "casino"'

    _, changes = run_weeks([(W42, [seen("moviedle", "hijacked", status=status, reason=reason)])])

    assert changes == [[ls.Change("moviedle", "retired", "retired", f"link check 2026-W42: {reason}")]]


def test_a_passing_active_game_is_not_tracked() -> None:
    state, _ = run_weeks([(W42, [seen("worldle", "ok")])])

    assert state == {"version": 1, "week": W42, "games": {}}


def test_notes_fit_the_schema() -> None:
    long = "x" * 500

    _, changes = run_weeks([(W41, [seen("moviedle", "http-404")]), (W42, [seen("moviedle", "http-404", reason=long)])])

    assert len(changes[1][0].note) == 300
    assert changes[1][0].note.endswith("…")


def test_state_survives_a_json_round_trip(tmp_path: Path) -> None:
    state, _ = ls.track([seen("moviedle", "http-404")], {}, W41)
    path = tmp_path / "state.json"

    ls.write_state(path, state)
    _, changes = ls.track([seen("moviedle", "http-404")], ls.load_state(path), W42)

    assert [change.status for change in changes] == ["broken"]


def test_a_missing_or_unreadable_state_is_empty(tmp_path: Path) -> None:
    assert ls.load_state(tmp_path / "missing.json") == {}
    garbage = tmp_path / "state.json"
    garbage.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match=r"state\.json"):
        ls.load_state(garbage)
    garbage.write_text('{"version": 99, "games": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="version"):
        ls.load_state(garbage)


def test_changes_survive_a_json_round_trip(tmp_path: Path) -> None:
    changes = [ls.Change("moviedle", "broken", "broken", "link check: http-404")]
    path = tmp_path / "changes.json"

    ls.write_changes(path, W42, changes)

    assert ls.load_changes(path) == changes


def catalog_games() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def test_applying_a_change_sets_the_status_and_appends_history() -> None:
    catalog = catalog_games()
    before = next(game for game in catalog["games"] if game["id"] == "worldle")
    history = list(before["history"])

    applied = ls.apply_changes(catalog, [ls.Change("worldle", "broken", "broken", "link check: http-404")], NOW)

    after = next(game for game in catalog["games"] if game["id"] == "worldle")
    assert applied == ["worldle"]
    assert after["status"] == "broken"
    assert after["history"] == [*history, {"date": "2026-10-18", "event": "broken", "note": "link check: http-404"}]
    assert catalog["generated_at"] == "2026-10-18T03:30:05Z"
    assert len(catalog["games"]) == len(catalog_games()["games"])


def test_applying_starts_a_missing_history_with_the_added_event() -> None:
    catalog = {"generated_at": "x", "games": [{"id": "a", "added": "2026-10-15", "status": "active"}]}

    ls.apply_changes(catalog, [ls.Change("a", "broken", "broken", "n")], NOW)

    assert catalog["games"][0]["history"] == [
        {"date": "2026-10-15", "event": "added"},
        {"date": "2026-10-18", "event": "broken", "note": "n"},
    ]


def test_a_change_that_is_already_made_is_skipped() -> None:
    catalog = {"generated_at": "x", "games": [{"id": "a", "added": "2026-10-15", "status": "broken", "history": []}]}

    applied = ls.apply_changes(catalog, [ls.Change("a", "broken", "broken", "n")], NOW)

    assert applied == []
    assert catalog == {
        "generated_at": "x",
        "games": [{"id": "a", "added": "2026-10-15", "status": "broken", "history": []}],
    }


def test_a_change_for_an_unknown_game_or_status_is_refused() -> None:
    catalog = {"generated_at": "x", "games": [{"id": "a", "added": "2026-10-15", "status": "active"}]}

    with pytest.raises(ValueError, match="nope"):
        ls.apply_changes(catalog, [ls.Change("nope", "broken", "broken", "n")], NOW)
    with pytest.raises(ValueError, match="gone"):
        ls.apply_changes(catalog, [ls.Change("a", "gone", "broken", "n")], NOW)


def test_the_catalog_is_written_byte_for_byte_as_committed() -> None:
    text = CATALOG.read_text(encoding="utf-8")

    assert ls.dump_catalog(json.loads(text)) == text
