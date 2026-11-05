"""SCRATCH: is there a grid with the forced 7 on r3c3 and six circles on other box centres? 8 CP-SAT workers.

usage: aqre_box_seven_r3c3.py DIR [LIMIT_SECONDS]

Chris's ask, 2026-11-05. The model is `aqre_box_seven.build`, with box 1 the 7 and r3c3 its 7. The solver chooses which two
of boxes 2-9 hold no circle. No extra facts are added: a first version added "box 1's edges are shaded", which is false, so
its run was stopped. A found grid goes through the plain Python check and is written to box-seven-r3c3.json. UNKNOWN at
the cap proves nothing.
"""

import json
import sys
import time
from pathlib import Path

from aqre_box_seven import CENTRES, build, check
from ortools.sat.python import cp_model

SEVEN = (2, 2)


def main(out, limit):
    begun = time.time()
    m, x, g, value = build()
    m.add(value[0, 7] == 1)
    m.add(x[SEVEN] == 7)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 8
    s.parameters.max_time_in_seconds = limit
    status = s.status_name(s.solve(m))
    print(f"status {status}, {time.time() - begun:.0f}s, cap {limit:.0f}s", flush=True)
    if status not in ("OPTIMAL", "FEASIBLE"):
        return
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[int(s.value(g[r, c])) for c in range(9)] for r in range(9)]
    circles = {0: SEVEN}
    for k in range(1, 9):
        if any(s.value(value[k, v]) for v in range(1, 7)):
            circles[k] = CENTRES[k]
    problem = check(digits, shade, circles)
    print(f"plain check: {problem or 'all rules hold'}", flush=True)
    for r in range(9):
        print(" ".join(f"{digits[r][c]}{'#' if shade[r][c] else '.'}{'o' if (r, c) in circles.values() else ' '}" for c in range(9)), flush=True)
    print("circles (box, row, column, digit):", [(k + 1, cell[0] + 1, cell[1] + 1, digits[cell[0]][cell[1]]) for k, cell in sorted(circles.items())], flush=True)
    if not problem:
        (out / "box-seven-r3c3.json").write_text(json.dumps({"digits": digits, "shade": shade, "circles": {str(k): cell for k, cell in circles.items()}}))


if __name__ == "__main__":
    main(Path(sys.argv[1]), float(sys.argv[2]) if len(sys.argv) > 2 else 1800.0)
