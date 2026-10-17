from collections.abc import Callable
from typing import Self

from gi.repository import GObject

from dailies.core.models import Game, Status
from dailies.core.sections import Listing
from dailies.ui import library


class GameObject(GObject.Object):
    """One game in the list model, with what the store adds to it, as properties that bindings and filters can watch.

    `name`, `category-label`, `difficulty-label`, `caption` ("Geography · Easy", all translated) and `available`
    (the game is active) follow `game`. A rank of 0 means the game is not on that shelf this week. `done` says whether
    the game was marked as done today; the store sets it apart from `update`, as it changes with the day. The window
    sets `in-favorites` (the game is a favourite and Favorites is shown), `can-move-up` and `can-move-down` (it can move
    in the favourite order there), which drive the tile's menu and drag-and-drop. `icon` is the game's icon as a
    `Gdk.Paintable` once `request_icon` has found one (`dailies.data.icons.Icons`), else None.
    """

    __gtype_name__ = "DailiesGameObject"

    game = GObject.Property(type=object)
    name = GObject.Property(type=str, default="")
    category_label = GObject.Property(type=str, default="")
    difficulty_label = GObject.Property(type=str, default="")
    caption = GObject.Property(type=str, default="")
    available = GObject.Property(type=bool, default=True)
    favorite = GObject.Property(type=bool, default=False)
    popular_rank = GObject.Property(type=int, default=0)
    trending_rank = GObject.Property(type=int, default=0)
    done = GObject.Property(type=bool, default=False)
    in_favorites = GObject.Property(type=bool, default=False)
    can_move_up = GObject.Property(type=bool, default=False)
    can_move_down = GObject.Property(type=bool, default=False)
    icon = GObject.Property(type=object)

    def __init__(self, game: Game, *, load_icon: Callable[[Self], None] | None = None) -> None:
        super().__init__()
        self._load_icon = load_icon
        self._set(_derived(game))

    def request_icon(self) -> None:
        """Ask for the game's icon; a tile calls this whenever it shows the game, and `icon` follows."""
        if self._load_icon is not None:
            self._load_icon(self)

    def update(self, *, game: Game, favorite: bool, popular_rank: int, trending_rank: int) -> None:
        """Set the properties that differ from the given values, so only real changes notify."""
        self._set(
            {
                **_derived(game),
                "favorite": favorite,
                "popular-rank": popular_rank,
                "trending-rank": trending_rank,
            }
        )

    def update_moves(self, *, in_favorites: bool, can_move_up: bool, can_move_down: bool) -> None:
        """Set where the game can move in Favorites; only real changes notify."""
        self._set({"in-favorites": in_favorites, "can-move-up": can_move_up, "can-move-down": can_move_down})

    def listing(self) -> Listing:
        """Return the game as the section rules see it."""
        return Listing(
            game=self.props.game,
            favorite=self.props.favorite,
            popular_rank=self.props.popular_rank,
            trending_rank=self.props.trending_rank,
            done=self.props.done,
        )

    def _set(self, values: dict[str, object]) -> None:
        for name, value in values.items():
            if self.get_property(name) != value:
                self.set_property(name, value)


def _derived(game: Game) -> dict[str, object]:
    category = library.category_title(game.category)
    difficulty = library.difficulty_title(game.difficulty)
    # `game` last: whoever watches it sees the other properties already updated.
    return {
        "name": game.name,
        "category-label": category,
        "difficulty-label": difficulty,
        "caption": library.caption(category, difficulty),
        "available": game.status is Status.ACTIVE,
        "game": game,
    }
