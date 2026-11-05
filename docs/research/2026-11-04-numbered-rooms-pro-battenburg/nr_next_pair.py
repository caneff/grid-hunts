"""SCRATCH: next hand deductions on the 19 marks with a two-way colour pair, negative on.

Runs nr_t36_next's simple rules on each way round of magenta and purple. Reports whether a
branch fails, facts true in both branches, and for each open fact a one-step try in each
branch. Solver check at the end: every reported fact is tested on the repo's full model.

Usage: nr_next_pair.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nr_t36_next as N
from nr import build, is_sudoku, marks
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

M = "r1c2 r1c4 r1c5 r2c1 r2c3 r2c6 r2c8 r3c2 r3c4 r3c5 r3c7 r4c2 r4c7 r4c9 r5c1 r5c8 r6c1 r6c8 r7c2 r7c9 r8c4 r8c6 r8c9 r9c5 r9c7 r9c8".split()
P = "r1c1 r1c3 r1c6 r1c7 r2c2 r2c4 r2c5 r2c7 r3c1 r3c3 r3c6 r3c8 r4c1 r4c8 r5c2 r5c7 r5c9 r6c2 r6c9 r7c1 r7c8 r8c5 r8c7 r8c8 r9c4 r9c6 r9c9".split()
G = "r1c8 r1c9 r2c9 r3c9".split()
DATA = json.loads((Path(__file__).resolve().parent / "board18m.json").read_text())
BOARD = frozenset(N.cell(n) for n in DATA["marks"])
N.BOARD = BOARD


def branch(pink, green):
    cand = {k: set(range(1, 10)) for k in N.BORDER}
    cand[(0, 8)] = {8, 9}
    status = dict.fromkeys(N.CELLS)
    for n in pink:
        status[N.cell(n)] = 1
    for n in green + G:
        status[N.cell(n)] = 0
    log = []
    try:
        N.propagate(cand, status, log)
    except N.Fail as err:
        return None, None, log, str(err)
    return cand, status, log, None


def solve(extra):
    m, x, b, t = build(BOARD, {})
    m.AddBoolOr([b[0, 8, 8], b[0, 8, 9]])
    for n in G:
        m.Add(t[N.cell(n)] == 0)
    extra(m, x, t)
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and marks(grid) == BOARD
    return grid


def main():
    a = branch(M, P)
    b = branch(P, M)
    for label, (cand, status, log, fail) in (("magenta targets", a), ("purple targets", b)):
        print(label, "fails:" if fail else "survives,", fail or f"{len(log)} steps")
        if cand:
            print("  r1c9", sorted(cand[(0, 8)]))
            print("  border", {N.nm(k): "".join(map(str, sorted(v))) for k, v in cand.items() if len(v) <= 3})
            print("  status")
            for r in range(9):
                print("   ", "".join("X" if status[r, c] == 1 else "." if status[r, c] == 0 else "?" for c in range(9)))
    if a[0] and b[0]:
        print("both branches:")
        for k in N.CELLS:
            if a[1][k] is not None and a[1][k] == b[1][k] and N.nm(k) not in M + P + G:
                print("  status", N.nm(k), a[1][k], "solver alternative:", bool(solve(lambda m, x, t, k=k: m.Add(t[k] == 1 - a[1][k]))))
        for k in N.BORDER:
            both = a[0][k] | b[0][k]
            if len(both) < 9:
                print("  ", N.nm(k), "".join(map(str, sorted(both))))
        print("one-step tries that fail in both branches, then in each:")
        for name, (cand, status, _, _) in (("magenta", a), ("purple", b)):
            fails = []
            for k in N.CELLS:
                if status[k] is None:
                    for v in (1, 0):
                        c2, s2 = N.copy(cand, status)
                        s2[k] = v
                        steps = []
                        try:
                            N.propagate(c2, s2, steps)
                        except N.Fail as err:
                            fails.append((len(steps), f"{N.nm(k)} {'target' if v else 'not'}", str(err), steps))
            for k in N.BORDER:
                if len(cand[k]) > 1:
                    for d in sorted(cand[k]):
                        c2, s2 = N.copy(cand, status)
                        c2[k] = {d}
                        steps = []
                        try:
                            N.propagate(c2, s2, steps)
                        except N.Fail as err:
                            fails.append((len(steps), f"{N.nm(k)} = {d}", str(err), steps))
            fails.sort(key=lambda f: f[0])
            print(" ", name, len(fails), "fail; shortest:")
            for n, label, why, steps in fails[:6]:
                print(f"    {label}: {n} steps, {why}")
                print("      ", " | ".join(steps[:10]))


if __name__ == "__main__":
    main()
