"""Tests for scripts/catalog_candidates.py: the games The Dles lists that the catalog does not.

The records in fixtures/dles/data/dles/ are copied unchanged from aukspot/dles (GPL-3.0) at commit
31afcb9640d2433dd0d4b3c7575725228ba80d26. The tests pack them into a tarball shaped like GitHub's and serve it from
a fake session, so nothing touches the network.
"""

import importlib.util
import io
import json
import tarfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "catalog_candidates.py"
UPSTREAM = Path(__file__).resolve().parent / "fixtures" / "dles"
COMMIT = "31afcb9640d2433dd0d4b3c7575725228ba80d26"
TARBALL_URL = f"https://codeload.github.com/aukspot/dles/tar.gz/{COMMIT}"
PUBLIC_IP = "93.184.215.14"
# Games on the same sites as NYT Wordle and Tagline in the fixture records, under other paths.
CATALOG = {
    "schema_version": 1,
    "games": [
        {"id": "connections", "url": "https://www.nytimes.com/games/connections"},
        {"id": "quordle", "url": "https://www.merriam-webster.com/games/quordle/"},
    ],
}


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("catalog_candidates", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cc = load_script()


class FakeResponse:
    def __init__(self, status: int = 200, body: bytes = b"") -> None:
        self.status_code = status
        self.headers: dict[str, str] = {}
        self.encoding = None
        self._body = body

    def iter_content(self, chunk_size: int) -> object:
        for start in range(0, len(self._body), chunk_size):
            yield self._body[start : start + chunk_size]

    def close(self) -> None:
        pass


class FakeSession:
    """Answers requests from a table of url -> response; unknown URLs get a 404."""

    def __init__(self, routes: dict[str, FakeResponse] | None = None) -> None:
        self.routes = routes or {}
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        assert kwargs["allow_redirects"] is False
        self.calls.append((method, url))
        return self.routes.get(url, FakeResponse(404))


def resolve_public(_host: str) -> list[str]:
    return [PUBLIC_IP]


def tarball(extra: dict[str, str | bytes] | None = None) -> bytes:
    """The fixture repository as GitHub serves it: a gzipped tar under one top-level directory."""
    files = {path.relative_to(UPSTREAM).as_posix(): path.read_bytes() for path in UPSTREAM.rglob("*") if path.is_file()}
    files.update({name: text.encode() if isinstance(text, str) else text for name, text in (extra or {}).items()})
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(f"dles-{COMMIT}/{name}")
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    return buffer.getvalue()


def upstream(body: bytes | None = None, status: int = 200) -> FakeSession:
    return FakeSession({TARBALL_URL: FakeResponse(status, tarball() if body is None else body)})


def run(
    tmp_path: Path,
    *args: str,
    session: FakeSession | None = None,
    catalog: dict | None = None,
    resolve: object = resolve_public,
) -> int:
    path = tmp_path / "games.json"
    path.write_text(json.dumps(CATALOG if catalog is None else catalog), encoding="utf-8")
    argv = ["--commit", COMMIT, "--catalog", str(path), *args]
    return cc.main(argv, session=session or upstream(), resolve=resolve)


def rows(output: str) -> list[list[str]]:
    """The table's body rows, each cell without its code-span backticks."""
    lines = [line for line in output.splitlines() if line.startswith("| ")]
    return [[cell.strip().strip("`").strip() for cell in line[2:-2].split(" | ")] for line in lines[2:]]


def names(output: str) -> list[str]:
    return [row[1] for row in rows(output)]


def test_lists_active_games_whose_site_is_not_in_the_catalog_newest_first(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = run(tmp_path)

    assert status == 0
    assert names(capsys.readouterr().out) == ["Collagedle", "Cramdle", "Echo Chess", "Absurdle"]


def test_a_row_gives_the_added_date_name_category_and_url(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run(tmp_path)

    assert rows(capsys.readouterr().out)[0] == ["2026-10-27", "Collagedle", "Novelty", "https://collagedle.com"]


def test_with_an_empty_catalog_every_active_game_is_listed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run(tmp_path, catalog={"games": []})

    assert sorted(names(capsys.readouterr().out)) == [
        "Absurdle",
        "Collagedle",
        "Cramdle",
        "Echo Chess",
        "NYT Wordle",
        "Tagline",
    ]


def test_since_keeps_games_added_or_readded_on_or_after_that_day(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Echo Chess was added on 2024-04-10, removed, and readded on 2025-04-16.
    run(tmp_path, "--since", "2025-04-16")

    output = capsys.readouterr().out
    assert names(output) == ["Collagedle", "Cramdle", "Echo Chess"]
    assert output.splitlines()[0] == (
        f"Active games in aukspot/dles at {COMMIT} whose site is not in the catalog, added there on or after"
        " 2025-04-16: 3."
    )


def test_since_after_every_addition_lists_no_games(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    status = run(tmp_path, "--since", "2026-10-28")

    output = capsys.readouterr().out
    assert status == 0
    assert rows(output) == []
    assert "No candidates" in output


def test_the_report_names_the_commit_it_read(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    session = upstream()

    run(tmp_path, session=session)

    assert session.calls == [("GET", TARBALL_URL)]
    assert COMMIT in capsys.readouterr().out


def test_upstream_text_stays_inert_inside_its_cell(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    record = (
        "id: 900\nname: Pipe | [dle](https://evil.example) @someone\nurl: https://pipedle.example\n"
        "category: Words\nstatus: active\nhistory:\n- date: '2026-10-30'\n  event: added\n"
    )
    session = upstream(tarball({"data/dles/0900-pipe.yaml": record}))

    run(tmp_path, session=session)

    line = next(line for line in capsys.readouterr().out.splitlines() if "pipedle" in line)
    assert line.count(" | ") == 3
    assert "`Pipe \\| [dle](https://evil.example) @someone`" in line


def test_a_record_that_is_not_a_mapping_is_not_a_game(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    session = upstream(tarball({"data/dles/0902-empty.yaml": "", "data/dles/0903-list.yaml": "- status: active\n"}))

    status = run(tmp_path, session=session)

    assert status == 0
    assert names(capsys.readouterr().out) == ["Collagedle", "Cramdle", "Echo Chess", "Absurdle"]


@pytest.mark.parametrize("text", [None, "{not json"], ids=["missing", "not-json"])
def test_an_unreadable_catalog_exits_2_before_any_download(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str | None
) -> None:
    path = tmp_path / "games.json"
    if text is not None:
        path.write_text(text, encoding="utf-8")
    session = upstream()

    status = cc.main(["--commit", COMMIT, "--catalog", str(path)], session=session, resolve=resolve_public)

    assert status == 2
    assert session.calls == []
    assert capsys.readouterr().err.startswith("catalog_candidates: ")


def test_only_full_commit_hashes_are_accepted(tmp_path: Path) -> None:
    session = upstream()

    with pytest.raises(SystemExit) as exit_info:
        cc.main(["--commit", "main", "--catalog", str(tmp_path / "games.json")], session=session)

    assert exit_info.value.code == 2
    assert session.calls == []


def test_a_host_on_a_private_address_is_never_requested(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    session = upstream()

    status = run(tmp_path, session=session, resolve=lambda _host: ["10.0.0.7"])

    assert status == 2
    assert session.calls == []
    assert "non-public address" in capsys.readouterr().err


def test_a_failed_download_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    status = run(tmp_path, session=upstream(b"Not Found", status=404))

    captured = capsys.readouterr()
    assert status == 2
    assert "HTTP 404" in captured.err
    assert captured.out == ""


def test_a_download_over_the_size_limit_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cc, "MAX_ARCHIVE", 100)

    status = run(tmp_path)

    assert status == 2
    assert "larger than" in capsys.readouterr().err


def test_a_download_slower_than_the_timeout_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Each chunk arrives within the per-read timeout, but the clock passes the whole-body deadline.
    clock = iter(range(0, 1000, 6))
    monkeypatch.setattr(cc, "monotonic", lambda: next(clock))

    status = run(tmp_path, session=upstream(b"x" * (64 * 1024 * 5)))

    assert status == 2
    assert "did not download within" in capsys.readouterr().err


def test_a_download_that_is_not_a_tarball_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    status = run(tmp_path, session=upstream(b"<html>maintenance</html>"))

    assert status == 2
    assert "tarball" in capsys.readouterr().err


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(
            "id: 901\nname: Broken\nstatus: active\nhistory:\n- date: '2026-10-30'\n  event: added\n", id="no-url"
        ),
        pytest.param("id: 901\nname: Broken\nurl: https://broken.example\nstatus: active\n", id="no-history"),
        pytest.param(
            "id: 901\nname: Broken\nurl: https://broken.example\nstatus: active\nhistory:\n- date: 30/10/2026\n"
            "  event: added\n",
            id="date-not-iso",
        ),
        pytest.param("id: 901\nname: [Broken\nstatus: active\n", id="not-yaml"),
        pytest.param(
            "id: 901\nurl: https://broken.example\nstatus: active\nhistory:\n- date: '2026-10-30'\n  event: added\n",
            id="no-name",
        ),
        pytest.param(
            "id: 901\nname: Broken\nurl: https://broken.example\nstatus: active\nhistory:\n- added 2026-10-30\n",
            id="history-entry-not-a-mapping",
        ),
        pytest.param("id: 901\nname: Br\xf6ken\nstatus: active\n".encode("latin-1"), id="not-utf-8"),
    ],
)
def test_a_malformed_active_record_exits_2_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], record: str | bytes
) -> None:
    session = upstream(tarball({"data/dles/0901-broken.yaml": record}))

    status = run(tmp_path, session=session)

    captured = capsys.readouterr()
    assert status == 2
    assert "0901-broken.yaml" in captured.err
    assert captured.out == ""


def test_a_record_too_large_to_be_a_game_exits_2_naming_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # A YAML comment compresses about 1000:1, so the archive cap alone would let it decompress into memory.
    session = upstream(tarball({"data/dles/0904-huge.yaml": "#" * (1024 * 1024)}))

    status = run(tmp_path, session=session)

    captured = capsys.readouterr()
    assert status == 2
    assert "0904-huge.yaml is larger than" in captured.err
    assert captured.out == ""
