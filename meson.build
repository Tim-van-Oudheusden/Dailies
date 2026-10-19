project(
  'dailies',
  version: '0.2.2',
  meson_version: '>= 1.4',
  license: 'GPL-3.0-or-later',
)

gnome = import('gnome')
i18n = import('i18n')
python = import('python')

dependency('gtk4', version: '>= 4.24')
dependency('libadwaita-1', version: '>= 1.10')
# The built-in browser is optional: without WebKitGTK the app only opens games in the default browser.
webkit = dependency('webkitgtk-6.0', version: '>= 2.54', required: false)

py = python.find_installation('python3')

profile = get_option('profile')
if profile == 'development'
  app_id = 'io.github.tim_van_oudheusden.Dailies.Devel'
  prefix_path = '/io/github/tim_van_oudheusden/Dailies/Devel'
else
  app_id = 'io.github.tim_van_oudheusden.Dailies'
  prefix_path = '/io/github/tim_van_oudheusden/Dailies'
endif

bindir = get_option('prefix') / get_option('bindir')
localedir = get_option('prefix') / get_option('localedir')
pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'dailies'

conf = configuration_data()
conf.set('APP_ID', app_id)
conf.set('PREFIX_PATH', prefix_path)
conf.set('VERSION', meson.project_version())
conf.set('PROFILE', profile)
conf.set('BINDIR', bindir)
conf.set('PKGDATADIR', pkgdatadir)
conf.set('LOCALEDIR', localedir)
conf.set('PYTHON', py.full_path())
conf.set('HAVE_WEBKIT', webkit.found() ? 'True' : 'False')

subdir('data')
subdir('dailies')
subdir('po')
subdir('tests')

gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
