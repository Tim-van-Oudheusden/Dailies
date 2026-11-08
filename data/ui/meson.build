# Each .ui is a declared output, so Ninja rebuilds the GResource in the same run as a changed Blueprint file (#432).
blueprints = custom_target(
  'blueprints',
  input: files(
    'browser-page.blp',
    'game-tile.blp',
    'preferences.blp',
    'shortcuts-dialog.blp',
    'window.blp',
  ),
  output: [
    'browser-page.ui',
    'game-tile.ui',
    'preferences.ui',
    'shortcuts-dialog.ui',
    'window.ui',
  ],
  command: [
    find_program('blueprint-compiler', version: '>= 0.22'),
    'batch-compile',
    '--minify',
    '@OUTDIR@',
    '@CURRENT_SOURCE_DIR@',
    '@INPUT@',
  ],
)
