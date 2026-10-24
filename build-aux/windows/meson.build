# The Inno Setup script for the experimental installer (#242). Not installed: ISCC reads it from the build directory
# and packs the install prefix, after build-aux/windows/bundle.sh has added the MSYS2 runtime to it.
iss_conf = configuration_data()
iss_conf.set('VERSION', meson.project_version())
iss_conf.set('BUNDLE', get_option('prefix').replace('/', '\\'))
# The interpreter bundle.sh copies lib/python<version> from: the one Meson found.
iss_conf.set('PYTHON_VERSION', py.language_version())
iss_conf.set(
  'LICENSE',
  (meson.project_source_root() / 'LICENSE').replace('/', '\\'),
)
configure_file(
  input: 'Dailies.iss.in',
  output: 'Dailies.iss',
  configuration: iss_conf,
)
