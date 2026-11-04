"""SCRATCH: the smallest conflicting part of Chris's second board.

Deletion filter over the four outside givens and nine marks, with unmarked
windows free: drop an item when the rest stays infeasible. What remains is a
minimal conflict. Then, for each single item dropped from the whole board, says
whether the board becomes feasible, and with what grid. One worker.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, show
from nr_board2 import MARKS, RING
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

LIMIT = 120.0


def solve(items):
    m, x, _, t = build(None, {k: v for kind, k, v in items if kind == "g"})
    for kind, key, _ in items:
        if kind == "m":
            r, c = key
            a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
            m.Add(a == e)
            m.Add(f == d)
            m.Add(a + f == 1)
    s = solver(LIMIT)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(str(items))
    if status not in SOLVED:
        return None
    return [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]


def label(item):
    kind, key, v = item
    if kind == "g":
        return f"{key[0]}{key[1] + 1}={v}"
    return f"mark r{key[0] + 1}c{key[1] + 1}"


def main():
    items = [("g", k, v) for k, v in RING.items()]
    items += [("m", k, None) for k in sorted(MARKS)]
    print("givens only feasible:", solve(items[:4]) is not None)
    print("marks only feasible:", solve(items[4:]) is not None)
    core = list(items)
    for item in items:
        rest = [i for i in core if i != item]
        if solve(rest) is None:
            core = rest
    print("minimal conflict:", [label(i) for i in core])
    for item in items:
        grid = solve([i for i in items if i != item])
        print("drop", label(item), "->", "feasible" if grid else "infeasible", flush=True)


if __name__ == "__main__":
    main()
