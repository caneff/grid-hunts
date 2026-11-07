"""SCRATCH: re-check a pasted jigsaw board on the repo's tooling, one worker.

Regions, each region's most shaded cells under no-4-in-a-line alone, sudoku fills capped
at 1000, then whole-board shading: free counts, and counts equal to the region's label
1-8 with region 9 free, each with and without 5-whispers on shaded cells.
"""

import sys
from itertools import combinations
from pathlib import Path

from aqre_jigsaw_feasible import connected, controls, neighbours, violations
from connected import add_flow_connectivity
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import sudoku_model

BOARD = """111123333
441222223
441156623
441556623
441556623
745556683
799599688
779999888
777779888""".split()
LIMIT = 120.0
CELLS = [(r, c) for r in range(9) for c in range(9)]
REGIONS = [[cell for cell in CELLS if int(BOARD[cell[0]][cell[1]]) == k] for k in range(1, 10)]


def worker(limit=LIMIT):
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = limit
    return s


def shape_max(cells):
    inside = set(cells)
    lines = []
    for r, c in cells:
        for line in ([(r, c + i) for i in range(4)], [(r + i, c) for i in range(4)]):
            if all(x in inside for x in line):
                lines.append(line)
    for size in range(9, 0, -1):
        for chosen in combinations(cells, size):
            picked = set(chosen)
            if not any(all(x in picked for x in line) for line in lines):
                return size
    return 0


class Stop(cp_model.CpSolverSolutionCallback):
    def __init__(self, cap):
        super().__init__()
        self.cap, self.n = cap, 0

    def on_solution_callback(self):
        self.n += 1
        if self.n >= self.cap:
            self.stop_search()


def fills():
    m, x = sudoku_model(9, REGIONS)
    s = worker(60.0)
    s.parameters.enumerate_all_solutions = True
    cb = Stop(1000)
    status = s.solve(m, cb)
    return s.status_name(status), cb.n


def shading(whispers, labelled):
    m, x = sudoku_model(9, REGIONS)
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    add_flow_connectivity(m, g)
    shaded = lambda r, c: g[r * 9 + c]
    for a in range(9):
        for b in range(6):
            for line in (
                [shaded(a, b + i) for i in range(4)],
                [shaded(b + i, a) for i in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    for k, cells in enumerate(REGIONS):
        total = sum(shaded(*cell) for cell in cells)
        m.add(total >= 1)
        if labelled and k < 8:
            m.add(total == k + 1)
    if whispers:
        even_low = m.new_bool_var("even_low")
        for r, c in CELLS:
            low = even_low if (r + c) % 2 == 0 else even_low.Not()
            s = shaded(r, c)
            m.add(x[r, c] <= 4).only_enforce_if(s, low)
            m.add(x[r, c] >= 6).only_enforce_if(s, low.Not())
            for other in neighbours((r, c)):
                if (r, c) < other:
                    t = shaded(*other)
                    m.add(x[other] - x[r, c] >= 5).only_enforce_if(s, t, low)
                    m.add(x[r, c] - x[other] >= 5).only_enforce_if(s, t, low.Not())
    s = worker()
    status = s.solve(m)
    name = s.status_name(status)
    print(f"whispers {whispers}, counts = labels {labelled}: {name} in {s.wall_time:.1f}s", flush=True)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    controls(digits, shade, REGIONS)
    broken = violations(digits, shade, REGIONS)
    if not whispers:
        broken = [b for b in broken if not b.startswith("whisper")]
    print(f"  reader: {broken or 'none'}; counts {[sum(shade[r][c] for r, c in cells) for cells in REGIONS]}", flush=True)
    print("  " + "\n  ".join("".join("#" if v else "." for v in row) for row in shade), flush=True)


def main():
    print("region sizes", [len(x) for x in REGIONS], "connected", [connected(x) for x in REGIONS], flush=True)
    print("shape max by label", [shape_max(x) for x in REGIONS], flush=True)
    print("sudoku fills, capped at 1000:", fills(), flush=True)
    for whispers in (False, True):
        for labelled in (False, True):
            shading(whispers, labelled)


if __name__ == "__main__":
    main()
