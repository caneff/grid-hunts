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

The hybrid's answers (#782) are pinned at the end: the valid hybrid grids of
the whole 4x4 board with no condition, and the class of seven circle
conditions. They are what each engine must match; `test_ubahn_hybrid_model.py`
holds the CP-SAT engine to them (#783).

    uv run finders/ubahn/test_ubahn_brute.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brute
import hybrid
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
every_3x4 = brute.assignments(3, 4, set())
filled = [
    net
    for net in every_3x4
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

# The hybrid's enumeration (#782) never lists an edge set with a dead end: it
# decides each cell's last two edges together and drops a cell left with one
# arm. Against the full 3x4 list it must lose nothing else.
check(
    "3x4: the dead-end pruning keeps exactly the edge sets with no dead end",
    set(brute.no_dead_end(3, 4))
    == {net for net in every_3x4 if None not in network.kind_grid(net, 3, 4)},
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

# The hybrid's answers on the whole 4x4 board (#782): all 2^24 = 16,777,216
# edge sets, no condition. The enumeration drops dead ends as it goes and the
# solver-free rule reader judges every edge set left. The counts are the ones
# a separate throwaway script gave (numpy over all 2^24 edge sets, its own
# rule code): decision log, § Hybrid.
check(
    "4x4: 16,372 edge sets have no dead end",
    sum(1 for _ in brute.no_dead_end(4, 4)) == 16372,
)
grids = brute.hybrid_grids(4, 4)
check(f"4x4: 18 valid hybrid grids (got {len(grids)})", len(grids) == 18)
in_space = grids & valid
check(
    f"4x4 with exactly 2 crosses in r2: 8 valid hybrid grids (got {len(in_space)})",
    len(in_space) == 8
    and in_space == {net for net in grids if EXACTLY.holds(net, ROWS, COLS)},
)
with_blank = brute.hybrid_grids(4, 4, blank_strip=True)
check(
    f"4x4 with the blank strip: 8 valid hybrid grids (got {len(with_blank)})",
    len(with_blank) == 8 and with_blank < grids,
)
# Circle conditions, each classified in the words of the uniqueness check.
for names, want in (
    ((), ("not_unique", 18)),
    (("r2c2",), ("not_unique", 4)),
    (("c1:turn", "r2c4"), ("unique", 1)),
    (("r1:turn", "r4c2"), ("unique", 1)),
    (("r2c2", "r2c4"), ("infeasible", 0)),
    (("c4:turn", "r4:turn"), ("infeasible", 0)),
    (("r1c1",), ("infeasible", 0)),
):
    circles = frozenset(hybrid.parse_cell(name) for name in names)
    got = brute.classify(4, 4, circles)
    check(f"4x4 circles {' '.join(names) or 'none'}: {want} (got {got})", got == want)

sys.exit(0 if ok else 1)
