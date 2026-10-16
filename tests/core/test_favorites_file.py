import json

import pytest

from dailies.core import favorites_file
from dailies.core.favorites_file import FavoritesFileError, ImportMode


def test_dump_writes_the_versioned_document_as_utf8_two_space_json() -> None:
    data = favorites_file.dump(["worldle", "connections"])

    assert (
        data.decode("utf-8")
        == '{\n  "schema_version": 1,\n  "favorites": [\n    "worldle",\n    "connections"\n  ]\n}\n'
    )
    assert json.loads(data) == {"schema_version": 1, "favorites": ["worldle", "connections"]}


def test_parse_reads_back_what_dump_wrote_in_order() -> None:
    ids = ["worldle", "connections", "géo-dle"]
    assert favorites_file.parse(favorites_file.dump(ids)) == ids


@pytest.mark.parametrize("data", [b"", b'{"schema_version": 1, "favorites": [', b"\xff\xfe", b"not json"])
def test_malformed_json_is_rejected(data: bytes) -> None:
    with pytest.raises(FavoritesFileError, match="not valid JSON"):
        favorites_file.parse(data)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b'["worldle"]', "is not an object"),
        (b'{"favorites": ["worldle"]}', "missing required key 'schema_version'"),
        (b'{"schema_version": 2, "favorites": ["worldle"]}', "2 is not 1"),
        (b'{"schema_version": "1", "favorites": ["worldle"]}', "is not a int"),
        (b'{"schema_version": true, "favorites": ["worldle"]}', "is not a int"),
        (b'{"schema_version": 1}', "missing required key 'favorites'"),
        (b'{"schema_version": 1, "favorites": "worldle"}', "is not a list"),
    ],
)
def test_a_document_of_the_wrong_shape_or_version_is_rejected(data: bytes, message: str) -> None:
    with pytest.raises(FavoritesFileError, match=message):
        favorites_file.parse(data)


@pytest.mark.parametrize("ids", [["worldle", 3], ["worldle", None], [["worldle"]], ["worldle", ""], ["  "]])
def test_ids_must_be_non_empty_strings(ids: list[object]) -> None:
    data = json.dumps({"schema_version": 1, "favorites": ids}).encode()
    with pytest.raises(FavoritesFileError, match="is not a game id"):
        favorites_file.parse(data)


def test_a_duplicate_id_is_rejected() -> None:
    data = b'{"schema_version": 1, "favorites": ["worldle", "globle", "worldle"]}'
    with pytest.raises(FavoritesFileError, match="'worldle' is listed twice"):
        favorites_file.parse(data)


def test_merge_appends_the_unknown_ids_in_file_order_and_keeps_the_existing_order() -> None:
    current = ["globle", "worldle"]
    imported = ["connections", "worldle", "framed", "globle"]

    assert favorites_file.combine(current, imported, ImportMode.MERGE) == ["globle", "worldle", "connections", "framed"]


def test_replace_takes_the_file_order() -> None:
    current = ["globle", "worldle"]
    imported = ["connections", "worldle"]

    assert favorites_file.combine(current, imported, ImportMode.REPLACE) == ["connections", "worldle"]
