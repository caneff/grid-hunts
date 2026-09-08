#!/bin/bash
# One solver process per seed: memory returns to the OS between seeds, and a
# 9 GB address-space cap kills a runaway seed instead of the machine.
# usage: arm.sh outdir first last [extra hunt args after per_box...]
out=$1; first=$2; last=$3; shift 3
Z=/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/scratch-zombo
R=/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang
cd $Z/hunt || exit 1
for ((s=first; s<last; s++)); do
  [ -f "$Z/hunt/STOP" ] && exit 0
  (ulimit -v 9000000; uv run --with ortools python zb_bal.py hunt $s $((s+1)) 1500 $out 1 2 12 0 9:2 0 "$R/docs/research/zombo-brainanas/found/*.json" "$@") >> $out/run.log 2>&1
done
echo "ARM DONE $out" >> $out/PROGRESS.md
