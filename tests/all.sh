#!/usr/bin/env bash
# The gate's one listing of suites. A suite is one command (`uv run <file>`,
# one lint step), and it is its own label. With no flag this runs every suite
# `just check` runs, one at a time unless asked. Test files are found by glob
# from the tree on disk, so a new test needs no edit here; the lists below,
# the runner's own test (`tests/test_all_sh.py`) and the Pants edge check
# (`tests/test_pants_edges.py`), both in `suites`, are the exceptions.
#
#   bash tests/all.sh [--list] [--group <group>] [--jobs <n>] [--changed <base>]
#
# `--list` prints the suites the run would cover, one per line, and runs none.
# `--group <group>` runs one group: `lint`, `test`, or `slow` (outside the
# gate, run by hand through `just test-slow`).
#
# `--jobs <n>` runs n suites at once (default $GATE_JOBS when set, else 1: CI
# sets the variable, so a local run stays one suite at a time on the shared
# box). The suites are independent processes, each with its own temp
# directories.
#
# `--changed <base>` narrows the run to what the diff `<base>...HEAD` could
# affect, and Pants says what that is (pants.toml, docs/pants.md):
#   - lint, the runner's own test and the edge check (`tests/test_pants_edges.py`)
#     always run;
#   - a test suite runs when Pants lists its file among the dependents, at any
#     distance, of a file the diff changed: one call, `pants dependents
#     --transitive --closed <files>`. Pants infers the imports; each code
#     directory's BUILD file declares its data (the BUILD file among it) and
#     the scripts a file starts;
#   - a `.md` file and a path under `archive/` change nothing and are not
#     asked about, so a docs-only diff runs lint and the always-run suites;
#   - the run widens to every suite of the selected group, and the count line
#     ends `(widened: <why>)`, on: a change to `pyproject.toml`, `uv.lock`,
#     `pants.toml`, `justfile`, `tests/` or `.github/` (named first in diff
#     order); a deleted or renamed-away file (Pants answers from the tree as it
#     is now, where nothing imports it any more); a changed file Pants cannot
#     place, which no target owns (anything under `docs/` but `.md`, a loose
#     `finders/*.py`, a top-level dotfile); no `pants` on the PATH; and an
#     answer from Pants that is missing or cannot be read. A path names
#     itself as the why.
# `--list --changed <base>` prints that selection. With no `--changed`, the run
# is the full seam.
#
# One line per suite as it finishes (`PASS <suite>`); a failing suite prints
# `FAIL <suite>` and its whole output, no further suite starts, the suites
# already running finish, and the run exits 1. The last line states what ran:
# `N of M suites passed`, or `N of M suites passed, K failed: <suites>`. A
# suite that reports neither pass nor fail (its shell was killed) fails the run
# as well: every suite selected must have passed.
set -uf
# A caller's GIT_DIR or GIT_INDEX_FILE (a git hook sets both) would point every
# suite that calls git at that caller's repository.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd) || exit 1
cd "$root" || exit 1

# Finder tests that do not run as a plain `uv run <file>`:
#   finder_slow:   the `slow` group only (the halver/between hunt, a 9x9
#                  hunt plus its backtracking verify, about a minute; the
#                  halver/lockout 23-line board, about 200 s; the
#                  halver/lockout hunt from the empty board plus its verify;
#                  the five slowest U-Bahn suites, timed in
#                  docs/research/2026-10-22-ubahn-suite-times.md, #77; the
#                  Doppelganger rank 9x9 hunt, about a minute, #72).
#   finder_pytest: the pytest suites, run as `uv run pytest <file> -q`.
finder_slow="finders/halver_between/test_hunt.py finders/halver_lockout/test_unique_23.py finders/halver_lockout/test_hunt.py"
finder_slow="$finder_slow finders/ubahn/test_ubahn_fewest_markings.py finders/ubahn/test_ubahn_hybrid_bananas.py"
finder_slow="$finder_slow finders/ubahn/test_ubahn_hybrid_hunt.py finders/ubahn/test_ubahn_fewest_markings_e2e.py"
finder_slow="$finder_slow finders/ubahn/test_ubahn_brute.py"
finder_slow="$finder_slow finders/doppelganger_rank/test_hunt_9x9.py"
finder_pytest="finders/counting_shaded/test_counting_shaded.py"

# The suites every --changed selection keeps: the runner's own test, and the
# check that Pants still sees each edge a narrowed run selects by.
runner_test="uv run tests/test_all_sh.py"
edges_test="uv run tests/test_pants_edges.py"

listed() { case " $1 " in *" $2 "*) return 0 ;; esac; return 1; } # <list> <file>
suite_file() { local w; for w in $1; do case $w in *.py) echo "$w" ;; esac; done; } # <suite>
# Whether Pants's answer holds a target of the file, `<file>:<target>`.
placed() { case $'\n'"$affected" in *$'\n'"$1:"*) return 0 ;; esac; return 1; } # <file>

# Prints "<group>\t<command>" per suite, in run order.
suites() {
  local f
  printf 'lint\t%s\n' \
    "uvx ruff check finders tests" "uvx ruff format --check finders tests" "uv lock --check"
  printf 'test\t%s\n' "$runner_test" "$edges_test"
  for f in finders/**/test_*.py; do
    if listed "$finder_slow" "$f"; then continue
    elif listed "$finder_pytest" "$f"; then printf 'test\tuv run pytest %s -q\n' "$f"
    else printf 'test\tuv run %s\n' "$f"; fi
  done
  for f in $finder_slow; do printf 'slow\tuv run %s\n' "$f"; done
}

usage() { # <what is wrong>
  echo "tests/all.sh: $1" >&2
  echo "usage: tests/all.sh [--list] [--group <group>] [--jobs <n>] [--changed <base>]" >&2
  exit 2
}

list_only=0 group="" jobs=${GATE_JOBS:-1} base=""
while [ $# -gt 0 ]; do
  case $1 in
    --list) list_only=1; shift ;;
    --group)
      [ $# -ge 2 ] || usage "$1 needs a value"
      group=$2; shift 2 ;;
    --jobs)
      [ $# -ge 2 ] || usage "$1 needs a value"
      jobs=$2; shift 2 ;;
    --changed)
      [ $# -ge 2 ] || usage "$1 needs a value"
      base=$2; shift 2 ;;
    *) usage "no flag named $1" ;;
  esac
done

case $jobs in '' | *[!0-9]* | 0) usage "--jobs needs a positive integer, not '$jobs'" ;; esac

state=$(mktemp -d) || exit 1
trap 'rm -rf "$state"' EXIT

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

# Asks Pants for the targets of the changed files and every target that
# depends on one, at any distance. Sets `affected`, one address per line, or
# `widened` when Pants is missing, fails, gives an answer that is not a list of
# addresses, or holds no target of a changed file: no target owns that file.
ask_pants() { # <changed file>...
  local f
  command -v pants >/dev/null || {
    echo "tests/all.sh: no \`pants\` on the PATH, so the run is not narrowed." >&2
    widened="no \`pants\` on the PATH"; return; }
  # Pants writes its work directory into the tree it runs in unless told.
  affected=$(PANTS_WORKDIR=$state/pants pants dependents --transitive --closed "$@" </dev/null) || {
    widened="Pants gave no answer"; return; }
  while IFS= read -r f; do
    case $f in "" | *:*) ;; *) widened="Pants's answer cannot be read: $f"; return ;; esac
  done <<<"$affected"
  for f in "$@"; do placed "$f" || { widened=$f; return; }; done
}

# --changed: keep lint, the always-run suites, and the suites Pants lists among
# the dependents of the changed files; a path or an answer it cannot narrow on
# keeps every suite and names itself in $note.
if [ -n "$base" ]; then
  files=$(git -c core.quotepath=off diff --name-only --no-renames "$base...HEAD" 2>&1) || usage "git cannot diff $base...HEAD: $files"
  widened="" ask=() affected=""
  while IFS= read -r f; do
    case $f in
      '' | *.md | archive/*) ;; # archived finders are never suites
      pyproject.toml | uv.lock | pants.toml | justfile | tests/* | .github/*) widened=${widened:-$f} ;;
      *) if [ -e "$f" ] || [ -L "$f" ]; then ask+=("$f"); else widened=${widened:-$f}; fi ;;
    esac
  done <<<"$files"
  [ -n "$widened" ] || [ "${#ask[@]}" = 0 ] || ask_pants "${ask[@]}"
  if [ -z "$widened" ]; then
    narrowed=""
    while IFS=$'\t' read -r g c; do
      [ -n "$c" ] || continue
      if [ "$g" = lint ] || [ "$c" = "$runner_test" ] || [ "$c" = "$edges_test" ] ||
        placed "$(suite_file "$c")"; then
        narrowed="$narrowed$g"$'\t'"$c"$'\n'
      fi
    done <<<"$all"
    all=${narrowed%$'\n'}
  else
    note="$note (widened: $widened)"
  fi
fi
selected=$(cut -f2 <<<"$all")

if [ "$list_only" = 1 ]; then [ -z "$selected" ] || printf '%s\n' "$selected"; exit 0; fi

total=$(grep -c . <<<"$selected")

# One suite, run in the background of this shell: a PASS line and its name on
# the passed list, or a FAIL line with its whole output and its name on the
# failed list. A suite this function never finishes (its shell killed) is on
# neither list, which the count below refuses.
run_suite() { # <suite command>
  local out
  if out=$($1 2>&1 </dev/null); then
    echo "PASS $1"
    echo "$1" >>"$state/passed"
  else
    echo "$1" >>"$state/failed"
    printf 'FAIL %s\n%s\n' "$1" "$out"
  fi
}

touch "$state/passed" "$state/failed"
while IFS= read -r suite; do
  [ -n "$suite" ] || continue
  while [ "$(jobs -rp | wc -l)" -ge "$jobs" ]; do wait -n; done
  # A failure starts no further suite; those already running finish below.
  [ -s "$state/failed" ] && break
  run_suite "$suite" &
done <<<"$selected"
wait

passed=$(grep -c . "$state/passed")
failed=$(grep -c . "$state/failed")
if [ "$failed" -gt 0 ]; then
  echo "$passed of $total suites passed, $failed failed: $(paste -sd';' "$state/failed")$note"
  exit 1
fi
# Every suite must have said pass or fail; one that said neither was killed.
if [ "$passed" -ne "$total" ]; then
  echo "$passed of $total suites passed, the rest reported nothing$note"
  exit 1
fi
echo "$passed of $total suites passed$note"
