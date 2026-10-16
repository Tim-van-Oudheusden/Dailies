# Dailies
Play your daily guessing games in one place

## Custom browser command

Games open in the built-in browser, or in your default browser, without any extra permission. To open them with a
command of your choice instead, such as a particular browser or browser profile (`firefox --new-window`), Dailies
needs host access, which it never asks for itself.

**Granting it is a sandbox escape that you choose:** it lets Dailies run any command on your computer as you, outside
the Flatpak sandbox. Only grant it if you accept that.

```sh
flatpak override --user --talk-name=org.freedesktop.Flatpak io.github.tim_van_oudheusden.Dailies
```

Restart Dailies, choose **Custom command** under **Preferences → Opening games** and enter the command; the game's
address is added as its last argument and no shell interprets it. To take the access back:

```sh
flatpak override --user --no-talk-name=org.freedesktop.Flatpak io.github.tim_van_oudheusden.Dailies
```

[`CONTRIBUTING.md`](CONTRIBUTING.md#custom-browser-command) has the details.
