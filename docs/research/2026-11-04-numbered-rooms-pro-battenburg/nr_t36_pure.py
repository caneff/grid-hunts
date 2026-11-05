"""SCRATCH: 36 targets inferred from the marks alone, with no digits at all.

Chris's meaning of "just by Battenburg" (2026-11-05). The only rules are on a yes/no
target pattern of the 81 cells: marked windows are checkerboards, unmarked windows are
not, and each row and column holds 1 to 4 targets. A board is pure when exactly one
pattern fits and it has 36 targets. With no argument after "check", counts the 27-mark
and 13-mark boards; otherwise climbs for a pure board. Every hit's grid is found on the
repo's full model and re-read by the reader, and its targets must equal the pattern.
One worker. Enumeration is capped at CAP; only a complete count can be a hit.

Usage: nr_t36_pure.py check
       nr_t36_pure.py SECONDS SEED MIN_MARKS OUT
"""

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import WINDOWS, build, is_sudoku, marks, targets
from nr_full_targets_edges import BORDER
from nr_t36_climb import read_targets, sample
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

CAP = 20000
STUCK = 300
CELLS = [(r, c) for r in range(9) for c in range(9)]


def grid_of(rows):
    return [[int(d) for d in row] for row in rows.split()]


class Patterns(cp_model.CpSolverSolutionCallback):
    def __init__(self, t):
        super().__init__()
        self.t, self.n, self.first, self.yes = t, 0, None, {c: 0 for c in CELLS}

    def on_solution_callback(self):
        self.n += 1
        found = frozenset(c for c in CELLS if self.Value(self.t[c]))
        if self.first is None:
            self.first = found
        for c in found:
            self.yes[c] += 1
        if self.n >= CAP:
            self.StopSearch()


def patterns(board):
    """(count, one pattern, open cells), the count capped at CAP."""
    m = cp_model.CpModel()
    t = {c: m.NewBoolVar("t") for c in CELLS}
    for i in range(9):
        for line in ([(i, c) for c in range(9)], [(r, i) for r in range(9)]):
            total = sum(t[c] for c in line)
            m.Add(total >= 1)
            m.Add(total <= 4)
    for r, c in WINDOWS:
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        if (r, c) in board:
            m.Add(a == e)
            m.Add(f == d)
            m.Add(a + f == 1)
        else:
            m.AddBoolOr([a.Not(), e.Not(), f, d])
            m.AddBoolOr([f.Not(), d.Not(), a, e])
    s = solver(30.0)
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1
    keep = Patterns(t)
    status = s.Solve(m, keep)
    complete = s.StatusName(status) == "OPTIMAL" and keep.n < CAP
    opened = sum(0 < keep.yes[c] < keep.n for c in CELLS)
    return keep.n, keep.first, opened, complete


def check():
    for label, rows in {
        "27 marks": "918732456 465819327 273456819 346578291 187294563 529361748 851927634 792643185 634185972",
        "13 marks": "621483759 359721684 487596321 168942537 593617248 274835916 915378462 846259173 732164895",
    }.items():
        grid = grid_of(rows)
        n, _, opened, complete = patterns(marks(grid))
        print(label, "patterns", n if complete else f"{n}+", "open cells", opened, flush=True)


def fill(board, border, pattern):
    m, x, _, _ = build(board, {})
    for (r, c), d in zip(BORDER, border, strict=True):
        m.Add(x[r, c] == d)
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("fill")
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and marks(grid) == board and targets(grid) == set(pattern)
    return grid


def climb(seconds, seed, min_marks, out):
    rng = random.Random(seed)
    end = time.time() + seconds
    evals = hits = 0
    best = None
    log = open(out, "a")

    def write(kind, **fields):
        log.write(json.dumps({"kind": kind, "evals": evals, **fields}) + "\n")
        log.flush()

    while time.time() < end and hits < 3:
        border = sample(rng.randrange(1 << 30), min_marks, {})
        if border is None:
            write("no_sample")
            continue
        cur = patterns(read_targets(border)[1])[:1]
        stuck = 0
        while time.time() < end and stuck < STUCK and hits < 3:
            keep = rng.uniform(0.4, 0.9)
            pinned = {k: d for k, d in zip(BORDER, border, strict=True) if rng.random() < keep}
            cand = sample(rng.randrange(1 << 30), min_marks, pinned)
            stuck += 1
            if cand is None or cand == border:
                continue
            evals += 1
            hit, board = read_targets(cand)
            n, pattern, opened, complete = patterns(board)
            if (n,) > cur:
                continue
            if (n,) < cur:
                stuck = 0
            border, cur = cand, (n,)
            if best is None or n < best:
                best = n
                write("best", patterns=n, complete=complete, open=opened, marks=len(board), border="".join(map(str, cand)))
            if n == 1 and complete and len(pattern) == 36:
                grid = fill(board, cand, pattern)
                if grid is None:
                    write("no_fill", marks=len(board))
                    continue
                hits += 1
                write("HIT", count=len(board), marks=sorted(board), grid=" ".join("".join(map(str, row)) for row in grid))
    write("done", hits=hits, best=best)


if __name__ == "__main__":
    if sys.argv[1] == "check":
        check()
    else:
        climb(float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
