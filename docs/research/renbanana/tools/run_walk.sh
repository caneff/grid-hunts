#!/bin/sh
# Walk a set of seed grids in parallel, one worker per process.
#
# PROCS must stay at or below half the machine's cores (AGENTS.md).
# SEEDS is a glob of candidate files to start from, or SEEDFILE is a file
# holding one path per line -- walking seeds that are already walked out mostly
# returns grids the skip-set throws away, so point it at fresh ones.
# WANT and FLOOR aim the walk at circled shapes; leave them empty to let it
# wander on diversity alone.
set -eu
PROCS=${PROCS:-12}
BUDGET=${BUDGET:-900}
OUT=${OUT:-docs/research/renbanana/walk}
WANT=${WANT:-}
FLOOR=${FLOOR:-0}
CLIMB=${CLIMB:-circled}
SMALLMAX=${SMALLMAX:-4}
SEEDFILE=${SEEDFILE:-}
SEEDS=${SEEDS:-docs/research/renbanana/candidates*/cand_*.json}

if [ -n "$SEEDFILE" ]; then
  cat "$SEEDFILE"
else
  # shellcheck disable=SC2086
  ls $SEEDS
fi | xargs -P "$PROCS" -I{} uv run --with ortools \
      docs/research/renbanana/tools/probe_walk.py \
      --source {} --budget "$BUDGET" --seconds 20 --workers 1 \
      --want "$WANT" --floor "$FLOOR" --climb "$CLIMB" \
      --small-max "$SMALLMAX" --out "$OUT"
