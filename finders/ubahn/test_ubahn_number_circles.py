"""The condition "at least K valid circles on number cells" (#794), against
the brute force's 4x4 grids.

A valid circle is a cell whose value is the size of its region; the condition
counts the ones on number cells and nothing on a grid cell. The expected
counts are read off the decision log's 18 grids by `hybrid.py`, the
solver-free rule reader: 6 grids hold 2 such cells and the other 12 hold
none, 4 of those with 4 valid circles on grid cells.

    uv run finders/ubahn/test_ubahn_number_circles.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import random

import brute
import hybrid
import hybrid_finder
import hybrid_model
import hybrid_sat
import network
from ortools.sat.python import cp_model
from pysat.solvers import Cadical195

ROWS = COLS = 4
# The most valid circles on number cells any of the 18 grids holds.
MOST = 2
TIME_LIMIT = 20.0

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def split(net):
    """(valid circles on number cells, valid circles on grid cells), counted
    here from `valid_circles` alone."""
    cells = hybrid.valid_circles(hybrid.values(net, ROWS, COLS))
    on_numbers = sum(1 for r, c in cells if r < 0 or c < 0)
    return on_numbers, len(cells) - on_numbers


def meeting(k):
    """The brute force's grids with at least k valid circles on number cells."""
    return {net for net in GRIDS if split(net)[0] >= k}


def candidate(net, k):
    return hybrid_finder.Candidate(hybrid.Conditions(ROWS, COLS, number_circles=k), net)


GRIDS = brute.hybrid_grids(ROWS, COLS)
READER = hybrid_finder.HybridFinder(hybrid.Conditions(ROWS, COLS))

check(
    "the 18 grids: 6 with 2 valid circles on number cells, 12 with none",
    sorted(split(net)[0] for net in GRIDS) == [0] * 12 + [2] * 6,
)
check(
    "the reader counts a grid's valid circles on number cells",
    all(
        len(hybrid.number_cell_circles(hybrid.values(net, ROWS, COLS))) == split(net)[0]
        for net in GRIDS
    ),
)
check(
    f"verify takes every grid at the K it reaches and rejects it one above, "
    f"K up to {MOST + 1}",
    all(
        READER.verify(candidate(net, k)).ok == (net in meeting(k))
        for net in GRIDS
        for k in range(MOST + 2)
    ),
)
# Four grids have 4 valid circles, all on grid cells: they count for nothing.
grid_only = [net for net in GRIDS if split(net) == (0, 4)]
verdict = READER.verify(candidate(grid_only[0], 1))
check(
    f"a grid with 4 valid circles, none on a number cell, is rejected at K=1 "
    f"({verdict.reason!r})",
    len(grid_only) == 4
    and not verdict.ok
    and verdict.reason == "0 valid circles on number cells, fewer than 1",
)

# Each PySAT engine lists exactly the brute force's grids at every K, and one
# above the most there is lists none, the time limit not reached.
for connectivity in (hybrid_sat.LAZY, hybrid_sat.PROPAGATOR):
    for k in range(MOST + 2):
        found = hybrid_sat.listing(
            hybrid.Conditions(ROWS, COLS, number_circles=k),
            connectivity,
            cap=len(GRIDS) + 1,
            time_limit=TIME_LIMIT,
        )
        check(
            f"pysat-{connectivity}, at least {k}: the brute force's "
            f"{len(meeting(k))} grids, edge for edge (got {len(found.grids)})",
            not found.timed_out and set(found.grids) == meeting(k),
        )
    word, _ = hybrid_sat.Engine(connectivity).classify(
        hybrid.Conditions(ROWS, COLS, number_circles=MOST + 1),
        time_limit=TIME_LIMIT,
        workers=1,
    )
    check(
        f"pysat-{connectivity}, at least {MOST + 1}: infeasible ({word})",
        word == "infeasible",
    )


def takes(net, side, k):
    """Whether the clauses for "at least k" on this board allow this grid."""
    clauses, edge, _ = hybrid_sat.rules(hybrid.Conditions(side, side, number_circles=k))
    with Cadical195(bootstrap_with=clauses) as solver:
        return solver.solve(
            assumptions=[var if e in net else -var for e, var in edge.items()]
        )


def cpsat_takes(net, side, k):
    """The same question of the CP-SAT model."""
    built = hybrid_model.build(hybrid.Conditions(side, side, number_circles=k))
    for e, var in built.edge.items():
        built.m.add(var == (e in net))
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    status = solver.Solve(built.m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE):
        raise RuntimeError(solver.StatusName(status))
    return status != cp_model.INFEASIBLE


# Past any enumeration: a grid is pinned in the clauses edge by edge, and
# both sets of rules must take it at the reader's own count and refuse it one
# above. Two grids an engine found with no condition hold no such cell, so
# for them only the refusal at 1 says anything. The other three are grids of
# the climbs of record (docs/research/2026-10-11-u-bahn-number-circles), with
# what 4x4 never has: a circle in an odd region, and the most a board holds.
# 4x4 only ever circles a 2 or a 4.
MOST_OF_6X6 = [  # 14: six 2s, five 3s, three 4s
    "┌┬┬─┬┐",
    "├┼┤┌┼┤",
    "│└┤├┼┘",
    "└─┼┴┤ ",
    "┌┬┘┌┼┐",
    "└┘ └┴┘",
]
A_FIVE = [  # 14: thirteen 2s and a 5
    "┌┬┬─┬─┐",
    "├┼┼┐└─┘",
    "├┘├┼─┬┐",
    "├┐│├┐││",
    "├┼┤└┤││",
    "├┘├┐│└┤",
    "└─┴┴┴─┘",
]
MOST_OF_7X7 = [  # 18, all 2s
    "┌┬──┬─┐",
    "├┼┬┐│┌┤",
    "│├┼┘├┼┤",
    "│└┘ ├┘│",
    "├─┬┬┼┐│",
    "│┌┼┘└┼┤",
    "└┴┴──┴┘",
]
pinned = [
    (len(drawn), network.from_drawing(drawn))
    for drawn in (MOST_OF_6X6, A_FIVE, MOST_OF_7X7)
]
for side, seed in ((6, 0), (7, 1)):
    (net,) = hybrid_sat.listing(
        hybrid.Conditions(side, side),
        hybrid_sat.LAZY,
        cap=1,
        time_limit=TIME_LIMIT,
        rng=random.Random(seed),
    ).grids
    pinned.append((side, net))
wrong, held_values = [], []
for side, net in pinned:
    board = hybrid.values(net, side, side)
    values = sorted(board[cell] for cell in hybrid.number_cell_circles(board))
    held_values.append(values)
    for name, asked in (("pysat", takes), ("cpsat", cpsat_takes)):
        if not asked(net, side, len(values)) or asked(net, side, len(values) + 1):
            wrong.append((name, side, len(values)))
check(
    f"five grids pinned, holding 14, 14, 18, 0 and 0: taken at the reader's "
    f"count and refused one above (wrong: {wrong})",
    not wrong and [len(v) for v in held_values] == [14, 14, 18, 0, 0],
)
check(
    f"the pinned grids hold a 3 and a 5 on number cells, in odd regions "
    f"({held_values[0]}, {held_values[1]})",
    held_values[0].count(3) == 5 and held_values[1].count(5) == 1,
)


def cpsat_grids(k):
    """Every grid the CP-SAT model allows at "at least k": solve, forbid the
    grid on its edge variables, solve again, until there is none. It stops
    once it holds more grids than the board has."""
    built = hybrid_model.build(hybrid.Conditions(ROWS, COLS, number_circles=k))
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    found = set()
    while len(found) <= len(GRIDS):
        status = solver.Solve(built.m)
        if status == cp_model.INFEASIBLE:
            break
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError(solver.StatusName(status))
        net = frozenset(e for e, var in built.edge.items() if solver.Value(var))
        found.add(net)
        built.m.add_bool_or(
            [var.Not() if e in net else var for e, var in built.edge.items()]
        )
    return found


for k in range(MOST + 2):
    got = cpsat_grids(k)
    check(
        f"cpsat, at least {k}: the brute force's {len(meeting(k))} grids, edge "
        f"for edge (got {len(got)})",
        got == meeting(k),
    )
word, _ = hybrid_model.classify(
    hybrid.Conditions(ROWS, COLS, number_circles=MOST + 1),
    time_limit=TIME_LIMIT,
    workers=1,
)
check(f"cpsat, at least {MOST + 1}: infeasible ({word})", word == "infeasible")

sys.exit(0 if ok else 1)
