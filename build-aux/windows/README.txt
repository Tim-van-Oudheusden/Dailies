Dailies for Windows - EXPERIMENTAL

This build comes from the experimental Windows job in CI (issue #84). It is not a release, and nobody has tried it on
real hardware yet. Please report what works and what does not:
https://github.com/Tim-van-Oudheusden/Dailies/issues

There are two ways to run it:
- The installer (Dailies-...-setup.exe): run it, then start Dailies from the Start menu. It installs for your user
  only unless you choose otherwise, and Settings > Apps uninstalls it. It is not signed, so Windows may warn that the
  publisher is unknown.
- The folder: unzip it anywhere and run Dailies.cmd.

What differs from the Linux app:
- Games open in your default browser. The built-in browser needs WebKitGTK, which does not exist on Windows.
- Game icons are not shown; the tiles keep their category symbols.
