"""The Dutch catalog built from po/nl.po, under LANGUAGE=nl; run by Meson (see tests/meson.build).

Meson sets LANGUAGE=nl and points DAILIES_LOCALEDIR at the catalogs it built. Python's gettext reads LANGUAGE itself,
so this needs no Dutch locale in the sandbox; the Blueprint strings go through the C library instead, which ignores
LANGUAGE under the C locale.
"""

import gettext
import os
import unittest

# As dailies.application.main() installs it, with the build directory's catalogs instead of the installed ones.
gettext.install("dailies", os.environ["DAILIES_LOCALEDIR"], names=["ngettext"])

from dailies.core.models import Category, Difficulty
from dailies.ui import library


class DutchTest(unittest.TestCase):
    def test_the_sidebar_shows_dutch_category_names(self) -> None:
        assert library.category_title(Category.GEOGRAPHY) == "Aardrijkskunde"
        assert library.category_title(Category.NUMBERS_LOGIC) == "Getallen en logica"

    def test_a_tile_reads_its_caption_and_state_in_dutch(self) -> None:
        caption = library.caption(library.category_title(Category.WORDS), library.difficulty_title(Difficulty.HARD))

        assert library.tile_description(caption, available=False, done=True) == (
            "Woorden · Moeilijk, niet beschikbaar, vandaag gespeeld"
        )

    def test_plural_forms_follow_the_dutch_catalog(self) -> None:
        assert ngettext("Imported {n} favorite", "Imported {n} favorites", 1) == "{n} favoriet geïmporteerd"
        assert ngettext("Imported {n} favorite", "Imported {n} favorites", 3) == "{n} favorieten geïmporteerd"


if __name__ == "__main__":
    unittest.main()
