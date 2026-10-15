import importlib.util
import json
import re
import socket
from datetime import date
from pathlib import Path
from types import ModuleType

import pytest

# The validator's dependencies come from scripts/requirements.txt; without them there is nothing to test.
pytest.importorskip("jsonschema")
requests = pytest.importorskip("requests")
pytest.importorskip("tldextract")

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_submission.py"
SCHEMA = json.loads((ROOT / "data" / "v1" / "schema" / "catalog.schema.json").read_text(encoding="utf-8"))
TODAY = date(2026, 10, 15)
PUBLIC_IP = "93.184.215.14"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_submission", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vs = load_script()


class FakeResponse:
    def __init__(self, status: int = 200, headers: dict[str, str] | None = None, body: str = "") -> None:
        self.status_code = status
        self.headers = {key.lower(): value for key, value in (headers or {}).items()}
        self.encoding = "utf-8"
        self._body = body.encode()

    def iter_content(self, chunk_size: int) -> object:
        for start in range(0, len(self._body), chunk_size):
            yield self._body[start : start + chunk_size]

    def close(self) -> None:
        pass


class FakeSession:
    """Answers requests from a table of (method, url) -> response; unknown URLs get a 404."""

    def __init__(self, routes: dict[tuple[str, str], FakeResponse] | None = None) -> None:
        self.routes = routes or {}
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        assert kwargs["allow_redirects"] is False
        self.calls.append((method, url))
        return self.routes.get((method, url), FakeResponse(404))


def site(url: str, title: str = "Worldle - guess the country") -> FakeSession:
    page = f"<html><head><title>{title}</title></head><body></body></html>"
    return FakeSession({("HEAD", url): FakeResponse(200), ("GET", url): FakeResponse(200, body=page)})


def resolve_public(_host: str) -> list[str]:
    return [PUBLIC_IP]


def form(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "name": "Countryle",
        "url": "https://countryle.com/",
        "category": "Geography",
        "difficulty": "Medium",
        "description": "Guess the country from hints about its continent, population and climate.",
        "tags": "countries, Trivia Hints",
        "language": "en",
    }
    fields.update(overrides)
    return fields


CATALOG = {
    "schema_version": 1,
    "generated_at": "2026-10-15T12:00:00Z",
    "games": [
        {
            "id": "worldle",
            "name": "Worldle",
            "url": "https://worldle.teuteuf.fr/",
            "aliases": ["Wordle Geo"],
        }
    ],
}


def check(parsed: dict[str, object], session: FakeSession | None = None, resolve: object = resolve_public) -> object:
    validator = vs.Validator(CATALOG, SCHEMA, session if session is not None else site(str(parsed["url"])), resolve)
    return validator.validate(parsed, 42, TODAY)


def test_valid_submission_is_ok() -> None:
    result = check(form())

    assert result.errors == []
    assert result.ok
    assert result.entry == {
        "id": "countryle",
        "name": "Countryle",
        "url": "https://countryle.com/",
        "category": "geography",
        "difficulty": "medium",
        "description": "Guess the country from hints about its continent, population and climate.",
        "tags": ["countries", "trivia-hints"],
        "language": "en",
        "added": "2026-10-15",
        "status": "active",
        "domain": "countryle.com",
        "source_issue": 42,
        "history": [{"date": "2026-10-15", "event": "added", "note": "issue #42"}],
    }


def test_http_url_fails() -> None:
    session = site("http://countryle.com/")

    result = check(form(url="http://countryle.com/"), session)

    assert not result.ok
    assert any("https://" in error for error in result.errors)
    assert session.calls == []


@pytest.mark.parametrize("url", ["https://10.0.0.1/", "https://127.0.0.1/", "https://[::1]/"])
def test_private_ip_literal_fails(url: str) -> None:
    # The real resolver: getaddrinfo answers IP literals without asking DNS.
    session = site(url)

    result = check(form(url=url), session, resolve=vs.resolve_host)

    assert not result.ok
    assert any("non-public address" in error for error in result.errors)
    assert session.calls == []


@pytest.mark.parametrize("address", ["192.168.1.10", "169.254.169.254", "100.64.0.1", "fd00::1", "fe80::1"])
def test_host_resolving_to_a_private_address_fails(address: str) -> None:
    session = site("https://countryle.com/")

    result = check(form(), session, resolve=lambda _host: [PUBLIC_IP, address])

    assert not result.ok
    assert any(address in error for error in result.errors)
    assert session.calls == []


def test_unresolvable_host_fails() -> None:
    def fail(host: str) -> list[str]:
        raise socket.gaierror(host)

    result = check(form(), resolve=fail)

    assert not result.ok
    assert any("does not resolve" in error for error in result.errors)


# Hijacked or dead dle domains (docs/research/dle-catalog.md §1.4) that now redirect to another site.
GRAVEYARD = ["moviedle.app", "absurdle.online", "posterdle.com", "cladder.io", "cloudle.app", "foodle.io"]


@pytest.mark.parametrize("domain", GRAVEYARD)
def test_cross_domain_redirect_fails(domain: str) -> None:
    url = f"https://{domain}/"
    landing = "https://www.lucky-spin-777.net/promo"
    session = FakeSession(
        {
            ("HEAD", url): FakeResponse(301, {"Location": "https://www.lucky-spin-777.net/promo"}),
            ("HEAD", landing): FakeResponse(200),
            ("GET", url): FakeResponse(302, {"Location": landing}),
            ("GET", landing): FakeResponse(200, body="<title>Welcome</title>"),
        }
    )

    result = check(form(name=domain.partition(".")[0].title(), url=url), session)

    assert not result.ok
    assert any("redirects to another site (lucky-spin-777.net)" in error for error in result.errors)


def test_redirect_within_the_same_site_is_ok() -> None:
    url = "https://countryle.com/"
    final = "https://www.countryle.com/play"
    session = FakeSession(
        {
            ("HEAD", url): FakeResponse(308, {"Location": "/play"}),
            ("HEAD", "https://countryle.com/play"): FakeResponse(301, {"Location": final}),
            ("HEAD", final): FakeResponse(200),
            ("GET", final): FakeResponse(200, body="<title>Countryle</title>"),
        }
    )

    result = check(form(), session)

    assert result.errors == []


@pytest.mark.parametrize(
    "title", ["SLOT GACOR Hari Ini", "Situs Judi Online Terpercaya", "Best Online Casinos 2026", "Togel &amp; Poker"]
)
def test_gambling_title_fails(title: str) -> None:
    result = check(form(), site("https://countryle.com/", title=title))

    assert not result.ok
    assert any("gambling" in error for error in result.errors)


@pytest.mark.parametrize("title", ["Alphabetle - daily alphabet puzzle", "Betweenle", "Slotted Words", "Pokerdle"])
def test_blocklist_keyword_inside_a_longer_word_is_ok(title: str) -> None:
    result = check(form(), site("https://countryle.com/", title=title))

    assert result.errors == []


def test_page_without_a_title_is_ok() -> None:
    session = FakeSession(
        {
            ("HEAD", "https://countryle.com/"): FakeResponse(200),
            ("GET", "https://countryle.com/"): FakeResponse(200, body="<html><body>No title</body></html>"),
        }
    )

    assert check(form(), session).errors == []


def test_head_refused_falls_back_to_get() -> None:
    url = "https://countryle.com/"
    session = FakeSession(
        {
            ("HEAD", url): FakeResponse(405),
            ("GET", url): FakeResponse(200, body="<title>Countryle</title>"),
        }
    )

    result = check(form(), session)

    assert result.errors == []
    assert session.calls == [("HEAD", url), ("GET", url), ("GET", url)]


def test_requests_send_a_descriptive_user_agent_and_a_timeout() -> None:
    seen: list[dict[str, object]] = []

    class Recording(FakeSession):
        def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
            seen.append(kwargs)
            return super().request(method, url, **kwargs)

    check(form(), Recording(site("https://countryle.com/").routes))

    assert seen
    assert all(kwargs["timeout"] == 10 for kwargs in seen)
    assert all("Dailies" in kwargs["headers"]["User-Agent"] for kwargs in seen)


def test_not_found_fails() -> None:
    result = check(form(), FakeSession())

    assert not result.ok
    assert any("HTTP 404" in error for error in result.errors)


def test_more_than_five_redirects_fails() -> None:
    routes = {
        ("HEAD", f"https://countryle.com/{hop}"): FakeResponse(302, {"Location": f"/{hop + 1}"}) for hop in range(6)
    }
    routes[("HEAD", "https://countryle.com/6")] = FakeResponse(200)

    result = check(form(url="https://countryle.com/0"), FakeSession(routes))

    assert not result.ok
    assert any("more than 5 redirects" in error for error in result.errors)


def test_five_redirects_are_ok() -> None:
    routes = {
        ("HEAD", f"https://countryle.com/{hop}"): FakeResponse(302, {"Location": f"/{hop + 1}"}) for hop in range(5)
    }
    routes[("HEAD", "https://countryle.com/5")] = FakeResponse(200)
    routes[("GET", "https://countryle.com/5")] = FakeResponse(200, body="<title>Countryle</title>")

    assert check(form(url="https://countryle.com/0"), FakeSession(routes)).errors == []


def test_redirect_to_a_private_address_fails() -> None:
    session = FakeSession({("HEAD", "https://countryle.com/"): FakeResponse(302, {"Location": "https://10.0.0.1/"})})

    result = check(form(), session, resolve=vs.resolve_host)

    assert not result.ok
    assert any("10.0.0.1" in error for error in result.errors)
    assert session.calls == [("HEAD", "https://countryle.com/")]


def test_unreachable_site_fails() -> None:
    class Down(FakeSession):
        def request(self, _method: str, url: str, **_kwargs: object) -> FakeResponse:
            raise requests.ConnectTimeout(url)

    result = check(form(), Down())

    assert not result.ok
    assert any("unreachable (ConnectTimeout)" in error for error in result.errors)


def test_duplicate_url_with_www_and_trailing_slash_fails() -> None:
    url = "https://www.Worldle.teuteuf.fr?utm_source=reddit"
    result = check(form(name="Country Shapes", url=url), site(url))

    assert not result.ok
    assert any("already in the catalog as worldle" in error for error in result.errors)


@pytest.mark.parametrize("name", ["WORLDLE!", "Wordle: Geo"])
def test_duplicate_slug_fails(name: str) -> None:
    result = check(form(name=name))

    assert not result.ok
    assert any("name is already in the catalog as worldle" in error for error in result.errors)


def test_near_duplicate_name_is_a_warning() -> None:
    result = check(form(name="Worldl"))

    assert result.ok
    assert result.warnings == ['the name is close to "Worldle" (worldle); check it is not the same game']


def test_unknown_category_label_fails() -> None:
    result = check(form(category="Other"))

    assert not result.ok
    assert any('unknown category "Other"' in error for error in result.errors)


def test_too_short_description_fails() -> None:
    result = check(form(description="  Guess the flag.  "))

    assert not result.ok
    assert any("at least 20 characters" in error for error in result.errors)


def test_empty_optional_fields_get_defaults() -> None:
    result = check(form(tags="", language=""))

    assert result.errors == []
    assert "tags" not in result.entry
    assert result.entry["language"] == "en"


def test_entry_that_breaks_the_schema_fails() -> None:
    result = check(form(difficulty="Extreme", tags="a, b, c, d, e, f, g, h, i, j, k"))

    assert not result.ok
    assert any(error.startswith("difficulty: 'extreme' is not one of") for error in result.errors)
    assert any(error.startswith("tags: ") for error in result.errors)


def run_cli(tmp_path: Path, fields: object, session: FakeSession, **paths: Path) -> tuple[int, Path, Path]:
    parsed_path = tmp_path / "issue-parser-result.json"
    parsed_path.write_text(json.dumps(fields), encoding="utf-8")
    catalog_path = tmp_path / "games.json"
    catalog_path.write_text(json.dumps(CATALOG), encoding="utf-8")
    out = tmp_path / "result.json"
    report = tmp_path / "report.md"
    args = {
        "--parsed": parsed_path,
        "--catalog": catalog_path,
        "--schema": ROOT / "data" / "v1" / "schema" / "catalog.schema.json",
        "--out": out,
        "--report": report,
    }
    args.update({f"--{key}": value for key, value in paths.items()})
    argv = [str(part) for pair in args.items() for part in pair] + ["--issue", "42"]
    code = vs.main(argv, session=session, resolve=resolve_public, today=TODAY)
    return code, out, report


def test_cli_writes_result_and_report_for_a_valid_submission(tmp_path: Path) -> None:
    code, out, report = run_cli(tmp_path, form(), site("https://countryle.com/"))

    assert code == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["ok"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["entry"]["id"] == "countryle"
    text = report.read_text(encoding="utf-8")
    assert text.startswith("<!-- dailies-submission-check -->\n")
    assert "| Reachable | ✅ pass |" in text
    assert "```json\n" + json.dumps(result["entry"], indent=2, ensure_ascii=False) + "\n```" in text


def test_cli_exits_1_and_explains_an_invalid_submission(tmp_path: Path) -> None:
    url = "https://moviedle.app/"
    session = FakeSession({("HEAD", url): FakeResponse(301, {"Location": "https://www.lucky-spin-777.net/"})})
    session.routes[("HEAD", "https://www.lucky-spin-777.net/")] = FakeResponse(200)

    code, out, report = run_cli(tmp_path, form(name="Worldle", url=url, description="Short | <b>bold</b>"), session)

    assert code == 1
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["ok"] is False
    assert "redirects to another site (lucky-spin-777.net)" in result["errors"]
    assert "the name is already in the catalog as worldle" in result["errors"]
    text = report.read_text(encoding="utf-8")
    assert "| Same site | ❌ fail | `redirects to another site (lucky-spin-777.net)` |" in text
    assert "| Page title | ⏭️ skipped |" in text
    assert "| Form fields | ❌ fail | `the description must be at least 20 characters (it has 19)` |" in text


def test_report_lists_warnings_and_fences_backticks_in_the_entry() -> None:
    result = check(form(name="Worldl", description="Guess the ```country``` from its silhouette."))

    text = vs.render_report(result)

    assert '- `the name is close to "Worldle" (worldle); check it is not the same game`' in text
    assert "````json\n" in text
    assert text.rstrip().endswith("\n````")


def test_report_keeps_submitted_text_inside_its_table_cell() -> None:
    result = check(form(), site("https://countryle.com/", title="Casino | <img src=x>\nwin"))

    text = vs.render_report(result)

    assert r'| `the page title "Casino \| <img src=x> win" contains the gambling keyword "casino"` |' in text


@pytest.mark.parametrize("content", ["{not json", "[1, 2]"])
def test_cli_exits_2_on_an_unreadable_parsed_file(tmp_path: Path, content: str) -> None:
    parsed = tmp_path / "broken.json"
    parsed.write_text(content, encoding="utf-8")

    code, out, _ = run_cli(tmp_path, {}, FakeSession(), parsed=parsed)

    assert code == 2
    assert not out.exists()


def test_cli_exits_2_on_a_missing_catalog(tmp_path: Path) -> None:
    code, _, _ = run_cli(tmp_path, form(), FakeSession(), catalog=tmp_path / "missing.json")

    assert code == 2


@pytest.mark.parametrize("issue", ["0", "abc"])
def test_cli_exits_2_on_a_bad_issue_number(issue: str) -> None:
    with pytest.raises(SystemExit) as exit_info:
        vs.main(["--parsed", "p", "--catalog", "c", "--schema", "s", "--out", "o", "--report", "r", "--issue", issue])

    assert exit_info.value.code == 2


def test_cli_exits_2_on_an_internal_error(tmp_path: Path) -> None:
    schema = tmp_path / "schema.json"
    schema.write_text('{"type": "object"}', encoding="utf-8")

    code, out, _ = run_cli(tmp_path, form(), site("https://countryle.com/"), schema=schema)

    assert code == 2
    assert not out.exists()


def test_page_that_fails_on_get_fails() -> None:
    session = FakeSession({("HEAD", "https://countryle.com/"): FakeResponse(200)})

    result = check(form(), session)

    assert not result.ok
    assert any("HTTP 404 to GET" in error for error in result.errors)


def test_title_after_the_first_512_kib_is_not_read() -> None:
    page = "<html><head>" + " " * (512 * 1024) + "<title>Casino</title></head></html>"
    session = FakeSession(
        {
            ("HEAD", "https://countryle.com/"): FakeResponse(200),
            ("GET", "https://countryle.com/"): FakeResponse(200, body=page),
        }
    )

    assert check(form(), session).errors == []


def test_host_that_rebinds_to_a_private_address_after_the_check_is_never_sent_a_request() -> None:
    # The check sees a public address; the connection's own lookup of "localhost" then gets 127.0.0.1.
    with socket.create_server(("127.0.0.1", 0)) as listener:
        listener.settimeout(5)
        port = listener.getsockname()[1]
        url = f"https://localhost:{port}/"

        with vs.public_session() as session:
            result = check(form(url=url), session)

        assert not result.ok
        assert any("non-public address (127.0.0.1)" in error for error in result.errors)
        connection, _ = listener.accept()
        with connection:
            connection.settimeout(5)
            assert connection.recv(1) == b""


@pytest.mark.parametrize("url", ["https://straße.example/", "https://bücher.example/"])
def test_non_ascii_host_fails_without_a_lookup(url: str) -> None:
    looked_up: list[str] = []

    def resolve(host: str) -> list[str]:
        looked_up.append(host)
        return [PUBLIC_IP]

    result = check(form(url=url), resolve=resolve)

    assert not result.ok
    assert any("xn--" in error for error in result.errors)
    assert looked_up == []


def test_get_that_redirects_to_another_site_fails() -> None:
    url = "https://countryle.com/"
    landing = "https://lucky-spin-777.net/"
    session = FakeSession(
        {
            ("HEAD", url): FakeResponse(200),
            ("GET", url): FakeResponse(302, {"Location": landing}),
            ("GET", landing): FakeResponse(200, body="<title>Welcome</title>"),
        }
    )

    result = check(form(), session)

    assert not result.ok
    assert "redirects to another site (lucky-spin-777.net)" in result.errors


def test_page_that_takes_longer_than_10_s_in_total_to_load_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    # Every chunk arrives within the per-read timeout, but the clock passes 10 s before the title.
    clock = iter(range(0, 1000, 4))
    monkeypatch.setattr(vs, "monotonic", lambda: next(clock))
    page = "<html><head>" + " " * (256 * 1024) + "<title>Countryle</title></head></html>"
    session = FakeSession(
        {
            ("HEAD", "https://countryle.com/"): FakeResponse(200),
            ("GET", "https://countryle.com/"): FakeResponse(200, body=page),
        }
    )

    result = check(form(), session)

    assert not result.ok
    assert any("did not load within 10 s" in error for error in result.errors)


@pytest.mark.parametrize("url", ["https://[::1/x", "https://countryle.com:99999/"])
def test_malformed_url_fails_with_a_report(tmp_path: Path, url: str) -> None:
    code, out, report = run_cli(tmp_path, form(url=url), FakeSession())

    assert code == 1
    assert any("not a valid URL" in error for error in json.loads(out.read_text(encoding="utf-8"))["errors"])
    assert report.read_text(encoding="utf-8").startswith("<!-- dailies-submission-check -->")


def test_host_label_longer_than_63_characters_fails() -> None:
    url = f"https://{'a' * 64}.com/"

    result = check(form(url=url), resolve=vs.resolve_host)

    assert not result.ok
    assert any("does not resolve" in error for error in result.errors)


def test_redirect_to_a_malformed_url_fails() -> None:
    session = FakeSession({("HEAD", "https://countryle.com/"): FakeResponse(302, {"Location": "https://[::1/x"})})

    result = check(form(), session)

    assert not result.ok
    assert any("not a valid URL" in error for error in result.errors)


def test_unknown_charset_falls_back_to_utf_8() -> None:
    response = FakeResponse(200, body="<title>Casino Ünique</title>")
    response.encoding = "x-no-such-charset"
    session = FakeSession(
        {("HEAD", "https://countryle.com/"): FakeResponse(200), ("GET", "https://countryle.com/"): response}
    )

    result = check(form(), session)

    assert any('"Casino Ünique"' in error for error in result.errors)


def test_report_renders_untrusted_text_inert() -> None:
    title = "Casino @maintainer [win](https://evil.example) ![x](https://evil.example/x.png) ``tick``"
    result = check(form(name="Worldl"), site("https://countryle.com/", title=title))

    text = vs.render_report(result)

    detail = f'the page title "{title}" contains the gambling keyword "casino"'
    assert f"| Page title | ❌ fail | ```{detail}``` |" in text
    assert '- `the name is close to "Worldle" (worldle); check it is not the same game`' in text


SHELL_PAYLOADS = ["$(id)", "`id`", '"; rm -rf /']


def test_cli_report_quotes_shell_payloads_as_code(tmp_path: Path) -> None:
    payload = " ".join(SHELL_PAYLOADS)
    fields = form(name=f"Countryle {payload}", description=f"Guess {payload}", tags=f"countries, {payload}")

    code, _out, report = run_cli(tmp_path, fields, site("https://countryle.com/", title=f"Casino {payload}"))

    assert code == 1
    head, fence, entry = report.read_text(encoding="utf-8").partition("\nCandidate entry:\n")
    assert fence
    assert entry.startswith("\n```json\n")
    assert json.dumps(f"Guess {payload}") in entry
    assert "$(id)" in head
    # Outside the fenced candidate entry, form and page text only appears inside inline code spans.
    prose = re.sub(r"(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)", "", head)
    for fragment in SHELL_PAYLOADS:
        assert fragment not in prose
