#!/usr/bin/env bash
# The gate's one listing of suites. A suite is one command (`uv run <file>`,
# one lint step), and it is its own label. With no flag this runs every suite
# `just check` runs, one at a time unless asked. Test files are found by glob
# from the tree on disk, so a new test needs no edit here; the lists below are
# the exceptions.
#
#   bash tests/all.sh [--list] [--group <group>] [--jobs <n>]
#
# `--list` prints the suites the run would cover, one per line, and runs none.
# `--group <group>` runs one group: `lint`, `test`, or `slow` (outside the
# gate, run by hand through `just test-slow`).
#
# `--jobs <n>` runs n suites at once (default 1, or $GATE_JOBS when set: CI
# sets it, so a local run stays one suite at a time on the shared box). The
# suites are independent processes, each with its own temp directories.
#
# One line per suite as it finishes (`PASS <suite>`); a failing suite prints
# `FAIL <suite>` and its whole output, no further suite starts, the suites
# already running finish, and the run exits 1. The last line states what ran:
# `N of M suites passed`.
set -uf
# A caller's GIT_DIR or GIT_INDEX_FILE (a git hook sets both) would point every
# suite that calls git at that caller's repository.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd) || exit 1
cd "$root" || exit 1

# Finder tests that do not run as a plain `uv run <file>`:
#   finder_slow:   the `slow` group only (a CP-SAT solve per known grid,
#                  minutes overall; the Banabner hunt, one 1-worker solve of
#                  about three to four minutes).
#   finder_cover:  run with `--cover` (a subset, one grid per shape) in the
#                  gate, and in full in the `slow` group.
#   finder_pytest: the pytest suites, run as `uv run pytest <file> -q`.
finder_slow="finders/renbanana/tools/test_prove_two_stage_slow.py finders/banabner/test_hunt.py"
finder_cover="finders/renbanana/tools/test_probe_circle_pattern_accepts_known_grids.py finders/renbanana/tools/test_probe_finds_known_grids.py"
finder_pytest="finders/counting_shaded/test_counting_shaded.py"

listed() { case " $1 " in *" $2 "*) return 0 ;; esac; return 1; } # <list> <file>

# Prints "<group>\t<command>" per suite, in run order.
suites() {
  local f
  printf 'lint\t%s\n' \
    "uvx ruff check finders" "uvx ruff format --check finders" "uv lock --check"
  printf 'test\tuv run tests/test_all_sh.py\n'
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
  echo "usage: tests/all.sh [--list] [--group <group>] [--jobs <n>]" >&2
  exit 2
}

list_only=0 group="" jobs=${GATE_JOBS:-1}
while [ $# -gt 0 ]; do
  case $1 in
    --list) list_only=1; shift ;;
    --group)
      [ $# -ge 2 ] || usage "$1 needs a value"
      group=$2; shift 2 ;;
    --jobs)
      [ $# -ge 2 ] || usage "$1 needs a value"
      jobs=$2; shift 2 ;;
    *) usage "no flag named $1" ;;
  esac
done

case $jobs in '' | *[!0-9]* | 0) usage "--jobs needs a positive integer, not '$jobs'" ;; esac

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

# One suite: its PASS line (and a tally mark), or its FAIL line and whole
# output (and its name on the failed list) with exit 255, which makes xargs
# start no further suite. Run in a child bash, so it is exported.
run_suite() { # <suite command>
  local out
  set -f
  if out=$($1 2>&1 </dev/null); then
    echo "PASS $1"
    echo "$1" >>"$state/passed"
  else
    printf 'FAIL %s\n%s\n' "$1" "$out"
    echo "$1" >>"$state/failed"
    exit 255
  fi
}
export -f run_suite

state=$(mktemp -d) || exit 1
trap 'rm -rf "$state"' EXIT
export state
touch "$state/passed" "$state/failed"
grep . <<<"$selected" | xargs -d '\n' -n1 -P "$jobs" bash -c 'run_suite "$0"'
passed=$(grep -c . "$state/passed")
if [ -s "$state/failed" ]; then
  echo "$passed of $total suites passed before $(head -n1 "$state/failed") failed$note"
  exit 1
fi
echo "$passed of $total suites passed$note"
