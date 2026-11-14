"""The hand mutants in tests/gi/mutants.py (#454); run by Meson (see tests/meson.build).

For each row this copies `dailies/` to a temporary directory, applies the replacement there and runs the named GI test
in a fresh interpreter with the copy first on PYTHONPATH. Meson's environment for the GI tests already puts the source
root on PYTHONPATH and the built resources and config elsewhere, so a `.py` mutant needs no rebuild.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mutants import MUTANTS

GI = Path(__file__).resolve().parent
ROOT = GI.parents[1]

# Runs one test, `<module>.<TestCase>.<test>` with the module in `tests/gi`, and exits 0 when it passed, 1 when it
# failed or raised, 2 when it could not be loaded (the module did not import, or has no such test) and 3 when it did not
# run exactly one test (skipped, or the name was a whole class). Only 1 is a kill: a mutant that breaks the import of
# the test module, or a test that skips, says nothing about the assertion.
RUN_ONE = """
import importlib, sys, traceback, unittest

sys.path.insert(0, sys.argv[1])
module_name, _, test = sys.argv[2].partition(".")
loader = unittest.TestLoader()
try:
    suite = loader.loadTestsFromName(test, importlib.import_module(module_name))
except Exception:
    traceback.print_exc()
    sys.exit(2)
if loader.errors:
    print(*loader.errors, sep="\\n", file=sys.stderr)
    sys.exit(2)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if result.testsRun != 1 or result.skipped:
    sys.exit(3)
sys.exit(0 if result.wasSuccessful() else 1)
"""


def copy_package(dest: Path) -> Path:
    """Copy `dailies/` into `dest`, so the mutant never touches the source tree; return `dest`."""
    shutil.copytree(ROOT / "dailies", dest / "dailies", ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def run_test(root: Path, test: str) -> subprocess.CompletedProcess[str]:
    """Run `test` in a new interpreter that imports `dailies` from `root`, with this test's environment otherwise."""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, [str(root), os.environ.get("PYTHONPATH")]))
    return subprocess.run(  # noqa: S603 - this interpreter, test names from tests/gi/mutants.py
        [sys.executable, "-c", RUN_ONE, str(GI), test],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


class MutantsTest(unittest.TestCase):
    # Without this control, a harness that cannot run the copied test at all would count every mutant as killed.
    def test_the_killing_tests_pass_on_an_unmutated_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = copy_package(Path(directory))
            for test in sorted({mutant.killed_by for mutant in MUTANTS}):
                with self.subTest(test):
                    result = run_test(root, test)
                    assert result.returncode == 0, f"exit {result.returncode}:\n{result.stdout}{result.stderr}"

    def test_every_mutant_is_killed(self) -> None:
        for mutant in MUTANTS:
            with self.subTest(mutant.name):
                # dailies/core has mutmut (docs/testing.md "Python mutants"), and only .py sources skip a rebuild.
                assert mutant.path.startswith("dailies/"), mutant.path
                assert not mutant.path.startswith("dailies/core/"), mutant.path
                assert mutant.path.endswith(".py"), mutant.path
                source = (ROOT / mutant.path).read_text(encoding="utf-8")
                # A row the module has moved away from must fail here, not pass by mutating nothing.
                assert source.count(mutant.old) == 1, f"{mutant.old!r} must occur exactly once in {mutant.path}"
                with tempfile.TemporaryDirectory() as directory:
                    root = copy_package(Path(directory))
                    (root / mutant.path).write_text(source.replace(mutant.old, mutant.new), encoding="utf-8")
                    result = run_test(root, mutant.killed_by)
                assert result.returncode == 1, (
                    f"it survived {mutant.killed_by} (exit {result.returncode}):\n{result.stdout}{result.stderr}"
                )


if __name__ == "__main__":
    unittest.main()
