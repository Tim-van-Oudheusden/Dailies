"""Meson test: po/dailies.pot holds exactly the strings xgettext extracts from the files in po/POTFILES.in.

Usage: check_pot.py <xgettext> <msgcmp> <source root>

A change to a translatable string that skips `meson compile -C _build dailies-pot` leaves translators without the new
string and the translations falling back to English. This regenerates the template into a temporary directory and
compares its messages (context and msgid) with the committed one in both directions; line numbers and the header are
ignored. It runs under Meson rather than plain pytest because it needs gettext, which the GNOME SDK has.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

# The keywords of Meson's `glib` gettext preset (po/meson.build) plus the `-k_` Meson always adds.
KEYWORDS = ("_", "N_", "C_:1c,2", "NC_:1c,2", "g_dcgettext:2", "g_dngettext:2,3", "g_dpgettext2:2c,3")


def compare(msgcmp: str, definitions: Path, reference: Path) -> bool:
    """Whether every message in `reference` is also in `definitions`; msgcmp lists the ones that are not."""
    command = [msgcmp, "--use-untranslated", "--no-fuzzy-matching", definitions, reference]
    return subprocess.run(command, check=False).returncode == 0  # noqa: S603 - fixed command, no user input


def main(xgettext: str, msgcmp: str, source_root: str) -> int:
    """Return 0 when the committed template is current, 1 (after listing the differences) otherwise."""
    root = Path(source_root)
    committed = root / "po" / "dailies.pot"
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "dailies.pot"
        subprocess.run(  # noqa: S603 - fixed command, no user input
            [
                xgettext,
                "--package-name=dailies",
                "--from-code=UTF-8",
                "--add-comments",
                *(f"--keyword={keyword}" for keyword in KEYWORDS),
                "--directory",
                root,
                "--files-from",
                root / "po" / "POTFILES.in",
                "--output",
                fresh,
            ],
            check=True,
        )
        # Both directions: a string added to the sources, and one they no longer have (msgcmp already warns about
        # those while checking the first, so the second only runs when the first passes).
        current = compare(msgcmp, committed, fresh) and compare(msgcmp, fresh, committed)
    if not current:
        sys.stderr.write(
            "po/dailies.pot is out of date: run `meson compile -C _build dailies-pot` and "
            "`meson compile -C _build dailies-update-po`, then commit po/\n"
        )
    return 0 if current else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
