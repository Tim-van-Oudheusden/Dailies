from gi.repository import GLib, GObject, Gtk

from dailies import config
from dailies.core import sections
from dailies.ui.game_object import GameObject


@Gtk.Template(resource_path=f"{config.PREFIX}/ui/game-tile.ui")
class GameTile(Gtk.Overlay):
    """A game's card in the grid: its category glyph, name, category and difficulty pill, and a favourite star.

    Pressing the card activates `win.open-game` with the game's id.
    """

    __gtype_name__ = "DailiesGameTile"

    open_button: Gtk.Button = Gtk.Template.Child()
    glyph: Gtk.Image = Gtk.Template.Child()
    title_label: Gtk.Label = Gtk.Template.Child()
    category_label: Gtk.Label = Gtk.Template.Child()
    difficulty_label: Gtk.Label = Gtk.Template.Child()
    favorite_button: Gtk.ToggleButton = Gtk.Template.Child()

    def __init__(self, **kwargs: object) -> None:
        self._item: GameObject | None = None
        self._handler = 0
        super().__init__(**kwargs)

    @GObject.Property(type=GameObject)
    def game(self) -> GameObject | None:
        """The game shown, or None while the tile is not bound to an item."""
        return self._item

    @game.setter
    def game(self, item: GameObject | None) -> None:
        if self._item is not None:
            self._item.disconnect(self._handler)
        self._item = item
        if item is not None:
            self._handler = item.connect("notify::game", lambda *_args: self._update())
            self._update()

    def _update(self) -> None:
        item = self._item
        game = item.props.game
        self.glyph.props.icon_name = game.category.icon_name
        self.glyph.set_css_classes(["tile-glyph", sections.category_style(game.category)])
        self.difficulty_label.set_css_classes(
            ["caption-heading", "difficulty-badge", sections.difficulty_style(game.difficulty)]
        )
        self.open_button.update_property([Gtk.AccessibleProperty.DESCRIPTION], [item.props.caption])

    @Gtk.Template.Callback()
    def on_open_clicked(self, _button: Gtk.Button) -> None:
        """Open the game."""
        if self._item is not None:
            self.activate_action("win.open-game", GLib.Variant.new_string(self._item.props.game.id))
