"""A private Broadway display and the build's config module, for the tests/gi modules that need them.

Meson runs each test module as a script, so this directory is on `sys.path` and `import broadway` finds this file.
Call `start()` before importing Gtk, whose override opens the display on import.
"""

import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from gi.repository import Gio


def start() -> None:
    """Start `$BROADWAYD` in a private runtime directory and point GDK at it; fail the module if it does not start.

    The build sandbox has no display, and a Broadway server needs nothing but a socket in the runtime directory. The
    web client is served on a Unix socket there too, not on TCP port 8080 + the display number, so test modules that
    Meson runs in parallel have nothing left to clash over.
    """
    runtime = Path(tempfile.mkdtemp())
    os.environ["XDG_RUNTIME_DIR"] = str(runtime)
    display = f":{os.getpid()}"
    server = Gio.Subprocess.new(
        [os.environ["BROADWAYD"], "--unixsocket", str(runtime / "http.socket"), display],
        Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE,
    )
    unittest.addModuleCleanup(server.wait)
    unittest.addModuleCleanup(server.force_exit)
    deadline = time.monotonic() + 10
    while not any(runtime.glob("broadway*.socket")):
        assert time.monotonic() < deadline, f"gtk4-broadwayd opened no display socket in {runtime} within 10 s"
        time.sleep(0.05)
    os.environ.update(GDK_BACKEND="broadway", BROADWAY_DISPLAY=display)


def load_config() -> None:
    """Import dailies/config.py, which exists only in the build directory (`$DAILIES_CONFIG`), as `dailies.config`."""
    spec = importlib.util.spec_from_file_location("dailies.config", os.environ["DAILIES_CONFIG"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["dailies.config"] = module
