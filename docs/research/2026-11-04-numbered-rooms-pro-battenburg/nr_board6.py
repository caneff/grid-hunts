"""SCRATCH: Chris's fourth board, read from his picture, unmarked windows free.

Outside T1=6, L6=9, L9=4, R9=9. Eleven marks. Pink, including the half-magenta
cells, is a target; green is not. Tested in layers. If it fails, prints a minimal
conflict among the colours and the fewest colour changes. If it holds, a grid
re-read by the reader, the count (capped) and what is forced. One worker.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks, outside, show, targets
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

RING = {("T", 0): 6, ("L", 5): 9, ("L", 8): 4, ("R", 8): 9}
BOARD = frozenset(
    (r - 1, c - 1)
    for r, c in [
        (1, 3), (1, 5), (3, 1), (4, 1), (6, 1), (6, 4),
        (6, 8), (7, 1), (8, 1), (8, 7), (8, 8),
    ]
)
PINK = (
    "r1c4 r1c5 r1c8 r1c9 r2c3 r2c6 r3c2 r3c3 r4c1 r5c2 r6c2 r6c5 r6c6 r6c8 r7c1 r7c4 "
    "r7c9 r8c2 r8c6 r8c7 r8c9 r9c1 r9c6 r9c8"
).split()
GREEN = (
    "r1c1 r1c2 r1c3 r1c6 r1c7 r2c1 r2c2 r2c4 r2c5 r3c1 r3c5 r3c6 r4c2 r4c6 r5c1 r5c6 "
    "r6c1 r6c3 r6c4 r6c7 r6c9 r7c2 r7c3 r7c5 r7c6 r7c7 r7c8 r8c1 r8c3 r8c4 r8c5 r8c8 "
    "r9c2 r9c3 r9c7 r9c9"
).split()
DIGITS = {(0, 0): 9, (6, 0): 1, (8, 0): 6, (8, 5): 4, (8, 7): 9, (8, 8): 2}
CAP = 200


def cell(name):
    return int(name[1]) - 1, int(name[3]) - 1


def base(colours=(), digits=DIGITS, pencils=False):
    m, x, b, t = build(None, RING)
    for r, c in BOARD:
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        m.Add(a == e)
        m.Add(f == d)
        m.Add(a + f == 1)
    for name, want in colours:
        m.Add(t[cell(name)] == want)
    for (r, c), v in (digits or {}).items():
        m.Add(x[r, c] == v)
    if pencils:
        for (r, c), options in {
            (0, 1): (3, 5, 6, 8),
            (0, 5): (2, 6, 8),
            (0, 8): (1, 5, 6),
            (7, 8): (1, 3, 4, 8),
            (8, 1): (2, 5, 7),
        }.items():
            m.AddBoolOr([b[r, c, d] for d in options])
        for r, columns in {0: (3, 4, 7, 8), 7: (6, 7, 8), 8: (3, 4)}.items():
            m.AddBoolOr([b[r, c, 1] for c in columns])
    return m, x, b, t


def run(m):
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    return s, status


def holds(*args, **kwargs):
    return run(base(*args, **kwargs)[0])[1] in SOLVED


def main():
    colours = [(n, 1) for n in PINK] + [(n, 0) for n in GREEN]
    assert not set(PINK) & set(GREEN)
    print("givens + marks:", holds(digits=None))
    print("+ digits:", holds())
    print("+ colours:", holds(colours))
    print("+ pencils:", holds(colours, pencils=True))
    if not holds(colours):
        core = list(colours)
        for item in colours:
            rest = [i for i in core if i != item]
            if not holds(rest):
                core = rest
        print("minimal colour conflict:", core)
        m, x, _, t = base()
        changed = {n: (t[cell(n)].Not() if w else t[cell(n)]) for n, w in colours}
        m.Minimize(sum(changed.values()))
        s, status = run(m)
        print("fewest colour changes:", s.StatusName(status), s.ObjectiveValue())
        print("one such set:", sorted(n for n, lit in changed.items() if s.BooleanValue(lit)))
        return
    found = []
    while len(found) < CAP:
        m, x, b, _ = base(colours)
        for grid in found:
            m.AddBoolOr([b[r, c, grid[r][c]].Not() for r in range(9) for c in range(9)])
        s, status = run(m)
        if status not in SOLVED:
            break
        grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
        assert is_sudoku(grid) and BOARD <= marks(grid)
        ring = outside(grid)
        assert all(ring[k] == v for k, v in RING.items())
        tt = targets(grid)
        assert all((cell(n) in tt) == bool(w) for n, w in colours)
        found.append(grid)
    print(f"grids: {len(found)}{' (capped)' if len(found) == CAP else ''}")
    print(show(found[0]))


if __name__ == "__main__":
    main()
