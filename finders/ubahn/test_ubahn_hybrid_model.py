"""The hybrid's CP-SAT engine against the exhaustive 4x4 answers (#783).

`test_ubahn_brute.py` pins what the brute force finds on the whole 4x4 board:
18 valid hybrid grids, 8 with the blank strip, 8 with exactly 2 crosses in r2,
and the class of seven circle conditions. The engine must list the same grids
(solve, forbid the grid on its edges, re-solve) and classify each condition
the same way. The class words and counts below are the decision log's table,
§ Hybrid, written out again; the grids are the brute force's, judged by the
solver-free rule reader.

No 4x4 grid has a circle in a banana, so the last block leaves the brute
force for a 5x5 board, where a circled r1c2 is a branch in a bent banana of
three: a grid checked by hand, which the engine must call the only one, and
the engine's own grids without the circle, of which the rule reader must keep
what the engine keeps with it.

Last, the circle rule on 6x6 boards, past any enumeration: a grid the engine
found is pinned in the model, edge by edge, and the engine must then take a
circle exactly where the rule reader says the cell's value is its region's
size.

One CP-SAT worker; about fifteen seconds.

    uv run finders/ubahn/test_ubahn_hybrid_model.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brute
import hybrid
import hybrid_model
import network
from ortools.sat.python import cp_model

TIME_LIMIT = 10.0
TWO_CROSSES = network.Exactly.parse("2:cross:r2")

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def said(call, *args, **kwargs):
    """What a call answers, or the error it raises: a guard that is gone
    then fails its own check instead of ending the run."""
    try:
        return call(*args, **kwargs)
    except Exception as e:
        return e


def cells(*names):
    return frozenset(hybrid.parse_cell(name) for name in names)


def engine_grids(conditions, valid):
    """Every grid the engine's model allows: solve, forbid the grid on its
    edge variables, solve again, until the model is infeasible. It stops at
    the first grid `valid` refuses, with that grid in what it returns: a
    model that has lost a rule allows too many grids to list."""
    built = hybrid_model.build(conditions)
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
            raise RuntimeError("the model returned a forbidden grid again")
        found.add(net)
        if not valid(net):
            return found
        built.m.add_bool_or(
            [var.Not() if e in net else var for e, var in built.edge.items()]
        )


def agrees(name, conditions, want):
    got = engine_grids(conditions, want.__contains__)
    check(
        f"{name}: the brute-force grids exactly, {len(want)} of them "
        f"({len(got - want)} or more extra, {len(want - got)} missing)",
        got == want,
    )


grids = brute.hybrid_grids(4, 4)
agrees("4x4, no condition", hybrid.Conditions(4, 4), grids)
check("4x4, no condition: 18 grids", len(grids) == 18)

# The blank strip is off unless asked for, and changes the answer when on.
with_blank = brute.hybrid_grids(4, 4, blank_strip=True)
agrees(
    "4x4 with the blank strip", hybrid.Conditions(4, 4, blank_strip=True), with_blank
)
check("4x4 with the blank strip: 8 grids", len(with_blank) == 8)

# The pinned circle conditions (decision log, § Hybrid): the engine's grids
# are the brute force's, and its classification is the table's word.
for names, word, count in (
    ((), "not_unique", 18),
    (("r2c2",), "not_unique", 4),
    (("c1:turn", "r2c4"), "unique", 1),
    (("r1:turn", "r4c2"), "unique", 1),
    (("r2c2", "r2c4"), "infeasible", 0),
    (("c4:turn", "r4:turn"), "infeasible", 0),
    (("r1c1",), "infeasible", 0),
):
    label = f"4x4 circles {' '.join(names) or 'none'}"
    conditions = hybrid.Conditions(4, 4, cells(*names))
    want = {g for g in grids if not hybrid.why_not_hybrid(g, 4, 4, cells(*names))}
    check(f"{label}: the brute force counts {count}", len(want) == count)
    agrees(label, conditions, want)
    got = hybrid_model.classify(conditions, time_limit=TIME_LIMIT, workers=1)
    check(f"{label}: classified {word} (got {got.status})", got.status == word)
    check(
        f"{label}: the classification's grid is one of them, or None for none",
        got.network in want if want else got.network is None,
    )
    # A limit reached is a timeout whatever the true answer is.
    late = hybrid_model.classify(conditions, time_limit=0, workers=1)
    check(
        f"{label}: a zero time limit reads timeout (got {late.status})",
        late == hybrid.Classified("timeout", None),
    )
    # A limit below zero is reached too; the solver itself calls it invalid.
    late = said(hybrid_model.classify, conditions, time_limit=-1, workers=1)
    check(
        f"{label}: a time limit below zero reads timeout (got {late!r})",
        late == hybrid.Classified("timeout", None),
    )

# The piece-count condition, alone and together with circles.
two_crosses = {g for g in grids if TWO_CROSSES.holds(g, 4, 4)}
agrees(
    "4x4 with exactly 2 crosses in r2",
    hybrid.Conditions(4, 4, exactly=TWO_CROSSES),
    two_crosses,
)
check("4x4 with exactly 2 crosses in r2: 8 grids", len(two_crosses) == 8)
for names, count in ((("r4c2",), 4), (("r2c4",), 0), (("c1:turn", "c4:turn"), 2)):
    label = f"4x4 with exactly 2 crosses in r2, circles {' '.join(names)}"
    want = {g for g in two_crosses if not hybrid.why_not_hybrid(g, 4, 4, cells(*names))}
    check(f"{label}: the brute force counts {count}", len(want) == count)
    agrees(label, hybrid.Conditions(4, 4, cells(*names), TWO_CROSSES), want)

# One grid for a seed: a brute-force grid that meets the conditions, the same
# one on every run of the seed, and not the same one for every seed.
conditions = hybrid.Conditions(4, 4, cells("r2c2"))
want = {g for g in grids if not hybrid.why_not_hybrid(g, 4, 4, cells("r2c2"))}
sampled = [
    hybrid_model.grid(conditions, random.Random(seed), time_limit=TIME_LIMIT)
    for seed in range(12)
]
check(
    "a grid for a seed: found, and one of the brute-force grids",
    all(s.status == "found" and s.network in want for s in sampled),
)
check(
    "a grid for a seed: the same grid when the seed runs again",
    hybrid_model.grid(conditions, random.Random(3), time_limit=TIME_LIMIT)
    == sampled[3],
)
check(
    f"a grid for a seed: the seeds reach more than one grid "
    f"({len({s.network for s in sampled})})",
    len({s.network for s in sampled}) > 1,
)
check(
    "a grid for a seed: conditions with no grid read infeasible",
    hybrid_model.grid(
        hybrid.Conditions(4, 4, cells("r1c1")), random.Random(0), time_limit=TIME_LIMIT
    )
    == hybrid.Sampled("infeasible", None),
)
check(
    "a grid for a seed: a zero time limit reads timeout",
    hybrid_model.grid(conditions, random.Random(0), time_limit=0)
    == hybrid.Sampled("timeout", None),
)
check(
    "a grid for a seed: a time limit below zero reads timeout",
    said(hybrid_model.grid, conditions, random.Random(0), time_limit=-1)
    == hybrid.Sampled("timeout", None),
)
try:
    hybrid_model.build(hybrid.Conditions(4, 4, frozenset({(-1, -1)})))
    check("a circle on an icon cell is refused", False)
except ValueError as e:
    check("a circle on an icon cell is refused", "off the board" in str(e))

# A circle in a banana, which no 4x4 grid has. On this 5x5 grid, checked
# by hand, r1c2 is a branch (3). Its region is r1c1, r1c2 and r2c1: a turn, the
# branch and a branch, bent, so no rectangle. Round it everything is even: the
# straight at r1c3, the cross at r2c2, the straight at r3c1, and the turn
# numbers of rows 1 and 2 (2, 0) and of columns 1 and 2 (2, 0).
BRANCH_AT = cells("r1c2")
BENT_THREE = network.from_drawing(["┌┬─┬┐", "├┼┬┤│", "│├┘├┤", "├┴┬┼┘", "└─┴┘ "])
board = hybrid.values(BENT_THREE, 5, 5)
check(
    "5x5 bent three: the values round r1c2 as worked by hand",
    [board[0, 0], board[0, 1], board[1, 0]] == [1, 3, 3]
    and [board[0, 2], board[1, 1], board[2, 0]] == [2, 4, 2]
    and [board[0, -1], board[1, -1], board[-1, 0], board[-1, 1]] == [2, 0, 2, 0],
)
check(
    "5x5 bent three: the rule reader passes it with r1c2 circled",
    hybrid.failures(BENT_THREE, 5, 5, BRANCH_AT) == [],
)
got = hybrid_model.classify(
    hybrid.Conditions(5, 5, BRANCH_AT), time_limit=TIME_LIMIT, workers=1
)
check(
    f"5x5, r1c2 circled: exactly one grid, the bent three (got {got.status})",
    got == hybrid.Classified("unique", BENT_THREE),
)
# The same circle beside a piece-count condition. The engine without the
# circle lists every grid with 2 branches in r1; the rule reader says which
# of them the circle keeps.
TWO_BRANCHES_R1 = network.Exactly.parse("2:branch:r1")


def two_branches(net):
    return not hybrid.why_not_hybrid(net, 5, 5) and TWO_BRANCHES_R1.holds(net, 5, 5)


loose = engine_grids(hybrid.Conditions(5, 5, exactly=TWO_BRANCHES_R1), two_branches)
kept = {g for g in loose if not hybrid.why_not_hybrid(g, 5, 5, BRANCH_AT)}
check(
    f"5x5, 2 branches in r1: the rule reader passes every grid ({len(loose)}), "
    f"each with its 2 branches",
    len(loose) > 1 and all(map(two_branches, loose)),
)
check("5x5, 2 branches in r1: the circle keeps the bent three", kept == {BENT_THREE})
agrees(
    "5x5, 2 branches in r1, r1c2 circled",
    hybrid.Conditions(5, 5, BRANCH_AT, TWO_BRANCHES_R1),
    kept,
)


def takes(conditions, net):
    """Whether the engine's model of these conditions allows this grid."""
    built = hybrid_model.build(conditions)
    for e, var in built.edge.items():
        built.m.add(var == (e in net))
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    status = solver.Solve(built.m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE):
        raise RuntimeError(solver.StatusName(status))
    return status != cp_model.INFEASIBLE


# The circle rule where no enumeration reaches. Per grid: every cell the rule
# reader would let be circled, each alone and all at once, and every seventh
# of the others.
refused, wrongly_taken, circled = [], [], 0
for seed in range(3):
    found = hybrid_model.grid(
        hybrid.Conditions(6, 6), random.Random(seed), time_limit=TIME_LIMIT
    ).network
    board = hybrid.values(found, 6, 6)
    size = {cell: len(region) for region in hybrid.regions(board) for cell in region}
    can = {cell for cell in board if board[cell] == size[cell]}
    circled += len(can)
    refused += [
        (seed, sorted(circles))
        for circles in [can, *({cell} for cell in can)]
        if not takes(hybrid.Conditions(6, 6, frozenset(circles)), found)
    ]
    wrongly_taken += [
        (seed, cell)
        for cell in sorted(set(board) - can)[::7]
        if takes(hybrid.Conditions(6, 6, frozenset({cell})), found)
    ]
check(
    f"6x6: the rule reader passes the engine's grids' own circles ({circled})",
    circled > 6,
)
check(
    f"6x6: the engine takes every circle the rule reader does (refused: {refused})",
    not refused,
)
check(
    f"6x6: the engine refuses a circle the rule reader refuses "
    f"(taken: {wrongly_taken})",
    not wrongly_taken,
)

sys.exit(0 if ok else 1)
