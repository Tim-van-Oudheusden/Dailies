import pytest

from dailies.core.web import display_host, site_matches


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
