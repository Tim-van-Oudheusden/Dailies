from gi.repository import Gdk, Gio, GLib, GObject, Gtk

from dailies import config
from dailies.core import opening, sections, web
from dailies.core.opening import OpenMode
from dailies.core.reorder import Move
from dailies.ui import library, opener
from dailies.ui.game_object import GameObject


def _open_with_title(choice: str) -> str:
    titles = {
        "": _("_Default"),
        OpenMode.IN_APP.value: _("_Built-in Browser"),
        OpenMode.EXTERNAL.value: _("Default B_rowser"),
        OpenMode.CUSTOM.value: _("_Custom Command"),
    }
    return titles[choice]


def game_menu(item: GameObject, *, have_webkit: bool, host_access: bool) -> Gio.Menu:
    """Return the menu of `item`'s tile, built when it pops up, so its labels follow the game's state.

    Each concern is a section of its own. The done section activates `win.toggle-game-done` with the game's id. The
    options section holds "Open With", radio items of the tile's `tile.open-with` with each `open-mode-override` value
    this installation can do (`dailies.core.opening.game_choices`), and, with the built-in browser (`have_webkit`), the
    `tile.isolated-session` check item. In Favorites, the move section uses the tile's `tile.move-up`, `tile.move-down`
    and `tile.move-to-top` actions, disabled when the move is impossible, and the last section removes the game
    (`win.toggle-game-favorite`).
    """
    game_id = GLib.Variant.new_string(item.props.game.id)
    done = Gio.Menu()
    label = _("Mark as _Not Done") if item.props.done else _("Mark as _Done Today")
    entry = Gio.MenuItem.new(label, None)
    entry.set_action_and_target_value("win.toggle-game-done", game_id)
    done.append_item(entry)
    menu = Gio.Menu()
    menu.append_section(None, done)
    open_with = Gio.Menu()
    for choice in opening.game_choices(have_webkit=have_webkit, host_access=host_access):
        entry = Gio.MenuItem.new(_open_with_title(choice), None)
        entry.set_action_and_target_value("tile.open-with", GLib.Variant.new_string(choice))
        open_with.append_item(entry)
    options = Gio.Menu()
    options.append_submenu(_("_Open With"), open_with)
    # Only the built-in browser has sessions.
    if have_webkit:
        options.append(_("_Isolated Session"), "tile.isolated-session")
    menu.append_section(None, options)
    if item.props.in_favorites:
        moves = Gio.Menu()
        moves.append(_("Move _Up"), "tile.move-up")
        moves.append(_("Move _Down"), "tile.move-down")
        moves.append(_("Move to _Top"), "tile.move-to-top")
        menu.append_section(None, moves)
        remove = Gio.Menu()
        entry = Gio.MenuItem.new(_("_Remove from Favorites"), None)
        entry.set_action_and_target_value("win.toggle-game-favorite", game_id)
        remove.append_item(entry)
        menu.append_section(None, remove)
    return menu


@Gtk.Template(resource_path=f"{config.PREFIX}/ui/game-tile.ui")
class GameTile(Gtk.Overlay):
    """A game's card in the grid: its category glyph, name, category and difficulty pill, and a favourite star.

    Pressing the card activates `win.open-game` with the game's id; pressing the star activates
    `win.toggle-game-favorite` with it. `favorite` follows the game's and drives the star (Blueprint cannot bind a
    chained lookup bidirectionally). A game done today shows a "Done today" badge on a dimmed card. A right click, a
    long press or `popup_menu()` (`win.show-game-menu` from the keyboard) shows the game's menu (`game_menu`).

    The menu's "Open With" and "Isolated Session" items change the game's relocatable `Game` settings
    (`opener.game_settings`): `tile.open-with` holds the `open-mode-override` value the menu selects
    (`dailies.core.opening.shown_game_choice`), and choosing that value again keeps the setting, as Preferences does;
    `tile.isolated-session` holds whether the game has a session of its own and cannot change while every game has one
    (`dailies.core.web.isolated_session_toggle`). Both are read from the settings each time the menu pops up.

    In Favorites a favourite that can move is dragged as its id; dropping one on the first or the second half of a tile
    activates `win.drop-favorite` with the dragged id, this tile's id and whether it goes after this tile, while a bar
    shows that side. The menu's moves activate `win.move-favorite` with the id and the `Move` value.
    """

    __gtype_name__ = "DailiesGameTile"

    open_button: Gtk.Button = Gtk.Template.Child()
    glyph: Gtk.Image = Gtk.Template.Child()
    title_label: Gtk.Label = Gtk.Template.Child()
    category_label: Gtk.Label = Gtk.Template.Child()
    difficulty_label: Gtk.Label = Gtk.Template.Child()
    unavailable_label: Gtk.Label = Gtk.Template.Child()
    done_badge: Gtk.Box = Gtk.Template.Child()
    done_label: Gtk.Label = Gtk.Template.Child()
    favorite_button: Gtk.ToggleButton = Gtk.Template.Child()
    drop_indicator: Gtk.Box = Gtk.Template.Child()

    def __init__(self, **kwargs: object) -> None:
        self._item: GameObject | None = None
        self._game_settings: Gio.Settings | None = None
        self._handlers: list[int] = []
        self._favorite = False
        self._actions = self._create_actions()
        self._drag_hotspot = (0, 0)
        super().__init__(**kwargs)
        self._show_favorite()
        self.menu = Gtk.PopoverMenu(has_arrow=False, halign=Gtk.Align.START)
        self.menu.set_parent(self)
        right_click = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        right_click.connect("pressed", lambda _gesture, _n_press, x, y: self.popup_menu(x, y))
        self.add_controller(right_click)
        long_press = Gtk.GestureLongPress(touch_only=True)
        long_press.connect("pressed", lambda _gesture, x, y: self.popup_menu(x, y))
        self.add_controller(long_press)
        self.insert_action_group("tile", self._actions)
        self._add_drag_and_drop()
        self._sync_moves()

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        """Lay out the card and keep the menu attached to the tile."""
        Gtk.Overlay.do_size_allocate(self, width, height, baseline)
        self.menu.present()

    def do_dispose(self) -> None:
        """Unparent the menu, which the tile owns."""
        if self.menu is not None:
            self.menu.unparent()
            self.menu = None
        Gtk.Overlay.do_dispose(self)

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
        self._game_settings = None
        self._handlers = []
        if item is not None:
            self._handlers = [
                item.connect("notify::game", lambda *_args: self._update()),
                item.connect("notify::favorite", lambda *_args: self._sync_favorite()),
                item.connect("notify::done", lambda *_args: self._update()),
                item.connect("notify::can-move-up", lambda *_args: self._sync_moves()),
                item.connect("notify::can-move-down", lambda *_args: self._sync_moves()),
            ]
            self._update()
            self._sync_favorite()
        self._sync_moves()

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

    def popup_menu(self, x: float | None = None, y: float | None = None) -> None:
        """Show the game's menu at (`x`, `y`) in the tile, or under the whole tile when no point is given."""
        if self._item is None:
            return
        have_webkit, host_access = opener.have_webkit(), opener.host_access()
        self._sync_game_options(opener.game_settings(self._item.props.game.id), have_webkit, host_access)
        self.menu.props.menu_model = game_menu(self._item, have_webkit=have_webkit, host_access=host_access)
        if x is None or y is None:
            self.menu.set_pointing_to(None)
        else:
            rect = Gdk.Rectangle()
            rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
            self.menu.set_pointing_to(rect)
        self.menu.popup()

    def _create_actions(self) -> Gio.SimpleActionGroup:
        actions = Gio.SimpleActionGroup()
        for name, move in (("move-up", Move.UP), ("move-down", Move.DOWN), ("move-to-top", Move.TOP)):
            action = Gio.SimpleAction(name=name, enabled=False)
            action.connect("activate", lambda _action, _parameter, move=move: self._request_move(move))
            actions.add_action(action)
        open_with = Gio.SimpleAction.new_stateful("open-with", GLib.VariantType("s"), GLib.Variant.new_string(""))
        open_with.connect("change-state", self._on_open_with)
        isolated = Gio.SimpleAction.new_stateful("isolated-session", None, GLib.Variant.new_boolean(False))
        isolated.connect("change-state", self._on_isolated_session)
        for action in (open_with, isolated):
            action.props.enabled = False
            actions.add_action(action)
        return actions

    def _sync_game_options(self, game: Gio.Settings | None, have_webkit: bool, host_access: bool) -> None:
        """Show `game`'s settings in `tile.open-with` and `tile.isolated-session`; disable both when it has none."""
        self._game_settings = game
        open_with = self._actions.lookup_action("open-with")
        isolated = self._actions.lookup_action("isolated-session")
        open_with.props.enabled = isolated.props.enabled = game is not None
        if game is None:
            return
        override = game.get_string("open-mode-override")
        shown = opening.shown_game_choice(override, have_webkit=have_webkit, host_access=host_access)
        open_with.set_state(GLib.Variant.new_string(shown))
        isolation = web.SessionIsolation.from_id(Gio.Settings.new(config.APP_ID).get_string("session-isolation"))
        checked, changeable = web.isolated_session_toggle(isolation, isolated=game.get_boolean("isolated-session"))
        isolated.set_state(GLib.Variant.new_boolean(checked))
        isolated.props.enabled = changeable

    def _on_open_with(self, action: Gio.SimpleAction, value: GLib.Variant) -> None:
        # Choosing what is already shown keeps the setting, so an override this installation hides is kept.
        if self._game_settings is not None and value.get_string() != action.get_state().get_string():
            self._game_settings.set_string("open-mode-override", value.get_string())
        action.set_state(value)

    def _on_isolated_session(self, action: Gio.SimpleAction, value: GLib.Variant) -> None:
        if self._game_settings is not None:
            self._game_settings.set_boolean("isolated-session", value.get_boolean())
        action.set_state(value)

    def _add_drag_and_drop(self) -> None:
        # In the capture phase, so the drag wins over the card's click once the pointer has moved far enough.
        source = Gtk.DragSource(actions=Gdk.DragAction.MOVE, propagation_phase=Gtk.PropagationPhase.CAPTURE)
        source.connect("prepare", self._on_drag_prepare)
        source.connect("drag-begin", self._on_drag_begin)
        self.add_controller(source)
        target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        target.connect("enter", self._on_drop_motion)
        target.connect("motion", self._on_drop_motion)
        target.connect("leave", lambda _target: self._show_drop_side(None))
        target.connect("drop", self._on_drop)
        self.add_controller(target)

    def _movable(self) -> bool:
        item = self._item
        return item is not None and item.props.in_favorites and (item.props.can_move_up or item.props.can_move_down)

    def _sync_moves(self) -> None:
        item = self._item
        up = item is not None and item.props.can_move_up
        down = item is not None and item.props.can_move_down
        for name, enabled in (("move-up", up), ("move-down", down), ("move-to-top", up)):
            self._actions.lookup_action(name).props.enabled = enabled

    def _request_move(self, move: Move) -> None:
        if self._item is not None:
            parameter = GLib.Variant("(ss)", (self._item.props.game.id, move.value))
            self.activate_action("win.move-favorite", parameter)

    def _on_drag_prepare(self, _source: Gtk.DragSource, x: float, y: float) -> Gdk.ContentProvider | None:
        if not self._movable():
            return None
        self._drag_hotspot = (int(x), int(y))
        return Gdk.ContentProvider.new_for_value(GObject.Value(GObject.TYPE_STRING, self._item.props.game.id))

    def _on_drag_begin(self, source: Gtk.DragSource, _drag: Gdk.Drag) -> None:
        source.set_icon(Gtk.WidgetPaintable.new(self), *self._drag_hotspot)

    def _drops_after(self, x: float) -> bool:
        after = x > self.get_width() / 2
        return not after if self.get_direction() == Gtk.TextDirection.RTL else after

    def _on_drop_motion(self, _target: Gtk.DropTarget, x: float, _y: float) -> Gdk.DragAction:
        if not self._movable():
            return 0
        self._show_drop_side(self._drops_after(x))
        return Gdk.DragAction.MOVE

    def _show_drop_side(self, after: bool | None) -> None:
        self.drop_indicator.props.visible = after is not None
        if after is not None:
            self.drop_indicator.props.halign = Gtk.Align.END if after else Gtk.Align.START

    def _on_drop(self, _target: Gtk.DropTarget, value: str, x: float, _y: float) -> bool:
        self._show_drop_side(None)
        if not self._movable() or value == self._item.props.game.id:
            return False
        parameter = GLib.Variant("(ssb)", (value, self._item.props.game.id, self._drops_after(x)))
        self.activate_action("win.drop-favorite", parameter)
        return True

    def _sync_favorite(self) -> None:
        self.props.favorite = self._item.props.favorite

    def _show_favorite(self) -> None:
        star = self.favorite_button
        star.props.icon_name = "dailies-starred-symbolic" if self._favorite else "dailies-non-starred-symbolic"
        star.props.tooltip_text = _("Remove from Favorites") if self._favorite else _("Add to Favorites")

    def _update(self) -> None:
        item = self._item
        game = item.props.game
        done = item.props.done
        self.glyph.props.icon_name = game.category.icon_name
        self.glyph.set_css_classes(["tile-glyph", sections.category_style(game.category)])
        self.difficulty_label.set_css_classes(
            ["caption-heading", "difficulty-badge", sections.difficulty_style(game.difficulty)]
        )
        self.unavailable_label.props.visible = not item.props.available
        self.done_badge.props.visible = done
        if done:
            self.open_button.add_css_class("done")
        else:
            self.open_button.remove_css_class("done")
        description = library.tile_description(item.props.caption, available=item.props.available, done=done)
        self.open_button.update_property([Gtk.AccessibleProperty.DESCRIPTION], [description])

    @Gtk.Template.Callback()
    def on_open_clicked(self, _button: Gtk.Button) -> None:
        """Open the game."""
        if self._item is not None:
            self.activate_action("win.open-game", GLib.Variant.new_string(self._item.props.game.id))
