"""Structural checks shared by the catalog and popularity parsers.

A `Fields` wraps one JSON object together with its path (for error messages) and the error class to raise, so
`catalog.parse` raises `CatalogError` and `popularity.parse` raises `PopularityError`. Only presence and JSON types
are checked, not the full JSON Schema: CI validates the published files against the schema, and the app only needs to
know that what it reads will not crash it.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Never, Self

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Fields:
    """One JSON object being read."""

    record: Mapping[str, object]
    where: str
    error: type[Exception]

    @classmethod
    def load(cls, data: bytes, error: type[Exception]) -> Self:
        """Decode a JSON document whose top level is an object with the `schema_version` this app understands."""
        try:
            document = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            msg = f"not valid JSON: {e}"
            raise error(msg) from e
        fields = cls.of(document, "$", error)
        if (version := fields.required("schema_version", int)) != SCHEMA_VERSION:
            fields.fail("schema_version", f"{version} is not {SCHEMA_VERSION}")
        return fields

    @classmethod
    def of(cls, value: object, where: str, error: type[Exception]) -> Self:
        """Wrap `value`, which must be a JSON object."""
        if not isinstance(value, dict):
            msg = f"{where}: {value!r} is not an object"
            raise error(msg)
        return cls(value, where, error)

    def fail(self, key: str, message: str) -> Never:
        """Raise this reader's error for `key`."""
        msg = f"{self.where}.{key}: {message}"
        raise self.error(msg)

    def required[T](self, key: str, kind: type[T]) -> T:
        """Return the value of `key`, which must be present and a `kind` (a bool does not count as an int)."""
        if key not in self.record:
            msg = f"{self.where}: missing required key {key!r}"
            raise self.error(msg)
        value = self.record[key]
        if not isinstance(value, kind) or (isinstance(value, bool) and kind is not bool):
            self.fail(key, f"{value!r} is not a {kind.__name__}")
        return value

    def optional[T, D](self, key: str, kind: type[T], default: D) -> T | D:
        """Return the value of `key` checked as in `required`, or `default` when the key is absent."""
        return self.required(key, kind) if key in self.record else default

    def objects(self, key: str) -> list[Self]:
        """Return the required list `key`, each item wrapped as an object."""
        return [
            type(self).of(item, f"{self.where}.{key}[{i}]", self.error)
            for i, item in enumerate(self.required(key, list))
        ]

    def strings(self, key: str) -> tuple[str, ...]:
        """Return the optional list of strings `key` as a tuple, empty when absent."""
        values = self.optional(key, list, [])
        if not all(isinstance(value, str) for value in values):
            self.fail(key, f"{values!r} is not a list of strings")
        return tuple(values)

    def timestamp(self, key: str) -> datetime:
        """Return the required RFC 3339 date-time `key`; it must carry a time zone so comparisons are well defined."""
        value = self.required(key, str)
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            self.fail(key, f"{value!r} is not a date-time")
        if parsed.tzinfo is None:
            self.fail(key, f"{value!r} has no time zone")
        return parsed

    def day(self, key: str) -> date:
        """Return the required ISO 8601 calendar date `key`."""
        value = self.required(key, str)
        try:
            return date.fromisoformat(value)
        except ValueError:
            self.fail(key, f"{value!r} is not a date")
