"""The U-Bahn model against an exhaustive enumeration, on a 4x4 board with
exactly 2 crosses in r2 (#773).

A cross cannot sit on the border, so the two crosses are r2c2 and r2c3: their
7 edges are on and the other 17 are free, 131,072 edge assignments. `brute`
lists every one and keeps those `network.py`'s solver-free rule check passes;
the CP-SAT model
must return the same networks under both connectivity encodings, and the
finder's uniqueness verdict must match the count of networks that share a
full set of outside numbers.

A second space, 3x4 with no blank in r2, covers what the first cannot: a
condition on blank cells, and edge sets with no dead end that are not
connected.

    uv run finders/ubahn/test_ubahn_brute.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brute
import model
import network
from ortools.sat.python import cp_model

ROWS = COLS = 4
EXACTLY = network.Exactly(2, network.CROSS, "r", 1)
TIME_LIMIT = 10.0

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


space = brute.two_crosses_in_r2()
check("two crosses in r2 leave 17 free edges", space.free_edges == 17)
check("the space is 131,072 edge assignments", space.assignments == 131072)
valid, by_numbers, unique = space.valid, space.by_numbers, space.unique
# The counts a separate throwaway script gave for this space (#773).
check(f"557 valid networks (got {len(valid)})", len(valid) == 557)
check(
    f"554 distinct full sets of outside numbers (got {len(by_numbers)})",
    len(by_numbers) == 554,
)
check(
    f"551 networks unique under their full set (got {len(unique)})",
    len(unique) == 551,
)


def model_networks(connectivity, rows=ROWS, cols=COLS, exactly=EXACTLY):
    """Every network the model allows: solve, forbid the network on its edge
    variables, solve again, until the model is infeasible."""
    built = model.build(rows, cols, connectivity, exactly=exactly)
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    found = set()
    while True:
        status = solver.Solve(built.m)
        if status == cp_model.INFEASIBLE:
            return found
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError(solver.StatusName(status))
        net = frozenset(e for e, var in built.edge.items() if solver.Value(var))
        if net in found:
            raise RuntimeError("the model returned a forbidden network again")
        found.add(net)
        built.m.add_bool_or(
            [var.Not() if e in net else var for e, var in built.edge.items()]
        )


for connectivity in ("flow", "tree"):
    got = model_networks(connectivity)
    check(
        f"{connectivity} model: the brute-force networks exactly "
        f"({len(got - valid)} extra, {len(valid - got)} missing)",
        got == valid,
    )

for connectivity in ("flow", "tree"):
    wrong = []
    for numbers, count in by_numbers.items():
        status, _ = model.uniqueness(
            ROWS, COLS, numbers, connectivity, time_limit=TIME_LIMIT, workers=1
        )
        if status != ("unique" if count == 1 else "not_unique"):
            wrong.append((numbers, count, status))
    check(
        f"{connectivity} model: the uniqueness verdict matches the brute-force "
        f"count on all {len(by_numbers)} sets of outside numbers "
        f"(first mismatch: {wrong[:1]})",
        not wrong,
    )

# The 4x4 space above cannot hold two separate loops: the crosses' own cells
# leave no free 2x2 block. A 3x4 board can, and "no blank in r2" keeps them:
# every edge assignment of the board, 131,072 again, with no edge forced.
NO_BLANK_R2 = network.Exactly(0, network.BLANK, "r", 1)
filled = [
    net
    for net in brute.assignments(3, 4, set())
    if net
    and None not in network.kind_grid(net, 3, 4)
    and network.outside_numbers(net, 3, 4)[0][1][network.BLANK] == 0
]
connected = {net for net in filled if not network.why_not_network(net, 3, 4)}
check(
    f"3x4 with no blank in r2: {len(filled)} edge sets have no dead end, "
    f"{len(filled) - len(connected)} of them not connected",
    0 < len(connected) < len(filled),
)
for connectivity in ("flow", "tree"):
    got = model_networks(connectivity, 3, 4, NO_BLANK_R2)
    check(
        f"{connectivity} model, 3x4 with no blank in r2: the brute-force "
        f"networks exactly ({len(got - connected)} extra, "
        f"{len(connected - got)} missing)",
        got == connected,
    )

# Both spaces above shut the board with no edge out by their own condition.
# A 2x2 board with no condition does not: of its 16 edge assignments only
# the loop of all four is a network.
loop = frozenset(network.all_edges(2, 2))
small = {
    net
    for net in brute.assignments(2, 2, set())
    if not network.why_not_network(net, 2, 2)
}
check("2x2: the brute force finds the one loop and nothing else", small == {loop})
for connectivity in ("flow", "tree"):
    got = model_networks(connectivity, 2, 2, None)
    check(
        f"{connectivity} model, 2x2: the one loop and nothing else (got {len(got)})",
        got == {loop},
    )

sys.exit(0 if ok else 1)
