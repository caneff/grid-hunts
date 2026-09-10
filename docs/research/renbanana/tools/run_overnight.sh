#!/bin/sh
# Hunt grids holding more than one circled 2x2 or 2x3, round after round,
# until the deadline.
#
# Each round re-picks its seeds from the pool, so a grid found at 2am is a
# starting point by 2:20. The walk refuses to step downhill on the circled
# count, so seeding from the best grids is what makes the second circle
# reachable at all -- 518 shadings of the shading-first hunt never found one.
#
# Results are converted and committed every round: a kill at any moment loses
# at most the round in flight.
set -eu
PROCS=${PROCS:-24}
BUDGET=${BUDGET:-900}
HOURS=${HOURS:-10}
WANT=${WANT:-2x2,2x3}
POOL=${POOL:-docs/research/renbanana/candidates-circled}
WALK=${WALK:-docs/research/renbanana/walk-circled}
SEEDS=${SEEDS:-docs/research/renbanana/circled-seeds.txt}
PROGRESS=${PROGRESS:-PROGRESS_overnight.md}

END=$(( $(date +%s) + HOURS * 3600 ))
ROUND=0
mkdir -p "$WALK" "$POOL"

while [ "$(date +%s)" -lt "$END" ]; do
  ROUND=$((ROUND + 1))
  echo "=== round $ROUND at $(date '+%H:%M:%S')" >> "$PROGRESS"

  uv run python docs/research/renbanana/tools/pick_seeds.py \
      --want "$WANT" --top "$PROCS" --out "$SEEDS" >> "$PROGRESS" 2>&1

  PROCS="$PROCS" BUDGET="$BUDGET" OUT="$WALK" WANT="$WANT" FLOOR=1 \
    SEEDFILE="$SEEDS" sh docs/research/renbanana/tools/run_walk.sh \
    >> "$WALK/PROGRESS_circled.log" 2>&1 || true

  uv run --with ortools python docs/research/renbanana/tools/walk_to_candidates.py \
      --walk "$WALK" --out "$POOL" >> "$PROGRESS" 2>&1 || true

  # Shout about the thing we are actually hunting.
  uv run python docs/research/renbanana/tools/pick_seeds.py \
      --want "$WANT" --top 1 --min-score 2 \
      --out /dev/null >> "$PROGRESS" 2>&1 \
      && echo "  *** A GRID WITH TWO CIRCLED SHAPES EXISTS ***" >> "$PROGRESS"

  git add -A docs/research/renbanana >> /dev/null 2>&1 || true
  git commit -q -m "docs/research/renbanana: overnight circled hunt, round $ROUND" \
      >> /dev/null 2>&1 || true
  echo "  round $ROUND done at $(date '+%H:%M:%S'), pool $(ls "$POOL"/cand_*.json 2>/dev/null | wc -l)" >> "$PROGRESS"
done
echo "=== overnight run finished at $(date '+%H:%M:%S') after $ROUND rounds" >> "$PROGRESS"
