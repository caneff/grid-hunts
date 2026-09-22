"""The CP-SAT model agrees with the oracle whenever the grid is fixed.

Two seams. `add_cell_number` on rank variables pinned to chosen values, one
case per combination of one- and two-digit ranks, against `oracle.concat`.
Then the whole 9x9 model with every cell fixed to a random full sudoku grid:
its window ranks, cell numbers and cell ranks must equal the oracle's. The
grids come from a seeded shuffle of a base pattern, not from a solver, so the
run is the same every time. Workers pinned to 1, well under a second a grid.

    uv run finders/qqrr/test_model.py
"""

import itertools
import random
import sys
from pathlib import Path

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import model
import oracle
from grids import random_sudoku

from examples._shared import cpsat


def solve(m):
    s = cpsat.solver(30)
    status = s.Solve(m)
    assert status in cpsat.SOLVED, s.StatusName(status)
    return s


# Concatenation: every mix of one- and two-digit ranks, for one, two and four
# windows, reproduces the oracle's unpadded number.
for k in (1, 2, 4):
    for widths in itertools.product((1, 2), repeat=k):
        ranks = [
            random.Random(str(widths)).randint(*((1, 9) if w == 1 else (10, 64)))
            for w in widths
        ]
        m = cp_model.CpModel()
        rank_vars = [m.NewIntVar(1, 64, f"r{i}") for i in range(k)]
        for var, val in zip(rank_vars, ranks, strict=True):
            m.Add(var == val)
        num = model.add_cell_number(m, rank_vars, 64, "n")
        assert solve(m).Value(num) == oracle.concat(ranks), (ranks, widths)


rng = random.Random(592)
for trial in range(20):
    grid = random_sudoku(rng)
    q = model.build(9, ranked_cells=[(r, c) for r in range(9) for c in range(9)])
    for r in range(9):
        for c in range(9):
            q.m.Add(q.x[r][c] == grid[r][c])
    s = solve(q.m)
    ranks, numbers, cranks = oracle.rank_grid(grid)
    got = [[s.Value(v) for v in row] for row in q.rank]
    assert got == ranks, (trial, got, ranks)
    got = [[s.Value(v) for v in row] for row in q.num]
    assert got == numbers, (trial, got, numbers)
    got = [[s.Value(q.q[(r, c)]) for c in range(9)] for r in range(9)]
    assert got == cranks, (trial, got, cranks)

# The sudoku houses are in the model: a repeated digit in a row, a column or
# a box each leaves no solution.
for a, b in (((0, 0), (0, 8)), ((0, 0), (8, 0)), ((0, 0), (2, 2))):
    q = model.build(9)
    q.m.Add(q.x[a[0]][a[1]] == 5)
    q.m.Add(q.x[b[0]][b[1]] == 5)
    assert cpsat.solver(30).Solve(q.m) == cp_model.INFEASIBLE, (a, b)

# One width literal per window, shared by every cell reading it (map #591 item
# 4 as the ticket states it): 64 literals on a 9x9, not one per cell per window.
q = model.build(9)
assert sum(1 for v in q.m.Proto().variables if v.name.startswith("wide")) == 64
assert not any(
    v.name.startswith("num") and "_w" in v.name for v in q.m.Proto().variables
)

# The guards on the encoding: bounds are the extreme concatenations, and a
# rank width past two digits is refused rather than mis-encoded.
assert model.number_bounds(1, 64) == (1, 64)
assert model.number_bounds(2, 64) == (11, 6464)
assert model.number_bounds(4, 64) == (1111, 64646464)
try:
    model.number_bounds(2, 100)
    raise SystemExit("a three-digit top must be refused")
except AssertionError:
    pass

# The leading-digit band read backwards: rank 10 pins the top-left digit to 2,
# 51..56 to 8, 58 and up to 9, and the ambiguous rank 8 admits 1 or 2.
assert model.leading_digits(9, 10, 10) == [2]
assert model.leading_digits(9, 51, 56) == [8]
assert model.leading_digits(9, 58, 64) == [9]
assert model.leading_digits(9, 8, 8) == [1, 2]

print("ok test_model")
