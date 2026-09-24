#!/bin/bash
# 34–36 hunt: big channelled finder over (hunt, QR-10 window, corner), criterion q34, known grids forbidden.
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
S=${HUNT_LOGS:-$ROOT/.scratch/place}
mkdir -p "$S"
S=$(cd "$S" && pwd)
export HUNT_LOGS=$S
MAXPOOLS=4; LOADCAP=22; WORKERS=6; TIMEOUT=1800; COUNT=5; FLAGS="tables warm forbid-known criteria=q34"
cd "$ROOT"
JOBS=(
  "r5c1 r6c6 tl" "r5c1 r6c6 tr" "r5c1 r6c6 bl" "r5c1 r6c6 br"
  "r5c1 r6c7 tl" "r5c1 r6c7 tr" "r5c1 r6c7 bl" "r5c1 r6c7 br"
  "r5c1 r7c6 tl" "r5c1 r7c6 tr" "r5c1 r7c6 bl" "r5c1 r7c6 br"
  "r1c5 r6c7 tl" "r1c5 r6c7 tr" "r1c5 r6c7 bl" "r1c5 r6c7 br"
  "r1c5 r7c6 tl" "r1c5 r7c6 tr" "r1c5 r7c6 bl" "r1c5 r7c6 br"
  "r5c1 r7c7 tl" "r5c1 r7c7 tr" "r5c1 r7c7 bl" "r5c1 r7c7 br"
  "r1c5 r6c6 tl" "r1c5 r6c6 tr" "r1c5 r6c6 bl" "r1c5 r6c6 br"
  "r1c5 r7c7 tl" "r1c5 r7c7 tr" "r1c5 r7c7 bl" "r1c5 r7c7 br"
)
pools() { ps -eo args | grep '[c]han_big.py' | grep -v 'bash -c\|job-run\|uv run' | wc -l; }
for job in "${JOBS[@]}"; do
  set -- $job; hunt=$1; ten=$2; corner=$3
  log="$S/big-$hunt-$ten-$corner-q34.log"
  grep -q '^\(infeasible\|timeout\|multiple\|unique\):' "$log" 2>/dev/null && continue
  while [ $(pools) -ge $MAXPOOLS ] || [ $(cut -d. -f1 /proc/loadavg) -ge $LOADCAP ]; do sleep 30; done
  echo "$(date +%T) launch q34 $job" >> "$S/scheduler.log"
  job-run --name qqrr-q34-$hunt-$ten-$corner -- uv run python "$ROOT/finders/qqrr/hunt/chan_big.py" $hunt $ten $corner $WORKERS $TIMEOUT "$log" $COUNT $FLAGS >/dev/null 2>&1 &
  sleep 20
done
wait
echo "$(date +%T) all q34 finders finished" >> "$S/scheduler.log"
