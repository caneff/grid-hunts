"""SCRATCH: a 36-target grid whose marks alone fix every cell's target status.

Negative rule on, no givens. State is a border with 36 targets and at least MIN_MARKS
marks. A move re-solves it with a random part of the border pinned. Score is the number
of cells whose status differs across the borders that give the same marks, on the
border-only model, enumerated to CAP. A capped score is a floor, so only a complete
enumeration can count as a hit. A hit is proven on the repo's full model: a grid is
found and re-read by the reader, and forbidding its target set must be infeasible.
One worker. Logs to OUT; stops after WANT hits or at the time limit.

Usage: nr_t36_climb.py SECONDS SEED MIN_MARKS OUT
"""

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, WINDOWS, build, is_sudoku, line_cells, marks, targets
from nr_full_targets_edges import BORDER, model
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

CAP = 2000
WANT = 3
STUCK = 150
CELLS = [(r, c) for r in range(9) for c in range(9)]


def read_targets(border):
    """Target cells and marks of a border, without a solver."""
    digit = dict(zip(BORDER, border, strict=True))
    hit = set()
    for clue in CLUES:
        cells = line_cells(clue)
        hit.add(cells[digit[cells[0]] - 1])
    found = set()
    for r, c in WINDOWS:
        a, f, d, e = (r, c) in hit, (r, c + 1) in hit, (r + 1, c) in hit, (r + 1, c + 1) in hit
        if a == e and f == d and a != f:
            found.add((r, c))
    return hit, frozenset(found)


def sample(seed, min_marks, pinned):
    m, b = model(None)
    t = m.target_vars
    m.Add(sum(t.values()) == 36)
    windows = []
    for r, c in WINDOWS:
        one = m.NewBoolVar("one")
        two = m.NewBoolVar("two")
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        m.AddBoolAnd([a, e, f.Not(), d.Not()]).OnlyEnforceIf(one)
        m.AddBoolAnd([f, d, a.Not(), e.Not()]).OnlyEnforceIf(two)
        windows += [one, two]
    m.Add(sum(windows) >= min_marks)
    for cell, d in pinned.items():
        m.Add(b[cell, d] == 1)
    s = solver(20.0)
    s.parameters.random_seed = seed
    s.parameters.randomize_search = True
    s.parameters.num_workers = 1
    status = s.Solve(m)
    if status not in SOLVED:
        return None
    return [next(d for d in range(1, 10) if s.Value(b[cell, d])) for cell in BORDER]


class Keep(cp_model.CpSolverSolutionCallback):
    def __init__(self, t):
        super().__init__()
        self.t, self.yes, self.no, self.n = t, {c: 0 for c in CELLS}, {c: 0 for c in CELLS}, 0

    def on_solution_callback(self):
        self.n += 1
        for cell in CELLS:
            if self.Value(self.t[cell]):
                self.yes[cell] += 1
            else:
                self.no[cell] += 1
        if self.n >= CAP:
            self.StopSearch()


def score(board):
    m, _ = model(board, True)
    s = solver(20.0)
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1
    keep = Keep(m.target_vars)
    status = s.Solve(m, keep)
    complete = s.StatusName(status) == "OPTIMAL" and keep.n < CAP
    return sum(bool(keep.yes[c] and keep.no[c]) for c in CELLS), keep.n, complete


def prove(board, border):
    """A full grid with these marks and this border, and no other target set."""
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
    assert is_sudoku(grid) and marks(grid) == board
    hit = targets(grid)
    assert len(hit) == 36
    m, x, _, t = build(board, {})
    m.AddBoolOr([t[c].Not() if c in hit else t[c] for c in CELLS])
    s = solver(300.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("other target set")
    return grid if status not in SOLVED else "another target set exists"


def main(seconds, seed, min_marks, out):
    rng = random.Random(seed)
    end = time.time() + seconds
    best = None
    hits = evals = 0
    log = open(out, "a")

    def write(kind, **fields):
        log.write(json.dumps({"kind": kind, "evals": evals, **fields}) + "\n")
        log.flush()

    while time.time() < end and hits < WANT:
        border = sample(rng.randrange(1 << 30), min_marks, {})
        if border is None:
            write("no_sample")
            continue
        cur = score(read_targets(border)[1])
        stuck = 0
        while time.time() < end and stuck < STUCK and hits < WANT:
            keep = rng.uniform(0.3, 0.8)
            pinned = {cell: d for cell, d in zip(BORDER, border, strict=True) if rng.random() < keep}
            cand = sample(rng.randrange(1 << 30), min_marks, pinned)
            stuck += 1
            if cand is None or cand == border:
                continue
            evals += 1
            hit, board = read_targets(cand)
            assert len(hit) == 36
            value = score(board)
            if (value[0], value[1]) <= (cur[0], cur[1]):
                if (value[0], value[1]) < (cur[0], cur[1]):
                    stuck = 0
                border, cur = cand, value
                if best is None or (value[0], value[1]) < best:
                    best = (value[0], value[1])
                    write("best", open=value[0], borders=value[1], complete=value[2], marks=len(board),
                          border="".join(map(str, cand)))
                if value[0] == 0 and value[2]:
                    grid = prove(board, cand)
                    if isinstance(grid, str) or grid is None:
                        write("hit_failed", why=str(grid), border="".join(map(str, cand)))
                        continue
                    hits += 1
                    write("HIT", marks=sorted(board), borders=value[1],
                          grid=" ".join("".join(map(str, row)) for row in grid))
    write("done", hits=hits, best=best)


if __name__ == "__main__":
    main(float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
