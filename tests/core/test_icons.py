from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path

import pytest

from dailies.core import icons
from dailies.core.cache import Outcome, Request, Response
from dailies.core.icons import IconCache, IconFetch

PNG = (Path(__file__).resolve().parents[2] / "data" / "v1" / "icons" / "worldle.png").read_bytes()
NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
DAY = timedelta(days=1)
URLS = ["https://pages.example/v1/", "https://raw.example/v1/"]
ICON = "icons/worldle.png"


@pytest.fixture
def cache(tmp_path: Path) -> IconCache:
    return IconCache(tmp_path / "dailies" / "v1" / "icons")


def fetch(cache: IconCache, icon: str = ICON, **kwargs: object) -> IconFetch:
    options = {"urls": URLS, "now": NOW}
    options.update(kwargs)
    return IconFetch(icon, cache, **options)


def snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


# What counts as an icon


def test_a_published_icon_is_an_icon() -> None:
    assert icons.is_icon(PNG)


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"<!doctype html><title>Not found</title>", id="an HTML page"),
        pytest.param(b"GIF89a" + PNG[6:], id="another format"),
        pytest.param(PNG + bytes(icons.MAX_BYTES), id="too large"),
    ],
)
def test_anything_else_is_not_an_icon(body: bytes) -> None:
    assert not icons.is_icon(body)


@pytest.mark.parametrize(("width", "height"), [(64, 64), (1, 1), (icons.MAX_SIDE, icons.MAX_SIDE), (16, 64)])
def test_a_decoded_icon_of_a_tile_size_fits(width: int, height: int) -> None:
    assert icons.fits(width, height)


@pytest.mark.parametrize(("width", "height"), [(0, 64), (64, 0), (icons.MAX_SIDE + 1, 64), (64, 20000)])
def test_an_empty_or_huge_decoded_icon_does_not_fit(width: int, height: int) -> None:
    assert not icons.fits(width, height)


# IconCache


def test_an_empty_cache_has_nothing(cache: IconCache) -> None:
    assert cache.read(ICON) is None
    assert cache.etag(ICON) is None
    assert cache.fetched_at(ICON) is None


def test_store_writes_the_png_its_etag_and_the_fetched_time(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW)

    assert cache.read(ICON) == PNG
    assert cache.etag(ICON) == '"abc"'
    assert cache.fetched_at(ICON) == NOW
    assert sorted(path.name for path in cache.path.iterdir()) == ["worldle.etag", "worldle.fetched", "worldle.png"]


def test_store_without_an_etag_removes_the_old_one(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW)
    cache.store(ICON, PNG, None, NOW)
    assert cache.etag(ICON) is None


def test_touch_only_changes_the_fetched_time(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW)

    cache.touch(ICON, NOW + DAY)

    assert cache.read(ICON) == PNG
    assert cache.etag(ICON) == '"abc"'
    assert cache.fetched_at(ICON) == NOW + DAY


@pytest.mark.parametrize("value", [b"yesterday", b"2026-10-17T12:00:00"])
def test_an_unreadable_or_naive_fetched_time_counts_as_never_fetched(cache: IconCache, value: bytes) -> None:
    cache.store(ICON, PNG, None, NOW)
    (cache.path / "worldle.fetched").write_bytes(value)
    assert cache.fetched_at(ICON) is None


def test_remove_deletes_every_file_of_the_icon(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW)
    cache.store("icons/wordle.png", PNG, '"def"', NOW)

    cache.remove(ICON)

    assert sorted(path.name for path in cache.path.iterdir()) == ["wordle.etag", "wordle.fetched", "wordle.png"]


def test_removing_what_was_never_cached_is_harmless(cache: IconCache) -> None:
    cache.remove(ICON)
    assert not cache.path.exists()


def test_prune_deletes_the_icons_the_catalog_no_longer_names(cache: IconCache) -> None:
    for icon in (ICON, "icons/wordle.png", "icons/taken-down.png"):
        cache.store(icon, PNG, '"abc"', NOW)

    assert cache.prune({ICON, "icons/wordle.png", "icons/not-cached-yet.png"}) == ["icons/taken-down.png"]

    assert cache.read("icons/taken-down.png") is None
    assert cache.etag("icons/taken-down.png") is None
    assert cache.read(ICON) == PNG
    assert cache.read("icons/wordle.png") == PNG


def test_prune_also_deletes_stray_files(cache: IconCache) -> None:
    cache.store(ICON, PNG, None, NOW)
    (cache.path / "notes.txt").write_bytes(b"left behind")

    cache.prune({ICON})

    assert sorted(path.name for path in cache.path.iterdir()) == ["worldle.fetched", "worldle.png"]


def test_prune_without_a_cache_directory_deletes_nothing(cache: IconCache) -> None:
    assert cache.prune(set()) == []


def test_writes_leave_no_temporary_files(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW)
    cache.touch(ICON, NOW + DAY)
    assert all(not path.name.startswith(".") for path in cache.path.iterdir())


@pytest.mark.parametrize("icon", ["../games.json", "icons/../x.png", "icons/Worldle.png", "worldle.png"])
def test_a_path_that_is_not_an_icon_is_refused(cache: IconCache, icon: str) -> None:
    with pytest.raises(ValueError, match="not an icon path"):
        cache.read(icon)


# IconFetch: the first request


def test_an_icon_never_fetched_is_requested_unconditionally_from_the_first_url(cache: IconCache) -> None:
    assert fetch(cache).first_request(metered=False) == Request("https://pages.example/v1/icons/worldle.png", {})


def test_an_icon_younger_than_a_week_makes_no_request(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW - 6 * DAY)
    refresh = fetch(cache)

    assert refresh.first_request(metered=False) is None
    assert refresh.outcome is Outcome.FRESH


def test_an_icon_older_than_a_week_is_revalidated_with_its_etag(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW - icons.MAX_AGE)

    request = fetch(cache).first_request(metered=False)

    assert request == Request("https://pages.example/v1/icons/worldle.png", {"If-None-Match": '"abc"'})


def test_an_etag_without_a_cached_png_is_not_sent(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW - icons.MAX_AGE)
    (cache.path / "worldle.png").unlink()

    assert fetch(cache).first_request(metered=False).headers == {}


@pytest.mark.parametrize("cached", [True, False])
def test_a_metered_network_makes_no_request(cache: IconCache, cached: bool) -> None:
    if cached:
        cache.store(ICON, PNG, '"abc"', NOW - 30 * DAY)
    refresh = fetch(cache)

    assert refresh.first_request(metered=True) is None
    assert refresh.outcome is Outcome.SKIPPED


def test_a_path_that_is_not_an_icon_is_never_fetched(cache: IconCache) -> None:
    with pytest.raises(ValueError, match="not an icon path"):
        fetch(cache, icon="../games.json")


# IconFetch: the answers


def test_200_with_an_icon_stores_it(cache: IconCache) -> None:
    refresh = fetch(cache)
    refresh.first_request(metered=False)

    assert refresh.handle(Response(HTTPStatus.OK, PNG, etag='"new"')) is None

    assert refresh.outcome is Outcome.UPDATED
    assert cache.read(ICON) == PNG
    assert cache.etag(ICON) == '"new"'
    assert cache.fetched_at(ICON) == NOW


def test_304_only_bumps_the_fetched_time(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW - 8 * DAY)
    refresh = fetch(cache)
    refresh.first_request(metered=False)

    assert refresh.handle(Response(HTTPStatus.NOT_MODIFIED)) is None

    assert refresh.outcome is Outcome.NOT_MODIFIED
    assert cache.read(ICON) == PNG
    assert cache.fetched_at(ICON) == NOW


def test_200_with_something_that_is_not_an_icon_keeps_the_cached_one(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW - 8 * DAY)
    before = snapshot(cache.path)
    refresh = fetch(cache)
    refresh.first_request(metered=False)

    assert refresh.handle(Response(HTTPStatus.OK, b"<html>captive portal</html>")) is None

    assert refresh.outcome is Outcome.FAILED
    assert snapshot(cache.path) == before


@pytest.mark.parametrize("status", [None, HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.BAD_GATEWAY])
def test_a_server_error_or_network_failure_falls_through_to_the_next_url(cache: IconCache, status: int | None) -> None:
    refresh = fetch(cache)
    refresh.first_request(metered=False)

    assert refresh.handle(Response(status)) == Request("https://raw.example/v1/icons/worldle.png", {})
    assert refresh.outcome is Outcome.PENDING


def test_a_later_url_can_succeed(cache: IconCache) -> None:
    refresh = fetch(cache)
    refresh.first_request(metered=False)
    refresh.handle(Response(HTTPStatus.SERVICE_UNAVAILABLE))

    assert refresh.handle(Response(HTTPStatus.OK, PNG)) is None

    assert refresh.outcome is Outcome.UPDATED
    assert cache.read(ICON) == PNG


def test_when_every_url_fails_the_fetch_fails_and_keeps_the_cached_icon(cache: IconCache) -> None:
    cache.store(ICON, PNG, '"abc"', NOW - 8 * DAY)
    refresh = fetch(cache)
    refresh.first_request(metered=False)
    refresh.handle(Response(None))

    assert refresh.handle(Response(None)) is None

    assert refresh.outcome is Outcome.FAILED
    assert cache.read(ICON) == PNG


@pytest.mark.parametrize("status", [HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN, HTTPStatus.MOVED_PERMANENTLY])
def test_another_status_fails_without_trying_further_urls(cache: IconCache, status: int) -> None:
    refresh = fetch(cache)
    refresh.first_request(metered=False)

    assert refresh.handle(Response(status)) is None
    assert refresh.outcome is Outcome.FAILED


@pytest.mark.parametrize(
    "response", [Response(HTTPStatus.OK, PNG), Response(HTTPStatus.NOT_MODIFIED)], ids=["200", "304"]
)
def test_a_cache_write_error_fails_the_fetch(tmp_path: Path, response: Response) -> None:
    blocked = tmp_path / "icons"
    blocked.write_bytes(b"a file where the directory should be")
    refresh = fetch(IconCache(blocked))
    refresh.first_request(metered=False)

    assert refresh.handle(response) is None
    assert refresh.outcome is Outcome.FAILED


def test_a_finished_fetch_ignores_further_responses(cache: IconCache) -> None:
    refresh = fetch(cache)
    refresh.first_request(metered=False)
    refresh.handle(Response(HTTPStatus.NOT_FOUND))

    assert refresh.handle(Response(HTTPStatus.OK, PNG)) is None
    assert refresh.outcome is Outcome.FAILED
    assert cache.read(ICON) is None


def test_an_unreadable_cache_is_an_empty_one(tmp_path: Path) -> None:
    blocked = tmp_path / "icons"
    blocked.write_bytes(b"a file where the directory should be")
    cache = IconCache(blocked)

    assert cache.read(ICON) is None
    assert cache.fetched_at(ICON) is None
    assert cache.prune(set()) == []
