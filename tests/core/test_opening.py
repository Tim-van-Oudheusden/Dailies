import pytest

from dailies.core.opening import OpenMode, choices, resolve, show_first_run_banner, shown_choice

IN_APP, EXTERNAL, CUSTOM = OpenMode.IN_APP, OpenMode.EXTERNAL, OpenMode.CUSTOM


def test_open_mode_reads_the_setting_nicks() -> None:
    assert [OpenMode.from_id(nick) for nick in ("in-app", "external", "custom")] == [IN_APP, EXTERNAL, CUSTOM]


def test_an_unknown_open_mode_falls_back_to_the_schema_default() -> None:
    assert OpenMode.from_id("telepathy") is IN_APP


@pytest.mark.parametrize(
    ("mode", "have_webkit", "host_access", "command", "expected"),
    [
        # In-app: the built-in browser when WebKit is there, the default browser otherwise.
        (IN_APP, True, False, "", IN_APP),
        (IN_APP, False, False, "", EXTERNAL),
        (IN_APP, True, True, "firefox", IN_APP),
        # External: always the default browser, even when WebKit is there.
        (EXTERNAL, True, False, "", EXTERNAL),
        (EXTERNAL, False, True, "firefox", EXTERNAL),
        # Custom: the command only with host access and a command; otherwise the in-app rules.
        (CUSTOM, True, True, "firefox --new-window", CUSTOM),
        (CUSTOM, False, True, "firefox", CUSTOM),
        (CUSTOM, True, False, "firefox", IN_APP),
        (CUSTOM, False, False, "firefox", EXTERNAL),
        (CUSTOM, True, True, "", IN_APP),
        (CUSTOM, False, True, "   ", EXTERNAL),
    ],
)
def test_resolve(mode: OpenMode, have_webkit: bool, host_access: bool, command: str, expected: OpenMode) -> None:
    assert resolve(mode, have_webkit=have_webkit, host_access=host_access, command=command) is expected


def test_the_first_run_banner_shows_while_games_open_in_app() -> None:
    assert show_first_run_banner(IN_APP, have_webkit=True, dismissed=False)


def test_the_first_run_banner_stays_hidden_once_dismissed() -> None:
    assert not show_first_run_banner(IN_APP, have_webkit=True, dismissed=True)


@pytest.mark.parametrize(("mode", "have_webkit"), [(EXTERNAL, True), (IN_APP, False), (CUSTOM, False)])
def test_the_first_run_banner_is_hidden_when_games_do_not_open_in_app(mode: OpenMode, have_webkit: bool) -> None:
    assert not show_first_run_banner(mode, have_webkit=have_webkit, dismissed=False)


@pytest.mark.parametrize(
    ("have_webkit", "host_access", "expected"),
    [
        (True, False, (IN_APP, EXTERNAL)),
        (False, False, (EXTERNAL,)),
        (True, True, (IN_APP, EXTERNAL, CUSTOM)),
        (False, True, (EXTERNAL, CUSTOM)),
    ],
)
def test_choices_hide_what_this_installation_cannot_do(
    have_webkit: bool, host_access: bool, expected: tuple[OpenMode, ...]
) -> None:
    assert choices(have_webkit=have_webkit, host_access=host_access) == expected


@pytest.mark.parametrize(
    ("mode", "have_webkit", "host_access", "expected"),
    [
        (IN_APP, True, False, IN_APP),
        (EXTERNAL, True, False, EXTERNAL),
        # A choice that is hidden shows as what actually happens.
        (IN_APP, False, False, EXTERNAL),
        (CUSTOM, True, False, IN_APP),
        (CUSTOM, False, False, EXTERNAL),
        # Custom stays selected once it is offered, even before a command is entered.
        (CUSTOM, True, True, CUSTOM),
    ],
)
def test_shown_choice(mode: OpenMode, have_webkit: bool, host_access: bool, expected: OpenMode) -> None:
    assert shown_choice(mode, have_webkit=have_webkit, host_access=host_access) is expected
