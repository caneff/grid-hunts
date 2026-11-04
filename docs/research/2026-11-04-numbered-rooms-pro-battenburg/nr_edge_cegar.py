"""SCRATCH: does any sudoku grid have an edge with one completion?

Goal (c) needs one, because the marks read only the 32 edge cells. Counterexample
search on PySAT. The master proposes a grid. A second solver finds another
completion of its edge and shrinks the difference to a minimal interior pattern:
cells whose digits can be rearranged inside the pattern. No grid holding that
pattern can be fixed by its edge, so the master forbids it, along with every image
under the board symmetries that keep the edge and under digit relabelling.

Master UNSAT is a proof that no such grid exists. A found grid is tested for
marks-alone uniqueness. Stopping at the time or clause limit proves nothing.
Interior 4-cell rectangles are forbidden from the start.

Usage: nr_edge_cegar.py PROGRESS_FILE SECONDS
"""

import itertools
import json
import random
import sys
import time
from pathlib import Path

from pysat.solvers import Cadical153

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import is_sudoku, marks, solve

MAX_CLAUSES = 3_000_000
MAX_RELABEL_DIGITS = 4


def var(r, c, d):
    return r * 81 + c * 9 + d


def sudoku_clauses():
    out = []
    houses = []
    for i in range(9):
        houses.append([(i, k) for k in range(9)])
        houses.append([(k, i) for k in range(9)])
    for br in (0, 3, 6):
        for bc in (0, 3, 6):
            houses.append([(br + r, bc + c) for r in range(3) for c in range(3)])
    for r in range(9):
        for c in range(9):
            out.append([var(r, c, d) for d in range(1, 10)])
            for d, e in itertools.combinations(range(1, 10), 2):
                out.append([-var(r, c, d), -var(r, c, e)])
    for house in houses:
        for d in range(1, 10):
            out.append([var(r, c, d) for r, c in house])
            for a, b in itertools.combinations(house, 2):
                out.append([-var(*a, d), -var(*b, d)])
    return out


def read(model):
    on = set(lit for lit in model if lit > 0)
    return [
        [next(d for d in range(1, 10) if var(r, c, d) in on) for c in range(9)]
        for r in range(9)
    ]


def axis_maps():
    """Line maps that keep the edge: inner swaps, the middle band, the flip."""
    maps = []
    for inner_top in ((1, 2), (2, 1)):
        for middle in itertools.permutations((3, 4, 5)):
            for inner_low in ((6, 7), (7, 6)):
                base = [0, *inner_top, *middle, *inner_low, 8]
                maps.append(base)
                maps.append([8 - v for v in reversed(base)])
    return maps


AXIS = axis_maps()


def images(pattern):
    """Every symmetric image of {cell: digit}, as sorted item tuples."""
    seen = set()
    for rows in AXIS:
        for cols in AXIS:
            moved = {(rows[r], cols[c]): d for (r, c), d in pattern.items()}
            seen.add(tuple(sorted(moved.items())))
            flipped = {(c, r): d for (r, c), d in moved.items()}
            seen.add(tuple(sorted(flipped.items())))
    return seen


def cuts(pattern):
    """Clauses forbidding the pattern's images and its digit relabellings."""
    out = []
    for image in images(pattern):
        out.append([-var(r, c, d) for (r, c), d in image])
    digits = sorted(set(pattern.values()))
    if len(digits) <= MAX_RELABEL_DIGITS:
        for new in itertools.permutations(range(1, 10), len(digits)):
            swap = dict(zip(digits, new))
            out.append([-var(r, c, swap[d]) for (r, c), d in pattern.items()])
    return out


def rectangle_patterns():
    """All interior 4-cell swaps: x y / y x with both digit orders."""
    inner = range(1, 8)
    for (a, b), (c, d) in itertools.product(
        itertools.combinations(inner, 2), itertools.combinations(inner, 2)
    ):
        if a // 3 == b // 3 or c // 3 == d // 3:
            yield (a, b, c, d)


def minimal_pattern(alt_solver, grid, edge, flag):
    """A minimal set of interior cells whose digits can be rearranged."""
    interior = [(r, c) for r in range(1, 8) for c in range(1, 8)]
    alt_solver.add_clause(
        [-flag] + [-var(r, c, grid[r][c]) for r, c in interior]
    )
    base = [*edge, flag]
    if not alt_solver.solve(assumptions=base):
        return None
    other = read(alt_solver.get_model())
    held = []
    for r, c in interior:
        if other[r][c] == grid[r][c]:
            continue
        keep = var(r, c, grid[r][c])
        if alt_solver.solve(assumptions=[*base, *held, keep]):
            held.append(keep)
            other = read(alt_solver.get_model())
    assert is_sudoku(other)
    assert all(other[r][c] == grid[r][c] for r, c in [(0, i) for i in range(9)])
    return {
        (r, c): grid[r][c]
        for r, c in interior
        if other[r][c] != grid[r][c]
    }


def main(progress, seconds):
    began = time.time()
    rng = random.Random(20261106)
    base = sudoku_clauses()
    master = Cadical153(bootstrap_with=base)
    alt = Cadical153(bootstrap_with=base)
    total = 0
    for a, b, c, d in rectangle_patterns():
        for x, y in itertools.permutations(range(1, 10), 2):
            clause = [
                -var(a, c, x),
                -var(a, d, y),
                -var(b, c, y),
                -var(b, d, x),
            ]
            master.add_clause(clause)
            total += 1
    print(f"rectangle clauses {total}, {time.time() - began:.0f}s", flush=True)

    flag = 100000
    rounds = 0
    sizes = []
    verdict = "stopped at the limit, proves nothing"
    with open(progress, "a") as f:
        while time.time() - began < seconds and total < MAX_CLAUSES:
            # A random given digit steers the master away from repeats.
            cell = rng.randrange(9), rng.randrange(9)
            hint = [var(*cell, rng.randrange(1, 10))]
            if not master.solve(assumptions=hint) and not master.solve():
                verdict = "master UNSAT: no grid is fixed by its edge"
                break
            grid = read(master.get_model())
            flag += 1
            edge = [
                var(r, c, grid[r][c])
                for r in range(9)
                for c in range(9)
                if r in (0, 8) or c in (0, 8)
            ]
            pattern = minimal_pattern(alt, grid, edge, flag)
            alt.add_clause([-flag])
            rounds += 1
            if pattern is None:
                alone = solve(marks(grid), exclude=[grid], limit=120.0)
                row = {"grid": grid, "marks_alone_unique": alone is None}
                f.write(json.dumps(row) + "\n")
                f.flush()
                verdict = f"found a grid fixed by its edge: {row}"
                break
            sizes.append(len(pattern))
            for clause in cuts(pattern):
                master.add_clause(clause)
                total += 1
            if rounds % 25 == 0:
                recent = sizes[-25:]
                print(
                    f"{time.time() - began:.0f}s rounds {rounds} clauses {total} "
                    f"pattern size {min(recent)}..{max(recent)}",
                    flush=True,
                )
    print(f"done: {rounds} rounds, {total} clauses, {verdict}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
