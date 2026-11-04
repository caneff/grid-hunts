"""SCRATCH: is Chris's second opening board feasible? Read from his picture.

Outside T1=6, L6=9, L9=4, R9=9. Nine marks. Pink cells read as targets and green
as not targets. Blue digits r1c1=9, r9c1=6, r9c6=4; pencil marks r9c9 in 5,6,7 and
a 1 in r4c1 or r7c1. Layers are tested in turn, so a conflict can be traced. One
worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, marks, outside, show, targets
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

LIMIT = 120.0
RING = {("T", 0): 6, ("L", 5): 9, ("L", 8): 4, ("R", 8): 9}
MARKS = {
    (r - 1, c - 1)
    for r, c in [
        (3, 1), (4, 1), (6, 1), (7, 1), (8, 1),
        (1, 8), (6, 8), (8, 8), (8, 7),
    ]
}
PINK = "r1c9 r2c8 r3c2 r4c1 r5c2 r6c2 r6c6 r6c8 r7c1 r7c9 r8c2 r8c6 r8c7 r8c9 r9c1 r9c6 r9c8"
GREEN = (
    "r1c1 r1c2 r1c8 r2c1 r2c2 r2c9 r3c1 r4c2 r5c1 r6c1 r6c9 r7c2 r7c8 r8c1 r8c3 r8c4 "
    "r8c5 r8c8 r9c2 r9c3 r9c7 r9c9"
)
DIGITS = {(0, 0): 9, (8, 0): 6, (8, 5): 4}


def cell(name):
    return int(name[1]) - 1, int(name[3]) - 1


def check(label, use_negative=True, colours=(), digits=None, pencils=False, ring=RING):
    m, x, b, t = build(MARKS if use_negative else None, ring)
    if not use_negative:
        for r, c in MARKS:
            a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
            m.Add(a == e)
            m.Add(f == d)
            m.Add(a + f == 1)
    for name, want in colours:
        m.Add(t[cell(name)] == want)
    for (r, c), v in (digits or {}).items():
        m.Add(x[r, c] == v)
    if pencils:
        m.AddBoolOr([b[8, 8, 5], b[8, 8, 6], b[8, 8, 7]])
        m.AddBoolOr([b[3, 0, 1], b[6, 0, 1]])
    s = solver(LIMIT)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(label)
    ok = status in SOLVED
    print(f"{label}: {'feasible' if ok else 'INFEASIBLE'}", flush=True)
    if not ok:
        return None
    return [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]


def main():
    pink = [(n, 1) for n in PINK.split()]
    green = [(n, 0) for n in GREEN.split()]
    colours = pink + green
    check("givens only", use_negative=False, ring=RING)
    check("givens + marks, unmarked windows free", use_negative=False)
    check("givens + marks, all marked", use_negative=True)
    check("+ blue digits", digits=DIGITS)
    check("+ pink", colours=pink, digits=DIGITS)
    check("+ green", colours=green, digits=DIGITS)
    grid = check("+ pink and green", colours=colours, digits=DIGITS)
    grid2 = check("+ pencil marks", colours=colours, digits=DIGITS, pencils=True)
    print("each colour alone, all marked, with the blue digits; refused ones:")
    for name, want in colours:
        m_ok = check.__wrapped__ if False else None
        result = quiet(name, want)
        if not result:
            print("  refused", name, "pink" if want else "green", flush=True)
    for found in (grid2, grid):
        if found:
            assert marks(found) == frozenset(MARKS)
            ring = outside(found)
            assert all(ring[c] == v for c, v in RING.items())
            t = targets(found)
            print(show(found))
            print("reader agrees; targets", len(t))
            break


def quiet(name, want):
    m, x, _, t = build(MARKS, RING)
    m.Add(t[cell(name)] == want)
    for (r, c), v in DIGITS.items():
        m.Add(x[r, c] == v)
    status = solver(LIMIT).Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(name)
    return status in SOLVED


if __name__ == "__main__":
    main()
