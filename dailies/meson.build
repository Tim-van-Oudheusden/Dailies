configure_file(
  input: 'dailies.in',
  output: 'dailies',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x',
)

configure_file(
  input: 'config.py.in',
  output: 'config.py',
  configuration: conf,
  install: true,
  install_dir: moduledir,
)

# The package lives in PKGDATADIR, not site-packages: the launcher puts PKGDATADIR on sys.path.
install_data(
  '__init__.py',
  '__main__.py',
  'application.py',
  'window.py',
  install_dir: moduledir,
)
install_data(
  'core/__init__.py',
  'core/_fields.py',
  'core/catalog.py',
  'core/models.py',
  'core/popularity.py',
  'core/search.py',
  install_dir: moduledir / 'core',
)
install_data('data/__init__.py', install_dir: moduledir / 'data')
install_data('ui/__init__.py', install_dir: moduledir / 'ui')
