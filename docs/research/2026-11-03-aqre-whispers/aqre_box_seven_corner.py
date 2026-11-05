"""SCRATCH: plain boxes, 7 different circles, with the forced 7 on a box corner. One CP-SAT worker.

usage: aqre_box_seven_corner.py DIR [LIMIT_SECONDS]

A corner shares the box centres' colour, so a corner 7 makes every centre high, and a centre circle on the high colour
is always unshaded. The model is `aqre_box_seven.build`, with the 7 barred from every edge. The solver chooses the boxes.
A found grid goes through that script's plain Python check and is written to box-seven-corner.json.
"""

import json
import sys
import time
from pathlib import Path

from aqre_box_seven import BOXES, CENTRES, build, check
from ortools.sat.python import cp_model


def main(out, limit):
    begun = time.time()
    m, x, g, value = build()
    for k, cells in enumerate(BOXES):
        for r, c in cells:
            if (r + c) % 2:
                m.add(x[r, c] != 7).only_enforce_if(value[k, 7])
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = limit
    status = s.status_name(s.solve(m))
    print(f"status {status}, {time.time() - begun:.0f}s, cap {limit:.0f}s", flush=True)
    if status not in ("OPTIMAL", "FEASIBLE"):
        return
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[int(s.value(g[r, c])) for c in range(9)] for r in range(9)]
    circles = {}
    for k in range(9):
        for v in range(1, 8):
            if s.value(value[k, v]):
                circles[k] = CENTRES[k] if v < 7 else next(cell for cell in BOXES[k] if digits[cell[0]][cell[1]] == 7)
    problem = check(digits, shade, circles)
    print(f"plain check: {problem or 'all rules hold'}", flush=True)
    for r in range(9):
        print(" ".join(f"{digits[r][c]}{'#' if shade[r][c] else '.'}{'o' if (r, c) in circles.values() else ' '}" for c in range(9)), flush=True)
    print("circles (box, row, column, digit):", [(k + 1, cell[0] + 1, cell[1] + 1, digits[cell[0]][cell[1]]) for k, cell in sorted(circles.items())], flush=True)
    if not problem:
        (out / "box-seven-corner.json").write_text(json.dumps({"digits": digits, "shade": shade, "circles": {str(k): cell for k, cell in circles.items()}}))


if __name__ == "__main__":
    main(Path(sys.argv[1]), float(sys.argv[2]) if len(sys.argv) > 2 else 900.0)
