#!/bin/sh
# One optimization arm, round after round, until the deadline. Generalises
# run_overnight.sh: CLIMB and RANK choose what the arm is hunting.
#
#   CLIMB=circled  climb the count of circled 2x2 / 2x3, refuse to lose one
#   CLIMB=small    climb the count of banana groups of SMALLMAX cells or fewer
#   CLIMB=both     circles first, small groups as the tie-break
#
# A renban of k cells holds the run [m, m+k-1], so a group of 5 or more always
# contains its own size: its circle is forced and says nothing. Every grid in
# the pool at the time of writing carries a 9-cell banana group, and averages
# 0.8 small ones, so the small arm has a great deal of room to climb.
#
# Rounds re-pick their seeds, so tonight's find is tomorrow's starting point,
# and every round converts and commits -- a kill loses at most the round in
# flight. Progress files are working artifacts and stay out of git.
set -eu
PROCS=${PROCS:-8}
BUDGET=${BUDGET:-900}
HOURS=${HOURS:-10}
CLIMB=${CLIMB:-small}
RANK=${RANK:-small}
WANT=${WANT:-2x2,2x3}
FLOOR=${FLOOR:-0}
SMALLMAX=${SMALLMAX:-4}
MINSCORE=${MINSCORE:-0}
POOL=${POOL:-docs/research/renbanana/candidates-small}
WALK=${WALK:-docs/research/renbanana/walk-small}
SEEDS=${SEEDS:-docs/research/renbanana/small-seeds.txt}
PROGRESS=${PROGRESS:-PROGRESS_small.md}

END=$(( $(date +%s) + HOURS * 3600 ))
ROUND=0
mkdir -p "$WALK" "$POOL"

while [ "$(date +%s)" -lt "$END" ]; do
  ROUND=$((ROUND + 1))
  echo "=== round $ROUND at $(date '+%H:%M:%S')" >> "$PROGRESS"

  uv run python docs/research/renbanana/tools/pick_seeds.py \
      --rank "$RANK" --want "$WANT" --small-max "$SMALLMAX" \
      --min-score "$MINSCORE" --top "$PROCS" --out "$SEEDS" >> "$PROGRESS" 2>&1

  PROCS="$PROCS" BUDGET="$BUDGET" OUT="$WALK" WANT="$WANT" FLOOR="$FLOOR" \
    CLIMB="$CLIMB" SMALLMAX="$SMALLMAX" SEEDFILE="$SEEDS" \
    sh docs/research/renbanana/tools/run_walk.sh \
    >> "$WALK/PROGRESS_arm.log" 2>&1 || true

  uv run --with ortools python docs/research/renbanana/tools/walk_to_candidates.py \
      --walk "$WALK" --out "$POOL" >> "$PROGRESS" 2>&1 || true

  git add -A docs/research/renbanana >> /dev/null 2>&1 || true
  git commit -q -m "docs/research/renbanana: $CLIMB arm, round $ROUND" \
      >> /dev/null 2>&1 || true
  echo "  round $ROUND done at $(date '+%H:%M:%S'), pool $(ls "$POOL"/cand_*.json 2>/dev/null | wc -l)" >> "$PROGRESS"
done
echo "=== $CLIMB arm finished at $(date '+%H:%M:%S') after $ROUND rounds" >> "$PROGRESS"
