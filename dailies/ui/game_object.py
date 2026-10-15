from gi.repository import GObject

from dailies.core.models import Game


class GameObject(GObject.Object):
    """One game in the list model, with what the store adds to it, as properties that bindings and filters can watch.

    A rank of 0 means the game is not on that shelf this week.
    """

    __gtype_name__ = "DailiesGameObject"

    game = GObject.Property(type=object)
    favorite = GObject.Property(type=bool, default=False)
    popular_rank = GObject.Property(type=int, default=0)
    trending_rank = GObject.Property(type=int, default=0)

    def __init__(self, game: Game) -> None:
        super().__init__(game=game)

    def update(self, *, game: Game, favorite: bool, popular_rank: int, trending_rank: int) -> None:
        """Set the properties that differ from the given values, so only real changes notify."""
        for name, value in (
            ("game", game),
            ("favorite", favorite),
            ("popular-rank", popular_rank),
            ("trending-rank", trending_rank),
        ):
            if self.get_property(name) != value:
                self.set_property(name, value)
