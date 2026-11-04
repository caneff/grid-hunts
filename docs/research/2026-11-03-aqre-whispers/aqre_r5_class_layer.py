"""SCRATCH: does a digit-free class layer catch the logged r5 layouts' second failure?

Each cell is low (1-4), five or high (6-9); each house holds 4 low, 1 five, 4 high; a
shaded cell takes the class its colour sets and is never five. Whispers and exact digits
are absent. grid-8-r1's layout must pass.
"""

import json
import sys
from pathlib import Path

from ortools.sat.python import cp_model

CELLS = [(r, c) for r in range(9) for c in range(9)]


def class_status(region, shade):
    m = cp_model.CpModel()
    t = {cell: [m.new_bool_var("") for _ in range(3)] for cell in CELLS}
    even_low = m.new_bool_var("even_low")
    for cell in CELLS:
        m.add_exactly_one(t[cell])
    houses = [[(i, c) for c in range(9)] for i in range(9)]
    houses += [[(r, i) for r in range(9)] for i in range(9)]
    houses += [[cell for cell in CELLS if region[cell[0]][cell[1]] == k] for k in range(9)]
    for house in houses:
        for kind, size in ((0, 4), (1, 1), (2, 4)):
            m.add(sum(t[cell][kind] for cell in house) == size)
    for r, c in CELLS:
        if shade[r][c]:
            low = even_low if (r + c) % 2 == 0 else even_low.Not()
            m.add(t[r, c][1] == 0)
            m.add(t[r, c][0] == 1).only_enforce_if(low)
            m.add(t[r, c][2] == 1).only_enforce_if(low.Not())
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = 10.0
    return s.status_name(s.solve(m))


def main(known_path, path, limit):
    known = json.loads(Path(known_path).read_text())
    region = [[0] * 9 for _ in range(9)]
    for k, cells in enumerate(known["regions"]):
        for r, c in cells:
            region[r][c] = k
    print("control, grid-8-r1:", class_status(region, known["shaded"]))
    for i, line in enumerate(Path(path).read_text().splitlines()[:limit]):
        layout = json.loads(line)
        print(f"layout {i + 1}:", class_status(layout["region"], layout["shaded"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]))
