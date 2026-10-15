from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dailies.core import cache
from dailies.core.cache import Backoff, CacheDir, Outcome, Refresh, Request, Response

DATA = Path(__file__).resolve().parents[2] / "data" / "v1"
GAMES = (DATA / "games.json").read_bytes()
POPULARITY = (DATA / "popularity.json").read_bytes()
NOW = datetime(2026, 10, 15, 12, tzinfo=UTC)
DAY = timedelta(days=1)
URLS = ["https://pages.example/v1/", "https://raw.example/v1/"]


@pytest.fixture
def cache_dir(tmp_path: Path) -> CacheDir:
    return CacheDir(tmp_path / "dailies" / "v1")


def refresh(cache_dir: CacheDir, name: str = "games", **kwargs: object) -> Refresh:
    options = {"urls": URLS, "now": NOW, "backoff": Backoff()}
    options.update(kwargs)
    return Refresh(name, cache_dir, **options)


def snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


# CacheDir


def test_an_empty_cache_has_nothing(cache_dir: CacheDir) -> None:
    assert cache_dir.read("games") is None
    assert cache_dir.etag("games") is None
    assert cache_dir.fetched_at("games") is None


def test_store_writes_body_etag_and_fetched_time(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, '"abc"', NOW)

    assert cache_dir.read("games") == GAMES
    assert cache_dir.etag("games") == '"abc"'
    assert cache_dir.fetched_at("games") == NOW
    assert sorted(path.name for path in cache_dir.path.iterdir()) == ["games.etag", "games.fetched", "games.json"]


def test_store_without_an_etag_removes_the_old_one(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, '"abc"', NOW)
    cache_dir.store("games", GAMES, None, NOW)
    assert cache_dir.etag("games") is None


def test_touch_only_changes_the_fetched_time(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, '"abc"', NOW)
    later = NOW + timedelta(hours=7)

    cache_dir.touch("games", later)

    assert cache_dir.fetched_at("games") == later
    assert cache_dir.read("games") == GAMES
    assert cache_dir.etag("games") == '"abc"'


def test_seed_writes_the_body_and_forgets_etag_and_fetched_time(cache_dir: CacheDir) -> None:
    cache_dir.store("games", b"corrupt", '"abc"', NOW)

    cache_dir.seed("games", GAMES)

    assert cache_dir.read("games") == GAMES
    assert cache_dir.etag("games") is None
    assert cache_dir.fetched_at("games") is None


def test_an_unreadable_fetched_time_counts_as_never_fetched(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW)
    (cache_dir.path / "games.fetched").write_text("yesterday")
    assert cache_dir.fetched_at("games") is None


def test_a_naive_fetched_time_counts_as_never_fetched(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW)
    (cache_dir.path / "games.fetched").write_text("2026-10-15T12:00:00")
    assert cache_dir.fetched_at("games") is None


def test_a_fetched_time_edited_by_hand_may_end_in_a_newline(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW)
    (cache_dir.path / "games.fetched").write_text("2026-10-01T00:00:00+00:00\n")
    assert cache_dir.fetched_at("games") == datetime(2026, 10, 1, tzinfo=UTC)


def test_writes_leave_no_temporary_files(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, '"abc"', NOW)
    cache_dir.touch("games", NOW)
    cache_dir.seed("popularity", POPULARITY)
    assert not [path for path in cache_dir.path.iterdir() if path.suffix not in {".json", ".etag", ".fetched"}]


# Retry-After


def test_retry_after_in_seconds() -> None:
    assert cache.parse_retry_after("120", NOW, longest=DAY) == NOW + timedelta(seconds=120)


def test_retry_after_as_an_http_date() -> None:
    assert cache.parse_retry_after("Thu, 15 Oct 2026 13:00:00 GMT", NOW, longest=DAY) == NOW + timedelta(hours=1)


def test_retry_after_as_an_http_date_without_a_zone_is_utc() -> None:
    assert cache.parse_retry_after("Thu, 15 Oct 2026 13:00:00 -0000", NOW, longest=DAY) == NOW + timedelta(hours=1)


@pytest.mark.parametrize("value", ["300000000000", "9" * 400, "Fri, 31 Dec 9999 23:59:59 GMT"])
def test_retry_after_is_capped_at_the_longest_deferral(value: str) -> None:
    assert cache.parse_retry_after(value, NOW, longest=DAY) == NOW + DAY


@pytest.mark.parametrize("value", [None, "", "soon", "-5", "Thu, 99 Foo 2026"])
def test_a_missing_or_unreadable_retry_after_is_ignored(value: str | None) -> None:
    assert cache.parse_retry_after(value, NOW, longest=DAY) is None


# Backoff


def test_backoff_allows_a_url_until_deferred_and_again_once_the_time_has_passed() -> None:
    backoff = Backoff()
    assert backoff.allows(URLS[0], NOW)

    backoff.defer(URLS[0], NOW + timedelta(minutes=5))

    assert not backoff.allows(URLS[0], NOW + timedelta(minutes=4))
    assert backoff.allows(URLS[0], NOW + timedelta(minutes=5))
    assert backoff.allows(URLS[1], NOW)


# When a refresh asks


def test_a_fresh_file_makes_no_request(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, '"abc"', NOW - timedelta(hours=5, minutes=59))
    plan = refresh(cache_dir)
    assert plan.first_request() is None
    assert plan.outcome is Outcome.FRESH


def test_max_age_is_six_hours_for_the_catalog_and_a_day_for_popularity(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW - timedelta(hours=6))
    cache_dir.store("popularity", POPULARITY, None, NOW - timedelta(hours=23))

    assert refresh(cache_dir, "games").first_request() is not None
    assert refresh(cache_dir, "popularity").first_request() is None


def test_force_asks_even_when_fresh(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW)
    assert refresh(cache_dir).first_request(force=True) is not None


def test_a_file_never_fetched_is_requested_unconditionally_from_the_first_url(cache_dir: CacheDir) -> None:
    cache_dir.seed("games", GAMES)
    assert refresh(cache_dir).first_request() == Request("https://pages.example/v1/games.json", {})


def test_a_stale_file_with_an_etag_sends_if_none_match(cache_dir: CacheDir) -> None:
    cache_dir.store("popularity", POPULARITY, '"abc"', NOW - timedelta(days=2))
    assert refresh(cache_dir, "popularity").first_request() == Request(
        "https://pages.example/v1/popularity.json", {"If-None-Match": '"abc"'}
    )


def test_an_etag_without_a_cached_body_is_not_sent(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, '"abc"', NOW - timedelta(days=1))
    (cache_dir.path / "games.json").unlink()
    assert refresh(cache_dir).first_request().headers == {}


def test_an_unknown_file_name_is_rejected(cache_dir: CacheDir) -> None:
    with pytest.raises(ValueError, match="scores"):
        refresh(cache_dir, "scores")


# How a refresh handles answers


def test_304_only_bumps_the_fetched_time(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, '"abc"', NOW - timedelta(days=1))
    before = snapshot(cache_dir.path)
    plan = refresh(cache_dir)
    plan.first_request()

    assert plan.handle(Response(304)) is None

    assert plan.outcome is Outcome.NOT_MODIFIED
    after = snapshot(cache_dir.path)
    assert {name for name in after if after[name] != before[name]} == {"games.fetched"}
    assert cache_dir.fetched_at("games") == NOW


def test_200_with_a_valid_body_replaces_the_cache(cache_dir: CacheDir) -> None:
    cache_dir.seed("popularity", b"{}")
    plan = refresh(cache_dir, "popularity")
    plan.first_request()

    assert plan.handle(Response(200, POPULARITY, etag='"new"')) is None

    assert plan.outcome is Outcome.UPDATED
    assert cache_dir.read("popularity") == POPULARITY
    assert cache_dir.etag("popularity") == '"new"'
    assert cache_dir.fetched_at("popularity") == NOW


def test_200_with_a_corrupt_body_leaves_the_cache_untouched(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, '"abc"', NOW - timedelta(days=1))
    before = snapshot(cache_dir.path)
    plan = refresh(cache_dir)
    plan.first_request()

    assert plan.handle(Response(200, GAMES[: len(GAMES) // 2], etag='"new"')) is None

    assert plan.outcome is Outcome.FAILED
    assert snapshot(cache_dir.path) == before


def test_200_with_the_wrong_kind_of_file_is_rejected(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW - timedelta(days=1))
    plan = refresh(cache_dir)
    plan.first_request()

    plan.handle(Response(200, POPULARITY))

    assert plan.outcome is Outcome.FAILED
    assert cache_dir.read("games") == GAMES


@pytest.mark.parametrize("status", [None, 429, 500, 502, 503])
def test_a_server_error_or_network_failure_falls_through_to_the_next_url(cache_dir: CacheDir, status: int) -> None:
    cache_dir.store("games", GAMES, '"abc"', NOW - timedelta(days=1))
    plan = refresh(cache_dir)
    plan.first_request()

    assert plan.handle(Response(status)) == Request("https://raw.example/v1/games.json", {"If-None-Match": '"abc"'})


@pytest.mark.parametrize("status", [301, 403, 404])
def test_another_status_fails_without_trying_further_urls(cache_dir: CacheDir, status: int) -> None:
    cache_dir.store("games", GAMES, None, NOW - timedelta(days=1))
    plan = refresh(cache_dir)
    plan.first_request()

    assert plan.handle(Response(status)) is None
    assert plan.outcome is Outcome.FAILED


def test_each_url_is_tried_once_and_the_last_failure_fails_the_refresh(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW - timedelta(days=1))
    before = snapshot(cache_dir.path)
    plan = refresh(cache_dir)
    plan.first_request()
    plan.handle(Response(503))

    assert plan.handle(Response(None)) is None

    assert plan.outcome is Outcome.FAILED
    assert snapshot(cache_dir.path) == before


def test_a_later_url_can_succeed(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, '"abc"', NOW - timedelta(days=1))
    plan = refresh(cache_dir)
    plan.first_request()
    plan.handle(Response(500))

    assert plan.handle(Response(304)) is None
    assert plan.outcome is Outcome.NOT_MODIFIED


def test_retry_after_defers_that_url_for_later_refreshes(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW - timedelta(days=1))
    backoff = Backoff()
    plan = refresh(cache_dir, backoff=backoff)
    plan.first_request()
    plan.handle(Response(429, retry_after="600"))
    plan.handle(Response(200, GAMES))

    soon = refresh(cache_dir, now=NOW + timedelta(minutes=9), backoff=backoff)
    later = refresh(cache_dir, now=NOW + timedelta(minutes=10), backoff=backoff)

    assert soon.first_request(force=True).url == "https://raw.example/v1/games.json"
    assert later.first_request(force=True).url == "https://pages.example/v1/games.json"


@pytest.mark.parametrize("retry_after", ["Thu, 15 Oct 2026 13:00:00 -0000", "300000000000"])
def test_an_odd_retry_after_still_falls_through_and_defers_at_most_the_max_age(
    cache_dir: CacheDir, retry_after: str
) -> None:
    cache_dir.store("games", GAMES, None, NOW - timedelta(days=1))
    backoff = Backoff()
    plan = refresh(cache_dir, backoff=backoff)
    plan.first_request()

    assert plan.handle(Response(503, retry_after=retry_after)).url == "https://raw.example/v1/games.json"

    assert not backoff.allows("https://pages.example/v1/games.json", NOW)
    assert backoff.allows("https://pages.example/v1/games.json", NOW + timedelta(hours=6))


class FullDisk(CacheDir):
    def touch(self, *_args: object) -> None:
        raise OSError(28, "No space left on device")

    def store(self, *_args: object) -> None:
        raise OSError(30, "Read-only file system")


@pytest.mark.parametrize("response", [Response(304), Response(200, GAMES, etag='"new"')])
def test_a_cache_write_error_fails_the_refresh_and_keeps_the_saved_copy(tmp_path: Path, response: Response) -> None:
    full = FullDisk(tmp_path)
    CacheDir(tmp_path).store("games", GAMES, '"abc"', NOW - timedelta(days=1))
    before = snapshot(tmp_path)
    plan = refresh(full)
    plan.first_request()

    assert plan.handle(response) is None

    assert plan.outcome is Outcome.FAILED
    assert snapshot(tmp_path) == before


def test_when_every_url_is_deferred_there_is_no_request_and_the_refresh_fails(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW - timedelta(days=1))
    backoff = Backoff()
    for url in URLS:
        backoff.defer(f"{url}games.json", NOW + timedelta(hours=1))
    plan = refresh(cache_dir, backoff=backoff)

    assert plan.first_request() is None
    assert plan.outcome is Outcome.FAILED


def test_the_outcome_is_pending_until_the_refresh_ends(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW - timedelta(days=1))
    plan = refresh(cache_dir)
    assert plan.outcome is Outcome.PENDING
    plan.first_request()
    assert plan.outcome is Outcome.PENDING


def test_a_finished_refresh_ignores_further_responses(cache_dir: CacheDir) -> None:
    cache_dir.store("games", GAMES, None, NOW - timedelta(days=1))
    plan = refresh(cache_dir)
    plan.first_request()
    plan.handle(Response(404))

    assert plan.handle(Response(200, GAMES)) is None
    assert plan.outcome is Outcome.FAILED


# Banner


def test_the_stale_banner_needs_an_old_success_and_a_network() -> None:
    old = NOW - timedelta(days=14, seconds=1)
    assert cache.needs_stale_banner(old, NOW, online=True)
    assert not cache.needs_stale_banner(old, NOW, online=False)
    assert not cache.needs_stale_banner(NOW - timedelta(days=14), NOW, online=True)


def test_no_stale_banner_before_the_first_success() -> None:
    assert not cache.needs_stale_banner(None, NOW, online=True)


@pytest.mark.parametrize(
    ("outcomes", "expected"),
    [
        ({"games": Outcome.UPDATED, "popularity": Outcome.NOT_MODIFIED}, Outcome.UPDATED),
        ({"games": Outcome.NOT_MODIFIED, "popularity": Outcome.UPDATED}, Outcome.UPDATED),
        ({"games": Outcome.NOT_MODIFIED, "popularity": Outcome.FRESH}, Outcome.NOT_MODIFIED),
        ({"games": Outcome.FRESH, "popularity": Outcome.FRESH}, Outcome.NOT_MODIFIED),
        ({"games": Outcome.FAILED, "popularity": Outcome.NOT_MODIFIED}, Outcome.FAILED),
        # A failure wins over an update: the user should know that trying again may help.
        ({"games": Outcome.UPDATED, "popularity": Outcome.FAILED}, Outcome.FAILED),
        ({"games": Outcome.SKIPPED, "popularity": Outcome.SKIPPED}, Outcome.SKIPPED),
        ({"games": Outcome.SKIPPED, "popularity": Outcome.UPDATED}, Outcome.UPDATED),
    ],
)
def test_summarize_refresh_outcomes(outcomes: dict[str, Outcome], expected: Outcome) -> None:
    assert cache.summarize(outcomes) is expected
