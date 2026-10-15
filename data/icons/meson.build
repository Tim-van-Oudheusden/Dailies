# The Devel profile has its own app ID, so each profile installs its icons under its own ID: the release build the
# plain icon, the development build App Icon Preview's striped variant. The .Source.svg project is not installed.
base_id = 'io.github.tim_van_oudheusden.Dailies'

scalable_dir = 'hicolor' / 'scalable' / 'apps'
install_data(
  scalable_dir / (
    profile == 'development' ? base_id + '.Devel.svg' : base_id + '.svg'
  ),
  install_dir: get_option('datadir') / 'icons' / scalable_dir,
  rename: app_id + '.svg',
)

symbolic_dir = 'hicolor' / 'symbolic' / 'apps'
install_data(
  symbolic_dir / (base_id + '-symbolic.svg'),
  install_dir: get_option('datadir') / 'icons' / symbolic_dir,
  rename: app_id + '-symbolic.svg',
)
