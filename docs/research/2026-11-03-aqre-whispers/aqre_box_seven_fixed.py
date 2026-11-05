"""SCRATCH: does the empty 7-circle board have a solution? One CP-SAT worker.

usage: aqre_box_seven_fixed.py DIR [LIMIT_SECONDS]

The board is https://sudokumaker.app/p/DfGhj6JK7Q: circles on the centres of boxes 1, 3, 4, 6, 7 and 9 and on r4c5. The
model is `aqre_box_seven.build`, with boxes 2 and 8 circle-free and r4c5 the 7, which the centres' limit forces. A found
grid goes through that script's plain Python check and is written to box-seven-fixed.json. An UNKNOWN at the cap proves
nothing.
"""

import json
import sys
import time
from pathlib import Path

from aqre_box_seven import CENTRES, build, check
from ortools.sat.python import cp_model

UNCIRCLED = (1, 7)
SEVEN_BOX = 4
SEVEN_CELL = (3, 4)


def main(out, limit):
    begun = time.time()
    m, x, g, value = build()
    for k in UNCIRCLED:
        for v in range(1, 8):
            m.add(value[k, v] == 0)
    m.add(value[SEVEN_BOX, 7] == 1)
    m.add(x[SEVEN_CELL] == 7)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = limit
    status = s.status_name(s.solve(m))
    print(f"status {status}, {time.time() - begun:.0f}s, cap {limit:.0f}s", flush=True)
    if status not in ("OPTIMAL", "FEASIBLE"):
        return
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[int(s.value(g[r, c])) for c in range(9)] for r in range(9)]
    circles = {k: CENTRES[k] for k in range(9) if k not in UNCIRCLED and k != SEVEN_BOX}
    circles[SEVEN_BOX] = SEVEN_CELL
    problem = check(digits, shade, circles)
    print(f"plain check: {problem or 'all rules hold'}", flush=True)
    for r in range(9):
        print(" ".join(f"{digits[r][c]}{'#' if shade[r][c] else '.'}{'o' if (r, c) in circles.values() else ' '}" for c in range(9)), flush=True)
    if not problem:
        (out / "box-seven-fixed.json").write_text(json.dumps({"digits": digits, "shade": shade, "circles": {str(k): cell for k, cell in circles.items()}}))


if __name__ == "__main__":
    main(Path(sys.argv[1]), float(sys.argv[2]) if len(sys.argv) > 2 else 900.0)
