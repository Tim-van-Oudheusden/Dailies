import logging
import weakref
from collections.abc import Callable, Collection
from datetime import UTC, datetime

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Soup", "3.0")

from gi.repository import Gdk, Gio, GLib, Soup

try:
    gi.require_version("Gly", "2")
    gi.require_version("GlyGtk4", "2")
    from gi.repository import Gly, GlyGtk4
except (ValueError, ImportError):
    # MSYS2 packages glycin without its typelibs and loaders, so the Windows build has no decoder (#84).
    Gly = GlyGtk4 = None

from dailies.core import icons
from dailies.core.cache import Outcome, Request, Response
from dailies.core.icons import IconCache, IconFetch
from dailies.ui.game_object import GameObject

log = logging.getLogger(__name__)

type Decoder = Callable[[bytes, Callable[[Gdk.Texture | None], None]], None]


def decode(
    data: bytes,
    callback: Callable[[Gdk.Texture | None], None],
    *,
    sandbox: "Gly.SandboxSelector | None" = None,
) -> None:
    """Decode the image `data` with glycin and call `callback` with its first frame, or with None when it fails.

    The icons come from the network, so they are untrusted: glycin decodes them in a separate, sandboxed process
    (`sandbox` picks how, AUTO by default; inside the Flatpak, AUTO is `flatpak-spawn --sandbox`), never GdkPixbuf in
    the app.
    """
    loader = Gly.Loader.new_for_bytes(GLib.Bytes.new(data))
    loader.set_sandbox_selector(Gly.SandboxSelector.AUTO if sandbox is None else sandbox)

    def on_frame(image: Gly.Image, result: Gio.AsyncResult) -> None:
        try:
            frame = image.next_frame_finish(result)
        except GLib.Error as e:
            log.info("could not decode an icon: %s", e.message)
            callback(None)
            return
        callback(GlyGtk4.frame_get_texture(frame))

    def on_loaded(loader: Gly.Loader, result: Gio.AsyncResult) -> None:
        try:
            image = loader.load_finish(result)
        except GLib.Error as e:
            log.info("could not decode an icon: %s", e.message)
            callback(None)
            return
        image.next_frame_async(None, on_frame)

    loader.load_async(None, on_loaded)


class Icons:
    """Puts each game's icon on its `GameObject`: the cached PNG at once, then a newer one when the server has it.

    `load` runs whenever a tile shows a game, so only the icons on screen are read. Each icon is fetched at most once
    per run, only when the cached copy is a week old, and never on a metered network (`dailies.core.icons.IconFetch`).
    A game without an icon, or whose icon cannot be fetched or decoded, keeps its category glyph; so does every game
    when there is no decoder. `forget` drops the icons the catalog stopped naming.

    Args:
        cache: Where the PNGs are kept.
        urls: The data URLs, tried in order; an icon's URL is a data URL followed by the catalog's `icon` path.
        session: The libsoup session to fetch with.
        decode: Turns PNG bytes into a texture; `decode` with glycin's sandbox by default. None, the default without
            glycin, shows no icons and fetches none.
        metered: Says whether the network is metered; `Gio.NetworkMonitor` by default.
    """

    def __init__(
        self,
        cache: IconCache,
        urls: list[str],
        session: Soup.Session,
        *,
        decode: Decoder | None = decode if Gly is not None else None,
        metered: Callable[[], bool] | None = None,
    ) -> None:
        self._cache = cache
        self._urls = urls
        self._session = session
        self._decode = decode
        self._metered = metered or (lambda: Gio.NetworkMonitor.get_default().get_network_metered())
        self._textures: dict[str, Gdk.Texture] = {}
        self._items: dict[str, weakref.WeakSet[GameObject]] = {}
        self._started: set[str] = set()
        # The newest decode of each icon; an older one finishing late is ignored.
        self._decodes: dict[str, int] = {}

    def load(self, item: GameObject) -> None:
        """Show the icon of `item`'s game on it as soon as there is one; a game without an icon gets None."""
        icon = item.props.game.icon
        if icon is None or self._decode is None:
            _show(item, None)
            return
        self._items.setdefault(icon, weakref.WeakSet()).add(item)
        _show(item, self._textures.get(icon))
        if icon in self._started:
            return
        self._started.add(icon)
        if (data := self._cache.read(icon)) is not None:
            self._show_png(icon, data)
        fetch = IconFetch(icon, self._cache, urls=self._urls, now=datetime.now(UTC))
        self._run(fetch, fetch.first_request(metered=self._metered()))

    def forget(self, keep: Collection[str]) -> None:
        """Delete the cached icons that are not in `keep`, the current catalog's `icon` paths, and clear them on games.

        A game whose catalog entry lost its icon (a takedown) goes back to its category glyph, here and on the next
        start.
        """
        try:
            self._cache.prune(keep)
        except OSError as e:
            log.warning("could not clean up the icon cache: %s", e)
        for icon in [icon for icon in self._items if icon not in keep]:
            for item in self._items.pop(icon):
                if item.props.game.icon not in keep:
                    _show(item, None)
            self._textures.pop(icon, None)
            self._started.discard(icon)
            self._decodes.pop(icon, None)

    def _run(self, fetch: IconFetch, request: Request | None) -> None:
        if request is None:
            if fetch.outcome is Outcome.UPDATED and (data := self._cache.read(fetch.icon)) is not None:
                self._show_png(fetch.icon, data)
            return
        message = Soup.Message.new("GET", request.url)
        for header, value in request.headers.items():
            message.get_request_headers().append(header, value)

        def on_response(session: Soup.Session, result: Gio.AsyncResult) -> None:
            try:
                body = session.send_and_read_finish(result).get_data() or b""
            except GLib.Error as e:
                log.info("%s: %s", request.url, e.message)
                response = Response(None)
            else:
                etag = message.get_response_headers().get_one("ETag")
                response = Response(int(message.get_status()), body, etag=etag)
            self._run(fetch, fetch.handle(response))

        # Icons are decoration: the catalog refresh goes first.
        self._session.send_and_read_async(message, GLib.PRIORITY_LOW, None, on_response)

    def _show_png(self, icon: str, data: bytes) -> None:
        generation = self._decodes[icon] = self._decodes.get(icon, 0) + 1

        def decoded(texture: Gdk.Texture | None) -> None:
            if self._decodes.get(icon) != generation:
                return
            if texture is None or not icons.fits(texture.get_width(), texture.get_height()):
                log.warning("%s: the icon does not decode to a tile-sized image, deleting it", icon)
                try:
                    self._cache.remove(icon)
                except OSError as e:
                    log.warning("%s: could not delete it: %s", icon, e)
                return
            self._textures[icon] = texture
            for item in self._items.get(icon, ()):
                if item.props.game.icon == icon:
                    _show(item, texture)

        self._decode(data, decoded)


def _show(item: GameObject, texture: Gdk.Texture | None) -> None:
    if item.props.icon is not texture:
        item.props.icon = texture
