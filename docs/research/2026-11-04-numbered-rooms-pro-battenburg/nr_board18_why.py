"""SCRATCH: why r1c9 = 8 fails on the 19 marks under the negative rule.

Requires the 19 marks and r1c9 = 8, then finds a minimal set of unmarked windows whose
"not a checkerboard" rule makes it infeasible. Prints them, then for each single window
in that set what happens without it, as a grid's checkerboard there. One worker; a
timeout raises.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import WINDOWS, build, is_sudoku, marks
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

DATA = json.loads((Path(__file__).resolve().parent / "board18m.json").read_text())
BOARD = frozenset((int(n[1]) - 1, int(n[3]) - 1) for n in DATA["marks"])
FREE = [k for k in WINDOWS if k not in BOARD]


def nm(k):
    return f"r{k[0] + 1}c{k[1] + 1}"


def solve(banned):
    m, x, _, t = build(None, {})
    m.Add(x[0, 8] == 8)
    for r, c in BOARD:
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        m.Add(a == e)
        m.Add(f == d)
        m.Add(a + f == 1)
    for r, c in banned:
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        m.AddBoolOr([a.Not(), e.Not(), f, d])
        m.AddBoolOr([f.Not(), d.Not(), a, e])
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and BOARD <= marks(grid)
    return grid


def main():
    assert solve([]) is not None
    assert solve(FREE) is None
    core = list(FREE)
    for k in FREE:
        rest = [w for w in core if w != k]
        if solve(rest) is None:
            core = rest
    print("minimal unmarked windows:", [nm(k) for k in core], flush=True)
    for k in core:
        grid = solve([w for w in core if w != k])
        print(" without", nm(k), "extra marks", sorted(nm(w) for w in marks(grid) - BOARD))
        print("  ", " ".join("".join(map(str, row)) for row in grid), flush=True)


if __name__ == "__main__":
    main()
