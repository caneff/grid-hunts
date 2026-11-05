"""SCRATCH: which mark shapes force digits, no givens.

Shapes: a run of 8 or 7 overlapping marks along a row pair; a "gap row" of disjoint
marks across some column pairs; a "gap cross" of 16 disjoint marks leaving one row and
one column. D4 symmetry cuts the gap crosses to six. For each shape, negative rule off
and on: feasibility on the repo's full model, with a witness re-read by the reader, then
each border cell's options on the border-only model, which is a superset of the real
options, so a digit it forces is really forced. Borders are counted to a cap.
One worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks
from nr_full_targets_edges import BORDER, model
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

CAP = 5000


def starts(gap):
    """0-based first rows of the 4 disjoint pairs that leave 1-based line gap free."""
    above = list(range(0, gap - 1, 2))
    below = list(range(gap, 8, 2))
    return above + below


def shapes():
    yield "run of 8, r2-3", {(1, c) for c in range(8)}
    yield "run of 7, r2-3 c1-8", {(1, c) for c in range(7)}
    for gap in (1, 3, 5):
        for pairs in (1, 2, 3, 4):
            yield f"gap row r{gap}, {pairs} column pairs", {(r, c * 2) for r in starts(gap) for c in range(pairs)}
    for gap_r, gap_c in ((1, 1), (1, 3), (1, 5), (3, 3), (3, 5), (5, 5)):
        yield f"gap cross r{gap_r} c{gap_c}", {(r, c) for r in starts(gap_r) for c in starts(gap_c)}


def full(board, negative):
    m, x, _, t = build(board if negative else None, {})
    if not negative:
        for r, c in board:
            a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
            m.Add(a == e)
            m.Add(f == d)
            m.Add(a + f == 1)
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        return "TIMEOUT"
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid)
    found = marks(grid)
    assert found == board if negative else board <= found
    return grid


def options(board, negative):
    result = {}
    for cell in BORDER:
        allowed = []
        for d in range(1, 10):
            m, b = model(board, negative)
            m.Add(b[cell, d] == 1)
            s = solver(30.0)
            status = s.Solve(m)
            if status == UNKNOWN:
                raise TimeoutError(str(cell))
            if status in SOLVED:
                allowed.append(d)
        result[cell] = allowed
    return result


class Counter:
    def __init__(self):
        from ortools.sat.python import cp_model

        class C(cp_model.CpSolverSolutionCallback):
            def __init__(self):
                super().__init__()
                self.n = 0

            def on_solution_callback(self):
                self.n += 1
                if self.n >= CAP:
                    self.StopSearch()

        self.cb = C()


def count(board, negative):
    m, _ = model(board, negative)
    s = solver(60.0)
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1
    c = Counter().cb
    s.Solve(m, c)
    return c.n


def main():
    for label, cells in shapes():
        board = frozenset(cells)
        assert all(0 <= r < 8 and 0 <= c < 8 for r, c in board)
        for negative in (False, True):
            tag = "neg on " if negative else "neg off"
            grid = full(board, negative)
            if grid == "TIMEOUT" or grid is None:
                print(f"{label} | {len(board)} marks | {tag} | {'TIMEOUT' if grid else 'INFEASIBLE'}", flush=True)
                continue
            allowed = options(board, negative)
            forced = {f"r{r + 1}c{c + 1}": v[0] for (r, c), v in allowed.items() if len(v) == 1}
            n = count(board, negative)
            word = f"{n}+" if n >= CAP else str(n)
            print(f"{label} | {len(board)} marks | {tag} | feasible | borders {word} | forced {forced}", flush=True)
            print("   witness", " ".join("".join(map(str, row)) for row in grid), flush=True)


if __name__ == "__main__":
    main()
