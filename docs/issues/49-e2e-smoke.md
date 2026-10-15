---
key: 49
title: test(e2e): GTK smoke test under dbus-run-session + xvfb
type: Task
labels: milestone::M1, type::task, priority::medium, app, ci
parent: 3
blocked_by: 24, 27
---
> **Risk tier:** medium · **Size:** S · **ACMM:** `prereq-e2e` (by directory name `tests/e2e/`)

## Why

This is the only automated check that the installed app actually starts inside the Flatpak build environment. It catches a broken gresource, a missing typelib, a schema error or a Python import error.

## Tasks

- [ ] Add a hidden CLI flag `--smoke` (via `Adw.Application` `add_main_option`). It exits with status 0 shortly after the window's `map` signal, once the initial store load (#39) has run, and skips the network refresh
- [ ] `tests/e2e/test_smoke.py`: run `dbus-run-session -- xvfb-run -a dailies --smoke` with `GSETTINGS_BACKEND=memory`. Assert exit code 0 and that stderr contains no `CRITICAL` and no `Traceback`. 30 s timeout
- [ ] Register it as a Meson `test()` (suite `e2e`) so it runs under `flatpak-builder --run-tests`, i.e. in the CI job `Flatpak (x86_64)` (#27). The container provides xvfb
- [ ] Replace the placeholder from #20, keeping the `e2e` marker so plain `pytest` on a bare runner still skips it

## Acceptance criteria

- [ ] `Flatpak (x86_64)` runs the smoke test and reports it in the Meson test log
- [ ] Introducing a deliberate typo in `window.blp` (in a scratch branch) makes the job fail at build time; an exception raised in `do_activate` makes the smoke test fail

## References

- [`mvp-first.md` §12 (E2E smoke row)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`hive-acmm.md` §9 Phase 0](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/hive-acmm.md)
