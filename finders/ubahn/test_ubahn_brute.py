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
holds the CP-SAT engine to them (#783). After them, the answers under
Battenberg markings (#21), which the PySAT engines must match.

A slow test, outside the gate: `just test-slow` runs it (tests/all.sh's
`finder_slow`); 38 s on one core.

    uv run finders/ubahn/test_ubahn_brute.py
"""

import contextlib
import io
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import brute
import hybrid
import model
import network
from cli_checks import check, finish
from ortools.sat.python import cp_model

ROWS = COLS = 4
EXACTLY = network.Exactly(2, network.CROSS, "r", 1)
TIME_LIMIT = 10.0

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

# Battenberg markings (spec #20, #21): each marked window is a checkerboard
# window, and with the negative constraint no other window is one. The table
# of the decision log, § Hybrid: Battenberg markings, the 4x4 answers.
ONE_GRID = ("c1:turn", "c2:turn", "r3c1", "r1:turn", "r2:turn", "r1c3")
for names, only, want in (
    ((), False, ("not_unique", 18)),
    ((), True, ("not_unique", 16)),
    *(((name,), False, ("unique", 1)) for name in ONE_GRID),
    (("c1:turn", "c2:turn", "r3c1"), True, ("unique", 1)),
    (("r1:turn", "r2:turn", "r1c3"), True, ("unique", 1)),
    (("c1:turn",), True, ("infeasible", 0)),
    (("c1:turn", "r1:turn"), False, ("infeasible", 0)),
    (("r1c1",), False, ("infeasible", 0)),
):
    marked = hybrid.parse_windows(" ".join(names), 4, 4)
    got = brute.classify(4, 4, (), battenberg=marked, battenberg_only=only)
    check(
        f"4x4 Battenberg markings {' '.join(names) or 'none'}"
        f"{', negative constraint' if only else ''}: {want} (got {got})",
        got == want,
    )
with_windows = [
    hybrid.checkerboard_windows(hybrid.values(net, 4, 4))
    for net in brute.hybrid_grids(4, 4)
]
check(
    "4x4: 16 grids have no checkerboard window and 2 have 3 each",
    sorted(map(len, with_windows)) == [0] * 16 + [3, 3],
)


def printed(*argv):
    """What the brute-force command prints for these arguments, by line."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        brute.main(list(argv))
    return out.getvalue().splitlines()


check(
    "the command prints a count and class for each --battenberg",
    printed("4", "4", "--battenberg", "c1:turn", "--battenberg", "c1:turn r1:turn")[-2:]
    == [
        "Battenberg markings c1:turn: unique (1)",
        "Battenberg markings c1:turn r1:turn: infeasible (0)",
    ],
)
check(
    "with --battenberg-only it prints the negative constraint alone, then "
    "each --battenberg under it",
    printed(
        "4", "4", "--battenberg-only", "--battenberg", "c1:turn",
        "--battenberg", "c1:turn c2:turn r3c1",
    )[-3:]
    == [
        "no other checkerboard window: not_unique (16)",
        "Battenberg markings c1:turn, no other checkerboard window: infeasible (0)",
        "Battenberg markings c1:turn c2:turn r3c1, no other checkerboard window: "
        "unique (1)",
    ],
)  # fmt: skip
r = subprocess.run(
    [sys.executable, str(Path(__file__).with_name("brute.py")), "4", "4",
     "--battenberg", "r4c4"],
    capture_output=True,
    text=True,
)  # fmt: skip
check(
    f"a window off the board is refused, exit 2, naming r4c5 ({r.stderr[-200:]!r})",
    r.returncode == 2
    and "--battenberg: window r4c4 is not wholly on the 4x4 board" in r.stderr
    and "r4c5 is off it" in r.stderr,
)

finish()
