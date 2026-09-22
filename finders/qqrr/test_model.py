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
from grids import TIE_WITNESS, random_sudoku

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


# The tie pair (#601): two numbers equal, both 7 digits wide (three of four
# windows two digits wide), and the one-digit rank in a different slot. Each
# case pins both numbers and all eight width literals and asks for the pair.
def tie_pair_holds(num_a, num_b, wide_a, wide_b):
    m = cp_model.CpModel()
    nums = [m.NewIntVar(0, 10**8, f"n{i}") for i in range(2)]
    wides = [[m.NewBoolVar(f"w{i}{j}") for j in range(4)] for i in range(2)]
    for var, val in zip(nums, (num_a, num_b), strict=True):
        m.Add(var == val)
    for row, vals in zip(wides, (wide_a, wide_b), strict=True):
        for var, val in zip(row, vals, strict=True):
            m.Add(var == val)
    m.Add(model.add_tie_pair(m, *nums, *wides, "t") == 1)
    return cpsat.solver(30).Solve(m) in cpsat.SOLVED


# 1|23|45|67 and 12|3|45|67 both read 1234567: the worked tie from #594.
assert tie_pair_holds(1234567, 1234567, (0, 1, 1, 1), (1, 0, 1, 1))
assert not tie_pair_holds(1234567, 1234568, (0, 1, 1, 1), (1, 0, 1, 1))
# Same slot for the one-digit rank means the same rank list: no tie.
assert not tie_pair_holds(1234567, 1234567, (0, 1, 1, 1), (0, 1, 1, 1))
# Six or eight digits wide is not the hunt.
assert not tie_pair_holds(123456, 123456, (0, 0, 1, 1), (1, 0, 0, 1))
assert not tie_pair_holds(12345678, 12345678, (1, 1, 1, 1), (1, 1, 1, 1))
assert not tie_pair_holds(1234567, 1234567, (0, 1, 1, 1), (1, 1, 1, 1))
assert not tie_pair_holds(1234567, 1234567, (1, 1, 1, 1), (0, 1, 1, 1))
# Six digits on both sides, narrow slots disjoint: only the widths refuse it.
assert not tie_pair_holds(123456, 123456, (0, 0, 1, 1), (1, 1, 0, 0))


# The whole-grid tie: one pair literal per pair of interior cells that see
# each other. Counted by hand: 7 rows and 7 columns of C(7, 2) = 21 pairs, plus
# the box pairs off both lines -- 18 in the middle box, 6 in each of four
# 2x3 edge boxes, 2 in each of four 2x2 corner boxes -- 147 + 147 + 50.
def tie_model(grid):
    q = model.build(9)
    for r in range(9):
        for c in range(9):
            q.m.Add(q.x[r][c] == grid[r][c])
    return q, model.add_seeing_tie(q)


q, pairs = tie_model(TIE_WITNESS)
assert len(pairs) == 344
s = cpsat.solver(30)
assert s.Solve(q.m) in cpsat.SOLVED
assert [k for k, p in pairs.items() if s.Value(p)] == [((3, 5), (4, 3))]
# A grid with no such tie leaves the model with nothing to satisfy.
plain = random_sudoku(random.Random(601))
assert oracle.seven_digit_ties(oracle.window_ranks(plain)) == []
assert cpsat.solver(30).Solve(tie_model(plain)[0].m) == cp_model.INFEASIBLE

print("ok test_model")
