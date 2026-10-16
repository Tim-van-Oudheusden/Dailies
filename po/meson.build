# The .mo build targets, one per language in LINGUAS; tests/meson.build reads the Dutch one.
mo_files = i18n.gettext(meson.project_name(), preset: 'glib')[0]

# The committed template must match the sources, or new strings never reach translators (CONTRIBUTING.md,
# "Updating the template").
xgettext = find_program('xgettext', required: false)
msgcmp = find_program('msgcmp', required: false)
if xgettext.found() and msgcmp.found()
  test(
    'Template is up to date',
    py,
    args: [
      files('../tests/tooling/check_pot.py'),
      xgettext,
      msgcmp,
      meson.project_source_root(),
    ],
  )
endif
