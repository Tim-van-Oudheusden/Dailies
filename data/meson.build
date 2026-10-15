subdir('icons')

blueprints = custom_target(
  'blueprints',
  input: files('ui/browser-page.blp', 'ui/game-tile.blp', 'ui/window.blp'),
  output: '.',
  command: [
    find_program('blueprint-compiler', version: '>= 0.22'),
    'batch-compile',
    '--minify',
    '@OUTPUT@',
    '@CURRENT_SOURCE_DIR@',
    '@INPUT@',
  ],
)

desktop_file = i18n.merge_file(
  input: configure_file(
    input: 'io.github.tim_van_oudheusden.Dailies.desktop.in',
    output: app_id + '.desktop.in',
    configuration: conf,
  ),
  output: app_id + '.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: get_option('datadir') / 'applications',
)

metainfo_file = i18n.merge_file(
  input: configure_file(
    input: 'io.github.tim_van_oudheusden.Dailies.metainfo.xml.in',
    output: app_id + '.metainfo.xml.in',
    configuration: conf,
  ),
  output: app_id + '.metainfo.xml',
  po_dir: '../po',
  install: true,
  install_dir: get_option('datadir') / 'metainfo',
)

configure_file(
  input: 'io.github.tim_van_oudheusden.Dailies.service.in',
  output: app_id + '.service',
  configuration: conf,
  install: true,
  install_dir: get_option('datadir') / 'dbus-1' / 'services',
)

gschema = configure_file(
  input: 'io.github.tim_van_oudheusden.Dailies.gschema.xml.in',
  output: app_id + '.gschema.xml',
  configuration: conf,
  install: true,
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)

glib_compile_schemas = find_program('glib-compile-schemas', required: false)
if glib_compile_schemas.found()
  # A compiled copy next to the configured schema, so `gsettings --schemadir` and the gi tests can read it uninstalled.
  compiled_schemas = custom_target(
    'compiled-schemas',
    input: gschema,
    output: 'gschemas.compiled',
    command: [
      glib_compile_schemas,
      '--strict',
      '--targetdir',
      '@OUTDIR@',
      '@OUTDIR@',
    ],
    build_by_default: true,
  )
endif

resources = gnome.compile_resources(
  'dailies',
  configure_file(
    input: 'dailies.gresource.xml.in',
    output: 'dailies.gresource.xml',
    configuration: conf,
  ),
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: [blueprints, metainfo_file],
)

# The offline snapshot: the store seeds the cache from it on a first run and whenever the cached copy is unusable.
install_data(
  'v1/games.json',
  'v1/popularity.json',
  install_dir: pkgdatadir / 'data' / 'v1',
)

desktop_file_validate = find_program('desktop-file-validate', required: false)
if desktop_file_validate.found()
  test('Validate desktop file', desktop_file_validate, args: [desktop_file])
endif

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test(
    'Validate metainfo file',
    appstreamcli,
    args: ['validate', '--no-net', '--explain', metainfo_file],
    workdir: meson.current_build_dir(),
  )
endif

if glib_compile_schemas.found()
  # The configured schema lives in the build directory; the source directory only has the .in template.
  test(
    'Validate schema file',
    glib_compile_schemas,
    args: ['--strict', '--dry-run', meson.current_build_dir()],
  )
endif

# Every icon the UI looks up by name (the Category glyphs in dailies/core/models.py and the sidebar/favourite icons)
# must resolve from the bundled gresource.
test(
  'Bundled icons resolve',
  py,
  args: [files('../tests/icons/check_icons.py'), resources, prefix_path],
  env: {'PYTHONPATH': meson.project_source_root()},
)
