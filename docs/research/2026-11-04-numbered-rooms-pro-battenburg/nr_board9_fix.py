"""SCRATCH: the fewest marks to add so the seventh board holds under the negative rule.

Keeps T7=5 and his 12 marks, and minimises the checkerboards among the other windows:
those checkerboards are exactly the marks a negative-rule puzzle must add. Then lists
the smallest sets, capped. Second pass holds his colours too, in each polarity that
held with the negative rule off. Every grid is re-read by the reader. One worker; a
timeout is reported as such, and only an OPTIMAL status is a proven minimum.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import WINDOWS, build, is_sudoku, marks, targets
from nr_board9 import BLUE, BOARD, GREEN, ORANGE, R5_NOT, R5_YES, RING, YELLOW, name, pair
from ortools.sat.python.cp_model import OPTIMAL
from sudoku_kit.cpsat import SOLVED, solver

LIMIT = 150.0
CAP = 40
FREE = [k for k in WINDOWS if k not in BOARD]


def model(fixed):
    m, x, _, t = build(None, RING)
    cb = {}
    for k in WINDOWS:
        r, c = k
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        one = m.NewBoolVar("one")
        two = m.NewBoolVar("two")
        m.AddBoolAnd([a, e, f.Not(), d.Not()]).OnlyEnforceIf(one)
        m.AddBoolOr([a.Not(), e.Not(), f, d]).OnlyEnforceIf(one.Not())
        m.AddBoolAnd([f, d, a.Not(), e.Not()]).OnlyEnforceIf(two)
        m.AddBoolOr([f.Not(), d.Not(), a, e]).OnlyEnforceIf(two.Not())
        cb[k] = m.NewBoolVar("cb")
        m.AddMaxEquality(cb[k], [one, two])
        if k in BOARD:
            m.Add(cb[k] == 1)
    for cell, v in fixed:
        m.Add(t[cell] == v)
    return m, x, t, cb


def read(s, x, fixed, expect):
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and marks(grid) == frozenset(BOARD | expect)
    assert all((cell in targets(grid)) == bool(v) for cell, v in fixed)
    return grid


def minimum(fixed):
    m, x, _, cb = model(fixed)
    m.Minimize(sum(cb[k] for k in FREE))
    s = solver(LIMIT)
    status = s.Solve(m)
    if status not in SOLVED:
        return s.StatusName(status), None, None, None
    extra = frozenset(k for k in FREE if s.Value(cb[k]))
    grid = read(s, x, fixed, extra)
    return s.StatusName(status), len(extra), s.BestObjectiveBound(), (extra, grid, status == OPTIMAL)


def smallest_sets(fixed, size):
    found = []
    while len(found) < CAP:
        m, x, _, cb = model(fixed)
        m.Add(sum(cb[k] for k in FREE) == size)
        for extra in found:
            m.AddBoolOr([cb[k].Not() for k in extra])
        s = solver(LIMIT)
        status = s.Solve(m)
        name_ = s.StatusName(status)
        if status not in SOLVED:
            return found, name_
        extra = frozenset(k for k in FREE if s.Value(cb[k]))
        read(s, x, fixed, extra)
        found.append(extra)
        print("   ", " ".join(name(k) for k in sorted(extra)), flush=True)
    return found, "capped"


def main():
    print("marks + T7=5 only")
    status, size, bound, detail = minimum([])
    print(" ", status, "extra", size, "bound", bound, flush=True)
    if detail:
        print("  grid", " ".join("".join(map(str, row)) for row in detail[1]))
        found, end = smallest_sets([], size)
        print("  smallest sets:", len(found), end, flush=True)
    r5 = [(cell, 0) for cell in R5_NOT] + [(cell, 1) for cell in R5_YES]
    for po, py in ((1, 1), (1, 0), (0, 0)):
        fixed = pair(ORANGE, GREEN, po) + pair(YELLOW, BLUE, py) + r5
        status, size, bound, detail = minimum(fixed)
        word = f"orange={'T' if po else 'N'} yellow={'T' if py else 'N'}"
        print(word, "colours held:", status, "extra", size, "bound", bound, flush=True)
        if detail:
            print("  set", " ".join(name(k) for k in sorted(detail[0])))
            print("  grid", " ".join("".join(map(str, row)) for row in detail[1]), flush=True)


if __name__ == "__main__":
    main()
