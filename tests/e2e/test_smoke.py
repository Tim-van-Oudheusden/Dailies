import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.skip(reason="placeholder until the GTK smoke test lands (#49)")
def test_app_opens_a_window_and_quits() -> None:
    pass
