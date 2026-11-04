"""SCRATCH: Chris's third board, read from his picture, tested in layers.

Outside T1=6, L6=9, L9=4, R9=9. Ten marks. Pink cells read as targets, green as not
targets. Digits r1c1=9, r9c1=6, r9c6=4; pencil marks r1c9 in 1,2,3,5, a 1 in r4c1 or
r7c1, a 9 in r9c4 or r9c5. Prints the minimal conflict if infeasible. One worker; a
timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks, outside, solve
from nr_opening import report
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

RING = {("T", 0): 6, ("L", 5): 9, ("L", 8): 4, ("R", 8): 9}
MARKS = frozenset(
    (r - 1, c - 1)
    for r, c in [
        (1, 3), (1, 5), (3, 1), (4, 1), (6, 1),
        (6, 8), (7, 1), (8, 1), (8, 7), (8, 8),
    ]
)
PINK = (
    "r1c4 r1c5 r1c9 r2c3 r2c6 r3c2 r3c3 r4c1 r5c2 r6c2 r6c6 r6c8 r7c1 r7c9 r8c2 r8c6 "
    "r8c7 r8c9 r9c1 r9c6 r9c8"
).split()
GREEN = (
    "r1c1 r1c2 r1c3 r1c6 r2c1 r2c2 r2c4 r2c5 r3c1 r3c6 r4c2 r4c6 r5c1 r5c6 r6c1 r6c9 "
    "r7c2 r7c6 r7c8 r8c1 r8c3 r8c4 r8c5 r8c8 r9c2 r9c3 r9c7 r9c9"
).split()
DIGITS = {(0, 0): 9, (8, 0): 6, (8, 5): 4}
LIMIT = 120.0


def cell(name):
    return int(name[1]) - 1, int(name[3]) - 1


def feasible(items, negative=False, colours=(), digits=None, pencils=False):
    """`items` is givens and marks in force, as ("g", clue, value) and ("m", key, None)."""
    ring = {k: v for kind, k, v in items if kind == "g"}
    held = {k for kind, k, _ in items if kind == "m"}
    m, x, b, t = build(held if negative else None, ring)
    if not negative:
        for r, c in held:
            a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
            m.Add(a == e)
            m.Add(f == d)
            m.Add(a + f == 1)
    for name, want in colours:
        m.Add(t[cell(name)] == want)
    for (r, c), v in (digits or {}).items():
        m.Add(x[r, c] == v)
    if pencils:
        m.AddBoolOr([b[0, 8, d] for d in (1, 2, 3, 5)])
        m.AddBoolOr([b[3, 0, 1], b[6, 0, 1]])
        m.AddBoolOr([b[8, 3, 9], b[8, 4, 9]])
    status = solver(LIMIT).Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    return status in SOLVED


def label(item):
    kind, key, v = item
    return f"{key[0]}{key[1] + 1}={v}" if kind == "g" else f"mark r{key[0] + 1}c{key[1] + 1}"


def main():
    items = [("g", k, v) for k, v in RING.items()]
    items += [("m", k, None) for k in sorted(MARKS)]
    colours = [(n, 1) for n in PINK] + [(n, 0) for n in GREEN]
    print("givens + marks, unmarked windows free:", feasible(items))
    print("all marked:", feasible(items, negative=True))
    print("+ digits:", feasible(items, negative=True, digits=DIGITS))
    print("+ colours:", feasible(items, negative=True, colours=colours, digits=DIGITS))
    print(
        "+ pencils:",
        feasible(items, negative=True, colours=colours, digits=DIGITS, pencils=True),
    )
    if not feasible(items):
        core = list(items)
        for item in items:
            rest = [i for i in core if i != item]
            if not feasible(rest):
                core = rest
        print("minimal conflict:", [label(i) for i in core])
        for item in core:
            rest = [i for i in items if i != item]
            print(" drop", label(item), "->", feasible(rest), flush=True)
        return
    refused = [n for n, w in colours if not feasible(items, True, [(n, w)])]
    print("colours refused singly:", refused)
    print(
        "r9 9 at c:",
        [c + 1 for c in range(9) if feasible(items, True, digits={(8, c): 9})],
        "r1c9:",
        [d for d in range(1, 10) if feasible(items, True, digits={(0, 8): d})],
    )
    grid = solve(MARKS, RING, limit=LIMIT)
    assert is_sudoku(grid) and marks(grid) == MARKS
    ring = outside(grid)
    assert all(ring[c] == v for c, v in RING.items())
    print("reader confirms a grid")
    report("third board", MARKS, RING)


if __name__ == "__main__":
    main()
