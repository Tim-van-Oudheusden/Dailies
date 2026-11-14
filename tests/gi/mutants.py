"""Hand mutants of the `dailies/` code that only the GI tests reach (#454); tests/gi/test_mutants.py runs them.

mutmut mutates `dailies/core` only, and tests/scripts/test_shell_mutants.py runs its killing tests under plain pytest,
which skips tests/gi. So a branch of `dailies/data` or `dailies/ui` that runs but that no GI test asserts was found
only by hand (#422, #431, #449). Each row changes one string in a module and names the GI test that must fail on the
result. When a hand mutation pass finds one, add the test that kills it and a row here; see docs/testing.md "Shell
mutants". The table pins those known kills: it does not find new ones.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Mutant:
    """`old` in `path` replaced by `new`: the test `killed_by` must fail on the result.

    `path` is a `.py` file under `dailies/`, outside `dailies/core`. `killed_by` is `<module>.<TestCase>.<test>`, the
    module being a `tests/gi` test file without its `.py`.
    """

    name: str
    path: str
    old: str
    new: str
    killed_by: str


FETCHER = "dailies/data/fetcher.py"
BROWSER_PAGE = "dailies/ui/browser_page.py"
TILE = "dailies/ui/tile.py"
GAME_OBJECT = "dailies/ui/game_object.py"

MUTANTS = [
    Mutant(
        "a network error's warning names the transport error, not just 'network error' (#449)",
        FETCHER,
        "Response(None, error=e.message)",
        "Response(None)",
        "test_fetcher.FetcherTest.test_a_network_error_names_its_cause_in_the_warning",
    ),
    Mutant(
        "a page still shown gets WebKit's own beforeunload question (#422)",
        BROWSER_PAGE,
        "if self._closing() and dialog.get_dialog_type()",
        "if dialog.get_dialog_type()",
        "test_window.PageDecisionsTest.test_a_page_still_shown_keeps_its_own_questions",
    ),
    Mutant(
        "every other script dialog is left to WebKit (#422)",
        BROWSER_PAGE,
        "        return False\n\n    def _uri(self)",
        "        return True\n\n    def _uri(self)",
        "test_window.PageDecisionsTest.test_a_page_still_shown_keeps_its_own_questions",
    ),
    Mutant(
        "the card's description says when the game is unavailable or done (#431)",
        TILE,
        "[item.props.description]",
        "[item.props.caption]",
        "test_tile.GameTileTest.test_the_card_description_says_when_the_game_is_unavailable_or_done",
    ),
    Mutant(
        "the game updates its description before a tile reacts to done (#431)",
        GAME_OBJECT,
        'self.connect("notify::done"',
        'self.connect_after("notify::done"',
        "test_tile.GameTileTest.test_the_card_description_says_when_the_game_is_unavailable_or_done",
    ),
]
