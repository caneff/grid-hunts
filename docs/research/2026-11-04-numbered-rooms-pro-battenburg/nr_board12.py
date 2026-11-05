"""SCRATCH: Chris's board from his picture: 11 marks, r1c1 = 9, r1c9 = 1, no outside digits.

Marks r2c1 r2c3 r2c5 r2c7 r3c8 r4c2 r4c6 r6c2 r6c6 r8c2 r8c6. Pink is a target, green is
not. Pencil marks on r2c1, r3c1, r2c9, r3c9. Layers, negative rule off and on. If it
fails, a minimal conflict among digits, colours and pencils. Otherwise a grid re-read by
the reader, and a capped count of grids. One worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks, show, targets
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

BOARD = frozenset(
    (r - 1, c - 1)
    for r, c in [(2, 1), (2, 3), (2, 5), (2, 7), (3, 8), (4, 2), (4, 6), (6, 2), (6, 6), (8, 2), (8, 6)]
)
PINK = "r1c9 r2c2 r2c3 r2c6 r2c7 r3c1 r3c4 r3c5 r3c8 r4c9 r9c1".split()
GREEN = (
    "r1c1 r1c2 r1c3 r1c4 r1c5 r1c6 r1c7 r1c8 r2c1 r2c4 r2c5 r2c8 r2c9 r3c2 r3c3 r3c6 r3c7 r3c9 r4c8"
).split()
DIGITS = {(0, 0): 9, (0, 8): 1}
OPTIONS = {(1, 0): (2, 3, 6, 7), (2, 0): (1, 4, 5, 8), (1, 8): (3, 4, 7, 8), (2, 8): (2, 5, 6, 9)}
CAP = 200


def cell(name):
    return int(name[1]) - 1, int(name[3]) - 1


ITEMS = (
    [("c", cell(n), 1) for n in PINK]
    + [("c", cell(n), 0) for n in GREEN]
    + [("d", k, v) for k, v in DIGITS.items()]
    + [("o", k, v) for k, v in OPTIONS.items()]
)


def model(items, negative):
    m, x, b, t = build(BOARD if negative else None, {})
    if not negative:
        for r, c in BOARD:
            a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
            m.Add(a == e)
            m.Add(f == d)
            m.Add(a + f == 1)
    for kind, key, v in items:
        if kind == "c":
            m.Add(t[key] == v)
        elif kind == "d":
            m.Add(x[key] == v)
        else:
            m.AddBoolOr([b[key[0], key[1], d] for d in v])
    return m, x, b, t


def solve(m):
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    return s, status in SOLVED


def holds(items, negative):
    return solve(model(items, negative)[0])[1]


def main():
    for negative in (False, True):
        tag = "negative on " if negative else "negative off"
        print(tag, "marks:", holds([], negative), flush=True)
        print(tag, "marks + digits:", holds([i for i in ITEMS if i[0] == "d"], negative), flush=True)
        print(tag, "+ colours:", holds([i for i in ITEMS if i[0] != "o"], negative), flush=True)
        ok = holds(ITEMS, negative)
        print(tag, "+ pencils:", ok, flush=True)
        if not ok:
            core = list(ITEMS)
            for item in ITEMS:
                rest = [i for i in core if i != item]
                if not holds(rest, negative):
                    core = rest
            print(tag, "minimal conflict:", core, flush=True)
            continue
        found = []
        while len(found) < CAP:
            m, x, b, _ = model(ITEMS, negative)
            for g in found:
                m.AddBoolOr([b[r, c, g[r][c]].Not() for r in range(9) for c in range(9)])
            s, good = solve(m)
            if not good:
                break
            grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
            assert is_sudoku(grid)
            have = marks(grid)
            assert have == BOARD if negative else BOARD <= have
            hit = targets(grid)
            assert all((k in hit) == bool(v) for kind, k, v in ITEMS if kind == "c")
            found.append(grid)
        print(tag, "grids", len(found), "(capped)" if len(found) == CAP else "")
        print(show(found[0]), flush=True)


if __name__ == "__main__":
    main()
