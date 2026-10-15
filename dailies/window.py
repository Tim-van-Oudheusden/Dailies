from datetime import UTC, datetime

from gi.repository import Adw, Gio, GObject, Gtk

from dailies import config
from dailies.core import sections
from dailies.core.models import Category
from dailies.data.store import Store
from dailies.ui import library


@Gtk.Template(resource_path=f"{config.PREFIX}/ui/window.ui")
class Window(Adw.ApplicationWindow):
    """The main window: the sidebar of sections and, for now, a placeholder for the selected section's games.

    `section` is the id of the selected section (see `dailies.core.sections`); it is restored from and saved to the
    `last-section` key of the State settings, which also keep the window size.
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

    @Gtk.Template.Callback()
    def on_sidebar_activated(self, _sidebar: Adw.Sidebar, _index: int) -> None:
        """Navigate to the content, which matters when the split view is collapsed."""
        self.split_view.props.show_content = True

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
