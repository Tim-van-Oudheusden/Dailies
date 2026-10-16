"""The game tile against the built resources, on a private Broadway display; run by Meson (see tests/meson.build)."""

import gettext
import importlib.util
import os
import sys
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio


def _start_display() -> None:
    # The build sandbox has no display; a Broadway server needs nothing but a socket in the runtime directory.
    runtime = tempfile.mkdtemp()
    os.environ["XDG_RUNTIME_DIR"] = runtime
    display = str(10 + os.getpid() % 500)
    server = Gio.Subprocess.new(
        [os.environ["BROADWAYD"], f":{display}"],
        Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE,
    )
    deadline = time.monotonic() + 10
    while not any(Path(runtime).glob("broadway*.socket")) and time.monotonic() < deadline:
        time.sleep(0.05)
    os.environ.update(GDK_BACKEND="broadway", BROADWAY_DISPLAY=f":{display}")
    unittest.addModuleCleanup(server.force_exit)


def _load_config() -> None:
    # dailies/config.py exists only in the build directory.
    spec = importlib.util.spec_from_file_location("dailies.config", os.environ["DAILIES_CONFIG"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["dailies.config"] = module


_start_display()
_load_config()
gettext.install("dailies")

from gi.repository import Gdk, GLib, GObject, Gtk

from dailies import config
from dailies.core.models import Category, Difficulty, Game, Status
from dailies.ui import opener
from dailies.ui.game_object import GameObject

Gio.resources_register(Gio.Resource.load(os.environ["DAILIES_GRESOURCE"]))

from dailies.ui.tile import GameTile, game_menu


def worldle(**changes: object) -> Game:
    fields = {
        "id": "worldle",
        "name": "Worldle",
        "url": "https://worldle.teuteuf.fr/",
        "category": Category.GEOGRAPHY,
        "difficulty": Difficulty.EASY,
        "description": "Identify a country from its silhouette.",
        "added": date(2026, 10, 1),
        "status": Status.ACTIVE,
        "domain": "teuteuf.fr",
    }
    return Game(**{**fields, **changes})


class GameTileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.item = GameObject(worldle())
        self.tile = GameTile(game=self.item)
        self.opened: list[str] = []
        self.toggled: list[str] = []
        self.moved: list[tuple[str, str]] = []
        self.dropped: list[tuple[str, str, bool]] = []
        actions = Gio.SimpleActionGroup()
        for name, calls, parameter_type in (
            ("open-game", self.opened, "s"),
            ("toggle-game-favorite", self.toggled, "s"),
            ("move-favorite", self.moved, "(ss)"),
            ("drop-favorite", self.dropped, "(ssb)"),
        ):
            action = Gio.SimpleAction(name=name, parameter_type=GLib.VariantType(parameter_type))
            action.connect("activate", lambda _action, parameter, calls=calls: calls.append(parameter.unpack()))
            actions.add_action(action)
        self.window = Gtk.Window(child=self.tile)
        self.window.insert_action_group("win", actions)
        self.addCleanup(self.window.destroy)
        # The menu asks what this installation can do; here it has the built-in browser and no host access.
        for name, value in (("have_webkit", True), ("host_access", False)):
            patcher = mock.patch.object(opener, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def menu(self) -> Gio.Menu:
        return game_menu(self.item, have_webkit=True, host_access=False)

    def test_the_card_shows_the_name_category_and_difficulty(self) -> None:
        assert self.tile.title_label.props.label == "Worldle"
        assert self.tile.category_label.props.label == "Geography"
        assert self.tile.difficulty_label.props.label == "Easy"
        assert self.tile.difficulty_label.has_css_class("difficulty-easy")
        assert self.tile.glyph.props.icon_name == "dailies-category-geography-symbolic"
        assert self.tile.glyph.has_css_class("cat-geography")

    def test_the_card_follows_a_changed_game(self) -> None:
        changed = worldle(name="Worldle 2", category=Category.WORDS, difficulty=Difficulty.HARD)
        self.item.update(game=changed, favorite=False, popular_rank=0, trending_rank=0)
        assert self.tile.title_label.props.label == "Worldle 2"
        assert self.tile.difficulty_label.has_css_class("difficulty-hard")
        assert not self.tile.difficulty_label.has_css_class("difficulty-easy")
        assert self.tile.glyph.has_css_class("cat-words")
        assert not self.tile.glyph.has_css_class("cat-geography")

    def test_the_card_is_named_by_the_game_and_described_by_its_caption(self) -> None:
        card = self.tile.open_button
        assert Gtk.test_accessible_has_relation(card, Gtk.AccessibleRelation.LABELLED_BY)
        assert Gtk.test_accessible_has_property(card, Gtk.AccessibleProperty.DESCRIPTION)
        assert self.item.props.caption == "Geography · Easy"

    def test_pressing_the_card_opens_the_game(self) -> None:
        self.tile.open_button.emit("clicked")
        assert self.opened == ["worldle"]

    def test_the_star_shows_whether_the_game_is_a_favorite(self) -> None:
        star = self.tile.favorite_button
        assert not star.props.active
        assert star.props.icon_name == "dailies-non-starred-symbolic"
        assert star.props.tooltip_text == "Add to Favorites"
        self.item.props.favorite = True
        assert star.props.active
        assert star.props.icon_name == "dailies-starred-symbolic"
        assert star.props.tooltip_text == "Remove from Favorites"
        assert self.toggled == []

    def test_pressing_the_star_toggles_the_favorite(self) -> None:
        self.tile.favorite_button.emit("clicked")
        assert self.toggled == ["worldle"]
        self.item.props.favorite = True
        self.tile.favorite_button.emit("clicked")
        assert self.toggled == ["worldle", "worldle"]

    def test_an_unavailable_game_says_so(self) -> None:
        assert not self.tile.unavailable_label.get_visible()
        self.item.update(game=worldle(status=Status.BROKEN), favorite=True, popular_rank=0, trending_rank=0)
        assert self.tile.unavailable_label.get_visible()
        assert self.tile.unavailable_label.props.label == "Unavailable"

    def test_the_star_is_a_separate_labelled_button(self) -> None:
        star = self.tile.favorite_button
        assert star.get_parent() is self.tile
        assert star.props.focusable
        assert Gtk.test_accessible_has_property(star, Gtk.AccessibleProperty.LABEL)

    def test_a_game_done_today_shows_the_badge_and_is_dimmed(self) -> None:
        badge = self.tile.done_badge
        assert not badge.get_visible()
        assert not self.tile.open_button.has_css_class("done")
        self.item.props.done = True
        assert badge.get_visible()
        assert self.tile.done_label.props.label == "Done today"
        assert self.tile.open_button.has_css_class("done")
        self.item.props.done = False
        assert not badge.get_visible()
        assert not self.tile.open_button.has_css_class("done")

    def test_the_game_menu_marks_and_unmarks_the_game_as_done_today(self) -> None:
        assert menu_items(self.menu())[0] == ("Mark as _Done Today", "win.toggle-game-done", "worldle")
        self.item.props.done = True
        assert menu_items(self.menu())[0] == ("Mark as _Not Done", "win.toggle-game-done", "worldle")

    def test_the_game_menu_pops_up_on_the_tile(self) -> None:
        self.window.present()
        self.tile.popup_menu()
        assert self.tile.menu.props.visible
        assert menu_items(self.tile.menu.props.menu_model) == menu_items(self.menu())
        self.tile.menu.popdown()

    def test_the_game_menu_offers_each_way_to_open_the_game_and_an_isolated_session(self) -> None:
        menu = game_menu(self.item, have_webkit=True, host_access=True)
        assert menu_entries(menu)[1] == [("_Open With", None), ("_Isolated Session", "tile.isolated-session")]
        assert menu_items(open_with(menu)) == [
            ("_Default", "tile.open-with", ""),
            ("_Built-in Browser", "tile.open-with", "in-app"),
            ("Default B_rowser", "tile.open-with", "external"),
            ("_Custom Command", "tile.open-with", "custom"),
        ]

    def test_the_game_menu_offers_only_what_this_installation_can_do(self) -> None:
        # No built-in browser: no sessions either. No host access: no custom command.
        menu = game_menu(self.item, have_webkit=False, host_access=False)
        assert menu_entries(menu)[1] == [("_Open With", None)]
        assert menu_items(open_with(menu)) == [
            ("_Default", "tile.open-with", ""),
            ("Default B_rowser", "tile.open-with", "external"),
        ]

    def game_settings(self) -> Gio.Settings:
        game = opener.game_settings("worldle")
        for key in ("open-mode-override", "isolated-session"):
            self.addCleanup(game.reset, key)
        return game

    def pop_up_and_down(self) -> None:
        self.window.present()
        self.tile.popup_menu()
        self.tile.menu.popdown()

    def test_choosing_how_the_game_opens_sets_its_override(self) -> None:
        game = self.game_settings()
        self.pop_up_and_down()
        self.tile.activate_action("tile.open-with", GLib.Variant.new_string("external"))
        assert game.get_string("open-mode-override") == "external"
        self.tile.activate_action("tile.open-with", GLib.Variant.new_string(""))
        assert game.get_string("open-mode-override") == ""

    def test_choosing_what_a_hidden_override_shows_as_keeps_it(self) -> None:
        # Without host access a game set to the custom command opens in the built-in browser, and the menu says so.
        game = self.game_settings()
        game.set_string("open-mode-override", "custom")
        self.pop_up_and_down()
        self.tile.activate_action("tile.open-with", GLib.Variant.new_string("in-app"))
        assert game.get_string("open-mode-override") == "custom"
        self.tile.activate_action("tile.open-with", GLib.Variant.new_string("external"))
        assert game.get_string("open-mode-override") == "external"

    def test_the_isolated_session_item_toggles_the_games_own_session(self) -> None:
        game = self.game_settings()
        self.pop_up_and_down()
        self.tile.activate_action("tile.isolated-session", None)
        assert game.get_boolean("isolated-session")
        self.tile.activate_action("tile.isolated-session", None)
        assert not game.get_boolean("isolated-session")

    def test_the_isolated_session_item_cannot_change_while_every_game_is_isolated(self) -> None:
        settings = Gio.Settings.new(config.APP_ID)
        settings.set_string("session-isolation", "per-game")
        self.addCleanup(settings.reset, "session-isolation")
        game = self.game_settings()
        self.pop_up_and_down()
        self.tile.activate_action("tile.isolated-session", None)
        assert not game.get_boolean("isolated-session")

    def favorite_in_favorites(self, *, up: bool, down: bool) -> None:
        self.item.props.favorite = True
        self.item.update_moves(in_favorites=True, can_move_up=up, can_move_down=down)

    def test_outside_favorites_the_menu_neither_moves_nor_removes_the_game(self) -> None:
        self.item.props.favorite = True
        actions = [action for section in menu_entries(self.menu()) for _label, action in section]
        assert not {"tile.move-up", "tile.move-down", "tile.move-to-top", "win.toggle-game-favorite"} & set(actions)

    def test_in_favorites_the_menu_moves_then_removes_the_game(self) -> None:
        self.favorite_in_favorites(up=True, down=True)
        menu = self.menu()
        entries = menu_entries(menu)
        options = [("_Open With", None), ("_Isolated Session", "tile.isolated-session")]
        moves = [("Move _Up", "tile.move-up"), ("Move _Down", "tile.move-down"), ("Move to _Top", "tile.move-to-top")]
        remove = [("_Remove from Favorites", "win.toggle-game-favorite")]
        assert entries == [[("Mark as _Done Today", "win.toggle-game-done")], options, moves, remove]
        remove_section = menu.get_item_link(entries.index(remove), Gio.MENU_LINK_SECTION)
        assert remove_section.get_item_attribute_value(0, Gio.MENU_ATTRIBUTE_TARGET, None).get_string() == "worldle"

    def test_the_move_items_ask_the_window_to_move_the_game(self) -> None:
        self.favorite_in_favorites(up=True, down=True)
        for name in ("move-up", "move-down", "move-to-top"):
            self.tile.activate_action(f"tile.{name}", None)
        assert self.moved == [("worldle", "up"), ("worldle", "down"), ("worldle", "top")]

    def test_impossible_moves_are_disabled(self) -> None:
        self.favorite_in_favorites(up=False, down=True)
        for name in ("move-up", "move-down", "move-to-top"):
            self.tile.activate_action(f"tile.{name}", None)
        assert self.moved == [("worldle", "down")]

        self.item.update_moves(in_favorites=True, can_move_up=True, can_move_down=False)
        self.tile.activate_action("tile.move-up", None)
        self.tile.activate_action("tile.move-down", None)
        assert self.moved == [("worldle", "down"), ("worldle", "up")]

    def test_in_favorites_the_menu_pops_up_with_the_moves(self) -> None:
        self.favorite_in_favorites(up=True, down=True)
        self.window.present()
        self.tile.popup_menu()
        assert self.tile.menu.get_visible()
        assert ("Move _Up", "tile.move-up") in menu_entries(self.tile.menu.props.menu_model)[2]
        self.tile.menu.popdown()

    def test_a_movable_favorite_can_be_dragged_as_its_id(self) -> None:
        source = controller(self.tile, Gtk.DragSource)
        assert source.props.actions == Gdk.DragAction.MOVE
        assert source.emit("prepare", 10, 10) is None

        self.favorite_in_favorites(up=False, down=True)
        content = source.emit("prepare", 10, 10)
        assert content.ref_formats().contain_gtype(GObject.TYPE_STRING)
        assert content_string(content) == "worldle"

    def test_a_drop_asks_the_window_to_put_the_dragged_game_beside_this_one(self) -> None:
        self.favorite_in_favorites(up=True, down=False)
        self.window.present()
        drain_main_context()
        target = controller(self.tile, Gtk.DropTarget)
        assert target.props.actions == Gdk.DragAction.MOVE
        assert target.get_gtypes() == [GObject.TYPE_STRING]
        width = self.tile.get_width()

        assert target.emit("drop", "globle", 1, 10)
        assert target.emit("drop", "globle", width - 1, 10)
        assert self.dropped == [("globle", "worldle", False), ("globle", "worldle", True)]

    def test_dropping_on_a_tile_outside_favorites_is_refused(self) -> None:
        target = controller(self.tile, Gtk.DropTarget)
        assert not target.emit("drop", "globle", 1, 10)
        assert self.dropped == []

    def test_the_drop_indicator_shows_the_side_the_game_will_go(self) -> None:
        self.favorite_in_favorites(up=True, down=True)
        self.window.present()
        drain_main_context()
        target = controller(self.tile, Gtk.DropTarget)
        indicator = self.tile.drop_indicator
        assert not indicator.get_visible()

        target.emit("motion", 1, 10)
        assert indicator.get_visible()
        assert indicator.props.halign == Gtk.Align.START
        target.emit("motion", self.tile.get_width() - 1, 10)
        assert indicator.props.halign == Gtk.Align.END
        target.emit("leave")
        assert not indicator.get_visible()


def menu_items(menu: Gio.MenuModel) -> list[tuple[str, str, str | None]]:
    """The label, action and string target of every item, sections and submenus flattened."""
    items = []
    for index in range(menu.get_n_items()):
        linked = menu.get_item_link(index, Gio.MENU_LINK_SECTION) or menu.get_item_link(index, Gio.MENU_LINK_SUBMENU)
        if linked is not None:
            items += menu_items(linked)
            continue
        attribute = menu.get_item_attribute_value
        target = attribute(index, Gio.MENU_ATTRIBUTE_TARGET, None)
        items.append(
            (
                attribute(index, Gio.MENU_ATTRIBUTE_LABEL, None).get_string(),
                attribute(index, Gio.MENU_ATTRIBUTE_ACTION, None).get_string(),
                None if target is None else target.get_string(),
            )
        )
    return items


def open_with(menu: Gio.MenuModel) -> Gio.MenuModel:
    """The "Open With" submenu: the first item of the menu's second section."""
    return menu.get_item_link(1, Gio.MENU_LINK_SECTION).get_item_link(0, Gio.MENU_LINK_SUBMENU)


def menu_entries(menu: Gio.MenuModel) -> list[list[tuple[str, str | None]]]:
    """The label and action of every item, per section; a submenu has no action."""
    sections = []
    for i in range(menu.get_n_items()):
        section = menu.get_item_link(i, Gio.MENU_LINK_SECTION)
        entries = []
        for j in range(section.get_n_items()):
            label = section.get_item_attribute_value(j, Gio.MENU_ATTRIBUTE_LABEL, None).get_string()
            action = section.get_item_attribute_value(j, Gio.MENU_ATTRIBUTE_ACTION, None)
            entries.append((label, None if action is None else action.get_string()))
        sections.append(entries)
    return sections


def controller(widget: Gtk.Widget, kind: type) -> Gtk.EventController:
    controllers = widget.observe_controllers()
    return next(c for c in (controllers.get_item(i) for i in range(controllers.get_n_items())) if isinstance(c, kind))


def content_string(content: Gdk.ContentProvider) -> str:
    # PyGObject cannot pass get_value() its out GValue; a local clipboard hands the value over as it is.
    clipboard = Gdk.Display.get_default().get_clipboard()
    clipboard.set_content(content)
    result: list[str] = []
    clipboard.read_value_async(
        GObject.TYPE_STRING, GLib.PRIORITY_DEFAULT, None, lambda c, r: result.append(c.read_value_finish(r))
    )
    while not result:
        GLib.MainContext.default().iteration(may_block=True)
    return result[0]


def drain_main_context() -> None:
    context = GLib.MainContext.default()
    while context.iteration(may_block=False):
        pass


if __name__ == "__main__":
    unittest.main()
