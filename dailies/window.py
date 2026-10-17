import functools
import logging
from datetime import UTC, datetime

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from dailies import config
from dailies.core import done_today, languages, opening, reorder, sections, web
from dailies.core.models import Category, Game
from dailies.core.opening import OpenMode
from dailies.core.reorder import Move
from dailies.data.favorites import Favorites
from dailies.data.store import Store
from dailies.ui import library, opener
from dailies.ui.filters import LanguageFilter, SearchFilter, SearchSorter, SectionFilter, SectionSorter
from dailies.ui.game_object import GameObject
from dailies.ui.tile import GameTile

log = logging.getLogger(__name__)

# The grid's item factory builds DailiesGameTile by name.
GObject.type_ensure(GameTile.__gtype__)

SUGGEST_GAME_URL = "https://github.com/Tim-van-Oudheusden/Dailies/issues/new?template=new-game.yml"


@Gtk.Template(resource_path=f"{config.PREFIX}/ui/window.ui")
class Window(Adw.ApplicationWindow):
    """The main window: the sidebar of sections and the grid of the selected section's games.

    `section` is the id of the selected section (see `dailies.core.sections`); it is restored from and saved to the
    `last-section` key of the State settings, which also keep the window size. The grid shows the store's games through
    the section filter and the section sorter, whose order the `sort-mode` setting overrides (`win.sort-mode`); the
    `show-other-languages` setting hides, outside Favorites, the games and categories not in the system's languages.

    Games are marked as done today from a tile's menu (`win.toggle-game-done`), from the built-in browser's menu
    (`win.game-done`, the game shown there) or, with `auto-done-today` set, once the game has been open in the built-in
    browser for `done_today.AUTO_MARK_SECONDS`.
    """

    __gtype_name__ = "DailiesWindow"

    section = GObject.Property(type=str, default=sections.FAVORITES)

    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    navigation_view: Adw.NavigationView = Gtk.Template.Child()

    split_view: Adw.NavigationSplitView = Gtk.Template.Child()
    sidebar: Adw.Sidebar = Gtk.Template.Child()
    favorites_item: Adw.SidebarItem = Gtk.Template.Child()
    popular_item: Adw.SidebarItem = Gtk.Template.Child()
    trending_item: Adw.SidebarItem = Gtk.Template.Child()
    categories_section: Adw.SidebarSection = Gtk.Template.Child()
    week_label: Gtk.Label = Gtk.Template.Child()
    content_page: Adw.NavigationPage = Gtk.Template.Child()
    stale_banner: Adw.Banner = Gtk.Template.Child()
    content_stack: Gtk.Stack = Gtk.Template.Child()
    grid_view: Gtk.GridView = Gtk.Template.Child()
    empty_section_page: Adw.StatusPage = Gtk.Template.Child()
    search_bar: Gtk.SearchBar = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    first_run_banner: Adw.Banner = Gtk.Template.Child()

    def __init__(self, *, application: Adw.Application, store: Store, state: Gio.Settings) -> None:
        super().__init__(application=application)
        self._store = store
        self._state = state
        self._settings: Gio.Settings = application.settings
        self._done_today = application.done_today
        # The one live browser page (and so the one live web view), while it is pushed, and the game it shows.
        self._browser_page: Adw.NavigationPage | None = None
        self._browser_game: str | None = None
        # The automatic "done today" timer of the game in the browser page, while it runs.
        self._auto_done_source = 0
        # "Custom command unavailable" is said once per session.
        self._custom_notice_shown = False
        self.navigation_view.connect("popped", self._on_popped)
        self.navigation_view.connect("notify::visible-page", self._on_visible_page)
        for key, prop in (("width", "default-width"), ("height", "default-height"), ("is-maximized", "maximized")):
            state.bind(key, self, prop, Gio.SettingsBindFlags.DEFAULT)

        self._items = {
            sections.FAVORITES: self.favorites_item,
            sections.POPULAR: self.popular_item,
            sections.TRENDING: self.trending_item,
        }
        for category in Category:
            item = Adw.SidebarItem(title=library.category_title(category), icon_name=category.icon_name)
            self.categories_section.append(item)
            self._items[category.value] = item
        self._ids = {item: section for section, item in self._items.items()}

        self._setup_grid(application.settings, application.favorites)
        self.search_bar.connect_entry(self.search_entry)
        self._add_actions(application.settings)

        store.connect("notify::catalog", lambda *_args: self._update_categories())
        self._settings.connect("changed::show-other-languages", lambda *_args: self._update_categories())
        for prop in ("popularity", "popularity-stale"):
            store.connect(f"notify::{prop}", lambda *_args: self._update_week())
        for prop in ("stale-banner", "last-success"):
            store.connect(f"notify::{prop}", lambda *_args: self._update_banner())
        self._update_categories()
        self._update_week()
        self._update_banner()
        self._settings.connect("changed::open-mode", lambda *_args: self._update_first_run_banner())
        state.connect("changed::first-run-banner-dismissed", lambda *_args: self._update_first_run_banner())
        self._update_first_run_banner()
        self._done_today.connect("changed", lambda *_args: self._on_done_changed())
        # A GLib timer misses midnight while the computer sleeps, and a clock or time zone change: look again whenever
        # the user comes back to the window.
        self.connect("notify::is-active", lambda window, _pspec: window.props.is_active and self._done_today.refresh())

        visible = [section for section, item in self._items.items() if item.props.visible]
        self._select(sections.restore(state.get_string("last-section"), visible))
        self._show(self.sidebar.props.selected_item)
        self.sidebar.connect("notify::selected-item", lambda sidebar, _pspec: self._show(sidebar.props.selected_item))

    def open_game(self, game: Game) -> None:
        """Open `game` as its `open-mode-override` or `open-mode` says: custom command, built-in or default browser."""
        game_settings = opener.game_settings(game.id)
        how = opener.resolve(self._settings, game_settings)
        if how is OpenMode.CUSTOM:
            if opener.launch_custom(self._settings.get_string("external-browser-command"), game.url):
                return
            how = opener.resolve(self._settings, game_settings, custom_failed=True)
        if how is OpenMode.IN_APP:
            self._open_in_app(game.url, game.id)
        else:
            self.open_external(game.url)
        self._notify_opened(opener.open_mode(self._settings, game_settings), how, game.url, game.id)

    def _notify_opened(self, mode: OpenMode, how: OpenMode, url: str, game_id: str | None) -> None:
        """Toast where a game set to open with `mode` went (`how`); after an external open, offer "Open Here"."""
        notice = opening.notice(mode, how, custom_notice_shown=self._custom_notice_shown)
        if notice is None:
            return
        if notice is opening.Notice.CUSTOM_UNAVAILABLE:
            self._custom_notice_shown = True
        open_here = None
        if opening.offers_open_here(how, have_webkit=opener.have_webkit()):
            open_here = functools.partial(self._open_in_app, url, game_id)
        self.toast_overlay.add_toast(opener.opened_toast(notice, how, open_here=open_here))

    def open_external(self, url: str) -> None:
        """Open `url` in the host's default browser; anything but an http or https URL is dropped (#151)."""
        if not web.is_web_uri(url):
            log.warning("Not opening %r: only http and https links go to the browser", url)
            return
        opener.launch_external(self, url)

    def _hand_off_pop_up(self, url: str) -> None:
        # No "Open Here" either: the page chose this URI, and the built-in browser must not load a `file:` one.
        if not web.is_web_uri(url):
            log.warning("Not opening the pop-up %r: only http and https links go to the browser", url)
            return
        self.open_external(url)
        self._notify_opened(OpenMode.EXTERNAL, OpenMode.EXTERNAL, url, None)

    def _open_in_app(self, url: str, game_id: str | None) -> None:
        """Show `url` in the built-in browser; `game_id` is the game it is, None for a pop-up handed back in-app.

        A pop-up loads in the shown page's session, so it stays signed in like the game that opened it.
        """
        # Imported here: it loads WebKit, which a cold start must not.
        from dailies.ui import browser_page

        self._state.set_boolean("first-run-banner-dismissed", True)
        page = self._browser_page
        # A pop-up (no game) stays in the shown page's session; a game uses its own (`browser_page.session_dir_for`).
        if page is not None and (
            game_id is None or page.session == browser_page.session_dir_for(self._settings, game_id)
        ):
            page.load(url)
        else:
            # A web view's network session is fixed when it is made: another game's session needs a page of its own.
            self._browser_page = browser_page.BrowserPage(
                settings=self._settings,
                game_id=game_id,
                open_external=self.open_external,
                hand_off_pop_up=self._hand_off_pop_up,
                add_toast=self.toast_overlay.add_toast,
            )
            # Loaded before it is shown, so the page already has a title.
            self._browser_page.load(url)
            if page is not None:
                # The shown page gives way at once: popping it first would leave two pages tagged "browser" while it
                # slides out.
                self.navigation_view.replace([self.navigation_view.find_page("library"), self._browser_page])
                page.close()
            else:
                # A page popped a moment ago is still a child, sliding out, and holds the "browser" tag until then:
                # cut its animation short and drop it, or the new page would not be pushed at all.
                if (popping := self.navigation_view.find_page("browser")) is not None:
                    self.navigation_view.remove(popping)
                self.navigation_view.push(self._browser_page)
        self._set_browser_game(game_id)

    def _set_browser_game(self, game_id: str | None) -> None:
        self._browser_game = game_id
        if self._auto_done_source:
            GLib.source_remove(self._auto_done_source)
            self._auto_done_source = 0
        if game_id is not None and self._settings.get_boolean("auto-done-today"):
            self._auto_done_source = GLib.timeout_add_seconds(done_today.AUTO_MARK_SECONDS, self._on_auto_done, game_id)
        self._update_game_done_action()

    def _on_auto_done(self, game_id: str) -> bool:
        self._auto_done_source = 0
        self._done_today.mark(game_id)
        return GLib.SOURCE_REMOVE

    def _on_done_changed(self) -> None:
        # The sorter reads the games' done state but does not watch it.
        if sections.SortMode.from_id(self._sorter.props.sort_mode) is sections.SortMode.NOT_DONE:
            self._sorter.changed(Gtk.SorterChange.DIFFERENT)
        self._update_game_done_action()

    def _update_game_done_action(self) -> None:
        action = self.lookup_action("game-done")
        game_id = self._browser_game
        action.props.enabled = game_id is not None
        action.set_state(GLib.Variant.new_boolean(game_id is not None and self._done_today.is_done(game_id)))

    def _on_popped(self, _view: Adw.NavigationView, page: Adw.NavigationPage) -> None:
        if page is self._browser_page:
            self._browser_page = None
            self._set_browser_game(None)
            page.close()

    def _on_visible_page(self, view: Adw.NavigationView, _pspec: GObject.ParamSpec) -> None:
        # Toasts about the library (an undo, a refresh) are stale once the user leaves it; a toast about the page
        # just opened is added after it is pushed.
        page = view.props.visible_page
        if page is not None and page.props.tag != "library":
            self.toast_overlay.dismiss_all()

    @Gtk.Template.Callback()
    def on_sidebar_activated(self, _sidebar: Adw.Sidebar, _index: int) -> None:
        """Navigate to the content, which matters when the split view is collapsed."""
        self.split_view.props.show_content = True

    @Gtk.Template.Callback()
    def on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        """Filter the current section, and every section shown next, by the query."""
        self._search_filter.props.text = entry.props.text
        self._update_page()

    @Gtk.Template.Callback()
    def on_search_mode_changed(self, search_bar: Gtk.SearchBar, _pspec: GObject.ParamSpec) -> None:
        """Clear the query when the search bar closes (Escape or the search button), restoring the full section."""
        if not search_bar.props.search_mode_enabled:
            self.search_entry.props.text = ""

    @Gtk.Template.Callback()
    def on_suggest_clicked(self, _button: Gtk.Button) -> None:
        """Open the "Add a game" issue form, always in the host browser."""
        self.open_external(SUGGEST_GAME_URL)

    def _setup_grid(self, settings: Gio.Settings, favorites: Favorites) -> None:
        self._favorites = favorites
        self._section_filter = SectionFilter()
        self._search_filter = SearchFilter()
        self._system_languages = languages.system_languages(GLib.get_language_names())
        self._language_filter = LanguageFilter(self._system_languages)
        self._sorter = SectionSorter(favorites)
        # While a query is active the best matches come first; ties, and every game without a query, keep the section
        # order.
        search_sorter = SearchSorter()
        self._search_filter.bind_property("text", search_sorter, "text", GObject.BindingFlags.SYNC_CREATE)
        sorters = Gtk.MultiSorter()
        sorters.append(search_sorter)
        sorters.append(self._sorter)
        # The store, connected first, has already updated the game's `favorite` when this runs.
        favorites.connect("changed", lambda *_args: self._section_filter.changed(Gtk.FilterChange.DIFFERENT))
        for target in (self._section_filter, self._language_filter, self._sorter):
            self.bind_property("section", target, "section", GObject.BindingFlags.SYNC_CREATE)
        settings.bind("sort-mode", self._sorter, "sort-mode", Gio.SettingsBindFlags.GET)
        settings.bind("show-other-languages", self._language_filter, "show-other-languages", Gio.SettingsBindFlags.GET)
        every = Gtk.EveryFilter()
        every.append(self._section_filter)
        every.append(self._search_filter)
        every.append(self._language_filter)
        self._games = Gtk.SortListModel(
            model=Gtk.FilterListModel(model=self._store.model, filter=every), sorter=sorters
        )
        self.grid_view.props.model = Gtk.NoSelection(model=self._games)
        # A reload changes ranks and statuses, which the filter and the sorter read but do not watch.
        self._store.connect("notify::popularity", lambda *_args: self._refilter())
        self._games.connect("items-changed", lambda *_args: self._update_page())
        self.connect("notify::section", lambda *_args: self._update_page())
        # What the tiles' menus and drag-and-drop may do follows the section, the sort mode and the favourite order.
        favorites.connect("changed", lambda *_args: self._update_moves())
        self.connect("notify::section", lambda *_args: self._update_moves())
        settings.connect("changed::sort-mode", lambda *_args: self._update_moves())
        self._store.connect("notify::catalog", lambda *_args: self._update_moves())
        self._update_moves()
        # Ctrl+Up and Ctrl+Down move the focused favourite; in the capture phase, before the grid moves the focus.
        keys = Gtk.ShortcutController(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        for trigger, move in (("<Control>Up", Move.UP), ("<Control>Down", Move.DOWN)):
            action = Gtk.CallbackAction.new(lambda _widget, _args, move=move: self._on_move_key(move))
            keys.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string(trigger), action))
        self.grid_view.add_controller(keys)

    def _add_actions(self, settings: Gio.Settings) -> None:
        self.add_action(settings.create_action("sort-mode"))
        for name, parameter_type, callback in (
            ("show-section", "s", self._on_show_section),
            ("open-game", "s", self._on_open_game),
            ("toggle-game-favorite", "s", self._on_toggle_game_favorite),
            ("toggle-favorite", None, self._on_toggle_favorite),
            ("toggle-game-done", "s", self._on_toggle_game_done),
            ("show-game-menu", None, self._on_show_game_menu),
            ("move-favorite", "(ss)", self._on_move_favorite),
            ("drop-favorite", "(ssb)", self._on_drop_favorite),
            ("search", None, self._on_search),
        ):
            action = Gio.SimpleAction(
                name=name, parameter_type=GLib.VariantType(parameter_type) if parameter_type else None
            )
            action.connect("activate", callback)
            self.add_action(action)
        # The built-in browser's "Mark as Done Today" check: the state is whether the game shown there is done today.
        game_done = Gio.SimpleAction.new_stateful("game-done", None, GLib.Variant.new_boolean(False))
        game_done.props.enabled = False
        game_done.connect("activate", self._on_game_done)
        self.add_action(game_done)

    def _on_search(self, _action: Gio.SimpleAction, _parameter: None) -> None:
        self.search_bar.props.search_mode_enabled = True
        self.search_entry.grab_focus()

    def _on_show_section(self, _action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        item = self._items.get(parameter.get_string())
        if item is not None and item.props.visible:
            self.sidebar.props.selected = item.get_index()
            self.split_view.props.show_content = True

    @Gtk.Template.Callback()
    def on_game_activated(self, grid_view: Gtk.GridView, position: int) -> None:
        """Open the game whose tile was activated with the keyboard."""
        self._open_item(grid_view.props.model.get_item(position))

    def _on_open_game(self, _action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        self._open_item(self._store.get(parameter.get_string()))

    def _open_item(self, item: GameObject | None) -> None:
        if item is None:
            return
        if item.props.available:
            self.open_game(item.props.game)
            return
        # Only a favourite can be unavailable and still shown.
        game_id = item.props.game.id
        toast = Adw.Toast(title=_("This game is no longer available"), button_label=_("Remove from Favorites"))
        toast.connect("button-clicked", lambda _toast: self._remove_favorite(game_id))
        self.toast_overlay.add_toast(toast)

    def _on_toggle_game_favorite(self, _action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        self._toggle_favorite(parameter.get_string())

    def _on_toggle_favorite(self, _action: Gio.SimpleAction, _parameter: None) -> None:
        tile = self._focused_tile()
        if tile is not None:
            self._toggle_favorite(tile.props.game.props.game.id)

    def _on_show_game_menu(self, _action: Gio.SimpleAction, _parameter: None) -> None:
        tile = self._focused_tile()
        if tile is not None:
            tile.popup_menu()

    def _focused_tile(self) -> GameTile | None:
        """Return the tile that has the focus, or None.

        The focus is on a grid item, whose child is the tile, or on a tile's star.
        """
        tile = self.get_focus()
        while tile is not None and not isinstance(tile, GameTile):
            child = tile.get_first_child()
            tile = child if isinstance(child, GameTile) else tile.get_parent()
        return tile if tile is not None and tile.props.game is not None else None

    def _on_toggle_game_done(self, _action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        self._done_today.toggle(parameter.get_string())

    def _on_game_done(self, _action: Gio.SimpleAction, _parameter: None) -> None:
        if self._browser_game is not None:
            self._done_today.toggle(self._browser_game)

    def _on_move_favorite(self, _action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        game_id, move = parameter.unpack()
        self._move_favorite(game_id, Move(move))

    def _on_move_key(self, move: Move) -> bool:
        """Move the focused favourite with Ctrl+Up or Ctrl+Down; elsewhere the keys keep their grid meaning."""
        tile = self._focused_tile()
        if tile is None or not tile.props.game.props.in_favorites:
            return False
        if not self._move_favorite(tile.props.game.props.game.id, move):
            self.error_bell()
        return True

    def _move_favorite(self, game_id: str, move: Move) -> bool:
        """Move `game_id` in Favorites and keep the focus on it; return whether it could move that way."""
        order = self._favorites.order()
        if move not in sections.favorite_moves(self.props.section, self._sort_mode(), order, game_id):
            return False
        self._favorites.move(game_id, reorder.destination(order, game_id, move))
        self._focus_game(game_id)
        return True

    def _on_drop_favorite(self, _action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        game_id, target_id, after = parameter.unpack()
        order = self._favorites.order()
        if not sections.favorite_moves(self.props.section, self._sort_mode(), order, game_id):
            return
        index = reorder.drop_destination(order, game_id, target_id, after=after)
        if index is not None:
            self._favorites.move(game_id, index)

    def _focus_game(self, game_id: str) -> None:
        # On idle: a move from the tile menu happens before the menu closes, and closing it moves the focus again.
        GLib.idle_add(self._focus_game_now, game_id)

    def _focus_game_now(self, game_id: str) -> bool:
        for position in range(self._games.get_n_items()):
            if self._games.get_item(position).props.game.id == game_id:
                # scroll_to() only moves the focus within the grid; grab_focus() then brings it back from elsewhere.
                self.grid_view.scroll_to(position, Gtk.ListScrollFlags.FOCUS, None)
                if not self.grid_view.get_focus_child():
                    self.grid_view.grab_focus()
                break
        return GLib.SOURCE_REMOVE

    def _sort_mode(self) -> sections.SortMode:
        return sections.SortMode.from_id(self._settings.get_string("sort-mode"))

    def _update_moves(self) -> None:
        """Tell each game whether it is a favourite shown in Favorites and which ways it can move there."""
        section, mode, order = self.props.section, self._sort_mode(), self._favorites.order()
        for item in self._store.model:
            game_id = item.props.game.id
            moves = sections.favorite_moves(section, mode, order, game_id)
            item.update_moves(
                in_favorites=section == sections.FAVORITES and game_id in order,
                can_move_up=Move.UP in moves,
                can_move_down=Move.DOWN in moves,
            )

    def _toggle_favorite(self, game_id: str) -> None:
        if self._favorites.is_favorite(game_id):
            self._remove_favorite(game_id)
        else:
            self._favorites.add(game_id)

    def _remove_favorite(self, game_id: str) -> None:
        """Remove `game_id` from Favorites, offering to undo it: undo puts it back where it was."""
        if not self._favorites.is_favorite(game_id):
            return
        index = self._favorites.order().index(game_id)
        self._favorites.toggle(game_id)
        toast = Adw.Toast(title=_("Removed from Favorites"), button_label=_("Undo"))
        toast.connect("button-clicked", lambda _toast: self._favorites.add(game_id, index))
        self.toast_overlay.add_toast(toast)

    def _refilter(self) -> None:
        self._section_filter.changed(Gtk.FilterChange.DIFFERENT)
        self._sorter.changed(Gtk.SorterChange.DIFFERENT)

    def _update_page(self) -> None:
        searching = bool(self._search_filter.props.text.strip())
        page = sections.page(self.props.section, empty=self._games.get_n_items() == 0, searching=searching)
        self.content_stack.props.visible_child_name = page.value
        if page is sections.Page.EMPTY_SECTION:
            self.empty_section_page.props.icon_name = self._items[self.props.section].props.icon_name

    @Gtk.Template.Callback()
    def on_first_run_banner_clicked(self, _banner: Adw.Banner) -> None:
        """The banner's button opens Preferences (its action); that also dismisses the banner for good."""
        self._state.set_boolean("first-run-banner-dismissed", True)

    def _update_first_run_banner(self) -> None:
        self.first_run_banner.props.revealed = opening.show_first_run_banner(
            OpenMode.from_id(self._settings.get_string("open-mode")),
            have_webkit=opener.webkit_installed(),
            dismissed=self._state.get_boolean("first-run-banner-dismissed"),
        )

    def _select(self, section: str) -> None:
        self.sidebar.props.selected = self._items[section].get_index()

    def _show(self, item: Adw.SidebarItem | None) -> None:
        if item is None:
            return
        section = self._ids[item]
        self.props.section = section
        self.content_page.props.title = item.props.title
        self._state.set_string("last-section", section)

    def _update_categories(self) -> None:
        visible = sections.visible_categories(
            self._store.props.catalog,
            system_languages=self._system_languages,
            show_other=self._settings.get_boolean("show-other-languages"),
        )
        for category in Category:
            self._items[category.value].props.visible = category in visible
        if not self._items[self.props.section].props.visible:
            self._select(sections.FAVORITES)

    def _update_week(self) -> None:
        popularity = self._store.props.popularity
        as_of = sections.week_as_of(popularity, datetime.now(UTC))
        self.week_label.props.label = library.week_subtitle(popularity.week, as_of)

    def _update_banner(self) -> None:
        last_success = self._store.props.last_success
        if last_success is not None:
            self.stale_banner.props.title = library.stale_banner_title(last_success.date())
        self.stale_banner.props.revealed = self._store.props.stale_banner
