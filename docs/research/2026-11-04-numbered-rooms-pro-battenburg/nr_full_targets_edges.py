"""SCRATCH: every border (32 edge cells) that gives exactly the 36-target grid's 13 marks.

Marks read only the border, so the model holds the border digits alone: sudoku on the
border cells, targets from the first-cell digits, the 13 windows checkerboards and the
other 51 not. A border may still have no completion; the next step counts those. CP-SAT
enumerates all solutions, one worker, to the time limit. Appends each border to OUT.
The known grid's border must appear, or the run fails.

Usage: nr_full_targets_edges.py OUT LIMIT_SECONDS
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, WINDOWS, line_cells, marks
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver

ROWS = "621483759 359721684 487596321 168942537 593617248 274835916 915378462 846259173 732164895"
GRID = [[int(d) for d in row] for row in ROWS.split()]
BOARD = marks(GRID)
BORDER = [(r, c) for r in range(9) for c in range(9) if r in (0, 8) or c in (0, 8)]


def model(board=BOARD, negative=True):
    m = cp_model.CpModel()
    b = {(cell, d): m.NewBoolVar("b") for cell in BORDER for d in range(1, 10)}
    for cell in BORDER:
        m.AddExactlyOne(b[cell, d] for d in range(1, 10))
    units = [[(i, c) for c in range(9)] for i in (0, 8)] + [[(r, i) for r in range(9)] for i in (0, 8)]
    for br in range(3):
        for bc in range(3):
            units.append([(br * 3 + r, bc * 3 + c) for r in range(3) for c in range(3)])
    for r in range(1, 8):
        units.append([(r, c) for c in (0, 8)])
    for c in range(1, 8):
        units.append([(r, c) for r in (0, 8)])
    for unit in units:
        cells = [cell for cell in unit if cell in set(BORDER)]
        for d in range(1, 10):
            m.AddAtMostOne(b[cell, d] for cell in cells)
    hits = {(r, c): [] for r in range(9) for c in range(9)}
    for clue in CLUES:
        cells = line_cells(clue)
        for i, cell in enumerate(cells):
            hits[cell].append(b[cells[0], i + 1])
    t = {}
    for cell, literals in hits.items():
        t[cell] = m.NewBoolVar("t")
        m.AddMaxEquality(t[cell], literals)
    for k in WINDOWS:
        r, c = k
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        if k in board:
            m.Add(a == e)
            m.Add(f == d)
            m.Add(a + f == 1)
        elif negative:
            m.AddBoolOr([a.Not(), e.Not(), f, d])
            m.AddBoolOr([f.Not(), d.Not(), a, e])
    return m, b


class Writer(cp_model.CpSolverSolutionCallback):
    def __init__(self, b, out):
        super().__init__()
        self.b, self.out, self.count, self.seen_known = b, out, 0, False
        self.known = "".join(str(GRID[r][c]) for r, c in BORDER)

    def on_solution_callback(self):
        text = ""
        for cell in BORDER:
            text += str(next(d for d in range(1, 10) if self.Value(self.b[cell, d])))
        self.out.write(text + "\n")
        self.out.flush()
        self.count += 1
        self.seen_known = self.seen_known or text == self.known


def main(out_path, limit):
    m, b = model()
    s = solver(limit)
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1
    with open(out_path, "w") as out:
        writer = Writer(b, out)
        status = s.Solve(m, writer)
    print(s.StatusName(status), "borders", writer.count, "known seen", writer.seen_known, "seconds", s.WallTime())


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
