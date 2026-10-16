import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

requests = pytest.importorskip("requests")

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "popularity" / "collect.py"
NOW = datetime(2026, 10, 19, 4, 18, tzinfo=UTC)
API = "https://tranco-list.eu/api/ranks/domain/"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("collect", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collect = load_script()


class FakeResponse:
    def __init__(self, status: int = 200, body: object = None) -> None:
        self.status_code = status
        self._body = body

    def json(self) -> object:
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeSession:
    """Answers GETs from a table of url -> list of responses (one per attempt); unknown URLs get a 404."""

    def __init__(self, routes: dict[str, list[FakeResponse | Exception]]) -> None:
        self.routes = {url: list(answers) for url, answers in routes.items()}
        self.calls: list[str] = []
        self.sent_headers: list[dict[str, str] | None] = []
        self.headers: dict[str, str] = {}

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        assert kwargs["timeout"] == collect.TIMEOUT
        self.calls.append(url)
        self.sent_headers.append(kwargs.get("headers"))
        answers = self.routes.get(url)
        if not answers:
            return FakeResponse(404, {})
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeClock:
    """A monotonic clock that only advances when the collector sleeps."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def ranks_body(domain: str, *values: int) -> dict[str, Any]:
    return {
        "ranks": [{"date": f"2026-10-{18 - day:02d}", "rank": value} for day, value in enumerate(values)],
        "domain": domain,
    }


def ok(domain: str, *values: int) -> FakeResponse:
    return FakeResponse(200, ranks_body(domain, *values))


def catalog(*entries: tuple[str, str, str]) -> dict[str, Any]:
    return {"games": [{"id": game_id, "domain": domain, "status": status} for game_id, domain, status in entries]}


def run(session: FakeSession, cat: dict[str, Any], clock: FakeClock | None = None) -> dict[str, Any]:
    clock = clock or FakeClock()
    return collect.collect(cat, session, now=lambda: NOW, monotonic=clock.monotonic, sleep=clock.sleep)


def test_one_request_per_distinct_active_domain() -> None:
    cat = catalog(
        ("wordle", "nytimes.com", "active"),
        ("nyt-strands", "nytimes.com", "active"),
        ("worldle", "teuteuf.fr", "active"),
        ("gone", "gone.example", "retired"),
    )
    session = FakeSession(
        {API + "nytimes.com": [ok("nytimes.com", 156)], API + "teuteuf.fr": [ok("teuteuf.fr", 40873)]}
    )
    data = run(session, cat)
    assert session.calls == [API + "nytimes.com", API + "teuteuf.fr"]
    assert data["domains"]["nytimes.com"] == {
        "ok": True,
        "fetched_at": "2026-10-19T04:18:00Z",
        "status": 200,
        "ranks": [{"date": "2026-10-18", "rank": 156}],
    }
    assert data["health"] == {"ok": 2, "failed": 0, "count": 2}
    assert data["source"] == "tranco"
    assert data["fetched_at"] == "2026-10-19T04:18:00Z"


def test_requests_are_spaced_one_second_apart() -> None:
    cat = catalog(*[(f"g{index}", f"d{index}.com", "active") for index in range(3)])
    clock = FakeClock()
    session = FakeSession({API + f"d{index}.com": [ok(f"d{index}.com", 5)] for index in range(3)})
    run(session, cat, clock)
    assert clock.sleeps == [1.0, 1.0]


def test_retries_once_on_a_server_error() -> None:
    cat = catalog(("worldle", "teuteuf.fr", "active"))
    clock = FakeClock()
    session = FakeSession({API + "teuteuf.fr": [FakeResponse(502, {}), ok("teuteuf.fr", 40873)]})
    data = run(session, cat, clock)
    assert session.calls == [API + "teuteuf.fr"] * 2
    assert clock.sleeps == [1.0]
    assert data["domains"]["teuteuf.fr"]["ok"] is True


def test_second_server_error_marks_the_domain_failed() -> None:
    cat = catalog(("worldle", "teuteuf.fr", "active"), ("wordle", "nytimes.com", "active"))
    session = FakeSession(
        {
            API + "teuteuf.fr": [FakeResponse(503, {}), FakeResponse(500, {})],
            API + "nytimes.com": [ok("nytimes.com", 156)],
        }
    )
    data = run(session, cat)
    assert session.calls.count(API + "teuteuf.fr") == 2
    assert data["domains"]["teuteuf.fr"] == {
        "ok": False,
        "fetched_at": "2026-10-19T04:18:00Z",
        "status": 500,
        "ranks": [],
        "error": "HTTP 500",
    }
    assert data["health"] == {"ok": 1, "failed": 1, "count": 2}


def test_client_error_is_not_retried() -> None:
    cat = catalog(("worldle", "teuteuf.fr", "active"))
    session = FakeSession({API + "teuteuf.fr": [FakeResponse(403, {})]})
    data = run(session, cat)
    assert session.calls == [API + "teuteuf.fr"]
    assert data["domains"]["teuteuf.fr"]["error"] == "HTTP 403"


def test_rate_limited_request_waits_and_retries() -> None:
    cat = catalog(("worldle", "teuteuf.fr", "active"))
    clock = FakeClock()
    session = FakeSession({API + "teuteuf.fr": [FakeResponse(429, {}), FakeResponse(429, {}), ok("teuteuf.fr", 7)]})
    data = run(session, cat, clock)
    assert session.calls == [API + "teuteuf.fr"] * 3
    assert clock.sleeps == [2.0, 2.0]
    assert data["domains"]["teuteuf.fr"]["ok"] is True


def test_rate_limit_gives_up_after_three_retries() -> None:
    cat = catalog(("worldle", "teuteuf.fr", "active"))
    session = FakeSession({API + "teuteuf.fr": [FakeResponse(429, {})] * 5})
    data = run(session, cat)
    assert len(session.calls) == 4
    assert data["domains"]["teuteuf.fr"]["error"] == "HTTP 429"


def test_network_error_marks_the_domain_failed() -> None:
    cat = catalog(("worldle", "teuteuf.fr", "active"))
    session = FakeSession({API + "teuteuf.fr": [requests.ConnectionError("refused")]})
    data = run(session, cat)
    assert data["domains"]["teuteuf.fr"]["ok"] is False
    assert data["domains"]["teuteuf.fr"]["status"] is None
    assert "refused" in data["domains"]["teuteuf.fr"]["error"]


@pytest.mark.parametrize(
    "body",
    [
        ValueError("not json"),
        [],
        {"ranks": "none"},
        {"ranks": [{"date": "2026-10-18", "rank": 0}]},
        {"ranks": [{"date": "2026-10-18", "rank": "5"}]},
        {"ranks": [{"date": 5, "rank": 5}]},
        {"ranks": [{"date": "2026-10-18", "rank": True}]},
    ],
)
def test_malformed_body_marks_the_domain_failed(body: object) -> None:
    cat = catalog(("worldle", "teuteuf.fr", "active"))
    data = run(FakeSession({API + "teuteuf.fr": [FakeResponse(200, body)]}), cat)
    assert data["domains"]["teuteuf.fr"]["ok"] is False
    assert data["domains"]["teuteuf.fr"]["error"].startswith("malformed response")


def test_unranked_domain_is_ok_with_no_ranks() -> None:
    cat = catalog(("tiny", "tiny.example", "active"))
    data = run(FakeSession({API + "tiny.example": [FakeResponse(200, {"ranks": [], "domain": "tiny.example"})]}), cat)
    assert data["domains"]["tiny.example"] == {
        "ok": True,
        "fetched_at": "2026-10-19T04:18:00Z",
        "status": 200,
        "ranks": [],
    }


def test_domain_is_quoted_into_the_url() -> None:
    cat = catalog(("odd", "a/b?c", "active"))
    session = FakeSession({})
    run(session, cat)
    assert session.calls == [API + "a%2Fb%3Fc"]


def test_main_writes_raw_tranco_json(tmp_path: Path) -> None:
    cat_path = tmp_path / "games.json"
    cat_path.write_text(json.dumps(catalog(("worldle", "teuteuf.fr", "active"))), encoding="utf-8")
    session = FakeSession({API + "teuteuf.fr": [ok("teuteuf.fr", 40873)]})
    out = tmp_path / "raw"
    assert collect.main(["--catalog", str(cat_path), "--out", str(out)], session=session) == 0
    data = json.loads((out / "tranco.json").read_text(encoding="utf-8"))
    assert data["domains"]["teuteuf.fr"]["ranks"] == [{"date": "2026-10-18", "rank": 40873}]
    assert data["health"] == {"ok": 1, "failed": 0, "count": 1}


def test_main_reports_a_missing_catalog(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        collect.main(["--catalog", str(tmp_path / "missing.json"), "--out", str(tmp_path)], session=FakeSession({}))
        == 2
    )
    assert "collect" in capsys.readouterr().err


def test_default_session_sends_a_bot_user_agent_with_contact() -> None:
    with collect.popularity_session() as session:
        assert session.headers["User-Agent"] == collect.USER_AGENT
    # Wikimedia's User-Agent policy: identify the bot and give a way to contact its operator.
    assert "Bot/" in collect.USER_AGENT
    assert "https://github.com/Tim-van-Oudheusden/Dailies" in collect.USER_AGENT


# --- optional sources -----------------------------------------------------------------------------------------------

WIKI = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
# The seven full days before NOW.
WIKI_DAYS = "/daily/20261012/20261018"
UNTIL = int(NOW.timestamp())
SINCE = UNTIL - 28 * 86400
RADAR = "https://api.cloudflare.com/client/v4/radar/ranking/domain/"


def hn_url(name: str) -> str:
    query = name.replace(" ", "+")
    return (
        f"https://hn.algolia.com/api/v1/search_by_date?query={query}&tags=story&restrictSearchableAttributes=title"
        f"&typoTolerance=false&hitsPerPage=0&numericFilters=created_at_i%3E{SINCE}%2Ccreated_at_i%3C{UNTIL}"
    )


def views_body(*views: int) -> dict[str, Any]:
    return {"items": [{"timestamp": f"202610{12 + day:02d}00", "views": value} for day, value in enumerate(views)]}


def full_catalog(*games: dict[str, Any]) -> dict[str, Any]:
    return {"games": [{"status": "active", **entry} for entry in games]}


def clockwork() -> dict[str, Any]:
    clock = FakeClock()
    return {"clock": collect.Clock(lambda: NOW, clock.monotonic, clock.sleep)}


def test_wikipedia_sums_seven_days_of_views_for_games_with_an_article() -> None:
    cat = full_catalog(
        {"id": "wordle", "name": "Wordle", "domain": "nytimes.com", "wikipedia": "Wordle"},
        {"id": "globle", "name": "Globle", "domain": "globle-game.com", "wikipedia": "Globle (game)"},
        {"id": "framed", "name": "Framed", "domain": "framed.wtf"},
    )
    session = FakeSession(
        {
            WIKI + "Wordle" + WIKI_DAYS: [FakeResponse(200, views_body(*[10000] * 7))],
            WIKI + "Globle_%28game%29" + WIKI_DAYS: [FakeResponse(200, views_body(3, 4))],
        }
    )
    data = collect.collect_wikipedia(cat, session, **clockwork())
    assert sorted(session.calls) == [WIKI + "Globle_%28game%29" + WIKI_DAYS, WIKI + "Wordle" + WIKI_DAYS]
    assert data["source"] == "wikipedia"
    assert data["articles"]["wordle"] == {
        "ok": True,
        "fetched_at": "2026-10-19T04:18:00Z",
        "status": 200,
        "article": "Wordle",
        "views_7d": 70000,
    }
    assert data["articles"]["globle"]["views_7d"] == 7
    assert data["health"] == {"ok": 2, "failed": 0, "count": 2}


def test_wikipedia_missing_article_is_a_failed_entry() -> None:
    cat = full_catalog({"id": "scrandle", "name": "Scrandle", "domain": "scrandle.com", "wikipedia": "Scrandle"})
    data = collect.collect_wikipedia(cat, FakeSession({}), **clockwork())
    assert data["articles"]["scrandle"]["ok"] is False
    assert data["articles"]["scrandle"]["error"] == "HTTP 404"
    assert data["health"] == {"ok": 0, "failed": 1, "count": 1}


@pytest.mark.parametrize("body", [{}, {"items": [{"views": -1}]}, {"items": [{"views": "7"}]}, ["items"]])
def test_wikipedia_malformed_body_is_a_failed_entry(body: object) -> None:
    cat = full_catalog({"id": "wordle", "name": "Wordle", "domain": "nytimes.com", "wikipedia": "Wordle"})
    session = FakeSession({WIKI + "Wordle" + WIKI_DAYS: [FakeResponse(200, body)]})
    data = collect.collect_wikipedia(cat, session, **clockwork())
    assert data["articles"]["wordle"]["error"].startswith("malformed response")


def test_hn_counts_stories_with_the_name_in_their_title_over_28_days() -> None:
    cat = full_catalog(
        {"id": "wordle", "name": "Wordle", "domain": "nytimes.com"},
        {"id": "box-office-game", "name": "Box Office Game", "domain": "boxofficega.me"},
        {"id": "gone", "name": "Gone", "domain": "gone.example", "status": "retired"},
    )
    session = FakeSession(
        {
            hn_url("Wordle"): [FakeResponse(200, {"nbHits": 8, "hits": []})],
            hn_url("Box Office Game"): [FakeResponse(200, {"nbHits": 0, "hits": []})],
        }
    )
    data = collect.collect_hn(cat, session, **clockwork())
    assert sorted(session.calls) == sorted([hn_url("Wordle"), hn_url("Box Office Game")])
    assert data["games"]["wordle"] == {
        "ok": True,
        "fetched_at": "2026-10-19T04:18:00Z",
        "status": 200,
        "stories_28d": 8,
    }
    assert data["games"]["box-office-game"]["stories_28d"] == 0
    assert data["health"] == {"ok": 2, "failed": 0, "count": 2}


def test_hn_malformed_body_is_a_failed_entry() -> None:
    cat = full_catalog({"id": "wordle", "name": "Wordle", "domain": "nytimes.com"})
    session = FakeSession({hn_url("Wordle"): [FakeResponse(200, {"nbHits": "8"})]})
    data = collect.collect_hn(cat, session, **clockwork())
    assert data["games"]["wordle"]["error"].startswith("malformed response")


def test_radar_without_a_token_asks_nothing_and_reports_why() -> None:
    session = FakeSession({})
    data = collect.collect_radar(catalog(("wordle", "nytimes.com", "active")), session, None, **clockwork())
    assert session.calls == []
    assert data == {
        "source": "radar",
        "fetched_at": "2026-10-19T04:18:00Z",
        "error": "CLOUDFLARE_RADAR_TOKEN is not set",
        "health": {"ok": 0, "failed": 1, "count": 1},
        "domains": {},
    }


def test_radar_reads_the_popular_bucket_with_the_token() -> None:
    body = {"success": True, "result": {"details_0": {"bucket": "2000", "rank": 1534, "categories": []}}}
    unranked = {"success": True, "result": {"details_0": {"categories": []}}}
    session = FakeSession(
        {
            RADAR + "nytimes.com?rankingType=POPULAR&format=JSON": [FakeResponse(200, body)],
            RADAR + "tiny.example?rankingType=POPULAR&format=JSON": [FakeResponse(200, unranked)],
        }
    )
    cat = catalog(("wordle", "nytimes.com", "active"), ("tiny", "tiny.example", "active"))
    data = collect.collect_radar(cat, session, "secret", **clockwork())
    assert session.sent_headers == [{"Authorization": "Bearer secret"}] * 2
    assert data["domains"]["nytimes.com"] == {
        "ok": True,
        "fetched_at": "2026-10-19T04:18:00Z",
        "status": 200,
        "bucket": 2000,
        "rank": 1534,
    }
    assert data["domains"]["tiny.example"] == {
        "ok": True,
        "fetched_at": "2026-10-19T04:18:00Z",
        "status": 200,
        "bucket": None,
        "rank": None,
    }
    assert "error" not in data
    assert "secret" not in json.dumps(data)


@pytest.mark.parametrize(
    "body",
    [{"success": False, "result": None}, {"success": True, "result": {}}, {"success": True, "result": []}],
)
def test_radar_malformed_body_is_a_failed_entry(body: object) -> None:
    session = FakeSession({RADAR + "nytimes.com?rankingType=POPULAR&format=JSON": [FakeResponse(200, body)]})
    data = collect.collect_radar(catalog(("wordle", "nytimes.com", "active")), session, "secret", **clockwork())
    assert data["domains"]["nytimes.com"]["error"].startswith("malformed response")


def write_catalog(tmp_path: Path) -> Path:
    path = tmp_path / "games.json"
    entry = {"id": "worldle", "name": "Worldle", "domain": "teuteuf.fr", "wikipedia": "Worldle", "status": "active"}
    path.write_text(json.dumps({"games": [entry]}), encoding="utf-8")
    return path


def test_main_without_flags_asks_only_tranco(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_RADAR_TOKEN", "secret")
    session = FakeSession({API + "teuteuf.fr": [ok("teuteuf.fr", 40873)]})
    out = tmp_path / "raw"
    assert collect.main(["--catalog", str(write_catalog(tmp_path)), "--out", str(out)], session=session) == 0
    assert session.calls == [API + "teuteuf.fr"]
    assert sorted(path.name for path in out.iterdir()) == ["tranco.json"]


def test_main_with_flags_writes_each_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_RADAR_TOKEN", raising=False)
    session = FakeSession({API + "teuteuf.fr": [ok("teuteuf.fr", 40873)]})
    out = tmp_path / "raw"
    args = ["--catalog", str(write_catalog(tmp_path)), "--out", str(out), "--wikipedia", "--hn", "--radar"]
    assert collect.main(args, session=session) == 0
    assert sorted(path.name for path in out.iterdir()) == ["hn.json", "radar.json", "tranco.json", "wikipedia.json"]
    radar = json.loads((out / "radar.json").read_text(encoding="utf-8"))
    assert radar["error"] == "CLOUDFLARE_RADAR_TOKEN is not set"
    assert json.loads((out / "wikipedia.json").read_text(encoding="utf-8"))["health"]["count"] == 1
