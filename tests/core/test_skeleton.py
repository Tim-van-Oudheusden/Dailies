import sys


def test_runs_on_a_supported_python() -> None:
    # dailies/core targets Python >= 3.12 (org.gnome.Platform//51 ships a newer one).
    assert sys.version_info >= (3, 12)
