"""SCRATCH: what Chris's current board forces, with his colours.

Third board with mark r6c8 and the colours r6c8, r6c9, r7c8, r7c9 deleted, as he
ruled. Unmarked windows free. Colours and digits r1c1=9, r9c1=6, r9c6=4 held; his
pencil marks left out. Prints each cell's digits, the target status of each cell he
left white, and each outside cell's digits, then counts grids (capped). Answers are
CP-SAT solves on one worker; a timeout raises. A grid is re-read by the reader.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, build, clue_name, is_sudoku, line_cells, marks, outside, show, targets
from nr_board4 import DIGITS, GREEN, MARKS, PINK, RING, cell
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

BOARD = MARKS - {(5, 7)}
GONE = {"r6c8", "r6c9", "r7c8", "r7c9"}
COLOURS = [(n, 1) for n in PINK if n not in GONE] + [(n, 0) for n in GREEN if n not in GONE]
CAP = 200


def base(extra=None, ring=None):
    m, x, b, t = build(None, RING | (ring or {}))
    for r, c in BOARD:
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        m.Add(a == e)
        m.Add(f == d)
        m.Add(a + f == 1)
    for name, want in COLOURS:
        m.Add(t[cell(name)] == want)
    for (r, c), v in DIGITS.items():
        m.Add(x[r, c] == v)
    if extra:
        extra(m, x, b, t)
    return m, x, b


def feasible(extra=None, ring=None):
    m, _, _ = base(extra, ring)
    status = solver(60.0).Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    return status in SOLVED


def main():
    print("feasible:", feasible())
    print("digits per cell, . for all nine:")
    for r in range(9):
        row = []
        for c in range(9):
            options = [
                d
                for d in range(1, 10)
                if feasible(lambda m, x, b, t, r=r, c=c, d=d: m.Add(x[r, c] == d))
            ]
            row.append("".join(map(str, options)) if len(options) < 9 else ".")
        print(f"r{r + 1}", " ".join(f"{v:>9}" for v in row), flush=True)

    coloured = {cell(n) for n, _ in COLOURS}
    pink, green, stays = [], [], []
    for r in range(9):
        for c in range(9):
            if (r, c) in coloured:
                continue
            can = feasible(lambda m, x, b, t, r=r, c=c: m.Add(t[r, c] == 1))
            cannot = feasible(lambda m, x, b, t, r=r, c=c: m.Add(t[r, c] == 0))
            name = f"r{r + 1}c{c + 1}"
            if can and not cannot:
                pink.append(name)
            elif cannot and not can:
                green.append(name)
            else:
                stays.append(name)
    print("uncoloured cells forced to be targets:", pink)
    print("uncoloured cells forced not to be targets:", green)
    print("uncoloured cells still open:", stays)

    print("outside digits:")
    for clue in CLUES:
        if clue in RING:
            continue
        options = [d for d in range(1, 10) if feasible(ring={clue: d})]
        if len(options) < 9:
            print(f"  {clue_name(clue)}: {options}", flush=True)

    found = []
    while len(found) < CAP:
        m, x, b = base()
        for grid in found:
            m.AddBoolOr([b[r, c, grid[r][c]].Not() for r in range(9) for c in range(9)])
        s = solver(60.0)
        status = s.Solve(m)
        if status == UNKNOWN:
            raise TimeoutError("count")
        if status not in SOLVED:
            break
        grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
        assert is_sudoku(grid) and BOARD <= marks(grid)
        ring = outside(grid)
        assert all(ring[k] == v for k, v in RING.items())
        t = targets(grid)
        assert all((cell(n) in t) == bool(w) for n, w in COLOURS)
        found.append(grid)
    print(f"grids: {len(found)}{' (capped)' if len(found) == CAP else ''}")
    print(show(found[0]))
    _ = line_cells


if __name__ == "__main__":
    main()
