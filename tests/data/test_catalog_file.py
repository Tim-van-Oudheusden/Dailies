"""Checks for the published data files in data/v1/.

The schema tests use `jsonschema` when it is installed. The structural checks below re-implement the small subset of
JSON Schema the two schemas use, so enums, required keys, patterns and formats are checked even with only pytest
installed.
"""

import copy
import json
import re
from datetime import date, datetime, timedelta
from functools import cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "v1"
GAMES = DATA / "games.json"
POPULARITY = DATA / "popularity.json"
CATALOG_SCHEMA = DATA / "schema" / "catalog.schema.json"
POPULARITY_SCHEMA = DATA / "schema" / "popularity.schema.json"

CATEGORIES = (
    "words",
    "geography",
    "music",
    "movies-tv",
    "video-games",
    "numbers-logic",
    "trivia",
    "visual",
    "food",
    "sports",
)
DIFFICULTIES = ("easy", "medium", "hard")
STATUSES = ("active", "broken", "retired")

# Hijacked or dead domains from docs/research/dle-catalog.md §1.4; they must never be catalog entries.
GRAVEYARD_DOMAINS = frozenset(
    {
        "absurdle.online",
        "cladder.app",
        "cladder.io",
        "cloudle.app",
        "foodle.io",
        "hollywoodle.com",
        "moviedle.app",
        "posterdle.com",
    }
)

# Multi-label public suffixes (a subset of https://publicsuffix.org/list/). Hosts under these get one more label in
# their registrable domain, e.g. foo.github.io is its own site. Extend this when an entry needs a suffix not listed.
MULTI_LABEL_PUBLIC_SUFFIXES = frozenset(
    {
        "co.jp",
        "co.nz",
        "co.uk",
        "com.au",
        "com.br",
        "firebaseapp.com",
        "github.io",
        "gitlab.io",
        "herokuapp.com",
        "netlify.app",
        "org.uk",
        "pages.dev",
        "vercel.app",
        "web.app",
    }
)

MAX_GAMES_BYTES = 100 * 1024
VALIDITY = timedelta(days=10)


@cache
def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def games() -> list[dict]:
    return load(GAMES)["games"]


def registrable_domain(host: str) -> str:
    """Return the eTLD+1 of `host` using the short suffix list above."""
    labels = host.lower().rstrip(".").split(".")
    for i in range(1, len(labels)):
        if ".".join(labels[i:]) in MULTI_LABEL_PUBLIC_SUFFIXES:
            return ".".join(labels[i - 1 :])
    return ".".join(labels[-2:])


def normalise_url(url: str) -> str:
    """Lower-case the host, drop `www.`, the trailing slash, the fragment and `utm_*` parameters."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    host = host.removeprefix("www.")
    if parts.port:
        host = f"{host}:{parts.port}"
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.startswith("utm_")])
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/"), query, ""))


# --- A JSON Schema subset, enough for data/v1/schema/*.json ---------------------------------------------------------

ANNOTATION_KEYWORDS = frozenset({"$schema", "$id", "$defs", "title", "description", "default"})
CHECKED_KEYWORDS = frozenset(
    {
        "$ref",
        "type",
        "const",
        "enum",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "format",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "minItems",
        "maxItems",
        "uniqueItems",
    }
)
TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, int | float) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def is_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None


def is_date_time(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return "T" in value and parsed.tzinfo is not None


FORMATS = {"date": is_date, "date-time": is_date_time}


def check_scalar(value: object, schema: dict, where: str) -> list[str]:
    errors = []
    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: {value!r} is not {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} is not one of {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{where}: {value!r} does not match {schema['pattern']}")
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", len(value)):
            errors.append(f"{where}: length {len(value)} is out of range")
        check = FORMATS.get(schema.get("format", ""))
        if check and not check(value):
            errors.append(f"{where}: {value!r} is not a valid {schema['format']}")
    if TYPES["number"](value) and not schema.get("minimum", value) <= value <= schema.get("maximum", value):
        errors.append(f"{where}: {value!r} is out of range")
    return errors


def check_object(value: dict, schema: dict, root: dict, where: str) -> list[str]:
    errors = [f"{where}: missing required key {key!r}" for key in schema.get("required", []) if key not in value]
    properties = schema.get("properties", {})
    extra = schema.get("additionalProperties", True)
    for key, item in value.items():
        if key in properties:
            errors += check(item, properties[key], root, f"{where}.{key}")
        elif extra is False:
            errors.append(f"{where}: unexpected key {key!r}")
        elif isinstance(extra, dict):
            errors += check(item, extra, root, f"{where}.{key}")
    return errors


def check_array(value: list, schema: dict, root: dict, where: str) -> list[str]:
    errors = []
    if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", len(value)):
        errors.append(f"{where}: {len(value)} items is out of range")
    if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
        errors.append(f"{where}: items are not unique")
    if "items" in schema:
        for i, item in enumerate(value):
            errors += check(item, schema["items"], root, f"{where}[{i}]")
    return errors


def check(value: object, schema: dict, root: dict, where: str = "$") -> list[str]:
    """Validate `value` against `schema`; return human-readable errors (empty when valid)."""
    if "$ref" in schema:
        _, _, name = schema["$ref"].rpartition("/")
        schema = root["$defs"][name]
    types = schema.get("type")
    if types is not None:
        allowed = [types] if isinstance(types, str) else types
        if not any(TYPES[t](value) for t in allowed):
            return [f"{where}: {value!r} is not of type {types}"]
    errors = check_scalar(value, schema, where)
    if isinstance(value, dict):
        errors += check_object(value, schema, root, where)
    if isinstance(value, list):
        errors += check_array(value, schema, root, where)
    return errors


def schema_keywords(schema: dict) -> set[str]:
    found = set(schema)
    children = [*schema.get("properties", {}).values(), *schema.get("$defs", {}).values()]
    children += [schema[k] for k in ("items", "additionalProperties") if isinstance(schema.get(k), dict)]
    for child in children:
        found |= schema_keywords(child)
    return found


# --- Schemas and files ----------------------------------------------------------------------------------------------

FILE_PAIRS = [(GAMES, CATALOG_SCHEMA), (POPULARITY, POPULARITY_SCHEMA)]
FILE_IDS = ["games", "popularity"]


@pytest.mark.parametrize(("data_path", "schema_path"), FILE_PAIRS, ids=FILE_IDS)
def test_file_validates_against_its_schema(data_path: Path, schema_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    validator_class = jsonschema.Draft202012Validator
    schema = load(schema_path)
    validator_class.check_schema(schema)
    validator = validator_class(schema, format_checker=validator_class.FORMAT_CHECKER)
    assert [error.message for error in validator.iter_errors(load(data_path))] == []


@pytest.mark.parametrize(("data_path", "schema_path"), FILE_PAIRS, ids=FILE_IDS)
def test_file_passes_structural_checks(data_path: Path, schema_path: Path) -> None:
    assert check(load(data_path), load(schema_path), load(schema_path)) == []


@pytest.mark.parametrize("schema_path", [CATALOG_SCHEMA, POPULARITY_SCHEMA], ids=FILE_IDS)
def test_structural_checks_understand_every_schema_keyword(schema_path: Path) -> None:
    assert schema_keywords(load(schema_path)) <= CHECKED_KEYWORDS | ANNOTATION_KEYWORDS


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("id", "Bad_Id"),
        ("url", "http://example.com/"),
        ("category", "other"),
        ("difficulty", "extreme"),
        ("status", "removed"),
        ("description", "Too short."),
        ("added", "15-10-2026"),
        ("free_no_account", "yes"),
        ("tags", ["Not Kebab"]),
    ],
)
def test_structural_checks_reject_a_bad_entry(field: str, bad_value: object) -> None:
    schema = load(CATALOG_SCHEMA)
    entry = copy.deepcopy(games()[0])
    entry[field] = bad_value
    assert check(entry, schema["$defs"]["game"], schema) != []


def test_structural_checks_reject_a_missing_domain() -> None:
    schema = load(CATALOG_SCHEMA)
    entry = copy.deepcopy(games()[0])
    del entry["domain"]
    assert check(entry, schema["$defs"]["game"], schema) == ["$: missing required key 'domain'"]


def test_schema_enums_are_the_agreed_taxonomy() -> None:
    game = load(CATALOG_SCHEMA)["$defs"]["game"]["properties"]
    assert tuple(game["category"]["enum"]) == CATEGORIES
    assert tuple(game["difficulty"]["enum"]) == DIFFICULTIES
    assert tuple(game["status"]["enum"]) == STATUSES


def test_every_enum_value_is_valid() -> None:
    for game in games():
        assert game["category"] in CATEGORIES, game["id"]
        assert game["difficulty"] in DIFFICULTIES, game["id"]
        assert game["status"] in STATUSES, game["id"]


# --- games.json -----------------------------------------------------------------------------------------------------


def test_ids_are_unique_and_sorted() -> None:
    ids = [game["id"] for game in games()]
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids)


def test_normalised_urls_are_unique() -> None:
    seen: dict[str, str] = {}
    for game in games():
        url = normalise_url(game["url"])
        assert url not in seen, f"{game['id']} duplicates {seen[url]}"
        seen[url] = game["id"]


def test_domain_is_the_registrable_domain_of_the_url() -> None:
    for game in games():
        assert game["domain"] == registrable_domain(urlsplit(game["url"]).hostname or ""), game["id"]


def test_no_entry_uses_a_graveyard_domain() -> None:
    assert {game["domain"] for game in games()}.isdisjoint(GRAVEYARD_DOMAINS)


def test_history_starts_with_the_added_event() -> None:
    for game in games():
        first = game["history"][0]
        assert (first["event"], first["date"]) == ("added", game["added"]), game["id"]


def test_every_category_has_an_active_game() -> None:
    active = {game["category"] for game in games() if game["status"] == "active"}
    assert active == set(CATEGORIES)


def test_games_file_is_small() -> None:
    assert GAMES.stat().st_size < MAX_GAMES_BYTES


def test_games_file_is_two_space_json_with_a_final_newline() -> None:
    text = GAMES.read_text(encoding="utf-8")
    assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"


# --- popularity.json ------------------------------------------------------------------------------------------------


def test_popularity_ids_exist_in_the_catalog() -> None:
    known = {game["id"] for game in games()}
    popularity = load(POPULARITY)
    for shelf in ("popular", "trending"):
        assert {item["id"] for item in popularity[shelf]} <= known, shelf


@pytest.mark.parametrize("shelf", ["popular", "trending"])
def test_popularity_shelves_are_ranked(shelf: str) -> None:
    items = load(POPULARITY)[shelf]
    assert [item["rank"] for item in items] == list(range(1, len(items) + 1))
    assert len({item["id"] for item in items}) == len(items)
    scores = [item["score"] for item in items]
    assert scores == sorted(scores, reverse=True)


def test_popularity_is_valid_for_ten_days_of_its_week() -> None:
    popularity = load(POPULARITY)
    generated = datetime.fromisoformat(popularity["generated_at"])
    assert datetime.fromisoformat(popularity["valid_until"]) - generated == VALIDITY
    year, week, _ = generated.isocalendar()
    assert popularity["week"] == f"{year}-W{week:02d}"


# --- helpers --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("worldle.teuteuf.fr", "teuteuf.fr"),
        ("www.nytimes.com", "nytimes.com"),
        ("qntm.org", "qntm.org"),
        ("term.ooo", "term.ooo"),
        ("games.oec.world", "oec.world"),
        ("jonesnxt.github.io", "jonesnxt.github.io"),
        ("crosswordle.vercel.app", "crosswordle.vercel.app"),
        ("www.example.co.uk", "example.co.uk"),
        ("WWW.Example.com.", "example.com"),
    ],
)
def test_registrable_domain(host: str, expected: str) -> None:
    assert registrable_domain(host) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.Example.com/", "https://example.com"),
        ("https://example.com/game/?utm_source=x&level=2", "https://example.com/game?level=2"),
        ("https://example.com/game#today", "https://example.com/game"),
    ],
)
def test_normalise_url(url: str, expected: str) -> None:
    assert normalise_url(url) == expected
