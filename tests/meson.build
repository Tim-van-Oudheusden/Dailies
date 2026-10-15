# Tests that need gi run here, inside the SDK, not in a plain `pytest` (which ignores tests/gi, see pyproject.toml).
if glib_compile_schemas.found()
  gi_test_env = environment()
  gi_test_env.set('GSETTINGS_BACKEND', 'memory')
  gi_test_env.set('GSETTINGS_SCHEMA_DIR', meson.project_build_root() / 'data')
  gi_test_env.set('DAILIES_SCHEMA_ID', app_id)
  gi_test_env.prepend('PYTHONPATH', meson.project_source_root())

  foreach name : ['favorites']
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
