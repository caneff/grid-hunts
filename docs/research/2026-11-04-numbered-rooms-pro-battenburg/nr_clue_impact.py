"""SCRATCH: how much each outside digit narrows a board, negative rule on.

Enumerates every border the marks allow, counts each border's fillings per inner cell and
digit with count_cells.c, and for each outside cell and digit sums the solutions that keep
it. Reports each outside cell's expected remaining solutions over all solutions, and its
fewest remaining with any digit. The total is checked against count_fills-style totals by
construction, and the best digit is confirmed on the repo's full model. One worker.

Usage: nr_clue_impact.py BOARD_JSON COUNT_CELLS_BINARY
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, clue_name, line_cells, outside
from nr_check import Board
from nr_full_targets_edges import BORDER, model
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver


class Keep(cp_model.CpSolverSolutionCallback):
    def __init__(self, b):
        super().__init__()
        self.b, self.rows = b, []

    def on_solution_callback(self):
        self.rows.append("".join(str(next(d for d in range(1, 10) if self.Value(self.b[k, d]))) for k in BORDER))


def main(path, binary):
    data = json.loads(Path(path).read_text())
    board = frozenset((int(n[1]) - 1, int(n[3]) - 1) for n in data["marks"])
    m, b = model(board, True)
    s = solver(120.0)
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1
    keep = Keep(b)
    status = s.Solve(m, keep)
    assert s.StatusName(status) == "OPTIMAL"
    print("borders", len(keep.rows), flush=True)
    done = subprocess.run([binary], input="\n".join(keep.rows) + "\n", capture_output=True, text=True, check=True)
    tally = {clue: dict.fromkeys(range(1, 10), 0) for clue in CLUES}
    total = 0
    inner = [(r, c) for r in range(1, 8) for c in range(1, 8)]
    for line in done.stdout.splitlines():
        parts = line.split()
        text, fills, counts = parts[0], int(parts[1]), [int(v) for v in parts[2:]]
        total += fills
        print("  border", text, fills)
        digit = dict(zip(BORDER, map(int, text), strict=True))
        table = {k: counts[i * 9 : i * 9 + 9] for i, k in enumerate(inner)}
        keep_border = True
        for name, value in data.get("outside", {}).items():
            cells = line_cells((name[0], int(name[1:]) - 1))
            target = cells[digit[cells[0]] - 1]
            assert target in digit, "only outside digits read from the border can be given"
            keep_border = keep_border and digit[target] == value
        if not keep_border:
            total -= fills
            continue
        for clue in CLUES:
            cells = line_cells(clue)
            target = cells[digit[cells[0]] - 1]
            if target in digit:
                tally[clue][digit[target]] += fills
            else:
                for d in range(1, 10):
                    tally[clue][d] += table[target][d - 1]
    print("total solutions", total, flush=True)
    rows = []
    for clue, by in tally.items():
        assert sum(by.values()) == total
        expected = sum(v * v for v in by.values()) / total
        best = min((v, d) for d, v in by.items() if v)
        rows.append((expected, clue, best, {d: v for d, v in by.items() if v}))
    rows.sort(key=lambda row: row[0])
    for expected, clue, (fewest, d), by in rows:
        print(f"{clue_name(clue)} expected {expected:.0f} best {d} leaves {fewest} options {by}")
    for expected, clue, (fewest, d), _ in rows[:3]:
        name = clue_name(clue)
        check = Board({**data, "outside": {name: d}}, True)
        grid = check.solve(check.items)
        assert grid and outside(grid)[clue] == d
        print("confirmed", name, "=", d, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
