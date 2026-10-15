import logging
from datetime import UTC, datetime

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from dailies import config
from dailies.core import sections
from dailies.core.models import Category, Game
from dailies.data.favorites import Favorites
from dailies.data.store import Store
from dailies.ui import library
from dailies.ui.filters import SearchFilter, SectionFilter, SectionSorter
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
    the section filter and the section sorter, whose order the `sort-mode` setting overrides (`win.sort-mode`).
    """

    __gtype_name__ = "DailiesWindow"

    section = GObject.Property(type=str, default=sections.FAVORITES)

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

    def __init__(self, *, application: Adw.Application, store: Store, state: Gio.Settings) -> None:
        super().__init__(application=application)
        self._store = store
        self._state = state
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
        self._add_actions(application.settings)

        store.connect("notify::catalog", lambda *_args: self._update_categories())
        for prop in ("popularity", "popularity-stale"):
            store.connect(f"notify::{prop}", lambda *_args: self._update_week())
        for prop in ("stale-banner", "last-success"):
            store.connect(f"notify::{prop}", lambda *_args: self._update_banner())
        self._update_categories()
        self._update_week()
        self._update_banner()

        visible = [section for section, item in self._items.items() if item.props.visible]
        self._select(sections.restore(state.get_string("last-section"), visible))
        self._show(self.sidebar.props.selected_item)
        self.sidebar.connect("notify::selected-item", lambda sidebar, _pspec: self._show(sidebar.props.selected_item))

    def open_game(self, game: Game) -> None:
        """Open `game`; the single entry point for opening a game."""
        log.info("opening %s", game.url)

    @Gtk.Template.Callback()
    def on_sidebar_activated(self, _sidebar: Adw.Sidebar, _index: int) -> None:
        """Navigate to the content, which matters when the split view is collapsed."""
        self.split_view.props.show_content = True

    @Gtk.Template.Callback()
    def on_suggest_clicked(self, _button: Gtk.Button) -> None:
        """Open the "Add a game" issue form, always in the host browser."""
        Gtk.UriLauncher(uri=SUGGEST_GAME_URL).launch(self, None, self._on_launched)

    def _setup_grid(self, settings: Gio.Settings, favorites: Favorites) -> None:
        self._section_filter = SectionFilter()
        self._search_filter = SearchFilter()
        self._sorter = SectionSorter(favorites)
        for target in (self._section_filter, self._sorter):
            self.bind_property("section", target, "section", GObject.BindingFlags.SYNC_CREATE)
        settings.bind("sort-mode", self._sorter, "sort-mode", Gio.SettingsBindFlags.GET)
        every = Gtk.EveryFilter()
        every.append(self._section_filter)
        every.append(self._search_filter)
        self._games = Gtk.SortListModel(
            model=Gtk.FilterListModel(model=self._store.model, filter=every), sorter=self._sorter
        )
        self.grid_view.props.model = Gtk.NoSelection(model=self._games)
        # A reload changes ranks and statuses, which the filter and the sorter read but do not watch.
        self._store.connect("notify::popularity", lambda *_args: self._refilter())
        self._games.connect("items-changed", lambda *_args: self._update_page())
        self.connect("notify::section", lambda *_args: self._update_page())

    def _add_actions(self, settings: Gio.Settings) -> None:
        self.add_action(settings.create_action("sort-mode"))
        show_section = Gio.SimpleAction(name="show-section", parameter_type=GLib.VariantType("s"))
        show_section.connect("activate", self._on_show_section)
        self.add_action(show_section)
        open_game = Gio.SimpleAction(name="open-game", parameter_type=GLib.VariantType("s"))
        open_game.connect("activate", self._on_open_game)
        self.add_action(open_game)

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
        if item is not None:
            self.open_game(item.props.game)

    def _on_launched(self, launcher: Gtk.UriLauncher, result: Gio.AsyncResult) -> None:
        try:
            launcher.launch_finish(result)
        except GLib.Error as e:
            log.warning("could not open %s: %s", launcher.props.uri, e.message)

    def _refilter(self) -> None:
        self._section_filter.changed(Gtk.FilterChange.DIFFERENT)
        self._sorter.changed(Gtk.SorterChange.DIFFERENT)

    def _update_page(self) -> None:
        searching = bool(self._search_filter.props.text.strip())
        page = sections.page(self.props.section, empty=self._games.get_n_items() == 0, searching=searching)
        self.content_stack.props.visible_child_name = page.value
        if page is sections.Page.EMPTY_SECTION:
            self.empty_section_page.props.icon_name = self._items[self.props.section].props.icon_name

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
        visible = sections.visible_categories(self._store.props.catalog)
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
