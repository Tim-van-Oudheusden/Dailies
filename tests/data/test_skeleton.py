from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_editorconfig_formats_json_with_two_spaces() -> None:
    # Placeholder until data/v1/games.json lands; the catalog and the Flatpak manifests are 2-space JSON.
    text = (ROOT / ".editorconfig").read_text(encoding="utf-8")
    section = text.split("[*.json]", 1)[1].split("[", 1)[0]
    assert "indent_size = 2" in section
