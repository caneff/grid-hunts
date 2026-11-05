"""Per border of a board: its upper-clump target pattern and every outside clue that reads a
border cell, whose digit the border alone fixes. Negative rule on. One grid per border is
filled and read by the reader.

Usage: nr_border_clues.py BOARD_JSON
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, clue_name, line_cells, outside, targets
from nr_full_targets_edges import BORDER, model
from nr_outside_finish import all_grids
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver


class Keep(cp_model.CpSolverSolutionCallback):
    def __init__(self, b):
        super().__init__()
        self.b, self.rows = b, []

    def on_solution_callback(self):
        self.rows.append("".join(str(next(d for d in range(1, 10) if self.Value(self.b[k, d]))) for k in BORDER))


def main(path):
    board = frozenset((int(n[1]) - 1, int(n[3]) - 1) for n in json.loads(Path(path).read_text())["marks"])
    m, b = model(board, True)
    s = solver(60.0)
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1
    keep = Keep(b)
    assert s.StatusName(s.Solve(m, keep)) == "OPTIMAL"
    border_set = set(BORDER)
    for text in keep.rows:
        grids = all_grids(text, [])
        g = grids[0]
        hit = targets(g)
        ring = outside(g)
        print("border", text, "grids", len(grids))
        for r in range(3):
            print("  ", "".join("X" if (r, c) in hit else "." for c in range(9)))
        fixed = []
        for clue in CLUES:
            cells = line_cells(clue)
            target = cells[g[cells[0][0]][cells[0][1]] - 1]
            if target in border_set:
                fixed.append(f"{clue_name(clue)}={ring[clue]}")
        print("   border-read clues:", " ".join(fixed), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
