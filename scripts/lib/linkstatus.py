"""Turn the weekly link check's results into catalog status changes (issue #81).

The link check (scripts/check_links.py) remembers, per game, which check it failed (or, for a broken game, that it
passed) and in which ISO weeks, in a small JSON state file that the workflow keeps as an artifact between runs:

    {"version": 1, "week": "2026-W42",
     "games": {"moviedle": {"check": "http-404", "since": "2026-W41", "last": "2026-W42"}}}

From that state it proposes changes:
    - an active game that fails the same check in two consecutive weeks becomes `broken`, with a `broken` event;
    - a broken game that passes in two consecutive weeks becomes `active` again, with a `restored` event;
    - a game whose link redirects to another site with a gambling page title (outcome `hijacked`) is `retired` at once.

A second run in the same week (a manual run) does not count as another week, a skipped week starts over, and so does
any other result in between (a pass, another check, a bot wall). Entries are never deleted: a change only sets
`status` and appends a `history` event. Stdlib only, so the pull-request job needs no packages.
"""

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

STATE_VERSION = 1
STATUSES = frozenset({"active", "broken", "retired"})
EVENT = re.compile(r"^[a-z][a-z-]*$")
WEEK = re.compile(r"^(\d{4})-W(\d{2})$")
MAX_NOTE = 300
# Outcome names of scripts/check_links.py that the streaks treat specially.
OK = "ok"
WARNING = "bot-walled"
HIJACKED = "hijacked"


@dataclass(frozen=True)
class Observation:
    """One game's result in this week's link check: its catalog status, the outcome name and the reason."""

    id: str
    status: str
    outcome: str
    reason: str = ""


@dataclass(frozen=True)
class Change:
    """A status change for one catalog entry and the history event that records it."""

    id: str
    status: str
    event: str
    note: str


def iso_week(day: date) -> str:
    """The ISO week of a day, e.g. "2026-W42"."""
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def previous_week(week: str) -> str:
    """The ISO week before `week`."""
    match = WEEK.match(week)
    if match is None:
        msg = f"{week!r} is not an ISO week like 2026-W42"
        raise ValueError(msg)
    monday = date.fromisocalendar(int(match[1]), int(match[2]), 1)
    return iso_week(monday - timedelta(days=7))


def _note(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= MAX_NOTE else text[: MAX_NOTE - 1] + "…"


def _streak_key(observation: Observation) -> str | None:
    """What a game's streak counts: the failed check of an active game, a pass of a broken one, else nothing."""
    if observation.status == "active" and observation.outcome not in {OK, WARNING}:
        return observation.outcome
    if observation.status == "broken" and observation.outcome == OK:
        return OK
    return None


def track(observations: list[Observation], previous: dict[str, Any], week: str) -> tuple[dict[str, Any], list[Change]]:
    """Update the streaks with this week's observations.

    Args:
        observations: This run's result for every checked game.
        previous: The state the last run wrote, or {} without one.
        week: This run's ISO week.

    Returns:
        The new state, and the changes to propose, in the order of the observations.
    """
    earlier = previous.get("games", {})
    last_week = previous_week(week)
    games: dict[str, dict[str, str]] = {}
    changes: list[Change] = []
    for seen in observations:
        if seen.outcome == HIJACKED and seen.status in {"active", "broken"}:
            changes.append(Change(seen.id, "retired", "retired", _note(f"link check {week}: {seen.reason}")))
            continue
        key = _streak_key(seen)
        if key is None:
            continue
        before = earlier.get(seen.id)
        continued = before is not None and before.get("check") == key and before.get("last") in {week, last_week}
        since = before["since"] if continued else week
        games[seen.id] = {"check": key, "since": since, "last": week}
        if since == week:
            continue
        if key == OK:
            changes.append(Change(seen.id, "active", "restored", f"link check: passes in {since} and {week}"))
        else:
            note = f"link check: {key} in {since} and {week} ({seen.reason})"
            changes.append(Change(seen.id, "broken", "broken", _note(note)))
    return {"version": STATE_VERSION, "week": week, "games": games}, changes


def load_state(path: Path) -> dict[str, Any]:
    """The state a previous run wrote, or {} when there is none.

    Raises:
        ValueError: The file is not a state this version understands.
    """
    if not path.exists():
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        msg = f"{path} is not readable JSON ({error})"
        raise ValueError(msg) from error
    if not isinstance(state, dict) or state.get("version") != STATE_VERSION or not isinstance(state.get("games"), dict):
        msg = f"{path} is not a version {STATE_VERSION} link-check state"
        raise ValueError(msg)
    return state


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_state(path: Path, state: dict[str, Any]) -> None:
    """Write the state for the next run."""
    _write_json(path, state)


def write_changes(path: Path, week: str, changes: list[Change]) -> None:
    """Write the proposed changes for the pull-request job."""
    _write_json(path, {"week": week, "changes": [asdict(change) for change in changes]})


def load_changes(path: Path) -> list[Change]:
    """The changes write_changes wrote."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Change(**change) for change in data["changes"]]


def apply_changes(catalog: dict[str, Any], changes: list[Change], now: datetime) -> list[str]:
    """Set each change's status and append its history event, in place; never removes an entry.

    A change whose entry already has that status is skipped. When anything changed, `generated_at` becomes `now`.

    Returns:
        The ids of the entries that changed.

    Raises:
        ValueError: A change names an unknown game, status or event, and nothing was changed.
    """
    entries = {game["id"]: game for game in catalog["games"]}
    for change in changes:
        if change.status not in STATUSES:
            msg = f"{change.id}: unknown status {change.status!r}"
            raise ValueError(msg)
        if not EVENT.match(change.event) or len(change.note) > MAX_NOTE:
            msg = f"{change.id}: bad history event {change.event!r}"
            raise ValueError(msg)
        if change.id not in entries:
            msg = f"no catalog entry {change.id!r}"
            raise ValueError(msg)
    applied = []
    for change in changes:
        entry = entries[change.id]
        if entry.get("status") == change.status:
            continue
        entry["status"] = change.status
        # The catalog requires a history to start with the `added` event.
        history = entry.setdefault("history", [{"date": entry["added"], "event": "added"}])
        history.append({"date": now.date().isoformat(), "event": change.event, "note": change.note})
        applied.append(change.id)
    if applied:
        catalog["generated_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return applied


def dump_catalog(catalog: dict[str, Any]) -> str:
    """games.json text as committed: 2-space indent, keys in their order, UTF-8 without escaping, final newline."""
    return json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
