# Tests that need gi run here, inside the SDK, not in a plain `pytest` (which ignores tests/gi, see pyproject.toml).
if glib_compile_schemas.found()
  gi_test_env = environment()
  gi_test_env.set('GSETTINGS_BACKEND', 'memory')
  gi_test_env.set('GSETTINGS_SCHEMA_DIR', meson.project_build_root() / 'data')
  gi_test_env.set('DAILIES_SCHEMA_ID', app_id)
  gi_test_env.prepend('PYTHONPATH', meson.project_source_root())
  # The fetcher tests talk to a server on 127.0.0.1; inside a sandbox the proxy portal may refuse to resolve for them.
  gi_test_env.set('GIO_USE_PROXY_RESOLVER', 'dummy')

  foreach name : ['favorites', 'store', 'fetcher']
    test(
      name,
      py,
      args: [files('gi' / 'test_' + name + '.py')],
      env: gi_test_env,
      depends: compiled_schemas,
      suite: 'gi',
    )
  endforeach
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
