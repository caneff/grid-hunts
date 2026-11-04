"""SCRATCH: why Chris's third board fails only under the all-marked rule.

With unmarked windows free: which windows must be checkerboards, the fewest extra
checkerboards any grid can have, and whether his colours and digits survive. The
grid found is re-read by the reader. One worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import WINDOWS, build, is_sudoku, marks, outside, show
from nr_board4 import DIGITS, GREEN, MARKS, PINK, RING, cell
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

LIMIT = 120.0


def model(colours=(), digits=None):
    m, x, b, t = build(None, RING)
    w = {}
    for r, c in WINDOWS:
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        first = m.NewBoolVar(f"p{r}{c}")
        second = m.NewBoolVar(f"q{r}{c}")
        m.AddBoolAnd(a, f.Not(), d.Not(), e).OnlyEnforceIf(first)
        m.AddBoolOr(a.Not(), f, d, e.Not(), first)
        m.AddBoolAnd(a.Not(), f, d, e.Not()).OnlyEnforceIf(second)
        m.AddBoolOr(a, f.Not(), d.Not(), e, second)
        w[r, c] = m.NewBoolVar(f"w{r}{c}")
        m.AddBoolOr(first, second).OnlyEnforceIf(w[r, c])
        m.AddBoolAnd(first.Not(), second.Not()).OnlyEnforceIf(w[r, c].Not())
    for key in MARKS:
        m.Add(w[key] == 1)
    for name, want in colours:
        m.Add(t[cell(name)] == want)
    for (r, c), v in (digits or {}).items():
        m.Add(x[r, c] == v)
    m.target_vars = t
    return m, x, w


def status_of(m):
    s = solver(LIMIT)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    return s, status


def name(key):
    return f"r{key[0] + 1}c{key[1] + 1}"


def main():
    colours = [(n, 1) for n in PINK] + [(n, 0) for n in GREEN]
    _, status = status_of(model(colours, DIGITS)[0])
    print("marks, digits and all colours, windows free:", status in SOLVED)
    forced = []
    for key in WINDOWS:
        if key in MARKS:
            continue
        m, _, w = model()
        m.Add(w[key] == 0)
        if status_of(m)[1] not in SOLVED:
            forced.append(name(key))
    print("unmarked windows that must be checkerboards:", forced)
    m, x, w = model()
    extra = [w[k] for k in WINDOWS if k not in MARKS]
    m.Minimize(sum(extra))
    s, status = status_of(m)
    print("fewest extra:", s.StatusName(status), s.ObjectiveValue(), s.BestObjectiveBound())
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and MARKS <= marks(grid)
    ring = outside(grid)
    assert all(ring[c] == v for c, v in RING.items())
    print("extra windows in that grid:", [name(k) for k in sorted(marks(grid) - MARKS)])
    print(show(grid))


if __name__ == "__main__":
    main()
