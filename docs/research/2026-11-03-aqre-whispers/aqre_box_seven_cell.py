"""SCRATCH: is there a grid with the forced 7 on a given off-centre cell, and six circles on other box centres? 8 workers.

usage: aqre_box_seven_cell.py DIR RxC [LIMIT_SECONDS]

The model is `aqre_box_seven.build` with plain rules and no added facts, the 7 fixed on cell RxC, counted from 1. The solver
chooses which two other boxes hold no circle. A found grid goes through the plain Python check and is written to
box-seven-rRcC.json. UNKNOWN at the cap proves nothing.
"""

import json
import sys
import time
from pathlib import Path

from aqre_box_seven import BOXES, CENTRES, build, check
from ortools.sat.python import cp_model


def main(out, cell, limit):
    begun = time.time()
    seven = (cell[0] - 1, cell[1] - 1)
    box = next(k for k, cells in enumerate(BOXES) if seven in cells)
    if seven == CENTRES[box]:
        raise SystemExit("a box centre can never hold the circled 7")
    m, x, g, value = build()
    m.add(value[box, 7] == 1)
    m.add(x[seven] == 7)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 8
    s.parameters.max_time_in_seconds = limit
    status = s.status_name(s.solve(m))
    print(f"r{cell[0]}c{cell[1]}: status {status}, {time.time() - begun:.0f}s, cap {limit:.0f}s", flush=True)
    if status not in ("OPTIMAL", "FEASIBLE"):
        return
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[int(s.value(g[r, c])) for c in range(9)] for r in range(9)]
    circles = {box: seven}
    for k in range(9):
        if k != box and any(s.value(value[k, v]) for v in range(1, 7)):
            circles[k] = CENTRES[k]
    problem = check(digits, shade, circles)
    print(f"plain check: {problem or 'all rules hold'}", flush=True)
    for r in range(9):
        print(" ".join(f"{digits[r][c]}{'#' if shade[r][c] else '.'}{'o' if (r, c) in circles.values() else ' '}" for c in range(9)), flush=True)
    print("circles (box, row, column, digit):", [(k + 1, c[0] + 1, c[1] + 1, digits[c[0]][c[1]]) for k, c in sorted(circles.items())], flush=True)
    if not problem:
        (out / f"box-seven-r{cell[0]}c{cell[1]}.json").write_text(json.dumps({"digits": digits, "shade": shade, "circles": {str(k): c for k, c in circles.items()}}))


if __name__ == "__main__":
    main(Path(sys.argv[1]), tuple(map(int, sys.argv[2].split("x"))), float(sys.argv[3]) if len(sys.argv) > 3 else 1800.0)
