"""SCRATCH: check one of Chris's boards under his standing ruling.

No negative rule. Holds every mark, colour, digit and pencil mark. Reads a JSON file:
{"marks": ["r2c1", ...], "pink": [...], "green": [...], "digits": {"r1c1": 9},
 "pencils": {"r2c1": "2367"}, "outside": {"T7": 5},
 "corners": [{"digit": 9, "cells": ["r4c1", "r7c1"]}]}, a corner set meaning the digit is in
 one of those cells. Prints feasibility, a minimal
conflict if it fails, otherwise each cell's target status and digits, and a count of
grids to CAP. Every grid is re-read by the reader. One worker; a timeout raises.

Usage: nr_check.py BOARD_JSON
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks, outside, show, targets
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

CAP = 200


def cell(name):
    return int(name[1]) - 1, int(name[3]) - 1


def nm(k):
    if isinstance(k[0], tuple):
        return "/".join(nm(c) for c in k)
    return f"r{k[0] + 1}c{k[1] + 1}"


class Board:
    def __init__(self, data):
        self.marks = frozenset(cell(n) for n in data.get("marks", []))
        self.ring = {(k[0], int(k[1:]) - 1): v for k, v in data.get("outside", {}).items()}
        self.items = (
            [("c", cell(n), 1) for n in data.get("pink", [])]
            + [("c", cell(n), 0) for n in data.get("green", [])]
            + [("d", cell(n), v) for n, v in data.get("digits", {}).items()]
            + [("o", cell(n), tuple(int(d) for d in v)) for n, v in data.get("pencils", {}).items()]
            + [("g", tuple(cell(n) for n in g["cells"]), g["digit"]) for g in data.get("corners", [])]
        )

    def model(self, items):
        m, x, b, t = build(None, self.ring)
        for r, c in self.marks:
            a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
            m.Add(a == e)
            m.Add(f == d)
            m.Add(a + f == 1)
        for kind, k, v in items:
            if kind == "c":
                m.Add(t[k] == v)
            elif kind == "d":
                m.Add(x[k] == v)
            elif kind == "g":
                m.AddBoolOr([b[r, c, v] for r, c in k])
            else:
                m.AddBoolOr([b[k[0], k[1], d] for d in v])
        return m, x, b, t

    def solve(self, items, extra=None):
        m, x, b, t = self.model(items)
        if extra:
            extra(m, x, b, t)
        s = solver(120.0)
        status = s.Solve(m)
        if status == UNKNOWN:
            raise TimeoutError("no verdict")
        if status not in SOLVED:
            return None
        grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
        self.reread(grid, items)
        return grid

    def reread(self, grid, items):
        assert is_sudoku(grid) and self.marks <= marks(grid)
        hit = targets(grid)
        ring = outside(grid)
        assert all(ring[k] == v for k, v in self.ring.items())
        for kind, k, v in items:
            if kind == "c":
                assert (k in hit) == bool(v)
            elif kind == "d":
                assert grid[k[0]][k[1]] == v
            elif kind == "g":
                assert any(grid[r][c] == v for r, c in k)
            else:
                assert grid[k[0]][k[1]] in v


def bad_marks(board, items):
    """Marks alone fail: the smallest clashing set, then each single removal."""
    all_marks = board.marks
    core = set(all_marks)
    for k in sorted(all_marks):
        board.marks = frozenset(core - {k})
        if not board.solve([]):
            core.discard(k)
    print("minimal clashing marks:", [nm(k) for k in sorted(core)], flush=True)
    for k in sorted(core):
        board.marks = all_marks - {k}
        alone = bool(board.solve([]))
        drawn = bool(alone and board.solve(items))
        print(f"  remove {nm(k)}: marks {alone}, with everything drawn {drawn}", flush=True)
        if alone and not drawn:
            rest = list(items)
            for item in items:
                trial = [i for i in rest if i != item]
                if not board.solve(trial):
                    rest = trial
            print("    conflict:", [(kind, nm(c), v) for kind, c, v in rest], flush=True)


def main(path):
    board = Board(json.loads(Path(path).read_text()))
    items = board.items
    alone = bool(board.solve([]))
    print("marks alone feasible:", alone, flush=True)
    if not alone:
        bad_marks(board, items)
        return
    grid = board.solve(items)
    print("as drawn feasible:", bool(grid), flush=True)
    if not grid:
        core = list(items)
        for item in items:
            rest = [i for i in core if i != item]
            if not board.solve(rest):
                core = rest
        print("minimal conflict:", [(kind, nm(k), v) for kind, k, v in core])
        return
    print(show(grid), flush=True)
    found = [grid]
    while len(found) < CAP:
        def block(m, x, b, t):
            for g in found:
                m.AddBoolOr([b[r, c, g[r][c]].Not() for r in range(9) for c in range(9)])
        g = board.solve(items, block)
        if not g:
            break
        found.append(g)
    print("grids", len(found), "(capped)" if len(found) == CAP else "", flush=True)
    pool = list(found)

    def seen(test, extra):
        """True if a known grid passes test, otherwise ask the solver and keep its grid."""
        if any(test(g) for g in pool):
            return True
        g = board.solve(items, extra)
        if g:
            pool.append(g)
        return bool(g)

    print("status: X target, . not, ? open")
    for r in range(9):
        row = ""
        for c in range(9):
            yes = seen(lambda g, k=(r, c): k in targets(g), lambda m, x, b, t, r=r, c=c: m.Add(t[r, c] == 1))
            no = seen(lambda g, k=(r, c): k not in targets(g), lambda m, x, b, t, r=r, c=c: m.Add(t[r, c] == 0))
            row += "X" if yes and not no else "." if no and not yes else "?"
        print(row, flush=True)
    print("digits with 4 or fewer options")
    for r in range(9):
        row = []
        for c in range(9):
            allowed = [
                d
                for d in range(1, 10)
                if seen(lambda g, r=r, c=c, d=d: g[r][c] == d, lambda m, x, b, t, r=r, c=c, d=d: m.Add(x[r, c] == d))
            ]
            row.append("".join(map(str, allowed)) if len(allowed) <= 4 else ".")
        print(f"r{r + 1}", " ".join(f"{v:>5}" for v in row), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
