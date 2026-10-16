from pathlib import PurePosixPath

import pytest

from dailies.core.web import (
    SessionIsolation,
    all_sessions,
    cookie_accept_policy,
    custom_user_agent,
    display_host,
    game_settings_path,
    hardware_acceleration_policy,
    isolated_session_toggle,
    session_dir,
    site_matches,
)


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        ("https://www.nytimes.com/games/wordle/index.html", "www.nytimes.com"),
        ("https://WWW.Example.ORG:8443/path?q=1#x", "www.example.org"),
        # The real host, not what the user name part pretends to be.
        ("https://www.nytimes.com@evil.example/", "evil.example"),
        # Internationalised hosts stay in their ASCII form, so look-alike letters cannot pose as another site.
        ("https://xn--80ak6aa92e.com/", "xn--80ak6aa92e.com"),
        ("http://127.0.0.1:8000/test.html", "127.0.0.1"),
        ("about:blank", ""),
        ("", ""),
        (None, ""),
    ],
)
def test_display_host(uri: str | None, expected: str) -> None:
    assert display_host(uri) == expected


@pytest.mark.parametrize(
    ("name", "host"),
    [
        ("nytimes.com", "nytimes.com"),
        ("nytimes.com", "www.nytimes.com"),
        ("NYTimes.com", "www.nytimes.com"),
        (".nytimes.com", "www.nytimes.com"),
        ("www.nytimes.com", "www.nytimes.com"),
    ],
)
def test_website_data_of_the_site_and_its_parent_domain_matches(name: str, host: str) -> None:
    assert site_matches(name, host)


@pytest.mark.parametrize(
    ("name", "host"),
    [
        ("nytimes.com", "notnytimes.com"),
        ("games.nytimes.com", "www.nytimes.com"),
        ("example.com", "www.nytimes.com"),
        ("nytimes.com", ""),
        ("", "www.nytimes.com"),
    ],
)
def test_website_data_of_other_sites_does_not_match(name: str, host: str) -> None:
    assert not site_matches(name, host)


@pytest.mark.parametrize(
    ("isolation", "game_id", "isolated", "expected"),
    [
        # Shared (the default): every game uses the one session of v0.1, so sibling games share a login.
        (SessionIsolation.SHARED, "wordle", False, PurePosixPath("shared")),
        (SessionIsolation.SHARED, "connections", False, PurePosixPath("shared")),
        # Per game: a directory of its own for every game.
        (SessionIsolation.PER_GAME, "wordle", False, PurePosixPath("games/wordle")),
        (SessionIsolation.PER_GAME, "connections", False, PurePosixPath("games/connections")),
        # A game's `isolated-session` key isolates it even while the others share.
        (SessionIsolation.SHARED, "wordle", True, PurePosixPath("games/wordle")),
        (SessionIsolation.PER_GAME, "wordle", True, PurePosixPath("games/wordle")),
        # A game whose id is not a catalog slug never names a directory: it shares.
        (SessionIsolation.PER_GAME, "../shared", False, PurePosixPath("shared")),
        (SessionIsolation.PER_GAME, "a/b", True, PurePosixPath("shared")),
        (SessionIsolation.PER_GAME, "", False, PurePosixPath("shared")),
        (SessionIsolation.PER_GAME, "Wordle", False, PurePosixPath("shared")),
        (SessionIsolation.PER_GAME, None, False, PurePosixPath("shared")),
    ],
)
def test_session_dir(isolation: SessionIsolation, game_id: str | None, isolated: bool, expected: PurePosixPath) -> None:
    assert session_dir(isolation, game_id, isolated=isolated) == expected


def test_session_isolation_reads_the_setting_nicks() -> None:
    assert [SessionIsolation.from_id(nick) for nick in ("shared", "per-game")] == list(SessionIsolation)
    assert SessionIsolation.from_id("telepathy") is SessionIsolation.SHARED


@pytest.mark.parametrize(
    ("isolation", "isolated", "expected"),
    [
        # While games share, the toggle shows the game's own `isolated-session` key and changes it.
        (SessionIsolation.SHARED, False, (False, True)),
        (SessionIsolation.SHARED, True, (True, True)),
        # Per game, every game already has a session of its own: checked, and nothing to change.
        (SessionIsolation.PER_GAME, False, (True, False)),
        (SessionIsolation.PER_GAME, True, (True, False)),
    ],
)
def test_isolated_session_toggle_is_checked_and_changeable(
    isolation: SessionIsolation, isolated: bool, expected: tuple[bool, bool]
) -> None:
    assert isolated_session_toggle(isolation, isolated=isolated) == expected


def test_every_session_on_disk_is_cleared_including_ones_not_opened_in_this_run() -> None:
    on_disk = ["wordle", "connections", "not a game", "..", "Wordle", "connections"]

    assert all_sessions(on_disk) == [
        PurePosixPath("shared"),
        PurePosixPath("games/connections"),
        PurePosixPath("games/wordle"),
    ]


def test_the_shared_session_is_always_cleared() -> None:
    assert all_sessions([]) == [PurePosixPath("shared")]


@pytest.mark.parametrize(
    ("nick", "expected"),
    [
        # The default keeps v0.1: log-in flows (the New York Times) set cookies from third-party domains.
        ("always", "ALWAYS"),
        ("no-third-party", "NO_THIRD_PARTY"),
        ("never", "NEVER"),
        ("telepathy", "ALWAYS"),
    ],
)
def test_cookie_policy_names_the_webkit_accept_policy(nick: str, expected: str) -> None:
    assert cookie_accept_policy(nick) == expected


@pytest.mark.parametrize(
    ("nick", "expected"),
    [
        # Always leaves WebKit's own choice, which turns acceleration off where the system cannot do it (v0.1).
        ("always", None),
        ("never", "NEVER"),
        ("telepathy", None),
    ],
)
def test_hardware_acceleration_names_the_webkit_policy_to_force(nick: str, expected: str | None) -> None:
    assert hardware_acceleration_policy(nick) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Empty keeps WebKit's user agent with "Dailies/<version>" appended: no spoofing by default.
        ("", None),
        ("   ", None),
        ("Mozilla/5.0 (X11; Linux x86_64) Custom/1.0", "Mozilla/5.0 (X11; Linux x86_64) Custom/1.0"),
        ("  Mozilla/5.0 Custom/1.0\n", "Mozilla/5.0 Custom/1.0"),
    ],
)
def test_a_user_agent_replaces_the_default_only_when_set(value: str, expected: str | None) -> None:
    assert custom_user_agent(value) == expected


def test_a_game_settings_path_is_under_games_by_id() -> None:
    assert game_settings_path("/io/github/tim_van_oudheusden/Dailies", "wordle") == (
        "/io/github/tim_van_oudheusden/Dailies/games/wordle/"
    )


@pytest.mark.parametrize("game_id", ["", "../State", "a/b", "Wordle", None])
def test_a_game_that_is_not_a_catalog_id_has_no_settings_path(game_id: str | None) -> None:
    assert game_settings_path("/io/github/tim_van_oudheusden/Dailies", game_id) is None
