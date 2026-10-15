# shellcheck shell=bash
# Coverage report helpers, sourced by scripts/coverage-check.sh (and the quality report).
#
# Report contract: `pytest --cov=dailies/core --cov=scripts --cov-report=xml` writes coverage.py's Cobertura XML to
# coverage.xml. Its <sources> lists every measured root that exists (absolute paths, or relative to the repository
# root with `relative_files`), and each <class filename="…"> is a file relative to *one* of those roots, with
# <package name="…"> its directory in dots. Files from different roots share packages (both roots' top-level files
# land in package "."), so neither the package name nor the filename says which root a file came from. A file is
# therefore attributed to the root it exists under on disk; with a single <source> no lookup is needed.
#
# Floor groups: each group in .github/auto-qa-tuning.json names one measured root (coverage_group_dir). A group's
# counts are summed over the <line> elements of all its files, across every package, rather than averaging the
# per-package rates: a branch line's condition-coverage "(covered/valid)" gives its branches.
#
# Files are looked up under <root>, the repository root, or $COVERAGE_ROOT when set (tests point it at a fixture
# tree); a <source> is matched to a group by its trailing path, so a report written in another checkout still maps.

# coverage_group_dir <group>: the measured root of a floor group, relative to the repository root; fails for an
# unknown group.
coverage_group_dir() {
  case "$1" in
    core) echo dailies/core ;;
    scripts) echo scripts ;;
    *) return 1 ;;
  esac
}

# coverage_group_dirs: every group's measured root, one per line.
coverage_group_dirs() {
  coverage_group_dir core
  coverage_group_dir scripts
}

# coverage_counters <report> <group>: prints "<lines-missed> <lines-covered> <branches-missed> <branches-covered>"
# for the group. Returns 2, with the reason on stderr, for an unknown group, an unreadable or malformed report, or a
# file that cannot be attributed to exactly one <source> root.
coverage_counters() {
  local dir dirs
  if ! dir="$(coverage_group_dir "$2")"; then
    echo "Unknown coverage group '$2'" >&2
    return 2
  fi
  dirs="$(coverage_group_dirs)"
  # shellcheck disable=SC2086 # one argument per group root
  python3 -I - "$1" "${COVERAGE_ROOT:-$ROOT}" "$dir" $dirs <<'PY'
import os
import re
import sys
import xml.etree.ElementTree as ET

report, root, target, *group_dirs = sys.argv[1:]


def fail(message):
    print(f"{report}: {message}", file=sys.stderr)
    sys.exit(2)


def under(source, group_dir):
    return source == group_dir or source.endswith("/" + group_dir)


def local_dir(source):
    for group_dir in group_dirs:
        if under(source, group_dir):
            return os.path.join(root, group_dir)
    return source if os.path.isabs(source) else os.path.join(root, source)


try:
    coverage = ET.parse(report).getroot()
except (OSError, ET.ParseError) as error:
    fail(f"not readable as XML ({error})")
if coverage.tag != "coverage":
    fail(f"root element is <{coverage.tag}>, not Cobertura's <coverage>")

sources = [
    os.path.normpath(s.text.strip()).replace("\\", "/")
    for s in coverage.iterfind("sources/source")
    if s.text and s.text.strip()
]
classes = list(coverage.iterfind("packages/package/classes/class"))
if classes and not sources:
    fail("has files but no <sources> roots to attribute them to")

lines_valid = lines_covered = branches_valid = branches_covered = 0
for cls in classes:
    filename = cls.get("filename")
    if not filename:
        fail("has a <class> without a filename")
    if len(sources) == 1:
        owner = sources[0]
    else:
        owners = [s for s in sources if os.path.isfile(os.path.join(local_dir(s), filename))]
        if not owners:
            fail(f"{filename} is under none of the <source> roots {sources}; was the report written in this checkout?")
        if len(owners) > 1:
            fail(f"{filename} exists under several <source> roots {owners}; cannot tell which one it was measured in")
        owner = owners[0]
    if not under(owner, target):
        continue
    for line in cls.iterfind("lines/line"):
        hits = line.get("hits", "")
        if not hits.isdigit():
            fail(f"{filename} line {line.get('number')} has hits={hits!r}")
        lines_valid += 1
        lines_covered += int(hits) > 0
        if line.get("branch") == "true":
            match = re.search(r"\((\d+)/(\d+)\)", line.get("condition-coverage", ""))
            if not match:
                fail(f"{filename} line {line.get('number')} is a branch without condition-coverage counts")
            branches_covered += int(match[1])
            branches_valid += int(match[2])

print(lines_valid - lines_covered, lines_covered, branches_valid - branches_covered, branches_covered)
PY
}

# coverage_percent <missed> <covered>: coverage in percent with two decimals; 100.00 when there is nothing to cover.
coverage_percent() {
  awk -v m="$1" -v c="$2" 'BEGIN { if (m + c == 0) print "100.00"; else printf "%.2f\n", c * 100 / (m + c) }'
}
