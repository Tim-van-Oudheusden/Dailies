import importlib.util
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

# The fetcher's dependencies come from scripts/requirements.txt; without them there is nothing to test.
pytest.importorskip("requests")
pytest.importorskip("tldextract")
Image = pytest.importorskip("PIL.Image")

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "icons" / "fetch_icon.py"
PUBLIC_IP = "93.184.215.14"
GAME_URL = "https://worldle.teuteuf.fr/"
FAVICON = "https://worldle.teuteuf.fr/favicon.ico"
GOOGLE = (
    "https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL"
    "&url=https%3A%2F%2Fworldle.teuteuf.fr&size=64"
)
DUCKDUCKGO = "https://icons.duckduckgo.com/ip3/worldle.teuteuf.fr.ico"
NOW = datetime(2026, 10, 19, 9, 30, 15, 123, tzinfo=UTC)


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fetch_icon", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fi = load_script()


class FakeResponse:
    def __init__(self, status: int = 200, headers: dict[str, str] | None = None, body: bytes | str = b"") -> None:
        self.status_code = status
        self.headers = {key.lower(): value for key, value in (headers or {}).items()}
        self.encoding = "utf-8"
        self._body = body.encode() if isinstance(body, str) else body

    def iter_content(self, chunk_size: int) -> object:
        for start in range(0, len(self._body), chunk_size):
            yield self._body[start : start + chunk_size]

    def close(self) -> None:
        pass


class FakeSession:
    """Answers GET requests from a table of url -> response or exception; unknown URLs get a 404."""

    def __init__(self, routes: dict[str, FakeResponse | Exception] | None = None) -> None:
        self.routes = routes or {}
        self.calls: list[str] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        assert method == "GET"
        assert kwargs["allow_redirects"] is False
        self.calls.append(url)
        answer = self.routes.get(url, FakeResponse(404))
        if isinstance(answer, Exception):
            raise answer
        return answer


def resolve_public(_host: str) -> list[str]:
    return [PUBLIC_IP]


def image(size: tuple[int, int], fmt: str = "PNG", colour: tuple[int, int, int, int] = (200, 30, 30, 255)) -> bytes:
    out = io.BytesIO()
    picture = Image.new("RGBA", size, colour)
    if fmt == "JPEG":
        picture = picture.convert("RGB")
    picture.save(out, fmt)
    return out.getvalue()


def ok(body: bytes | str) -> FakeResponse:
    return FakeResponse(200, body=body)


def page(head: str) -> FakeResponse:
    return ok(f"<!doctype html><html><head><title>Worldle</title>{head}</head><body></body></html>")


def decoded(png: bytes) -> "Image.Image":
    picture = Image.open(io.BytesIO(png))
    picture.load()
    return picture


def game(game_id: str = "worldle", url: str = GAME_URL, status: str = "active", **extra: str) -> dict[str, str]:
    entry = {"id": game_id, "name": game_id.title(), "url": url, "status": status, "domain": "teuteuf.fr"}
    return {**entry, **extra, "history": [{"date": "2026-10-15", "event": "added"}]}


# --- candidates -------------------------------------------------------------------------------------------------------


def test_candidates_follow_the_documented_order() -> None:
    html = (
        '<link rel="icon" href="/icon.png">'
        '<link rel="apple-touch-icon" href="/touch.png">'
        '<link rel="manifest" href="/site.webmanifest">'
    )
    links = fi.page_links(html, GAME_URL)
    manifest = {"icons": [{"src": "android-192.png", "sizes": "192x192", "type": "image/png"}]}

    candidates = fi.candidates(GAME_URL, links, fi.manifest_icons(manifest, "https://worldle.teuteuf.fr/m/x.json"))

    assert candidates == [
        ("manifest", "https://worldle.teuteuf.fr/m/android-192.png"),
        ("apple-touch-icon", "https://worldle.teuteuf.fr/touch.png"),
        ("icon", "https://worldle.teuteuf.fr/icon.png"),
        ("favicon.ico", FAVICON),
        ("google", GOOGLE),
        ("duckduckgo", DUCKDUCKGO),
    ]
    assert links.manifest == "https://worldle.teuteuf.fr/site.webmanifest"


def test_sizes_prefer_the_smallest_icon_of_at_least_64_px_then_unknown_then_the_largest_smaller_one() -> None:
    html = (
        '<link rel="icon" href="/16.png" sizes="16x16">'
        '<link rel="icon" href="/any.png">'
        '<link rel="shortcut icon" href="/32.png" sizes="32x32">'
        '<link rel="icon" href="/192.png" sizes="192x192">'
        '<link rel="icon" href="/96.png" sizes="48x48 96X96">'
    )

    links = fi.page_links(html, GAME_URL)

    assert [url.rsplit("/", 1)[1] for url in links.icons] == ["96.png", "192.png", "any.png", "32.png", "16.png"]


def test_svg_mask_and_unrelated_links_are_not_candidates() -> None:
    html = (
        '<link rel="icon" href="/logo.svg" type="image/svg+xml">'
        '<link rel="icon" href="/vector.SVG">'
        '<link rel="mask-icon" href="/mask.png">'
        '<link rel="stylesheet" href="/style.css">'
        '<link rel="icon">'
        '<link rel="apple-touch-icon-precomposed" href="/touch.png">'
    )

    links = fi.page_links(html, GAME_URL)

    assert links.icons == []
    assert links.touch_icons == ["https://worldle.teuteuf.fr/touch.png"]
    assert links.manifest is None


def test_manifest_icons_keep_any_purpose_raster_icons_resolved_against_the_manifest() -> None:
    manifest = {
        "icons": [
            {"src": "/mask.png", "sizes": "512x512", "purpose": "maskable"},
            {"src": "logo.svg", "sizes": "any", "type": "image/svg+xml"},
            {"src": "big.png", "sizes": "512x512", "purpose": "any maskable"},
            {"src": "small.png", "sizes": "72x72"},
            {"src": 7},
            "not an icon",
        ]
    }

    icons = fi.manifest_icons(manifest, "https://cdn.example.org/app/manifest.json")

    assert icons == ["https://cdn.example.org/app/small.png", "https://cdn.example.org/app/big.png"]


@pytest.mark.parametrize("manifest", [None, [], {"icons": "no"}, {"name": "x"}])
def test_a_manifest_without_an_icon_list_gives_no_icons(manifest: object) -> None:
    assert fi.manifest_icons(manifest, "https://worldle.teuteuf.fr/manifest.json") == []


def test_a_url_named_by_two_sources_is_tried_once() -> None:
    links = fi.page_links('<link rel="icon" href="/favicon.ico">', GAME_URL)

    candidates = fi.candidates(GAME_URL, links, [])

    assert [source for source, _url in candidates] == ["icon", "google", "duckduckgo"]


# --- normalise --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["PNG", "ICO", "JPEG", "GIF", "WEBP", "BMP"])
def test_each_raster_format_becomes_a_64_px_rgba_png(fmt: str) -> None:
    result = fi.normalise(image((128, 128), fmt))

    assert result is not None
    png, source_size = result
    assert source_size == 128
    picture = decoded(png)
    assert picture.format == "PNG"
    assert picture.size == (64, 64)
    assert picture.mode == "RGBA"


def test_a_slightly_wide_image_is_centred_on_a_transparent_square() -> None:
    result = fi.normalise(image((80, 64)))

    assert result is not None
    png, source_size = result
    assert source_size == 64
    picture = decoded(png)
    assert picture.getpixel((32, 0))[3] == 0
    assert picture.getpixel((32, 32)) == (200, 30, 30, 255)


@pytest.mark.parametrize("size", [(1400, 1000), (64, 96)])
def test_a_banner_that_is_not_nearly_square_is_refused(size: tuple[int, int]) -> None:
    # Some sites name their social-media cover image as the apple-touch-icon.
    assert fi.normalise(image(size)) is None


def test_the_same_image_always_gives_the_same_bytes() -> None:
    first = fi.normalise(image((180, 180)))
    second = fi.normalise(image((180, 180)))

    assert first is not None
    assert first == second


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"<svg xmlns='http://www.w3.org/2000/svg'/>",
        b"<!doctype html><title>Not found</title>",
        image((64, 64), colour=(0, 0, 0, 0)),
        image((64, 64))[:40],
    ],
    ids=["empty", "svg", "html", "fully-transparent", "truncated"],
)
def test_what_is_not_a_usable_raster_image_is_refused(data: bytes) -> None:
    assert fi.normalise(data) is None


def test_an_image_with_too_many_pixels_is_refused_before_it_is_decoded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fi, "MAX_PIXELS", 100 * 100)

    assert fi.normalise(image((101, 100))) is None
    assert fi.normalise(image((100, 100))) is not None


# --- fetch_icon -------------------------------------------------------------------------------------------------------


def test_the_first_candidate_of_at_least_64_px_is_used() -> None:
    session = FakeSession(
        {
            GAME_URL: page('<link rel="apple-touch-icon" href="/touch.png"><link rel="icon" href="/icon.png">'),
            "https://worldle.teuteuf.fr/touch.png": ok(image((180, 180))),
            "https://worldle.teuteuf.fr/icon.png": ok(image((256, 256))),
        }
    )

    icon = fi.fetch_icon(game(), session, resolve_public)

    assert icon is not None
    assert icon.source == "apple-touch-icon"
    assert icon.url == "https://worldle.teuteuf.fr/touch.png"
    assert icon.source_size == 180
    assert decoded(icon.png).size == (64, 64)
    assert "https://worldle.teuteuf.fr/icon.png" not in session.calls


def test_the_manifest_icon_comes_first() -> None:
    manifest_url = "https://worldle.teuteuf.fr/manifest.json"
    manifest = {"icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}]}
    session = FakeSession(
        {
            GAME_URL: page(
                '<link rel="manifest" href="/manifest.json"><link rel="apple-touch-icon" href="/touch.png">'
            ),
            manifest_url: ok(json.dumps(manifest)),
            "https://worldle.teuteuf.fr/icon-192.png": ok(image((192, 192))),
            "https://worldle.teuteuf.fr/touch.png": ok(image((180, 180))),
        }
    )

    icon = fi.fetch_icon(game(), session, resolve_public)

    assert icon is not None
    assert icon.source == "manifest"


def test_an_unreadable_manifest_is_skipped() -> None:
    session = FakeSession(
        {
            GAME_URL: page('<link rel="manifest" href="/manifest.json">'),
            "https://worldle.teuteuf.fr/manifest.json": ok("{not json"),
            FAVICON: ok(image((64, 64), "ICO")),
        }
    )

    icon = fi.fetch_icon(game(), session, resolve_public)

    assert icon is not None
    assert icon.source == "favicon.ico"


def test_a_failing_candidate_falls_through_to_the_next() -> None:
    session = FakeSession(
        {
            GAME_URL: page('<link rel="apple-touch-icon" href="/touch.png"><link rel="icon" href="/icon.png">'),
            "https://worldle.teuteuf.fr/touch.png": ok("<!doctype html><title>Soft 404</title>"),
            "https://worldle.teuteuf.fr/icon.png": ok(image((96, 96))),
        }
    )

    icon = fi.fetch_icon(game(), session, resolve_public)

    assert icon is not None
    assert icon.source == "icon"


def test_a_small_icon_is_kept_only_when_no_later_candidate_is_bigger() -> None:
    session = FakeSession(
        {
            GAME_URL: page(""),
            FAVICON: ok(image((16, 16), "ICO")),
            GOOGLE: ok(image((32, 32))),
            DUCKDUCKGO: ok(image((24, 24), "ICO")),
        }
    )

    icon = fi.fetch_icon(game(), session, resolve_public)

    assert icon is not None
    assert icon.source == "google"
    assert icon.source_size == 32
    assert DUCKDUCKGO in session.calls


def test_an_icon_below_16_px_is_not_used() -> None:
    session = FakeSession({GAME_URL: page(""), FAVICON: ok(image((8, 8), "ICO"))})

    assert fi.fetch_icon(game(), session, resolve_public) is None


def test_a_bot_walled_page_still_gets_the_sites_favicon() -> None:
    session = FakeSession({GAME_URL: FakeResponse(403), FAVICON: ok(image((48, 48), "ICO"))})

    icon = fi.fetch_icon(game(), session, resolve_public)

    assert icon is not None
    assert icon.source == "favicon.ico"


def test_the_favicon_is_asked_of_the_site_the_page_redirected_to() -> None:
    moved = "https://www.worldle.example/play"
    session = FakeSession(
        {
            GAME_URL: FakeResponse(301, {"Location": moved}),
            moved: page(""),
            "https://www.worldle.example/favicon.ico": ok(image((64, 64), "ICO")),
        }
    )

    icon = fi.fetch_icon(game(), session, resolve_public)

    assert icon is not None
    assert icon.url == "https://www.worldle.example/favicon.ico"


def test_an_icon_on_a_non_public_address_is_never_requested() -> None:
    internal = "https://intranet.example/icon.png"

    def resolve(host: str) -> list[str]:
        return ["10.0.0.7"] if host == "intranet.example" else [PUBLIC_IP]

    session = FakeSession(
        {
            GAME_URL: page(f'<link rel="apple-touch-icon" href="{internal}">'),
            internal: ok(image((180, 180))),
            FAVICON: ok(image((64, 64), "ICO")),
        }
    )

    icon = fi.fetch_icon(game(), session, resolve)

    assert icon is not None
    assert icon.source == "favicon.ico"
    assert internal not in session.calls


def test_an_icon_larger_than_the_download_cap_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    big = image((180, 180))
    monkeypatch.setattr(fi, "MAX_ICON_BYTES", len(big) - 1)
    session = FakeSession(
        {
            GAME_URL: page('<link rel="apple-touch-icon" href="/touch.png">'),
            "https://worldle.teuteuf.fr/touch.png": ok(big),
            GOOGLE: ok(image((64, 64))),
        }
    )

    icon = fi.fetch_icon(game(), session, resolve_public)

    assert icon is not None
    assert icon.source == "google"


def test_a_request_error_is_a_failed_candidate() -> None:
    import requests

    session = FakeSession(
        {
            GAME_URL: requests.ConnectionError("refused"),
            FAVICON: requests.Timeout("slow"),
            GOOGLE: ok(image((64, 64))),
        }
    )

    icon = fi.fetch_icon(game(), session, resolve_public)

    assert icon is not None
    assert icon.source == "google"


def test_a_game_with_no_usable_candidate_has_no_icon() -> None:
    session = FakeSession({GAME_URL: page("")})

    assert fi.fetch_icon(game(), session, resolve_public) is None
    assert session.calls == [GAME_URL, FAVICON, GOOGLE, DUCKDUCKGO]


# --- main -------------------------------------------------------------------------------------------------------------


GENERATED = "2026-10-15T00:00:00Z"


def write_catalog(tmp_path: Path, games: list[dict[str, str]]) -> Path:
    path = tmp_path / "games.json"
    catalog = {"schema_version": 1, "generated_at": GENERATED, "games": games}
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def entries(catalog: Path) -> dict[str, dict[str, object]]:
    return {entry["id"]: entry for entry in json.loads(catalog.read_text(encoding="utf-8"))["games"]}


def run(tmp_path: Path, args: list[str], session: FakeSession, takedowns: str = "") -> int:
    takedown_file = tmp_path / "takedowns.txt"
    takedown_file.write_text(takedowns, encoding="utf-8")
    return fi.main([*args, "--takedowns", str(takedown_file)], session=session, resolve=resolve_public, now=NOW)


def test_main_writes_one_png_per_listed_game_and_skips_retired_ones(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    other = "https://other.example/"
    catalog = write_catalog(
        tmp_path,
        [game(), game("other", other), game("gone", "https://gone.example/", "retired")],
    )
    out = tmp_path / "icons"
    session = FakeSession({GAME_URL: page(""), FAVICON: ok(image((64, 64), "ICO"))})

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(out)], session)

    assert status == 0
    assert sorted(path.name for path in out.iterdir()) == ["worldle.png"]
    assert decoded((out / "worldle.png").read_bytes()).size == (64, 64)
    assert not any("gone.example" in url for url in session.calls)
    printed = capsys.readouterr().out
    assert f"worldle: favicon.ico {FAVICON} (64 px)" in printed
    assert "other: no icon, the category glyph stays" in printed


def test_main_records_each_icon_in_the_catalog_entry(tmp_path: Path) -> None:
    other = "https://other.example/"
    google = GOOGLE.replace("worldle.teuteuf.fr", "other.example")
    catalog = write_catalog(tmp_path, [game("other", other), game()])
    session = FakeSession(
        {GAME_URL: page(""), FAVICON: ok(image((64, 64), "ICO")), other: page(""), google: ok(image((64, 64)))}
    )

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(tmp_path / "icons")], session)

    assert status == 0
    worldle, other_entry = entries(catalog)["worldle"], entries(catalog)["other"]
    assert (worldle["icon"], worldle["icon_source"]) == ("icons/worldle.png", "site")
    assert (other_entry["icon"], other_entry["icon_source"]) == ("icons/other.png", "google")
    # The fields go right after `domain`, and the file keeps its committed format.
    assert list(worldle) == ["id", "name", "url", "status", "domain", "icon", "icon_source", "history"]
    text = catalog.read_text(encoding="utf-8")
    data = json.loads(text)
    assert text == json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    assert data["generated_at"] == "2026-10-19T09:30:15Z"


def test_main_records_a_game_without_an_icon_as_none(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path, [game(icon="icons/worldle.png", icon_source="site")])

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(tmp_path / "icons")], FakeSession())

    assert status == 0
    worldle = entries(catalog)["worldle"]
    assert "icon" not in worldle
    assert worldle["icon_source"] == "none"


def test_main_leaves_the_catalog_untouched_when_nothing_changed(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path, [game(icon_source="none")])
    before = catalog.read_text(encoding="utf-8")

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(tmp_path / "icons")], FakeSession())

    assert status == 0
    assert catalog.read_text(encoding="utf-8") == before


def test_main_never_replaces_a_manual_icon(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path, [game(icon="icons/worldle.png", icon_source="manual")])
    out = tmp_path / "icons"
    out.mkdir()
    (out / "worldle.png").write_bytes(b"hand-made")
    session = FakeSession({GAME_URL: page(""), FAVICON: ok(image((64, 64), "ICO"))})

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(out)], session)

    assert status == 0
    assert session.calls == []
    assert (out / "worldle.png").read_bytes() == b"hand-made"
    assert entries(catalog)["worldle"]["icon_source"] == "manual"


def test_main_fetches_only_the_ids_asked_for(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path, [game(), game("other", "https://other.example/")])
    session = FakeSession({GAME_URL: page(""), FAVICON: ok(image((64, 64), "ICO"))})

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(tmp_path / "icons"), "--id", "worldle"], session)

    assert status == 0
    assert not any("other.example" in url for url in session.calls)


def test_main_refuses_an_unknown_id(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    catalog = write_catalog(tmp_path, [game()])
    session = FakeSession()

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(tmp_path / "icons"), "--id", "nope"], session)

    assert status == 2
    assert session.calls == []
    assert "nope" in capsys.readouterr().err


def test_main_with_missing_only_leaves_existing_icons_alone(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path, [game()])
    out = tmp_path / "icons"
    out.mkdir()
    (out / "worldle.png").write_bytes(b"kept")
    session = FakeSession()

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(out), "--missing-only"], session)

    assert status == 0
    assert session.calls == []
    assert (out / "worldle.png").read_bytes() == b"kept"


def test_main_keeps_the_old_icon_when_a_fetch_finds_nothing(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path, [game(icon="icons/worldle.png", icon_source="site")])
    out = tmp_path / "icons"
    out.mkdir()
    (out / "worldle.png").write_bytes(b"kept")

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(out)], FakeSession())

    assert status == 0
    assert (out / "worldle.png").read_bytes() == b"kept"
    assert entries(catalog)["worldle"]["icon"] == "icons/worldle.png"


def test_main_never_fetches_a_taken_down_icon_and_deletes_its_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    catalog = write_catalog(tmp_path, [game(icon="icons/worldle.png", icon_source="manual")])
    out = tmp_path / "icons"
    out.mkdir()
    (out / "worldle.png").write_bytes(b"old")
    session = FakeSession({GAME_URL: page(""), FAVICON: ok(image((64, 64), "ICO"))})

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(out)], session, "# owner asked\nworldle\n")

    assert status == 0
    assert session.calls == []
    assert not (out / "worldle.png").exists()
    assert "icon" not in entries(catalog)["worldle"]
    assert entries(catalog)["worldle"]["icon_source"] == "none"
    assert "worldle: taken down" in capsys.readouterr().out


@pytest.mark.parametrize("status", ["retired", "active"])
@pytest.mark.parametrize("ids", [[], ["--id", "gone"], ["--id", "worldle"]], ids=["full run", "its id", "another id"])
def test_main_applies_every_takedown_even_to_a_retired_game_or_one_not_asked_for(
    tmp_path: Path, ids: list[str], status: str
) -> None:
    catalog = write_catalog(
        tmp_path,
        [game("gone", "https://gone.example/", status, icon="icons/gone.png", icon_source="site"), game()],
    )
    out = tmp_path / "icons"
    out.mkdir()
    (out / "gone.png").write_bytes(b"old")
    session = FakeSession({GAME_URL: page(""), FAVICON: ok(image((64, 64), "ICO"))})

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(out), *ids], session, "gone\n")

    assert status == 0
    assert not any("gone.example" in url for url in session.calls)
    assert not (out / "gone.png").exists()
    assert "icon" not in entries(catalog)["gone"]
    assert entries(catalog)["gone"]["icon_source"] == "none"


def test_main_skips_an_id_that_is_not_a_safe_file_name(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path, [game("../escape")])
    out = tmp_path / "icons"
    session = FakeSession({GAME_URL: page(""), FAVICON: ok(image((64, 64), "ICO"))})

    status = run(tmp_path, ["--catalog", str(catalog), "--out", str(out)], session)

    assert status == 0
    assert session.calls == []
    assert not (tmp_path / "escape.png").exists()


def test_main_reports_an_unreadable_catalog_as_a_usage_error(tmp_path: Path) -> None:
    catalog = tmp_path / "games.json"
    catalog.write_text("[]", encoding="utf-8")

    assert run(tmp_path, ["--catalog", str(catalog), "--out", str(tmp_path / "icons")], FakeSession()) == 2
    assert run(tmp_path, ["--catalog", str(tmp_path / "missing.json"), "--out", str(tmp_path)], FakeSession()) == 2


def test_the_shipped_takedown_list_parses() -> None:
    assert isinstance(fi.load_takedowns(fi.TAKEDOWNS), set)


# --- throttle ---------------------------------------------------------------------------------------------------------


class Clock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_the_throttle_starts_at_most_one_request_per_interval() -> None:
    clock = Clock()
    inner = FakeSession()
    throttle = fi.Throttle(inner, interval=0.5, clock=clock.monotonic, sleep=clock.sleep)

    for _ in range(3):
        throttle.request("GET", GAME_URL, allow_redirects=False)

    assert clock.sleeps == [0.5, 0.5]
    assert len(inner.calls) == 3
