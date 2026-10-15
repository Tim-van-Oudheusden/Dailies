from gi.repository import GLib, GObject, Gtk

from dailies import config
from dailies.core import sections
from dailies.ui import library
from dailies.ui.game_object import GameObject


@Gtk.Template(resource_path=f"{config.PREFIX}/ui/game-tile.ui")
class GameTile(Gtk.Overlay):
    """A game's card in the grid: its category glyph, name, category and difficulty pill, and a favourite star.

    Pressing the card activates `win.open-game` with the game's id; pressing the star activates
    `win.toggle-game-favorite` with it. `favorite` follows the game's and drives the star (Blueprint cannot bind a
    chained lookup bidirectionally).
    """

    __gtype_name__ = "DailiesGameTile"

    open_button: Gtk.Button = Gtk.Template.Child()
    glyph: Gtk.Image = Gtk.Template.Child()
    title_label: Gtk.Label = Gtk.Template.Child()
    category_label: Gtk.Label = Gtk.Template.Child()
    difficulty_label: Gtk.Label = Gtk.Template.Child()
    unavailable_label: Gtk.Label = Gtk.Template.Child()
    favorite_button: Gtk.ToggleButton = Gtk.Template.Child()

    def __init__(self, **kwargs: object) -> None:
        self._item: GameObject | None = None
        self._handlers: list[int] = []
        self._favorite = False
        super().__init__(**kwargs)
        self._show_favorite()

    @GObject.Property(type=GameObject)
    def game(self) -> GameObject | None:
        """The game shown, or None while the tile is not bound to an item."""
        return self._item

    @game.setter
    def game(self, item: GameObject | None) -> None:
        if self._item is not None:
            for handler in self._handlers:
                self._item.disconnect(handler)
        self._item = item
        if item is not None:
            self._handlers = [
                item.connect("notify::game", lambda *_args: self._update()),
                item.connect("notify::favorite", lambda *_args: self._sync_favorite()),
            ]
            self._update()
            self._sync_favorite()

    @GObject.Property(type=bool, default=False)
    def favorite(self) -> bool:
        """Whether the star is on; turning it on or off asks the window to toggle the game's favourite state."""
        return self._favorite

    @favorite.setter
    def favorite(self, value: bool) -> None:
        if value == self._favorite:
            return
        self._favorite = value
        self._show_favorite()
        if self._item is not None and value != self._item.props.favorite:
            self.activate_action("win.toggle-game-favorite", GLib.Variant.new_string(self._item.props.game.id))

    def _sync_favorite(self) -> None:
        self.props.favorite = self._item.props.favorite

    def _show_favorite(self) -> None:
        star = self.favorite_button
        star.props.icon_name = "dailies-starred-symbolic" if self._favorite else "dailies-non-starred-symbolic"
        star.props.tooltip_text = _("Remove from Favorites") if self._favorite else _("Add to Favorites")

    def _update(self) -> None:
        item = self._item
        game = item.props.game
        self.glyph.props.icon_name = game.category.icon_name
        self.glyph.set_css_classes(["tile-glyph", sections.category_style(game.category)])
        self.difficulty_label.set_css_classes(
            ["caption-heading", "difficulty-badge", sections.difficulty_style(game.difficulty)]
        )
        self.unavailable_label.props.visible = not item.props.available
        description = library.tile_description(item.props.caption, available=item.props.available)
        self.open_button.update_property([Gtk.AccessibleProperty.DESCRIPTION], [description])

    @Gtk.Template.Callback()
    def on_open_clicked(self, _button: Gtk.Button) -> None:
        """Open the game."""
        if self._item is not None:
            self.activate_action("win.open-game", GLib.Variant.new_string(self._item.props.game.id))
