"""Start the installed app headless and check that it opens its window and quits cleanly.

Meson runs this file as a stdlib unittest script (suite `e2e`) inside `flatpak-builder --run-tests`, where the SDK has
no pytest and no Xvfb: the display is a private `gtk4-broadwayd`, listening on a Unix socket only. A plain `pytest`
deselects it through the `e2e` marker.
"""

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

with contextlib.suppress(ImportError):  # the SDK has no pytest
    import pytest

    pytestmark = pytest.mark.e2e

# Meson passes the installed launcher; by hand, the one on PATH.
APP = os.environ.get("DAILIES_BIN") or shutil.which("dailies")
BROADWAYD = shutil.which("gtk4-broadwayd")
DBUS_RUN_SESSION = shutil.which("dbus-run-session")
DISPLAY = ":49"
TIMEOUT = 30
SKIP = 77  # Meson's exit status for a skipped test


class SmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        assert APP is not None, "dailies is not installed"
        assert BROADWAYD is not None, "gtk4-broadwayd is missing"
        assert DBUS_RUN_SESSION is not None, "dbus-run-session is missing"
        self.runtime_dir = Path(tempfile.mkdtemp(prefix="dailies-smoke-"))
        self.addCleanup(shutil.rmtree, self.runtime_dir, ignore_errors=True)
        self.env = {
            **os.environ,
            # A private runtime dir holds the broadway socket; HOME and the XDG dirs keep the app off the user's files.
            "XDG_RUNTIME_DIR": str(self.runtime_dir),
            "HOME": str(self.runtime_dir),
            "XDG_CACHE_HOME": str(self.runtime_dir / "cache"),
            "XDG_CONFIG_HOME": str(self.runtime_dir / "config"),
            "XDG_DATA_HOME": str(self.runtime_dir / "data"),
            "GDK_BACKEND": "broadway",
            "BROADWAY_DISPLAY": DISPLAY,
            "GSETTINGS_BACKEND": "memory",
            "GIO_USE_PROXY_RESOLVER": "dummy",
            "GTK_A11Y": "none",
        }
        # -u serves the broadway web client on a Unix socket instead of a TCP port.
        broadwayd = subprocess.Popen(  # noqa: S603 - fixed command, no user input
            [BROADWAYD, "-u", str(self.runtime_dir / "http.socket"), DISPLAY],
            env=self.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(broadwayd.wait)
        self.addCleanup(broadwayd.terminate)
        # The display socket's number is not the display's (`:49` listens on broadway50.socket); the dir is private.
        deadline = time.monotonic() + 10
        while not any(self.runtime_dir.glob("broadway*.socket")):
            if broadwayd.poll() is not None or time.monotonic() > deadline:
                self.fail(f"gtk4-broadwayd did not open its display socket in {self.runtime_dir}")
            time.sleep(0.05)

    def test_app_opens_its_window_and_quits_cleanly(self) -> None:
        result = subprocess.run(  # noqa: S603 - fixed command, no user input
            [DBUS_RUN_SESSION, "--", APP, "--smoke"],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
        sys.stderr.write(result.stderr)
        assert result.returncode == 0
        assert "CRITICAL" not in result.stderr
        assert "Traceback" not in result.stderr


if __name__ == "__main__":
    if APP is None or not Path(APP).exists():
        sys.stderr.write(f"{APP or 'dailies'} is not installed; the smoke test runs against the installed app\n")
        sys.exit(SKIP)
    unittest.main()
