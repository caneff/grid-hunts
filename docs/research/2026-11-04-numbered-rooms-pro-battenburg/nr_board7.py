"""SCRATCH: Chris's sixth board, read from his picture, with the negative rule.

Outside T1=6, L6=9, L9=4, R9=9. Thirteen marks. Pink, including half-magenta and the
selected r6c5, is a target; green is not. Tested in layers, negative rule off and on.
If it fails, prints a minimal conflict among digits and colours. If it holds, the
count (capped), each cell's digits and the uncoloured cells' status. Every grid is
re-read by the reader. One worker; a timeout raises.
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
        (1, 3), (1, 5), (3, 1), (4, 1), (6, 1), (6, 4), (6, 8),
        (7, 1), (7, 7), (7, 8), (8, 1), (8, 7), (8, 8),
    ]
)
PINK = (
    "r1c4 r1c5 r1c8 r1c9 r2c3 r2c6 r3c2 r3c3 r4c1 r5c2 r5c9 r6c2 r6c5 r6c6 r6c9 r7c1 "
    "r7c4 r7c8 r8c2 r8c6 r8c7 r8c9 r9c1 r9c5 r9c6 r9c8"
).split()
GREEN = (
    "r1c1 r1c2 r1c3 r1c6 r1c7 r2c1 r2c2 r2c4 r2c5 r2c9 r3c1 r3c5 r3c6 r3c9 r4c2 r4c6 "
    "r4c9 r5c1 r5c6 r6c1 r6c3 r6c4 r6c7 r6c8 r7c2 r7c3 r7c5 r7c6 r7c7 r7c9 r8c1 r8c3 "
    "r8c4 r8c5 r8c8 r9c2 r9c3 r9c4 r9c7 r9c9"
).split()
DIGITS = {
    (0, 0): 9, (0, 3): 1, (0, 8): 5, (5, 8): 1, (6, 0): 1, (6, 8): 6,
    (8, 0): 6, (8, 4): 1, (8, 5): 4, (8, 7): 9, (8, 8): 2,
}
OPTIONS = {
    (0, 1): (3, 5, 6, 8),
    (0, 2): (2, 3, 4, 5),
    (0, 5): (2, 6, 8),
    (0, 7): (2, 3, 4, 5, 7),
    (4, 8): (3, 5, 6, 7, 8),
    (5, 0): (2, 5),
    (7, 0): (2, 7),
    (7, 8): (3, 4, 8),
    (8, 1): (5, 7),
}
CORNERS = [((5, 1), 9), ((5, 4), 9)], [((7, 6), 1), ((7, 7), 1)]
CAP = 200


def cell(name):
    return int(name[1]) - 1, int(name[3]) - 1


COLOURS = [("c", n, 1) for n in PINK] + [("c", n, 0) for n in GREEN]
ENTERED = [("d", k, v) for k, v in DIGITS.items()]


def model(items, negative, pencils=False):
    m, x, b, t = build(BOARD if negative else None, RING)
    if not negative:
        for r, c in BOARD:
            a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
            m.Add(a == e)
            m.Add(f == d)
            m.Add(a + f == 1)
    for kind, key, v in items:
        if kind == "c":
            m.Add(t[cell(key)] == v)
        else:
            m.Add(x[key] == v)
    if pencils:
        for (r, c), options in OPTIONS.items():
            m.AddBoolOr([b[r, c, d] for d in options])
        for group in CORNERS:
            m.AddBoolOr([b[r, c, d] for (r, c), d in group])
    return m, x, b, t


def run(m):
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    return s, status


def holds(items, negative, pencils=False):
    return run(model(items, negative, pencils)[0])[1] in SOLVED


def can(items, negative, fn):
    m, x, _, t = model(items, negative)
    fn(m, x, t)
    return run(m)[1] in SOLVED


def main():
    assert not set(PINK) & set(GREEN)
    everything = ENTERED + COLOURS
    for negative in (False, True):
        word = "negative on" if negative else "negative off"
        print(word, "givens + marks:", holds([], negative))
        print(word, "+ digits:", holds(ENTERED, negative))
        print(word, "+ colours:", holds(everything, negative))
        print(word, "+ pencils:", holds(everything, negative, True), flush=True)
    negative = True
    if not holds(everything, negative):
        for off in (True, False):
            if holds(everything, not off):
                print("holds only with negative off" if off else "")
                break
        core = list(everything)
        for item in everything:
            rest = [i for i in core if i != item]
            if not holds(rest, negative):
                core = rest
        print("minimal conflict, negative on:", core)
        return
    found = []
    while len(found) < CAP:
        m, x, b, _ = model(everything, negative)
        for grid in found:
            m.AddBoolOr([b[r, c, grid[r][c]].Not() for r in range(9) for c in range(9)])
        s, status = run(m)
        if status not in SOLVED:
            break
        grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
        assert is_sudoku(grid) and marks(grid) == BOARD
        ring = outside(grid)
        assert all(ring[k] == v for k, v in RING.items())
        tt = targets(grid)
        assert all((cell(n) in tt) == bool(w) for _, n, w in COLOURS)
        assert all(grid[k[0]][k[1]] == v for k, v in DIGITS.items())
        found.append(grid)
    print(f"grids: {len(found)}{' (capped)' if len(found) == CAP else ''}")
    print(show(found[0]))
    for r in range(9):
        row = []
        for c in range(9):
            options = [
                d
                for d in range(1, 10)
                if can(everything, negative, lambda m, x, t, r=r, c=c, d=d: m.Add(x[r, c] == d))
            ]
            row.append("".join(map(str, options)) if len(options) < 9 else ".")
        print(f"r{r + 1}", " ".join(f"{v:>9}" for v in row), flush=True)
    coloured = {cell(n) for _, n, _ in COLOURS}
    pink, green, open_cells = [], [], []
    for r in range(9):
        for c in range(9):
            if (r, c) in coloured:
                continue
            yes = can(everything, negative, lambda m, x, t, r=r, c=c: m.Add(t[r, c] == 1))
            no = can(everything, negative, lambda m, x, t, r=r, c=c: m.Add(t[r, c] == 0))
            name = f"r{r + 1}c{c + 1}"
            (pink if yes and not no else green if no and not yes else open_cells).append(name)
    print("uncoloured forced pink:", pink)
    print("uncoloured forced green:", green)
    print("uncoloured open:", open_cells)


if __name__ == "__main__":
    main()
