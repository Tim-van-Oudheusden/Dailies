# Tests that need gi run here, inside the SDK, not in a plain `pytest` (which ignores tests/gi, see pyproject.toml).
if glib_compile_schemas.found()
  gi_test_env = environment()
  gi_test_env.set('GSETTINGS_BACKEND', 'memory')
  gi_test_env.set('GSETTINGS_SCHEMA_DIR', meson.project_build_root() / 'data')
  gi_test_env.set('DAILIES_SCHEMA_ID', app_id)
  gi_test_env.prepend('PYTHONPATH', meson.project_source_root())
  # The fetcher tests talk to a server on 127.0.0.1; inside a sandbox the proxy portal may refuse to resolve for them.
  gi_test_env.set('GIO_USE_PROXY_RESOLVER', 'dummy')

  foreach name : ['favorites', 'done_today', 'store', 'fetcher', 'filters']
    test(
      name,
      py,
      args: [files('gi' / 'test_' + name + '.py')],
      env: gi_test_env,
      depends: compiled_schemas,
      suite: 'gi',
    )
  endforeach

  # These tests need the built resources and config.py, and a display: each test starts its own Broadway server.
  broadwayd = find_program('gtk4-broadwayd', required: false)
  if broadwayd.found()
    tile_test_env = gi_test_env
    tile_test_env.set('BROADWAYD', broadwayd.full_path())
    tile_test_env.set('DAILIES_GRESOURCE', resources[0].full_path())
    tile_test_env.set('DAILIES_CONFIG', meson.project_build_root() / 'dailies' / 'config.py')
    foreach name : ['tile', 'opening', 'window', 'favorites_transfer']
      test(
        name,
        py,
        args: [files('gi' / 'test_' + name + '.py')],
        env: tile_test_env,
        depends: [compiled_schemas, resources],
        suite: 'gi',
      )
    endforeach

    # The built-in browser's sessions and WebKit settings, against a real WebKit network process.
    if webkit.found()
      test(
        'browser',
        py,
        args: [files('gi' / 'test_browser.py')],
        env: tile_test_env,
        depends: [compiled_schemas, resources],
        suite: 'gi',
        timeout: 60,
      )
    endif
  endif

  # The bundled Shortcuts and About dialogs; the test opens its own Broadway display.
  dialogs_test_env = gi_test_env
  dialogs_test_env.set('DAILIES_GRESOURCE', resources[0].full_path())
  dialogs_test_env.set('DAILIES_PREFIX', prefix_path)
  dialogs_test_env.set('DAILIES_VERSION', meson.project_version())
  test(
    'dialogs',
    py,
    args: [files('gi' / 'test_dialogs.py')],
    env: dialogs_test_env,
    depends: [compiled_schemas, resources],
    suite: 'gi',
  )

  # The Dutch catalog built from po/nl.po, read under LANGUAGE=nl.
  translations_test_env = gi_test_env
  translations_test_env.set('LANGUAGE', 'nl')
  translations_test_env.set('DAILIES_LOCALEDIR', meson.project_build_root() / 'po')
  test(
    'translations',
    py,
    args: [files('gi' / 'test_translations.py')],
    env: translations_test_env,
    depends: mo_files,
    suite: 'gi',
  )
endif

# The e2e smoke test starts the installed app, so it only passes after `meson install` (flatpak-builder runs the tests
# after installing); otherwise it reports SKIP.
test(
  'smoke',
  py,
  args: [files('e2e' / 'test_smoke.py')],
  env: {'DAILIES_BIN': bindir / 'dailies'},
  suite: 'e2e',
  timeout: 60,
)
