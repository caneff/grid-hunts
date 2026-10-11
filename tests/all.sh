#!/usr/bin/env bash
# The gate's one listing of suites. A suite is one command (`uv run <file>`,
# one lint step), and it is its own label. With no flag this runs every suite
# `just check` runs, one at a time. Test files are found by glob from the tree
# on disk, so a new test needs no edit here; the lists below are the
# exceptions.
#
#   bash tests/all.sh [--list] [--group <group>]
#
# `--list` prints the suites the run would cover, one per line, and runs none.
# `--group <group>` runs one group: `lint`, `test`, or `slow` (outside the
# gate, run by hand through `just test-slow`).
#
# One line per suite as it finishes (`PASS <suite>`); the first failing suite
# prints `FAIL <suite>` and its whole output, and the run exits 1 there. The
# last line states what ran: `N of M suites passed`.
set -uf
# A caller's GIT_DIR or GIT_INDEX_FILE (a git hook sets both) would point every
# suite that calls git at that caller's repository.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd) || exit 1
cd "$root" || exit 1

# Finder tests that do not run as a plain `uv run <file>`:
#   finder_slow:   the `slow` group only (a CP-SAT solve per known grid,
#                  minutes overall).
#   finder_cover:  run with `--cover` (a subset, one grid per shape) in the
#                  gate, and in full in the `slow` group.
#   finder_pytest: the pytest suites, run as `uv run pytest <file> -q`.
finder_slow="finders/renbanana/tools/test_prove_two_stage_slow.py"
finder_cover="finders/renbanana/tools/test_probe_circle_pattern_accepts_known_grids.py finders/renbanana/tools/test_probe_finds_known_grids.py"
finder_pytest="finders/counting_shaded/test_counting_shaded.py"

listed() { case " $1 " in *" $2 "*) return 0 ;; esac; return 1; } # <list> <file>

# Prints "<group>\t<command>" per suite, in run order.
suites() {
  local f
  printf 'lint\t%s\n' \
    "uvx ruff check finders" "uvx ruff format --check finders" "uv lock --check"
  for f in finders/**/test_*.py; do
    if listed "$finder_slow" "$f"; then continue
    elif listed "$finder_pytest" "$f"; then printf 'test\tuv run pytest %s -q\n' "$f"
    elif listed "$finder_cover" "$f"; then printf 'test\tuv run %s --cover\n' "$f"
    else printf 'test\tuv run %s\n' "$f"; fi
  done
  for f in $finder_cover $finder_slow; do printf 'slow\tuv run %s\n' "$f"; done
}

usage() { # <what is wrong>
  echo "tests/all.sh: $1" >&2
  echo "usage: tests/all.sh [--list] [--group <group>]" >&2
  exit 2
}

list_only=0 group=""
while [ $# -gt 0 ]; do
  case $1 in
    --list) list_only=1; shift ;;
    --group)
      [ $# -ge 2 ] || usage "$1 needs a value"
      group=$2; shift 2 ;;
    *) usage "no flag named $1" ;;
  esac
done

# The tree is globbed here and nowhere else; `set -f` holds everywhere else so
# a suite command is word-split without its path being expanded.
set +f; shopt -s nullglob globstar
all=$(suites)
set -f

if [ -n "$group" ]; then
  case $group in lint | test | slow) ;; *) usage "no group named $group" ;; esac
  all=$(awk -F'\t' -v group="$group" '$1 == group' <<<"$all")
  note=" (group: $group)"
else
  all=$(awk -F'\t' '$1 != "slow"' <<<"$all")
  note=""
fi
selected=$(cut -f2 <<<"$all")

if [ "$list_only" = 1 ]; then [ -z "$selected" ] || printf '%s\n' "$selected"; exit 0; fi

total=$(grep -c . <<<"$selected")
passed=0
while IFS= read -r suite; do
  [ -n "$suite" ] || continue
  if out=$($suite 2>&1 </dev/null); then
    echo "PASS $suite"
    passed=$((passed + 1))
  else
    echo "FAIL $suite"
    printf '%s\n' "$out"
    echo "$passed of $total suites passed before $suite failed$note"
    exit 1
  fi
done <<<"$selected"
echo "$passed of $total suites passed$note"
